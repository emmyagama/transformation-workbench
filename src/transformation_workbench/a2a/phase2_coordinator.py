"""Week 3 Phase 2 coordinator using real local A2A exchanges."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from contextlib import suppress
from typing import Any

import httpx
from a2a.client import (
    A2ACardResolver,
    A2AClientTimeoutError,
    AgentCardResolutionError,
    ClientConfig,
    create_client,
)
from a2a.helpers import get_data_parts, get_message_text, new_data_message
from a2a.types import (
    AgentCard,
    Role,
    SendMessageRequest,
    SendMessageResponse,
    Task,
    TaskState,
)
from pydantic import ValidationError

from .boundary import require_loopback_url
from .contracts import (
    Calculation,
    CoordinatorResult,
    EvidencePack,
    ProtocolTraceEvent,
    SolutionOptions,
)
from .evidence_specialist import EVIDENCE_SKILL_ID
from .solution_designer import SOLUTION_SKILL_ID
from ..security import SafetyError, validate_case_id
from .validation import (
    ContractValidationError,
    validate_evidence_pack,
    validate_solution_options,
    verify_evidence_against_fixture,
)

logger = logging.getLogger(__name__)

AGENT_CARD_PATH = "/.well-known/agent-card.json"
MAX_REQUESTED_CASES = 20
JSON_MEDIA_TYPE = "application/json"

EventHandler = Callable[[ProtocolTraceEvent], None]


class CoordinatorError(RuntimeError):
    """Bounded, explanatory coordinator failure."""

    def __init__(
        self,
        code: str,
        message: str,
        trace: Sequence[ProtocolTraceEvent] = (),
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.trace = tuple(trace)


class Phase2Coordinator:
    """Discover two A2A specialists and validate their typed handoffs."""

    def __init__(
        self,
        evidence_url: str,
        solution_url: str,
        *,
        timeout: float = 10.0,
        max_retries: int = 1,
    ) -> None:
        require_loopback_url(evidence_url)
        require_loopback_url(solution_url)
        if max_retries < 0:
            raise ValueError("max_retries must be zero or greater.")
        self.evidence_url = evidence_url
        self.solution_url = solution_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._cache: dict[str, tuple[str, CoordinatorResult]] = {}
        self._lock = asyncio.Lock()

    async def run(
        self,
        request_id: str,
        case_ids: Sequence[str],
    ) -> CoordinatorResult:
        """Run one bounded evidence-to-options A2A workflow."""
        cleaned_request_id = request_id.strip()
        if not cleaned_request_id:
            raise CoordinatorError(
                "invalid_request",
                "request_id must not be blank.",
            )
        normalized_ids = _normalize_case_ids(case_ids)
        fingerprint = hashlib.sha256(
            f"{cleaned_request_id}:{','.join(normalized_ids)}".encode("utf-8")
        ).hexdigest()

        async with self._lock:
            cached = self._cache.get(cleaned_request_id)
            if cached is not None:
                cached_fingerprint, result = cached
                if cached_fingerprint != fingerprint:
                    raise CoordinatorError(
                        "request_conflict",
                        "Duplicate request_id was replayed with different inputs.",
                        result.trace,
                    )
                return result.model_copy(
                    update={
                        "trace": [
                            *result.trace,
                            ProtocolTraceEvent(
                                step="duplicate_replay",
                                agent="coordinator",
                                method="NONE",
                                path="(cached result)",
                                skill_id="duplicate_request_guard",
                            ),
                        ]
                    }
                )

            result = await self._run_once(cleaned_request_id, normalized_ids)
            self._cache[cleaned_request_id] = (fingerprint, result)
            return result

    async def _run_once(
        self,
        request_id: str,
        case_ids: list[str],
    ) -> CoordinatorResult:
        trace: list[ProtocolTraceEvent] = []

        evidence_card = await self._discover(
            self.evidence_url,
            EVIDENCE_SKILL_ID,
            trace,
        )
        evidence_payload = {"request_id": request_id, "case_ids": case_ids}
        _, evidence_raw = await self._send(
            evidence_card,
            evidence_payload,
            EVIDENCE_SKILL_ID,
            trace,
        )
        pack = _parse_evidence_pack(evidence_raw, trace)
        try:
            validate_evidence_pack(pack, expected_request_id=request_id)
            verify_evidence_against_fixture(pack)
        except ContractValidationError as exc:
            raise CoordinatorError(exc.code, exc.message, trace) from exc
        if (
            set(pack.requested_case_ids) != set(case_ids)
            or len(pack.requested_case_ids) != len(case_ids)
        ):
            raise CoordinatorError(
                "case_set_mismatch",
                "Evidence pack requested case set does not match the "
                "coordinator request.",
                trace,
            )

        solution_card = await self._discover(
            self.solution_url,
            SOLUTION_SKILL_ID,
            trace,
        )
        _, solution_raw = await self._send(
            solution_card,
            pack.model_dump(mode="json"),
            SOLUTION_SKILL_ID,
            trace,
        )
        options = _parse_solution_options(solution_raw, trace)
        try:
            validate_solution_options(options, pack)
        except ContractValidationError as exc:
            raise CoordinatorError(exc.code, exc.message, trace) from exc

        return CoordinatorResult(
            request_id=request_id,
            measured_facts=pack,
            calculations=_calculations(pack),
            assumptions=[
                "Measured facts come only from the read-only synthetic MCP fixture.",
                "SLA targets come from the read-only process-context resource.",
                "Calculations are derived from measured metrics, not new facts.",
                "Recommendations are proposals and are not implemented.",
                *options.assumptions,
            ],
            solution_options=options,
            trace=trace,
        )

    async def _discover(
        self,
        base_url: str,
        expected_skill: str,
        trace: list[ProtocolTraceEvent],
    ) -> AgentCard:
        async def operation() -> AgentCard:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                trust_env=False,
                follow_redirects=False,
            ) as http_client:
                resolver = A2ACardResolver(
                    httpx_client=http_client,
                    base_url=base_url,
                )
                return await resolver.get_agent_card()

        card, attempt = await self._with_retries(
            operation,
            f"discover card for {expected_skill}",
            trace,
        )
        _validate_agent_card(card, expected_skill, trace)
        trace.append(
            ProtocolTraceEvent(
                step="discover_card",
                agent=card.name,
                method="GET",
                path=AGENT_CARD_PATH,
                skill_id=expected_skill,
                attempt=attempt,
            )
        )
        return card

    async def _send(
        self,
        card: AgentCard,
        payload: dict[str, Any],
        expected_skill: str,
        trace: list[ProtocolTraceEvent],
    ) -> tuple[Task, dict[str, Any]]:
        async def operation() -> tuple[Task, dict[str, Any]]:
            return await _send_once(
                card,
                payload,
                self.timeout,
                skill_id=expected_skill,
            )

        (task, artifact), attempt = await self._with_retries(
            operation,
            f"send task to {expected_skill}",
            trace,
        )
        state = TaskState.Name(task.status.state)
        trace.append(
            ProtocolTraceEvent(
                step="send_task",
                agent=card.name,
                method="POST",
                path="/",
                skill_id=expected_skill,
                task_id=task.id,
                context_id=task.context_id,
                state=state,
                attempt=attempt,
            )
        )
        return task, artifact

    async def _with_retries(
        self,
        operation: Callable[[], Awaitable[Any]],
        label: str,
        trace: list[ProtocolTraceEvent],
    ) -> tuple[Any, int]:
        attempts = self.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                result = await asyncio.wait_for(
                    operation(),
                    timeout=self.timeout,
                )
                return result, attempt
            except CoordinatorError:
                raise
            except Exception as exc:
                code = _transient_code(exc)
                if code is None:
                    raise CoordinatorError(
                        "protocol_error",
                        f"Failed to {label} ({type(exc).__name__}).",
                        trace,
                    ) from exc
                if attempt >= attempts:
                    raise CoordinatorError(
                        code,
                        f"Failed to {label} after {attempt} attempt(s): "
                        f"{type(exc).__name__}.",
                        trace,
                    ) from exc
                logger.info(
                    "Retrying %s after transient failure (%s)",
                    label,
                    type(exc).__name__,
                )
        raise CoordinatorError(  # pragma: no cover - loop always returns/raises
            "protocol_error",
            f"Failed to {label} with no attempts.",
            trace,
        )


async def _send_once(
    card: AgentCard,
    payload: dict[str, Any],
    timeout: float,
    *,
    skill_id: str,
) -> tuple[Task, dict[str, Any]]:
    async with httpx.AsyncClient(
        timeout=timeout,
        trust_env=False,
        follow_redirects=False,
    ) as http_client:
        client = await create_client(
            agent=card,
            client_config=ClientConfig(
                streaming=False,
                httpx_client=http_client,
            ),
        )
        try:
            request = SendMessageRequest(
                message=new_data_message(
                    payload,
                    media_type=JSON_MEDIA_TYPE,
                    role=Role.ROLE_USER,
                )
            )
            response: SendMessageResponse | None = None
            async for chunk in client.send_message(request):
                response = chunk
        finally:
            with suppress(Exception):
                await client.close()

    task = _require_task(response, skill_id)
    state = TaskState.Name(task.status.state)
    if state != "TASK_STATE_COMPLETED":
        detail = _status_message(task)
        suffix = f": {detail}" if detail else "."
        raise CoordinatorError(
            "task_failure",
            f"{skill_id} task ended in {state}{suffix}",
        )
    return task, _extract_json_artifact(task, skill_id)


def _require_task(
    response: SendMessageResponse | None,
    skill_id: str,
) -> Task:
    if response is None:
        raise CoordinatorError(
            "non_task_response",
            f"{skill_id} returned no response.",
        )
    if response.WhichOneof("payload") != "task":
        raise CoordinatorError(
            "non_task_response",
            f"{skill_id} returned a message instead of a task.",
        )
    return response.task


def _extract_json_artifact(task: Task, skill_id: str) -> dict[str, Any]:
    for artifact in task.artifacts:
        for part in artifact.parts:
            if part.media_type != JSON_MEDIA_TYPE:
                continue
            if part.WhichOneof("content") == "data":
                data = get_data_parts([part])
                if len(data) != 1 or not isinstance(data[0], dict):
                    raise CoordinatorError(
                        "malformed_result",
                        f"{skill_id} returned an invalid JSON data part.",
                    )
                return data[0]
            if part.WhichOneof("content") == "text":
                try:
                    payload = json.loads(part.text)
                except json.JSONDecodeError as exc:
                    raise CoordinatorError(
                        "malformed_result",
                        f"{skill_id} returned JSON text that did not parse.",
                    ) from exc
                if not isinstance(payload, dict):
                    raise CoordinatorError(
                        "malformed_result",
                        f"{skill_id} returned a non-object JSON artifact.",
                    )
                return payload
    raise CoordinatorError(
        "malformed_result",
        f"{skill_id} returned no application/json artifact.",
    )


def _parse_evidence_pack(
    payload: dict[str, Any],
    trace: list[ProtocolTraceEvent],
) -> EvidencePack:
    try:
        return EvidencePack.model_validate(payload)
    except ValidationError as exc:
        raise CoordinatorError(
            "invalid_evidence_pack",
            _validation_summary(exc),
            trace,
        ) from exc


def _parse_solution_options(
    payload: dict[str, Any],
    trace: list[ProtocolTraceEvent],
) -> SolutionOptions:
    try:
        return SolutionOptions.model_validate(payload)
    except ValidationError as exc:
        raise CoordinatorError(
            "invalid_solution_options",
            _validation_summary(exc),
            trace,
        ) from exc


def _validate_agent_card(
    card: AgentCard,
    expected_skill: str,
    trace: list[ProtocolTraceEvent],
) -> None:
    skills = [skill.id for skill in card.skills]
    if expected_skill not in skills:
        raise CoordinatorError(
            "invalid_agent_card",
            f"Card {card.name!r} does not advertise skill {expected_skill!r}.",
            trace,
        )
    if card.capabilities.streaming:
        raise CoordinatorError(
            "invalid_agent_card",
            f"Card {card.name!r} advertises unexpected streaming.",
            trace,
        )
    interfaces = [
        item
        for item in card.supported_interfaces
        if item.protocol_binding == "JSONRPC"
    ]
    if not interfaces or any(
        item.protocol_version != "1.0" for item in interfaces
    ):
        raise CoordinatorError(
            "invalid_agent_card",
            f"Card {card.name!r} does not advertise JSONRPC protocol 1.0.",
            trace,
        )
    try:
        for interface in card.supported_interfaces:
            require_loopback_url(interface.url)
    except ValueError as exc:
        raise CoordinatorError(
            "invalid_agent_card",
            f"Card {card.name!r} advertises a non-loopback endpoint.",
            trace,
        ) from exc
    if JSON_MEDIA_TYPE not in card.default_input_modes:
        raise CoordinatorError(
            "invalid_agent_card",
            f"Card {card.name!r} does not accept application/json.",
            trace,
        )
    if JSON_MEDIA_TYPE not in card.default_output_modes:
        raise CoordinatorError(
            "invalid_agent_card",
            f"Card {card.name!r} does not emit application/json.",
            trace,
        )


def _calculations(pack: EvidencePack) -> list[Calculation]:
    measurable = _metric(pack, "measurable_closed")
    sla_met = _metric(pack, "sla_met_count")
    input_rows = _metric(pack, "input_rows")
    excluded = _metric(pack, "excluded_count")
    backlog = _metric(pack, "backlog_cases")
    overdue = _metric(pack, "backlog_overdue")

    calculations: list[Calculation] = []
    if measurable is not None and sla_met is not None:
        misses = int(measurable) - int(sla_met)
        calculations.append(
            Calculation(
                calculation_id="calc.sla_misses",
                label="SLA misses among measurable closed cases",
                formula="measurable_closed - sla_met_count",
                value=misses,
                unit="count",
                evidence_ids=["metric.measurable_closed", "metric.sla_met_count"],
            )
        )
    if input_rows and excluded is not None:
        share = round(100 * float(excluded) / float(input_rows), 1)
        calculations.append(
            Calculation(
                calculation_id="calc.excluded_share",
                label="Excluded rows as a share of input rows",
                formula="excluded_count / input_rows * 100",
                value=share,
                unit="percent",
                evidence_ids=["metric.excluded_count", "metric.input_rows"],
            )
        )
    if backlog and overdue is not None:
        share = round(100 * float(overdue) / float(backlog), 1)
        calculations.append(
            Calculation(
                calculation_id="calc.backlog_overdue_share",
                label="Overdue backlog cases as a share of backlog",
                formula="backlog_overdue / backlog_cases * 100",
                value=share,
                unit="percent",
                evidence_ids=["metric.backlog_overdue", "metric.backlog_cases"],
            )
        )
    return calculations


def _metric(pack: EvidencePack, name: str) -> int | float | None:
    fact = pack.metrics.get(name)
    return None if fact is None else fact.value


def _status_message(task: Task) -> str:
    message = task.status.message
    if message is None or not message.parts:
        return ""
    return get_message_text(message).strip()


def _validation_summary(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors()[:3]:
        location = ".".join(str(item) for item in error.get("loc", ()))
        parts.append(f"{location}: {error.get('msg', 'invalid')}")
    return "; ".join(parts) or "Schema validation failed."


def _transient_code(exc: Exception) -> str | None:
    if isinstance(exc, AgentCardResolutionError):
        cause = exc.__cause__
        if isinstance(cause, (httpx.ConnectError, httpx.ConnectTimeout)):
            return "specialist_unavailable"
        if isinstance(cause, httpx.TimeoutException):
            return "a2a_timeout"
        if exc.status_code is None:
            return "specialist_unavailable"
        return None
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
        return "specialist_unavailable"
    if isinstance(
        exc,
        (
            A2AClientTimeoutError,
            httpx.TimeoutException,
            asyncio.TimeoutError,
            TimeoutError,
        ),
    ):
        return "a2a_timeout"
    if isinstance(exc, httpx.TransportError):
        return "specialist_unavailable"
    cause = exc.__cause__
    if isinstance(cause, (httpx.ConnectError, httpx.ConnectTimeout)):
        return "specialist_unavailable"
    if isinstance(cause, (A2AClientTimeoutError, httpx.TimeoutException)):
        return "a2a_timeout"
    return None


def _normalize_case_ids(case_ids: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for value in case_ids:
        raw = str(value).strip()
        if not raw:
            continue
        try:
            cleaned = validate_case_id(raw)
        except SafetyError as exc:
            raise CoordinatorError(exc.code, exc.message) from exc
        if cleaned not in normalized:
            normalized.append(cleaned)
    if len(normalized) > MAX_REQUESTED_CASES:
        raise CoordinatorError(
            "invalid_request",
            f"At most {MAX_REQUESTED_CASES} case IDs are supported.",
        )
    return normalized
