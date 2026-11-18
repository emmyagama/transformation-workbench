"""Read-only MCP evidence collection for the A2A Evidence Specialist."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, Protocol

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import ValidationError

from ..security import SafetyError, validate_case_id
from .contracts import (
    PROCESS_CONTEXT_URI,
    REQUIRED_METRIC_FIELDS,
    EVIDENCE_SOURCE,
    CaseObservation,
    EvidencePack,
    ExceptionRecord,
    MetricFact,
    MissingData,
    ProcessContext,
    Provenance,
    ToolErrorRecord,
)

METRICS_TOOL = "calculate_baseline_metrics"
EXCEPTIONS_TOOL = "list_case_exceptions"
CASE_DETAILS_TOOL = "get_case_details"

METRICS_PROVENANCE = Provenance(
    source=EVIDENCE_SOURCE,
    kind="mcp_tool",
    reference=METRICS_TOOL,
)
EXCEPTIONS_PROVENANCE = Provenance(
    source=EVIDENCE_SOURCE,
    kind="mcp_tool",
    reference=EXCEPTIONS_TOOL,
)
CASE_DETAILS_PROVENANCE = Provenance(
    source=EVIDENCE_SOURCE,
    kind="mcp_tool",
    reference=CASE_DETAILS_TOOL,
)
CONTEXT_PROVENANCE = Provenance(
    source=EVIDENCE_SOURCE,
    kind="mcp_resource",
    reference=PROCESS_CONTEXT_URI,
)

SNAPSHOT_PATTERN = re.compile(r"Snapshot:\s*([^\s]+)")
SLA_BLOCK_PATTERN = re.compile(r"SLA targets:\s*(.+)")
SLA_ITEM_PATTERN = re.compile(r"(P[0-9]+)\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*h")
MAX_REQUESTED_CASES = 20

SessionFactory = Callable[
    [],
    AbstractAsyncContextManager[Any],
]


class EvidenceSourceError(RuntimeError):
    """Bounded, explanatory evidence failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class EvidenceSource(Protocol):
    async def collect(
        self,
        request_id: str,
        case_ids: Sequence[str],
    ) -> EvidencePack: ...


class McpEvidenceSource:
    """Collect evidence by launching the existing MCP server over stdio."""

    def __init__(
        self,
        server_params: StdioServerParameters | None = None,
        *,
        session_factory: SessionFactory | None = None,
        timeout: float = 20.0,
    ) -> None:
        server_env = {}
        if "TRANSFORMATION_WORKBENCH_LOG_LEVEL" in os.environ:
            server_env["TRANSFORMATION_WORKBENCH_LOG_LEVEL"] = os.environ[
                "TRANSFORMATION_WORKBENCH_LOG_LEVEL"
            ]
        self._server_params = server_params or StdioServerParameters(
            command=sys.executable,
            args=["-m", "transformation_workbench.mcp_server"],
            env=server_env,
        )
        self._session_factory = session_factory or self._default_session
        self._timeout = timeout

    @asynccontextmanager
    async def _default_session(self) -> AsyncIterator[ClientSession]:
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def collect(
        self,
        request_id: str,
        case_ids: Sequence[str],
    ) -> EvidencePack:
        normalized_ids = _normalize_case_ids(case_ids)
        if not request_id.strip():
            raise EvidenceSourceError(
                "invalid_request",
                "request_id must not be blank.",
            )
        try:
            async with asyncio.timeout(self._timeout):
                async with self._session_factory() as session:
                    return await self._collect_from_session(
                        session,
                        request_id.strip(),
                        normalized_ids,
                    )
        except EvidenceSourceError:
            raise
        except TimeoutError as exc:
            raise EvidenceSourceError(
                "mcp_timeout",
                "The MCP evidence session timed out.",
            ) from exc
        except Exception as exc:
            raise EvidenceSourceError(
                "mcp_unavailable",
                f"The MCP evidence session failed ({type(exc).__name__}).",
            ) from exc

    async def _collect_from_session(
        self,
        session: Any,
        request_id: str,
        case_ids: list[str],
    ) -> EvidencePack:
        context = await _read_process_context(session)

        metrics_payload = await _call_tool(session, METRICS_TOOL, {})
        metric_status = metrics_payload.get("status")
        if metric_status not in ("ok", "no measurable cases"):
            raise EvidenceSourceError(
                "mcp_tool_error",
                "calculate_baseline_metrics returned an unexpected status.",
            )
        snapshot = metrics_payload.get("snapshot_at")
        if not isinstance(snapshot, str) or not snapshot:
            raise EvidenceSourceError(
                "mcp_tool_error",
                "calculate_baseline_metrics did not return a snapshot.",
            )
        if snapshot != context.snapshot:
            raise EvidenceSourceError(
                "mcp_resource_mismatch",
                "Tool snapshot does not match the process-context snapshot.",
            )

        missing_data: list[MissingData] = []
        metrics: dict[str, MetricFact] = {}
        for name, unit in REQUIRED_METRIC_FIELDS.items():
            raw = metrics_payload.get(name)
            if raw is None:
                missing_data.append(
                    MissingData(
                        field=f"metric.{name}",
                        reason=f"{METRICS_TOOL} returned no value.",
                    )
                )
                value: int | float | None = None
            else:
                try:
                    value = _coerce_metric_value(raw, unit)
                except (TypeError, ValueError) as exc:
                    raise EvidenceSourceError(
                        "mcp_tool_error",
                        f"{METRICS_TOOL} returned a non-numeric {name}.",
                    ) from exc
            metrics[name] = MetricFact(
                evidence_id=f"metric.{name}",
                name=name,
                value=value,
                unit=unit,
                provenance=METRICS_PROVENANCE,
            )

        tool_errors: list[ToolErrorRecord] = []
        exceptions = await _collect_exceptions(
            session,
            missing_data,
            tool_errors,
        )

        observations: list[CaseObservation] = []
        for case_id in case_ids:
            try:
                payload = await _call_tool(
                    session,
                    CASE_DETAILS_TOOL,
                    {"case_id": case_id},
                )
                observations.append(_observation_from_payload(payload))
            except EvidenceSourceError as exc:
                tool_errors.append(
                    ToolErrorRecord(
                        tool=CASE_DETAILS_TOOL,
                        message=exc.message,
                        case_id=case_id,
                    )
                )
                missing_data.append(
                    MissingData(
                        field=f"case.{case_id}",
                        reason=exc.message,
                    )
                )

        digest = hashlib.sha256(
            f"{request_id}:{','.join(case_ids)}".encode("utf-8")
        ).hexdigest()[:16]
        return EvidencePack(
            evidence_pack_id=f"evidence-{digest}",
            request_id=request_id,
            generated_by="workbench-evidence-specialist",
            metric_status=metric_status,
            snapshot=context.snapshot,
            process_context=context,
            metrics=metrics,
            exceptions=exceptions,
            case_observations=observations,
            requested_case_ids=case_ids,
            missing_data=missing_data,
            tool_errors=tool_errors,
        )


async def _read_process_context(session: Any) -> ProcessContext:
    try:
        listing = await session.list_resources()
    except Exception as exc:
        raise EvidenceSourceError(
            "mcp_resource_unavailable",
            "MCP resources/list failed.",
        ) from exc
    available = [str(getattr(item, "uri", "")) for item in listing.resources]
    if PROCESS_CONTEXT_URI not in available:
        raise EvidenceSourceError(
            "mcp_resource_unavailable",
            f"MCP resource {PROCESS_CONTEXT_URI} was not listed.",
        )
    try:
        result = await session.read_resource(PROCESS_CONTEXT_URI)
    except Exception as exc:
        raise EvidenceSourceError(
            "mcp_resource_unavailable",
            f"MCP resources/read failed for {PROCESS_CONTEXT_URI}.",
        ) from exc
    contents = list(result.contents)
    content = next(
        (item for item in contents if getattr(item, "uri", None) == PROCESS_CONTEXT_URI),
        contents[0] if contents else None,
    )
    text = getattr(content, "text", None)
    if not isinstance(text, str) or not text.strip():
        raise EvidenceSourceError(
            "mcp_resource_invalid",
            "Process-context resource returned no text.",
        )
    mime_type = getattr(content, "mime_type", None) or "text/markdown"

    snapshot_match = SNAPSHOT_PATTERN.search(text)
    sla_match = SLA_BLOCK_PATTERN.search(text)
    if snapshot_match is None or sla_match is None:
        raise EvidenceSourceError(
            "mcp_resource_invalid",
            "Process-context text is missing snapshot or SLA metadata.",
        )
    sla_targets = {
        name: float(value) for name, value in SLA_ITEM_PATTERN.findall(sla_match.group(1))
    }
    if not sla_targets:
        raise EvidenceSourceError(
            "mcp_resource_invalid",
            "Process-context text has no parsable SLA targets.",
        )
    if "synthetic" not in text.lower() or "read-only" not in text.lower():
        raise EvidenceSourceError(
            "mcp_resource_invalid",
            "Process-context text does not state the synthetic/read-only policy.",
        )

    return ProcessContext(
        uri=PROCESS_CONTEXT_URI,
        mime_type=str(mime_type),
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        text=text,
        snapshot=snapshot_match.group(1),
        sla_targets=sla_targets,
        synthetic_only=True,
        read_only=True,
        provenance=CONTEXT_PROVENANCE,
    )


async def _collect_exceptions(
    session: Any,
    missing_data: list[MissingData],
    tool_errors: list[ToolErrorRecord],
) -> list[ExceptionRecord]:
    try:
        payload = await _call_tool(session, EXCEPTIONS_TOOL, {})
    except EvidenceSourceError as exc:
        tool_errors.append(
            ToolErrorRecord(tool=EXCEPTIONS_TOOL, message=exc.message)
        )
        missing_data.append(
            MissingData(field="exceptions", reason=exc.message)
        )
        return []

    raw_exceptions = payload.get("exceptions")
    if not isinstance(raw_exceptions, list):
        tool_errors.append(
            ToolErrorRecord(
                tool=EXCEPTIONS_TOOL,
                message="Tool returned no exception list.",
            )
        )
        missing_data.append(
            MissingData(
                field="exceptions",
                reason="Tool returned no exception list.",
            )
        )
        return []

    records: list[ExceptionRecord] = []
    try:
        for item in raw_exceptions:
            row_number = int(item["row_number"])
            records.append(
                ExceptionRecord(
                    evidence_id=f"exception.row.{row_number}",
                    case_id=item.get("case_id"),
                    row_number=row_number,
                    reason=str(item.get("reason", "")),
                    provenance=EXCEPTIONS_PROVENANCE,
                )
            )
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        message = f"{EXCEPTIONS_TOOL} returned an invalid exception row."
        tool_errors.append(
            ToolErrorRecord(tool=EXCEPTIONS_TOOL, message=message)
        )
        missing_data.append(MissingData(field="exceptions", reason=message))
        return []
    return records


async def _call_tool(
    session: Any,
    tool: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    try:
        result = await session.call_tool(tool, arguments)
    except Exception as exc:
        raise EvidenceSourceError(
            "mcp_tool_error",
            f"{tool} raised {type(exc).__name__}.",
        ) from exc
    if getattr(result, "is_error", False):
        detail = _content_text(result)
        raise EvidenceSourceError(
            "mcp_tool_error",
            f"{tool} returned an error{': ' + detail if detail else '.'}",
        )
    payload = _structured_payload(result)
    if not isinstance(payload, dict):
        raise EvidenceSourceError(
            "mcp_tool_error",
            f"{tool} returned no structured object.",
        )
    return payload


def _structured_payload(result: Any) -> Any:
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured
    text = _content_text(result)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _content_text(result: Any) -> str:
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def _observation_from_payload(payload: dict[str, Any]) -> CaseObservation:
    try:
        return CaseObservation(
            evidence_id=_case_evidence_id(payload),
            case_id=payload.get("case_id"),
            row_number=int(payload["row_number"]),
            classification=payload["classification"],
            status=payload.get("status"),
            priority=payload.get("priority"),
            received_at=payload.get("received_at"),
            acknowledged_at=payload.get("acknowledged_at"),
            closed_at=payload.get("closed_at"),
            rework_count=payload.get("rework_count"),
            duplicate_of=payload.get("duplicate_of"),
            exclusion_reason=payload.get("exclusion_reason"),
            cycle_time_hours=payload.get("cycle_time_hours"),
            sla_target_hours=payload.get("sla_target_hours"),
            sla_met=payload.get("sla_met"),
            backlog_age_hours=payload.get("backlog_age_hours"),
            backlog_overdue=payload.get("backlog_overdue"),
            provenance=CASE_DETAILS_PROVENANCE,
        )
    except (KeyError, TypeError, ValidationError) as exc:
        raise EvidenceSourceError(
            "mcp_tool_error",
            f"{CASE_DETAILS_TOOL} returned an invalid observation.",
        ) from exc


def _case_evidence_id(payload: dict[str, Any]) -> str:
    case_id = payload.get("case_id")
    if isinstance(case_id, str) and case_id:
        return f"case.{case_id}"
    return f"case.row.{int(payload['row_number'])}"


def _coerce_metric_value(raw: Any, unit: str) -> int | float:
    if unit == "count":
        if isinstance(raw, bool):
            raise EvidenceSourceError(
                "mcp_tool_error",
                "A count metric returned a boolean.",
            )
        if isinstance(raw, float) and raw.is_integer():
            return int(raw)
        if isinstance(raw, int):
            return raw
        return int(raw)
    return float(raw)


def _normalize_case_ids(case_ids: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for value in case_ids:
        raw = str(value).strip()
        if not raw:
            continue
        try:
            cleaned = validate_case_id(raw)
        except SafetyError as exc:
            raise EvidenceSourceError("invalid_request", exc.message) from exc
        if cleaned not in normalized:
            normalized.append(cleaned)
    if len(normalized) > MAX_REQUESTED_CASES:
        raise EvidenceSourceError(
            "invalid_request",
            f"At most {MAX_REQUESTED_CASES} case IDs are supported.",
        )
    return normalized
