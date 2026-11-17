"""Typed A2A handoff contracts for the Week 3 Phase 2 workflow."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

CONTRACT_VERSION = "1.0"
PROCESS_CONTEXT_URI = "workbench://process-context"
EVIDENCE_SOURCE = "transformation-workbench-mcp"

REQUIRED_METRIC_FIELDS: dict[str, str] = {
    "input_rows": "count",
    "measurable_closed": "count",
    "cycle_time_sum_hours": "hours",
    "mean_cycle_time_hours": "hours",
    "median_cycle_time_hours": "hours",
    "sla_met_count": "count",
    "sla_met_percent": "percent",
    "rework_cases": "count",
    "rework_rate_percent": "percent",
    "rework_volume": "count",
    "backlog_cases": "count",
    "backlog_overdue": "count",
    "excluded_count": "count",
}

EXPECTED_TOOL_REFERENCES: dict[str, str] = {
    "metrics": "calculate_baseline_metrics",
    "exceptions": "list_case_exceptions",
    "case_details": "get_case_details",
}


class ContractModel(BaseModel):
    """Base model that rejects undeclared fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Provenance(ContractModel):
    source: str
    kind: Literal["mcp_tool", "mcp_resource"]
    reference: str
    access: Literal["read_only"] = "read_only"


class MetricFact(ContractModel):
    evidence_id: str
    name: str
    value: int | float | None
    unit: Literal["count", "hours", "percent"]
    provenance: Provenance


class ProcessContext(ContractModel):
    uri: str
    mime_type: str
    sha256: str
    text: str
    snapshot: str
    sla_targets: dict[str, float]
    synthetic_only: bool
    read_only: bool
    provenance: Provenance


class ExceptionRecord(ContractModel):
    evidence_id: str
    case_id: str | None
    row_number: int
    reason: str
    provenance: Provenance


class CaseObservation(ContractModel):
    evidence_id: str
    case_id: str | None
    row_number: int
    classification: Literal["measurable", "backlog", "duplicate", "invalid"]
    status: str | None
    priority: str | None
    received_at: str | None
    acknowledged_at: str | None
    closed_at: str | None
    rework_count: int | None
    duplicate_of: str | None
    exclusion_reason: str | None
    cycle_time_hours: float | None
    sla_target_hours: float | None
    sla_met: bool | None
    backlog_age_hours: float | None
    backlog_overdue: bool | None
    provenance: Provenance


class MissingData(ContractModel):
    field: str
    reason: str


class ToolErrorRecord(ContractModel):
    tool: str
    message: str
    case_id: str | None = None


class EvidencePack(ContractModel):
    contract_version: Literal["1.0"] = CONTRACT_VERSION
    evidence_pack_id: str
    request_id: str
    generated_by: str
    metric_status: Literal["ok", "no measurable cases"]
    snapshot: str
    process_context: ProcessContext
    metrics: dict[str, MetricFact]
    exceptions: list[ExceptionRecord]
    case_observations: list[CaseObservation]
    requested_case_ids: list[str]
    missing_data: list[MissingData]
    tool_errors: list[ToolErrorRecord]

    def evidence_ids(self) -> set[str]:
        ids = {"context", "snapshot"}
        ids.update(f"metric.{name}" for name in self.metrics)
        ids.update(item.evidence_id for item in self.exceptions)
        ids.update(item.evidence_id for item in self.case_observations)
        return ids


class RationaleLink(ContractModel):
    evidence_ids: list[str] = Field(min_length=1)
    explanation: str = Field(min_length=1)


class SolutionOption(ContractModel):
    option_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    rationale: list[RationaleLink] = Field(min_length=1)
    trade_offs: list[str] = Field(min_length=1)
    assumptions: list[str] = Field(min_length=1)
    validation_steps: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)


class SolutionOptions(ContractModel):
    contract_version: Literal["1.0"] = CONTRACT_VERSION
    request_id: str = Field(min_length=1)
    evidence_pack_id: str = Field(min_length=1)
    generated_by: str
    options: list[SolutionOption] = Field(min_length=1)
    assumptions: list[str]
    limitations: list[str]


class Calculation(ContractModel):
    calculation_id: str
    label: str
    formula: str
    value: int | float
    unit: Literal["count", "percent", "hours"]
    evidence_ids: list[str] = Field(min_length=1)


class ProtocolTraceEvent(ContractModel):
    step: Literal["discover_card", "send_task", "duplicate_replay"]
    agent: str
    method: Literal["GET", "POST", "NONE"]
    path: str
    skill_id: str
    task_id: str | None = None
    context_id: str | None = None
    state: str | None = None
    attempt: int = 1


class CoordinatorResult(ContractModel):
    request_id: str
    status: Literal["complete"] = "complete"
    measured_facts: EvidencePack
    calculations: list[Calculation]
    assumptions: list[str]
    solution_options: SolutionOptions
    trace: list[ProtocolTraceEvent]

    @computed_field
    @property
    def recommendations(self) -> list[SolutionOption]:
        return self.solution_options.options
