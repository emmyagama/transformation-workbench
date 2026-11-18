"""Deterministic end-to-end report for the synthetic Workbench demo."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .a2a.claims import assert_supported_text
from .a2a.contracts import (
    Calculation,
    CaseObservation,
    ExceptionRecord,
    ProtocolTraceEvent,
    SolutionOption,
)
from .a2a.summary import CoordinatorSummary, SummaryMetric, render_summary
from .approval import ApprovalCheckpoint, ApprovalGate
from .intake import IntakeRequest


class ReportError(ValueError):
    """Raised when an end-to-end report cannot be assembled safely."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str
    label: str
    source: str
    reference: str
    kind: str


class FutureStateStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step_id: str
    title: str
    description: str
    status: Literal["proposed"] = "proposed"
    evidence_ids: list[str]


class RiskItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    risk_id: str
    description: str
    severity: Literal["low", "medium", "high"]
    mitigation: str
    evidence_ids: list[str] = Field(min_length=1)


class RoadmapItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    priority: int = Field(ge=1)
    title: str
    description: str
    status: Literal["proposed"] = "proposed"
    evidence_ids: list[str] = Field(min_length=1)


class TransformationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    status: Literal["complete"] = "complete"
    request_id: str
    intake: IntakeRequest
    approval: ApprovalCheckpoint
    executive_brief: str
    observations: list[str]
    metrics: list[SummaryMetric]
    calculations: list[Calculation]
    exceptions: list[ExceptionRecord]
    case_observations: list[CaseObservation]
    future_state: list[FutureStateStep]
    automation_opportunities: list[SolutionOption]
    risks: list[RiskItem]
    assumptions: list[str]
    roadmap: list[RoadmapItem]
    evidence_appendix: list[EvidenceReference]
    limitations: list[str]
    protocol_trace: list[ProtocolTraceEvent]
    rendered_markdown: str


def build_report(
    intake: IntakeRequest,
    result: object,
    gate: ApprovalGate,
) -> TransformationReport:
    """Build one deterministic report from a validated coordinator result."""
    from .a2a.contracts import CoordinatorResult

    if not isinstance(result, CoordinatorResult):
        raise ReportError("invalid_result", "Expected a CoordinatorResult.")
    if intake.request_id != result.request_id:
        raise ReportError(
            "request_mismatch",
            "Intake request ID does not match the coordinator result.",
        )
    if gate.request_id != intake.request_id:
        raise ReportError(
            "approval_mismatch",
            "Approval checkpoint does not match the intake request.",
        )

    summary = render_summary(result)
    observations = _observations(summary)
    appendix = _evidence_appendix(result, summary, gate)
    future_state = _future_state(result)
    risks = _risks(result)
    assumptions = _assumptions(result)
    limitations = _limitations(summary)
    roadmap = _roadmap(result)
    executive_brief = _executive_brief(intake, summary, result)

    report = TransformationReport(
        request_id=intake.request_id,
        intake=intake,
        approval=gate.checkpoint(),
        executive_brief=executive_brief,
        observations=observations,
        metrics=summary.metrics,
        calculations=result.calculations,
        exceptions=result.measured_facts.exceptions,
        case_observations=result.measured_facts.case_observations,
        future_state=future_state,
        automation_opportunities=result.solution_options.options,
        risks=risks,
        assumptions=assumptions,
        roadmap=roadmap,
        evidence_appendix=appendix,
        limitations=limitations,
        protocol_trace=result.trace,
        rendered_markdown="",
    )
    rendered = _render(report)
    guard_text = rendered
    for value, marker in (
        (intake.process_name, "[process name]"),
        (intake.desired_outcome, "[requested outcome]"),
    ):
        guard_text = guard_text.replace(value, marker)
    approval_note = gate.checkpoint().note
    if approval_note:
        guard_text = guard_text.replace(approval_note, "[review note]")
    assert_supported_text(guard_text, "rendered report")
    return report.model_copy(update={"rendered_markdown": rendered})


def _executive_brief(
    intake: IntakeRequest,
    summary: CoordinatorSummary,
    result: object,
) -> str:
    from .a2a.contracts import CoordinatorResult

    assert isinstance(result, CoordinatorResult)
    metrics = _metric_values(summary)
    exceptions = result.measured_facts.exceptions
    exception_detail = _exception_detail(exceptions)
    return (
        f"The synthetic fixture contains {_display(metrics['input_rows'])} input "
        f"rows. {_display(metrics['measurable_closed'])} closed cases are "
        f"measurable; {_display(metrics['sla_met_count'])} met their SLA target "
        f"({_display(metrics['sla_met_percent'])}%), and "
        f"{_display(_sla_misses(metrics))} missed. Mean cycle time is "
        f"{_display(metrics['mean_cycle_time_hours'])} hours and median cycle "
        f"time is {_display(metrics['median_cycle_time_hours'])} hours. "
        f"{_display(metrics['rework_cases'])} measurable cases had rework "
        f"({_display(metrics['rework_rate_percent'])}%), with "
        f"{_display(metrics['rework_volume'])} rework events. At the snapshot, "
        f"backlog is {_display(metrics['backlog_cases'])} cases; "
        f"{_display(metrics['backlog_overdue'])} overdue. "
        f"{len(exceptions)} rows are excluded for data-quality reasons"
        f"{exception_detail}.\n\n"
        "The evidence supports a review of backlog triage, data quality, and "
        "rework handling. It does not establish root cause or quantify any "
        "future outcome. The proposed future-state workflow keeps calculations "
        "deterministic and pauses at a human approval checkpoint. No external "
        "network, write, or business action exists in this demo.\n\n"
        f"Requested outcome: {intake.desired_outcome}"
    )


def _observations(summary: CoordinatorSummary) -> list[str]:
    metrics = _metric_values(summary)
    return [
        f"{_display(metrics['input_rows'])} synthetic input rows.",
        (
            f"{_display(metrics['measurable_closed'])} measurable closed cases; "
            f"{_display(metrics['sla_met_count'])} met SLA "
            f"({_display(metrics['sla_met_percent'])}%)."
        ),
        (
            f"Mean cycle time {_display(metrics['mean_cycle_time_hours'])} hours; "
            f"median {_display(metrics['median_cycle_time_hours'])} hours."
        ),
        (
            f"Rework: {_display(metrics['rework_cases'])} cases "
            f"({_display(metrics['rework_rate_percent'])}%), "
            f"{_display(metrics['rework_volume'])} events."
        ),
        (
            f"Backlog: {_display(metrics['backlog_cases'])} cases; "
            f"{_display(metrics['backlog_overdue'])} overdue at the snapshot."
        ),
        (
            f"Excluded rows: {_display(metrics['excluded_count'])}; "
            "each has a recorded reason and tool provenance."
        ),
    ]


def _future_state(result: object) -> list[FutureStateStep]:
    from .a2a.contracts import CoordinatorResult

    assert isinstance(result, CoordinatorResult)
    option_evidence = _dedupe(
        [
            evidence_id
            for option in result.solution_options.options
            for link in option.rationale
            for evidence_id in link.evidence_ids
        ]
    )
    return [
        FutureStateStep(
            step_id="future.intake",
            title="Validate the request before analysis",
            description=(
                "Capture the synthetic request, desired outcome, and bounded "
                "case IDs. Reject path-like selectors and instruction-injection "
                "text before the workflow starts."
            ),
            evidence_ids=["context", "assumption.synthetic_only"],
        ),
        FutureStateStep(
            step_id="future.evidence",
            title="Assemble a provenance-linked evidence pack",
            description=(
                "Use read-only MCP tools for metrics, exceptions, and case "
                "details. Keep source references and the fixed snapshot."
            ),
            evidence_ids=[
                "context",
                "snapshot",
                "metric.input_rows",
                "metric.excluded_count",
            ],
        ),
        FutureStateStep(
            step_id="future.calculate",
            title="Calculate the baseline in deterministic code",
            description=(
                "Derive throughput, delay, rework, and exception measures from "
                "the validated fixture. Do not replace measured values with "
                "model prose."
            ),
            evidence_ids=_metric_evidence_ids(),
        ),
        FutureStateStep(
            step_id="future.review",
            title="Review evidence-linked options with a human owner",
            description=(
                "Present only options whose rationale references known evidence "
                "IDs. Keep trade-offs, assumptions, validation steps, and "
                "limits visible."
            ),
            evidence_ids=option_evidence or ["context"],
        ),
        FutureStateStep(
            step_id="future.approval",
            title="Pause at the human approval checkpoint",
            description=(
                "Stop at a pending review state. The demo has no external "
                "network, write, or business action endpoint to call."
            ),
            evidence_ids=["assumption.no_consequential_action"],
        ),
    ]


def _risks(result: object) -> list[RiskItem]:
    from .a2a.contracts import CoordinatorResult

    assert isinstance(result, CoordinatorResult)
    exception_ids = [item.evidence_id for item in result.measured_facts.exceptions]
    measurable = int(result.measured_facts.metrics["measurable_closed"].value or 0)
    sla_met = int(result.measured_facts.metrics["sla_met_count"].value or 0)
    backlog = int(result.measured_facts.metrics["backlog_cases"].value or 0)
    overdue = int(result.measured_facts.metrics["backlog_overdue"].value or 0)
    return [
        RiskItem(
            risk_id="risk.data_quality",
            description=(
                "Excluded source rows can hide missing or contradictory data. "
                "A future workflow must not treat the baseline as complete until "
                "the exclusions are reviewed."
            ),
            severity="high",
            mitigation=(
                "Review each exclusion with the process owner and keep the "
                "reason and provenance visible in the report."
            ),
            evidence_ids=["metric.excluded_count", *exception_ids],
        ),
        RiskItem(
            risk_id="risk.sla_gap",
            description=(
                f"{measurable - sla_met} measurable cases missed their SLA "
                "target. The fixture does not establish why."
            ),
            severity="medium",
            mitigation=(
                "Inspect the affected cases and validate any proposed cause "
                "against additional evidence rather than assuming one."
            ),
            evidence_ids=["metric.sla_met_count", "metric.measurable_closed"],
        ),
        RiskItem(
            risk_id="risk.backlog",
            description=(
                f"{overdue} of {backlog} backlog cases is overdue at the fixed "
                "snapshot. Backlog age can change after the snapshot."
            ),
            severity="medium",
            mitigation=(
                "Recompute backlog age with a fresh, approved snapshot before "
                "using the measure for a decision."
            ),
            evidence_ids=["metric.backlog_cases", "metric.backlog_overdue"],
        ),
        RiskItem(
            risk_id="risk.synthetic",
            description=(
                "The packaged fixture is synthetic and small. It cannot support "
                "claims about a real operation or its outcomes."
            ),
            severity="medium",
            mitigation=(
                "Label every demo result as synthetic and require new evidence "
                "before any real-world use."
            ),
            evidence_ids=["assumption.synthetic_only"],
        ),
        RiskItem(
            risk_id="risk.approval",
            description=(
                "The approval checkpoint is a review state, not an action "
                "authorization. A future integration would need a separate, "
                "enforceable write gate."
            ),
            severity="high",
            mitigation=(
                "Define action scope, reviewer identity, audit records, and "
                "rollback before connecting any write path."
            ),
            evidence_ids=["assumption.no_consequential_action"],
        ),
        RiskItem(
            risk_id="risk.untrusted_input",
            description=(
                "Intake text can contain instruction-injection or path-like "
                "content. Evidence text is fixed and hash-verified."
            ),
            severity="low",
            mitigation=(
                "Reject unsafe intake text, validate case IDs, and keep the "
                "evidence source read-only and fixture-bound."
            ),
            evidence_ids=["assumption.safe_intake"],
        ),
    ]


def _assumptions(result: object) -> list[str]:
    from .a2a.contracts import CoordinatorResult

    assert isinstance(result, CoordinatorResult)
    return _dedupe(
        [
            *result.assumptions,
            "All inputs are synthetic; the fixture is fixed and packaged with the demo.",
            "The deterministic report is the authoritative user-facing output.",
            "The local model prose is not part of the authoritative report path.",
            "Approval is a demo review state; no external network, write, or "
            "business action exists.",
            "No financial outcome or enterprise deployment is claimed.",
        ]
    )


def _limitations(summary: CoordinatorSummary) -> list[str]:
    return _dedupe(
        [
            *summary.limitations,
            "The fixture is not a real operation and cannot support generalization.",
            "Root causes are not established by the baseline measures.",
            "The approval checkpoint is not connected to a business system.",
            "The report is a demo, not a deployable service.",
            "The local 3B model prose remains unreliable and is excluded from this path.",
        ]
    )


def _roadmap(result: object) -> list[RoadmapItem]:
    from .a2a.contracts import CoordinatorResult

    assert isinstance(result, CoordinatorResult)
    first_option = (
        result.solution_options.options[0].rationale[0].evidence_ids
        if result.solution_options.options
        else ["context"]
    )
    return [
        RoadmapItem(
            priority=1,
            title="Confirm the baseline and data-quality exclusions",
            description=(
                "Walk through the measured baseline and every excluded row with "
                "the process owner. Confirm the snapshot and SLA targets."
            ),
            evidence_ids=["metric.input_rows", "metric.excluded_count"],
        ),
        RoadmapItem(
            priority=2,
            title="Review the evidence-linked options",
            description=(
                "Select, reject, or defer each proposed option. Keep the "
                "rationale and trade-offs attached to the decision."
            ),
            evidence_ids=first_option,
        ),
        RoadmapItem(
            priority=3,
            title="Define the action gate before any integration",
            description=(
                "Specify write scope, reviewer identity, audit records, and "
                "rollback. No action path exists in the current demo."
            ),
            evidence_ids=["assumption.no_consequential_action"],
        ),
        RoadmapItem(
            priority=4,
            title="If approved, run a bounded pilot and re-measure",
            description=(
                "Use the same deterministic method on a new approved snapshot. "
                "Do not compare the pilot with an unvalidated forecast."
            ),
            evidence_ids=["context", "snapshot"],
        ),
    ]


def _evidence_appendix(
    result: object,
    summary: CoordinatorSummary,
    gate: ApprovalGate,
) -> list[EvidenceReference]:
    from .a2a.contracts import CoordinatorResult

    assert isinstance(result, CoordinatorResult)
    context = result.measured_facts.process_context
    appendix = [
        EvidenceReference(
            evidence_id="context",
            label=f"Process context {context.uri}",
            source=context.provenance.source,
            reference=context.provenance.reference,
            kind=context.provenance.kind,
        ),
        EvidenceReference(
            evidence_id="snapshot",
            label=f"Snapshot {context.snapshot}",
            source=context.provenance.source,
            reference=context.provenance.reference,
            kind=context.provenance.kind,
        ),
    ]
    for metric in summary.metrics:
        fact = result.measured_facts.metrics[metric.name]
        appendix.append(
            EvidenceReference(
                evidence_id=fact.evidence_id,
                label=(
                    f"{metric.name} = {_display(metric.value)} {metric.unit}"
                ),
                source=fact.provenance.source,
                reference=fact.provenance.reference,
                kind=fact.provenance.kind,
            )
        )
    for item in result.measured_facts.exceptions:
        appendix.append(
            EvidenceReference(
                evidence_id=item.evidence_id,
                label=(
                    f"Exception {item.case_id or 'unknown'} row "
                    f"{item.row_number}: {item.reason}"
                ),
                source=item.provenance.source,
                reference=item.provenance.reference,
                kind=item.provenance.kind,
            )
        )
    for item in result.measured_facts.case_observations:
        appendix.append(
            EvidenceReference(
                evidence_id=item.evidence_id,
                label=(
                    f"Case {item.case_id or 'unknown'} row {item.row_number}: "
                    f"{item.classification}"
                ),
                source=item.provenance.source,
                reference=item.provenance.reference,
                kind=item.provenance.kind,
            )
        )
    for option in result.solution_options.options:
        appendix.append(
            EvidenceReference(
                evidence_id=f"recommendation.{option.option_id}",
                label=option.title,
                source=result.solution_options.generated_by,
                reference=option.option_id,
                kind="recommendation",
            )
        )
    for evidence_id, label in (
        ("assumption.synthetic_only", "All inputs are synthetic."),
        ("assumption.safe_intake", "Intake and case IDs are bounded and checked."),
        (
            "assumption.no_consequential_action",
            "No external network, write, or business action exists.",
        ),
    ):
        appendix.append(
            EvidenceReference(
                evidence_id=evidence_id,
                label=label,
                source="transformation-workbench",
                reference="report-policy",
                kind="assumption",
            )
        )
    appendix.append(
        EvidenceReference(
            evidence_id="approval.checkpoint",
            label=f"Approval state: {gate.status.value}",
            source="transformation-workbench",
            reference="approval-gate",
            kind="policy",
        )
    )
    return appendix


def _render(report: TransformationReport) -> str:
    lines = [
        "# Transformation Workbench decision brief",
        "",
        "**Synthetic-data demonstration.** No real business, customer, or "
        "personal data is used. This report is not a production service.",
        "",
        f"- Request: `{report.request_id}`",
        f"- Process: {report.intake.process_name}",
        f"- Desired outcome: {report.intake.desired_outcome}",
        f"- Approval status: **{report.approval.status.value}**",
        f"- Approval reference: `{report.approval.approval_id}`",
        "- Consequential action permitted: **no**",
        "",
        "## 1. Executive brief",
        "",
        report.executive_brief,
        "",
        "## 2. Observed facts",
        "",
    ]
    for item in report.observations:
        lines.append(f"- {item}")
    lines.extend(["", "## 3. Calculations"])
    for item in report.calculations:
        lines.append(
            f"- {item.label}: {_display(item.value)} {item.unit} "
            f"({item.formula}; evidence: {', '.join(item.evidence_ids)})"
        )
    lines.extend(["", "## 4. Data-quality exceptions"])
    if report.exceptions:
        for item in report.exceptions:
            case = item.case_id or "unknown"
            lines.append(
                f"- {case} row {item.row_number}: {item.reason} "
                f"(evidence: {item.evidence_id}; source: {item.provenance.reference})"
            )
    else:
        lines.append("- No excluded rows.")
    lines.extend(["", "## 5. Requested case observations"])
    if report.case_observations:
        for item in report.case_observations:
            case = item.case_id or "unknown"
            details = _case_details(item)
            lines.append(
                f"- {case} row {item.row_number}: {item.classification}"
                f"{details} (evidence: {item.evidence_id}; "
                f"source: {item.provenance.reference})"
            )
    else:
        lines.append("- No case IDs were requested.")
    lines.extend(["", "## 6. Proposed future-state workflow"])
    for item in report.future_state:
        lines.append(f"- **{item.title}** ({item.status}): {item.description}")
        lines.append(f"  - Evidence: {', '.join(item.evidence_ids)}")
    lines.extend(["", "## 7. Automation opportunities for review"])
    for option in report.automation_opportunities:
        lines.append(f"- `{option.option_id}`: {option.title}")
        lines.append(f"  - {option.description}")
        for link in option.rationale:
            lines.append(
                f"  - Rationale: {link.explanation} "
                f"(evidence: {', '.join(link.evidence_ids)})"
            )
        lines.append(f"  - Trade-offs: {'; '.join(option.trade_offs)}")
        lines.append(f"  - Validation: {'; '.join(option.validation_steps)}")
        lines.append(f"  - Limits: {'; '.join(option.limitations)}")
    lines.extend(["", "## 8. Risks and controls"])
    for item in report.risks:
        lines.append(
            f"- **{item.severity}** `{item.risk_id}`: {item.description}"
        )
        lines.append(f"  - Mitigation: {item.mitigation}")
        lines.append(f"  - Evidence: {', '.join(item.evidence_ids)}")
    lines.extend(["", "## 9. Assumptions"])
    for item in report.assumptions:
        lines.append(f"- {item}")
    lines.extend(["", "## 10. Prioritized roadmap (proposal only)"])
    for item in report.roadmap:
        lines.append(f"{item.priority}. **{item.title}** ({item.status})")
        lines.append(f"   - {item.description}")
        lines.append(f"   - Evidence: {', '.join(item.evidence_ids)}")
    lines.extend(["", "## 11. Evidence and assumptions appendix"])
    for item in report.evidence_appendix:
        lines.append(
            f"- `{item.evidence_id}`: {item.label} "
            f"(source: {item.source}; reference: {item.reference}; "
            f"kind: {item.kind})"
        )
    lines.extend(["", "## 12. Protocol trace"])
    for event in report.protocol_trace:
        identifiers = []
        if event.task_id:
            identifiers.append(f"task {event.task_id}")
        if event.context_id:
            identifiers.append(f"context {event.context_id}")
        suffix = f" ({', '.join(identifiers)})" if identifiers else ""
        lines.append(
            f"- {event.skill_id}: {event.step} {event.method} {event.path} "
            f"{event.state or ''}{suffix}".rstrip()
        )
    lines.extend(["", "## 13. Known limitations"])
    for item in report.limitations:
        lines.append(f"- {item}")
    lines.extend(["", "## 14. Human approval checkpoint"])
    lines.append(f"- Status: **{report.approval.status.value}**")
    lines.append(f"- Approval reference: `{report.approval.approval_id}`")
    lines.append(
        "- Consequential action permitted: **no**; this is a review state only."
    )
    if report.approval.note:
        lines.append(f"- Reviewer note: {report.approval.note}")
    lines.append(_approval_instruction(report.approval.status.value))
    cleaned_lines = [
        line if line is report.executive_brief else _sanitize_line(line)
        for line in lines
    ]
    return "\n".join(cleaned_lines) + "\n"


def _approval_instruction(status: str) -> str:
    if status == "approved":
        return (
            "A CLI review decision marked the report approved. No external "
            "network, write, or business action was performed."
        )
    if status == "declined":
        return (
            "A CLI review decision marked the report declined. No external "
            "network, write, or business action was performed."
        )
    return (
        "The workflow is paused before any consequential action. A human "
        "reviewer must decide before review continues. No external network, "
        "write, or business action is performed."
    )


def _case_details(item: CaseObservation) -> str:
    details: list[str] = []
    for label, value in (
        ("status", item.status),
        ("priority", item.priority),
        ("cycle_time_hours", item.cycle_time_hours),
        ("sla_met", item.sla_met),
        ("backlog_age_hours", item.backlog_age_hours),
        ("backlog_overdue", item.backlog_overdue),
        ("duplicate_of", item.duplicate_of),
        ("exclusion_reason", item.exclusion_reason),
    ):
        if value is not None:
            details.append(f"{label}={_display(value)}")
    return ", " + ", ".join(details) if details else ""


def _metric_values(summary: CoordinatorSummary) -> dict[str, int | float]:
    values = {item.name: item.value for item in summary.metrics}
    _require_metric(values, "input_rows")
    _require_metric(values, "measurable_closed")
    _require_metric(values, "mean_cycle_time_hours")
    _require_metric(values, "median_cycle_time_hours")
    _require_metric(values, "sla_met_count")
    _require_metric(values, "sla_met_percent")
    _require_metric(values, "rework_cases")
    _require_metric(values, "rework_rate_percent")
    _require_metric(values, "rework_volume")
    _require_metric(values, "backlog_cases")
    _require_metric(values, "backlog_overdue")
    _require_metric(values, "excluded_count")
    return values


def _require_metric(values: dict[str, int | float], name: str) -> None:
    if name not in values:
        raise ReportError(
            "incomplete_metrics",
            f"Required metric {name!r} is missing.",
        )


def _metric_evidence_ids() -> list[str]:
    return [
        "metric.input_rows",
        "metric.measurable_closed",
        "metric.cycle_time_sum_hours",
        "metric.mean_cycle_time_hours",
        "metric.median_cycle_time_hours",
        "metric.sla_met_count",
        "metric.sla_met_percent",
        "metric.rework_cases",
        "metric.rework_rate_percent",
        "metric.rework_volume",
        "metric.backlog_cases",
        "metric.backlog_overdue",
        "metric.excluded_count",
    ]


def _sla_misses(metrics: dict[str, int | float]) -> int:
    return int(metrics["measurable_closed"]) - int(metrics["sla_met_count"])


def _exception_detail(exceptions: list[ExceptionRecord]) -> str:
    reasons = {item.reason for item in exceptions}
    details: list[str] = []
    if any(reason.startswith("DUPLICATE_OF:") for reason in reasons):
        details.append("a duplicate")
    if any("MISSING_CLOSED_AT" in reason for reason in reasons):
        details.append("a missing close timestamp")
    if not details:
        return ""
    if len(details) == 1:
        return f", including {details[0]}"
    return f", including {details[0]} and {details[1]}"


def _dedupe(values: list[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


_LINE_CONTROL_PATTERN = re.compile(
    r"[\x00-\x1f\x7f\u2028\u2029\u202a-\u202e\u2066-\u2069]"
)


def _sanitize_line(value: str) -> str:
    return _LINE_CONTROL_PATTERN.sub(" ", value)


def _display(value: int | float | None) -> str:
    if value is None:
        return "not available"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
