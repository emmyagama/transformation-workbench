"""Deterministic, schema-validated summary rendering for A2A results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .claims import assert_supported_text
from .contracts import (
    REQUIRED_METRIC_FIELDS,
    Calculation,
    CaseObservation,
    CoordinatorResult,
    ProtocolTraceEvent,
    SolutionOption,
)


class SummaryError(ValueError):
    """Raised when a result cannot produce a complete safe summary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class SummaryMetric(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    value: int | float
    unit: str


class CoordinatorSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    request_id: str
    status: Literal["complete"] = "complete"
    discoveries: list[ProtocolTraceEvent]
    task_evidence: list[ProtocolTraceEvent]
    metrics: list[SummaryMetric]
    calculations: list[Calculation]
    assumptions: list[str]
    options: list[SolutionOption]
    limitations: list[str]
    rendered_markdown: str


def render_summary(result: CoordinatorResult) -> CoordinatorSummary:
    """Render a deterministic summary and reject incomplete evidence."""
    if not (
        result.request_id
        == result.measured_facts.request_id
        == result.solution_options.request_id
    ):
        raise SummaryError(
            "request_mismatch",
            "Result request IDs are not correlated.",
        )

    discoveries = [
        event for event in result.trace if event.step == "discover_card"
    ]
    sends = [event for event in result.trace if event.step == "send_task"]
    expected_skills = {"workbench_evidence", "solution_options"}
    if (
        {event.skill_id for event in discoveries} != expected_skills
        or len(discoveries) != 2
    ):
        raise SummaryError(
            "incomplete_trace",
            "Expected one card discovery per specialist.",
        )
    if {event.skill_id for event in sends} != expected_skills or len(sends) != 2:
        raise SummaryError(
            "incomplete_trace",
            "Expected one completed task per specialist.",
        )
    if any(
        event.state != "TASK_STATE_COMPLETED"
        or not event.task_id
        or not event.context_id
        for event in sends
    ):
        raise SummaryError(
            "incomplete_trace",
            "A specialist task is not completed with identifiers.",
        )

    metrics: list[SummaryMetric] = []
    for name in REQUIRED_METRIC_FIELDS:
        fact = result.measured_facts.metrics.get(name)
        if fact is None or fact.value is None:
            raise SummaryError(
                "incomplete_metrics",
                f"Required metric {name!r} is missing.",
            )
        metrics.append(
            SummaryMetric(name=name, value=fact.value, unit=fact.unit)
        )

    if not result.solution_options.options:
        raise SummaryError(
            "incomplete_options",
            "No solution options were returned.",
        )

    limitations = _dedupe(
        [
            "Synthetic data only.",
            "Read-only local workflow.",
            "No hosted model, deployment, or business action.",
            *result.solution_options.limitations,
        ]
    )
    context = result.measured_facts.process_context
    lines = [
        f"# A2A diagnosis: {result.request_id}",
        "",
        "## Protocol evidence",
    ]
    for event in discoveries:
        lines.append(
            f"- {event.skill_id}: card discovered via "
            f"{event.method} {event.path}"
        )
    for event in sends:
        lines.append(
            f"- {event.skill_id}: {event.state} "
            f"(task {event.task_id}, context {event.context_id})"
        )
    lines.extend(
        [
            "",
            "## Data provenance",
            f"- Resource: {context.uri} ({context.mime_type})",
            f"- Snapshot: {context.snapshot}",
            f"- Resource SHA-256: {context.sha256}",
            f"- Source: {context.provenance.source}; "
            f"access: {context.provenance.access}",
        ]
    )
    lines.extend(["", "## Measured baseline"])
    for metric in metrics:
        fact = result.measured_facts.metrics[metric.name]
        lines.append(
            f"- {metric.name}: {_display(metric.value)} {metric.unit} "
            f"(evidence: {fact.evidence_id}; source: {fact.provenance.reference})"
        )
    lines.extend(["", "## Calculations"])
    for calculation in result.calculations:
        lines.append(
            f"- {calculation.label}: {_display(calculation.value)} "
            f"{calculation.unit} ({calculation.formula}; "
            f"evidence: {', '.join(calculation.evidence_ids)})"
        )
    lines.extend(["", "## Data quality and requested cases"])
    for exception in result.measured_facts.exceptions:
        case = exception.case_id or "unknown"
        lines.append(
            f"- Exception {case} row {exception.row_number}: "
            f"{exception.reason} (evidence: {exception.evidence_id}; "
            f"source: {exception.provenance.reference})"
        )
    for observation in result.measured_facts.case_observations:
        case = observation.case_id or "unknown"
        lines.append(
            f"- Case {case} row {observation.row_number}, "
            f"{observation.classification}: {_observation_details(observation)} "
            f"(evidence: {observation.evidence_id}; "
            f"source: {observation.provenance.reference})"
        )
    lines.extend(["", "## Assumptions"])
    for assumption in result.assumptions:
        lines.append(f"- {assumption}")
    lines.extend(["", "## Decision options"])
    for option in result.solution_options.options:
        lines.append(f"- {option.option_id}: {option.title}")
        lines.append(f"  - Description: {option.description}")
        for link in option.rationale:
            lines.append(
                f"  - Rationale: {link.explanation} "
                f"(evidence: {', '.join(link.evidence_ids)})"
            )
        lines.append(f"  - Trade-offs: {'; '.join(option.trade_offs)}")
        lines.append(f"  - Assumptions: {'; '.join(option.assumptions)}")
        lines.append(f"  - Validation: {'; '.join(option.validation_steps)}")
        lines.append(f"  - Limits: {'; '.join(option.limitations)}")
    lines.extend(["", "## Limits"])
    for limitation in limitations:
        lines.append(f"- {limitation}")
    rendered = "\n".join(lines) + "\n"
    assert_supported_text(rendered, "rendered summary")

    return CoordinatorSummary(
        request_id=result.request_id,
        discoveries=discoveries,
        task_evidence=sends,
        metrics=metrics,
        calculations=result.calculations,
        assumptions=result.assumptions,
        options=result.solution_options.options,
        limitations=limitations,
        rendered_markdown=rendered,
    )


def _observation_details(observation: CaseObservation) -> str:
    details: list[str] = []
    for label, value in (
        ("status", observation.status),
        ("priority", observation.priority),
        ("cycle_time_hours", observation.cycle_time_hours),
        ("sla_met", observation.sla_met),
        ("backlog_age_hours", observation.backlog_age_hours),
        ("backlog_overdue", observation.backlog_overdue),
        ("duplicate_of", observation.duplicate_of),
        ("exclusion_reason", observation.exclusion_reason),
    ):
        if value is not None:
            details.append(f"{label}={_display(value)}")
    return ", ".join(details) or "no additional fields"


def _dedupe(values: list[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


def _display(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
