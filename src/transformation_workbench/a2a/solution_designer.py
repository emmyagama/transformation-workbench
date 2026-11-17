"""A2A Solution Designer that only transforms a validated EvidencePack."""

from __future__ import annotations

import json
import logging

from a2a.helpers import (
    get_data_parts,
    get_message_text,
    new_data_part,
    new_task_from_user_message,
    new_text_message,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Role,
)
from pydantic import ValidationError
from starlette.applications import Starlette

from .boundary import require_loopback_url
from .contracts import (
    EvidencePack,
    RationaleLink,
    SolutionOption,
    SolutionOptions,
)
from .validation import ContractValidationError, validate_evidence_pack

logger = logging.getLogger(__name__)

SOLUTION_DESIGNER_NAME = "Workbench Solution Designer"
SOLUTION_DESIGNER_VERSION = "0.2.0"
SOLUTION_SKILL_ID = "solution_options"
SOLUTION_ARTIFACT_NAME = "solution_options"
SOLUTION_GENERATOR = "workbench-solution-designer"


class SolutionDesignError(RuntimeError):
    """Bounded, explanatory solution-design failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class SolutionExecutor(AgentExecutor):
    """Return deterministic options tied to validated evidence identifiers."""

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task = context.current_task
        if task is None:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.start_work(
            message=new_text_message(
                "Designing options from the validated evidence pack.",
                role=Role.ROLE_AGENT,
            )
        )
        try:
            pack = parse_evidence_pack(context.message)
            validate_evidence_pack(pack)
            options = design_options(pack)
        except (SolutionDesignError, ContractValidationError, ValueError) as exc:
            code = getattr(exc, "code", "invalid_evidence_pack")
            message = getattr(exc, "message", str(exc))
            logger.warning("Solution task failed: %s", code)
            await updater.failed(
                message=new_text_message(
                    f"Solution design failed: {code}: {message}",
                    role=Role.ROLE_AGENT,
                )
            )
            return
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.warning("Solution task failed: %s", type(exc).__name__)
            await updater.failed(
                message=new_text_message(
                    "Solution design failed: internal_error.",
                    role=Role.ROLE_AGENT,
                )
            )
            return

        await updater.add_artifact(
            parts=[
                new_data_part(
                    options.model_dump(mode="json"),
                    media_type="application/json",
                )
            ],
            name=SOLUTION_ARTIFACT_NAME,
        )
        await updater.complete(
            message=new_text_message(
                "Solution options completed.",
                role=Role.ROLE_AGENT,
            )
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task = context.current_task
        if task is None:
            return
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.cancel(
            message=new_text_message(
                "Solution design cancelled.",
                role=Role.ROLE_AGENT,
            )
        )


def parse_evidence_pack(message: object) -> EvidencePack:
    """Read an EvidencePack from a data or JSON-text A2A message."""
    payload: object | None = None
    data_parts = get_data_parts(message.parts)
    if data_parts:
        payload = data_parts[0]
    if payload is None:
        text = get_message_text(message).strip()
        if not text:
            raise SolutionDesignError(
                "invalid_evidence_pack",
                "Solution request carried no EvidencePack.",
            )
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SolutionDesignError(
                "invalid_evidence_pack",
                "Solution request was not valid JSON.",
            ) from exc
    try:
        return EvidencePack.model_validate(payload)
    except ValidationError as exc:
        raise SolutionDesignError(
            "invalid_evidence_pack",
            _validation_summary(exc),
        ) from exc


def design_options(pack: EvidencePack) -> SolutionOptions:
    """Build deterministic, evidence-linked options without outcomes claims."""
    options: list[SolutionOption] = []

    backlog_cases = _metric(pack, "backlog_cases")
    overdue = _metric(pack, "backlog_overdue")
    sla_percent = _metric(pack, "sla_met_percent")
    if backlog_cases is not None and overdue is not None and sla_percent is not None:
        options.append(
            SolutionOption(
                option_id="option-triage-backlog",
                title="Triage overdue backlog cases against published SLA targets",
                description=(
                    "Review overdue backlog cases in a fixed order before "
                    "considering any process change. This is a proposal, not a "
                    "measured outcome."
                ),
                rationale=[
                    RationaleLink(
                        evidence_ids=[
                            "metric.backlog_cases",
                            "metric.backlog_overdue",
                            "metric.sla_met_percent",
                        ],
                        explanation=(
                            f"The pack records {_display(backlog_cases)} backlog "
                            f"cases, {_display(overdue)} overdue, and "
                            f"{_display(sla_percent)}% SLA attainment."
                        ),
                    )
                ],
                trade_offs=[
                    "Manual triage consumes reviewer time.",
                    "Ordering by SLA risk can delay lower-risk cases.",
                ],
                assumptions=[
                    "The SLA targets in the read-only process context remain authoritative."
                ],
                validation_steps=[
                    "Recompute the baseline with the same synthetic fixture "
                    "and compare every metric value.",
                    "Confirm each recommendation references an evidence ID "
                    "present in the pack.",
                ],
                limitations=[
                    "This option is a proposal and has not been implemented.",
                    "No financial or productivity outcome is quantified.",
                ],
            )
        )

    excluded_count = _metric(pack, "excluded_count")
    if excluded_count is not None:
        exception_ids = [item.evidence_id for item in pack.exceptions]
        evidence_ids = ["metric.excluded_count", *exception_ids]
        options.append(
            SolutionOption(
                option_id="option-data-quality",
                title="Resolve data-quality exclusions before automation design",
                description=(
                    "Treat excluded rows as a data-quality workstream so later "
                    "automation is not designed against incomplete records."
                ),
                rationale=[
                    RationaleLink(
                        evidence_ids=evidence_ids,
                        explanation=(
                            f"The pack reports {_display(excluded_count)} excluded "
                            "rows, each with a reason and tool provenance."
                        ),
                    )
                ],
                trade_offs=[
                    "Remediation work precedes any automation design.",
                    "Some exclusions may be legitimate duplicates that only need documentation.",
                ],
                assumptions=[
                    "Excluded rows describe data quality, not process performance."
                ],
                validation_steps=[
                    "Re-run list_case_exceptions and confirm each reason is still present.",
                    "Inspect repaired rows with get_case_details before including them in metrics.",
                ],
                limitations=[
                    "No claim is made that exclusions will disappear.",
                    "This option is a proposal and has not been implemented.",
                ],
            )
        )

    rework_cases = _metric(pack, "rework_cases")
    rework_rate = _metric(pack, "rework_rate_percent")
    rework_volume = _metric(pack, "rework_volume")
    if (
        rework_cases is not None
        and rework_rate is not None
        and rework_volume is not None
        and float(rework_cases) > 0
    ):
        options.append(
            SolutionOption(
                option_id="option-rework-review",
                title="Review rework cases for recurring handling steps",
                description=(
                    "Use the measured rework counts to scope a manual review of "
                    "repeated handling. The option does not assume a root cause."
                ),
                rationale=[
                    RationaleLink(
                        evidence_ids=[
                            "metric.rework_cases",
                            "metric.rework_rate_percent",
                            "metric.rework_volume",
                        ],
                        explanation=(
                            f"The pack records {_display(rework_cases)} rework "
                            f"cases at {_display(rework_rate)}%, with "
                            f"{_display(rework_volume)} rework events."
                        ),
                    )
                ],
                trade_offs=[
                    "Reviewing rework may duplicate existing quality checks.",
                    "Root-cause conclusions require evidence outside this pack.",
                ],
                assumptions=[
                    "Rework count is a measured field from the fixed synthetic fixture."
                ],
                validation_steps=[
                    "Confirm rework counts by re-running calculate_baseline_metrics.",
                    "Inspect individual cases with get_case_details before drawing conclusions.",
                ],
                limitations=[
                    "The pack does not identify root causes.",
                    "This option is a proposal and has not been implemented.",
                ],
            )
        )

    if not options:
        options.append(
            SolutionOption(
                option_id="option-evidence-review",
                title="Review evidence completeness before proposing changes",
                description=(
                    "The pack does not contain enough non-null metrics to frame a "
                    "process option safely."
                ),
                rationale=[
                    RationaleLink(
                        evidence_ids=["context", "snapshot"],
                        explanation=(
                            "The process context and snapshot remain the only "
                            "available measured references."
                        ),
                    )
                ],
                trade_offs=[
                    "Deferring options avoids inventing unsupported findings."
                ],
                assumptions=[
                    "Absent metrics must not be replaced from memory."
                ],
                validation_steps=[
                    "Repair the evidence source and re-run the workflow."
                ],
                limitations=[
                    "No process option is proposed in this fallback."
                ],
            )
        )

    return SolutionOptions(
        request_id=pack.request_id,
        evidence_pack_id=pack.evidence_pack_id,
        generated_by=SOLUTION_GENERATOR,
        options=options,
        assumptions=[
            "The evidence pack is the only input to this designer.",
            "Options are proposals and are not measured facts.",
        ],
        limitations=[
            "No financial quantification is included.",
            "No external action is requested or performed.",
        ],
    )


def _metric(pack: EvidencePack, name: str) -> int | float | None:
    fact = pack.metrics.get(name)
    return None if fact is None else fact.value


def _display(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _validation_summary(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors()[:3]:
        location = ".".join(str(item) for item in error.get("loc", ()))
        parts.append(f"{location}: {error.get('msg', 'invalid')}")
    return "; ".join(parts) or "EvidencePack failed schema validation."


def build_agent_card(base_url: str) -> AgentCard:
    """Build the narrow loopback Agent Card for the Solution Designer."""
    require_loopback_url(base_url)
    return AgentCard(
        name=SOLUTION_DESIGNER_NAME,
        description=(
            "Deterministic Solution Designer that consumes only a validated "
            "EvidencePack. It returns evidence-linked options with trade-offs, "
            "assumptions, and validation steps. It never retrieves process data "
            "or requests an action."
        ),
        version=SOLUTION_DESIGNER_VERSION,
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
        ),
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                url=base_url,
                protocol_version="1.0",
            )
        ],
        skills=[
            AgentSkill(
                id=SOLUTION_SKILL_ID,
                name="Solution options",
                description=(
                    "Transforms a validated EvidencePack into deterministic "
                    "options tied to evidence IDs, with trade-offs and validation "
                    "steps."
                ),
                tags=["week3", "phase2", "options", "deterministic", "synthetic"],
                examples=["Design options from the supplied EvidencePack."],
                input_modes=["application/json"],
                output_modes=["application/json"],
            )
        ],
    )


def build_app(base_url: str) -> Starlette:
    """Build a loopback Starlette app serving the card and JSON-RPC."""
    agent_card = build_agent_card(base_url)
    request_handler = DefaultRequestHandler(
        agent_executor=SolutionExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    routes = create_agent_card_routes(agent_card)
    routes.extend(create_jsonrpc_routes(request_handler, "/"))
    return Starlette(routes=routes)
