"""Deterministic validation for coordinator-facing A2A handoffs."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from importlib.resources import files

from mcp.server.mcpserver.exceptions import ToolError
from transformation_workbench.data import (
    SLA_TARGET_HOURS,
    SNAPSHOT_AT,
    LoadResult,
    load_cases_from_csv,
)
from transformation_workbench.mcp_server import (
    PROCESS_CONTEXT,
    _select_case_details,
)
from transformation_workbench.metrics import MetricsResult, compute_metrics

from .claims import UnsupportedClaimError, assert_supported_chunks, assert_supported_text
from .contracts import (
    CONTRACT_VERSION,
    EVIDENCE_SOURCE,
    EXPECTED_TOOL_REFERENCES,
    PROCESS_CONTEXT_URI,
    REQUIRED_METRIC_FIELDS,
    EvidencePack,
    SolutionOptions,
)


class ContractValidationError(ValueError):
    """Raised when a handoff violates a contract rule."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def validate_evidence_pack(
    pack: EvidencePack,
    *,
    expected_request_id: str | None = None,
) -> None:
    """Reject missing, untraceable, or mismatched evidence."""
    if pack.contract_version != CONTRACT_VERSION:
        raise ContractValidationError(
            "invalid_contract_version",
            f"expected {CONTRACT_VERSION!r}, got {pack.contract_version!r}.",
        )
    if expected_request_id is not None and pack.request_id != expected_request_id:
        raise ContractValidationError(
            "request_mismatch",
            "Evidence pack request ID does not match the coordinator request.",
        )
    if not pack.snapshot:
        raise ContractValidationError("missing_snapshot", "Snapshot is empty.")
    if pack.snapshot != pack.process_context.snapshot:
        raise ContractValidationError(
            "provenance_mismatch",
            "Evidence snapshot does not match the process-context snapshot.",
        )
    if not pack.process_context.synthetic_only:
        raise ContractValidationError(
            "invalid_provenance",
            "Process context must be marked synthetic-only.",
        )
    if not pack.process_context.read_only:
        raise ContractValidationError(
            "invalid_provenance",
            "Process context must be marked read-only.",
        )
    _require_provenance(
        pack.process_context.provenance.source,
        EVIDENCE_SOURCE,
        "Process-context provenance has the wrong source.",
    )
    _require_provenance(
        pack.process_context.provenance.kind,
        "mcp_resource",
        "process-context provenance must reference an MCP resource.",
    )
    _require_provenance(
        pack.process_context.provenance.reference,
        PROCESS_CONTEXT_URI,
        "process-context provenance references the wrong resource.",
    )
    if len(pack.process_context.sha256) != 64:
        raise ContractValidationError(
            "invalid_provenance",
            "Process-context hash must be a SHA-256 hex digest.",
        )

    unexpected_metrics = sorted(
        set(pack.metrics) - set(REQUIRED_METRIC_FIELDS)
    )
    if unexpected_metrics:
        raise ContractValidationError(
            "unexpected_metric",
            "Unexpected metric fields: " + ", ".join(unexpected_metrics),
        )
    if any(
        item.provenance.kind != "mcp_tool"
        or item.provenance.source != EVIDENCE_SOURCE
        for item in pack.metrics.values()
    ):
        raise ContractValidationError(
            "invalid_provenance",
            "Metric provenance must reference a read-only MCP tool.",
        )

    missing_fields = {
        item.field for item in pack.missing_data
    }
    for name, expected_unit in REQUIRED_METRIC_FIELDS.items():
        fact = pack.metrics.get(name)
        if fact is None:
            raise ContractValidationError(
                "missing_metric",
                f"Required metric {name!r} is absent.",
            )
        if fact.value is None and f"metric.{name}" not in missing_fields:
            raise ContractValidationError(
                "missing_metric",
                f"Metric {name!r} is null without a missing-data reason.",
            )
        if fact.name != name or fact.evidence_id != f"metric.{name}":
            raise ContractValidationError(
                "invalid_provenance",
                f"Metric {name!r} has an inconsistent evidence identifier.",
            )
        if fact.unit != expected_unit:
            raise ContractValidationError(
                "invalid_unit",
                f"Metric {name!r} must use unit {expected_unit!r}.",
            )
        _require_provenance(
            fact.provenance.reference,
            EXPECTED_TOOL_REFERENCES["metrics"],
            f"Metric {name!r} does not reference the metrics tool.",
        )

    exception_ids = [item.evidence_id for item in pack.exceptions]
    _require_unique(exception_ids, "exception evidence identifier")
    for item in pack.exceptions:
        _require_provenance(
            item.provenance.source,
            EVIDENCE_SOURCE,
            "Exception has the wrong provenance source.",
        )
        _require_provenance(
            item.provenance.kind,
            "mcp_tool",
            "Exception provenance must reference an MCP tool.",
        )
        _require_provenance(
            item.provenance.reference,
            EXPECTED_TOOL_REFERENCES["exceptions"],
            "Exception does not reference the exceptions tool.",
        )

    observation_ids = [item.evidence_id for item in pack.case_observations]
    _require_unique(observation_ids, "case observation evidence identifier")
    observation_case_ids = [
        item.case_id for item in pack.case_observations if item.case_id
    ]
    _require_unique(observation_case_ids, "case observation case identifier")
    for item in pack.case_observations:
        _require_provenance(
            item.provenance.source,
            EVIDENCE_SOURCE,
            "Case observation has the wrong provenance source.",
        )
        _require_provenance(
            item.provenance.kind,
            "mcp_tool",
            "Case observation provenance must reference an MCP tool.",
        )
        _require_provenance(
            item.provenance.reference,
            EXPECTED_TOOL_REFERENCES["case_details"],
            "Case observation does not reference the case-details tool.",
        )

    observed_case_ids = {
        item.case_id for item in pack.case_observations if item.case_id
    }
    errored_case_ids = {
        item.case_id for item in pack.tool_errors if item.case_id
    }
    for case_id in pack.requested_case_ids:
        if (
            case_id not in observed_case_ids
            and case_id not in errored_case_ids
            and f"case.{case_id}" not in missing_fields
        ):
            raise ContractValidationError(
                "untraceable_case",
                f"Requested case {case_id!r} has no observation or error record.",
            )


def verify_evidence_against_fixture(pack: EvidencePack) -> None:
    """Verify self-reported context and metrics against the fixed fixture."""
    if pack.process_context.text != PROCESS_CONTEXT:
        raise ContractValidationError(
            "context_mismatch",
            "Process-context text does not match the fixed synthetic context.",
        )
    expected_hash = hashlib.sha256(
        pack.process_context.text.encode("utf-8")
    ).hexdigest()
    if pack.process_context.sha256 != expected_hash:
        raise ContractValidationError(
            "context_hash_mismatch",
            "Process-context SHA-256 does not match the received text.",
        )

    snapshot, metric_status, metrics, sla_targets = _trusted_fixture_values()
    if pack.snapshot != snapshot:
        raise ContractValidationError(
            "snapshot_mismatch",
            "Evidence snapshot does not match the fixed fixture snapshot.",
        )
    if pack.process_context.snapshot != snapshot:
        raise ContractValidationError(
            "snapshot_mismatch",
            "Process-context snapshot does not match the fixed fixture snapshot.",
        )
    if pack.metric_status != metric_status:
        raise ContractValidationError(
            "metric_status_mismatch",
            "Metric status does not match the fixed fixture.",
        )
    if pack.process_context.sla_targets != sla_targets:
        raise ContractValidationError(
            "sla_target_mismatch",
            "SLA targets do not match the fixed fixture.",
        )
    for name, expected in metrics.items():
        fact = pack.metrics.get(name)
        if fact is None or fact.value != expected:
            raise ContractValidationError(
                "metric_value_mismatch",
                f"Metric {name!r} does not match the fixed fixture.",
            )

    if pack.tool_errors or pack.missing_data:
        raise ContractValidationError(
            "incomplete_evidence",
            "Evidence pack contains unresolved tool errors or missing data.",
        )

    dataset, metrics_result = _trusted_fixture_bundle()
    expected_exceptions = {
        (
            f"exception.row.{issue.row_number}",
            issue.case_id,
            issue.row_number,
            issue.reason,
        )
        for issue in metrics_result.exclusions
    }
    actual_exceptions = {
        (
            item.evidence_id,
            item.case_id,
            item.row_number,
            item.reason,
        )
        for item in pack.exceptions
    }
    if actual_exceptions != expected_exceptions:
        raise ContractValidationError(
            "exception_mismatch",
            "Exception records do not match the fixed fixture.",
        )

    expected_case_ids = set(pack.requested_case_ids)
    observed = {
        item.case_id: item
        for item in pack.case_observations
        if item.case_id is not None
    }
    if set(observed) != expected_case_ids:
        raise ContractValidationError(
            "case_observation_mismatch",
            "Case observations do not match the requested case set.",
        )
    for case_id, item in observed.items():
        try:
            details = _select_case_details(
                dataset,
                metrics_result,
                case_id=case_id,
                row_number=None,
            )
        except ToolError as exc:
            raise ContractValidationError(
                "case_observation_mismatch",
                f"Fixture lookup failed for case {case_id!r}.",
            ) from exc
        actual = item.model_dump()
        for field, expected in details.model_dump().items():
            if actual.get(field) != expected:
                raise ContractValidationError(
                    "case_observation_mismatch",
                    f"Case observation {case_id!r} field {field!r} "
                    "does not match the fixed fixture.",
                )


def validate_solution_options(
    options: SolutionOptions,
    pack: EvidencePack,
) -> None:
    """Reject unknown evidence links and unsupported claims."""
    if options.contract_version != CONTRACT_VERSION:
        raise ContractValidationError(
            "invalid_contract_version",
            f"expected {CONTRACT_VERSION!r}, got {options.contract_version!r}.",
        )
    if options.request_id != pack.request_id:
        raise ContractValidationError(
            "request_mismatch",
            "Solution options request ID does not match the evidence pack.",
        )
    if options.evidence_pack_id != pack.evidence_pack_id:
        raise ContractValidationError(
            "evidence_pack_mismatch",
            "Solution options do not reference the validated evidence pack.",
        )

    known_ids = pack.evidence_ids()
    option_ids = [option.option_id for option in options.options]
    _require_unique(option_ids, "option identifier")

    for option in options.options:
        if not option.rationale:
            raise ContractValidationError(
                "missing_rationale",
                f"Option {option.option_id!r} has no rationale.",
            )
        if not option.trade_offs:
            raise ContractValidationError(
                "missing_trade_offs",
                f"Option {option.option_id!r} has no trade-offs.",
            )
        if not option.validation_steps:
            raise ContractValidationError(
                "missing_validation_steps",
                f"Option {option.option_id!r} has no validation steps.",
            )
        for link in option.rationale:
            if not link.evidence_ids:
                raise ContractValidationError(
                    "missing_evidence_reference",
                    f"Option {option.option_id!r} has an empty evidence reference.",
                )
            unknown = sorted(set(link.evidence_ids) - known_ids)
            if unknown:
                raise ContractValidationError(
                    "unknown_evidence_reference",
                    f"Option {option.option_id!r} references unknown evidence: "
                    + ", ".join(unknown),
                )

    _guard_claims(options)


def _guard_claims(options: SolutionOptions) -> None:
    try:
        assert_supported_chunks(options.assumptions, "solution assumptions")
        assert_supported_chunks(options.limitations, "solution limitations")
        for option in options.options:
            assert_supported_text(option.title, f"{option.option_id}.title")
            assert_supported_text(
                option.description,
                f"{option.option_id}.description",
            )
            for index, link in enumerate(option.rationale):
                assert_supported_text(
                    link.explanation,
                    f"{option.option_id}.rationale[{index}]",
                )
            assert_supported_chunks(
                option.trade_offs,
                f"{option.option_id}.trade_offs",
            )
            assert_supported_chunks(
                option.assumptions,
                f"{option.option_id}.assumptions",
            )
            assert_supported_chunks(
                option.validation_steps,
                f"{option.option_id}.validation_steps",
            )
            assert_supported_chunks(
                option.limitations,
                f"{option.option_id}.limitations",
            )
    except UnsupportedClaimError as exc:
        raise ContractValidationError("unsupported_claim", str(exc)) from exc


@lru_cache(maxsize=1)
def _trusted_fixture_bundle() -> tuple[LoadResult, MetricsResult]:
    fixture = (
        files("transformation_workbench")
        .joinpath("data")
        .joinpath("synthetic_cases.csv")
    )
    dataset = load_cases_from_csv(fixture.read_text(encoding="utf-8"))
    return dataset, compute_metrics(dataset)


@lru_cache(maxsize=1)
def _trusted_fixture_values() -> tuple[
    str,
    str,
    dict[str, int | float | None],
    dict[str, float],
]:
    _, result = _trusted_fixture_bundle()
    presentation = result.to_presentation()
    metrics: dict[str, int | float | None] = {}
    for name, unit in REQUIRED_METRIC_FIELDS.items():
        value = (
            result.sla_met_count
            if name == "sla_met_count"
            else presentation[name]
        )
        if value is None:
            metrics[name] = None
        elif unit == "count":
            metrics[name] = int(value)
        else:
            metrics[name] = float(value)
    snapshot = SNAPSHOT_AT.strftime("%Y-%m-%dT%H:%M:%SZ")
    sla_targets = {
        priority.value: float(hours)
        for priority, hours in SLA_TARGET_HOURS.items()
    }
    return snapshot, result.status.value, metrics, sla_targets


def _require_provenance(actual: str, expected: str, message: str) -> None:
    if actual != expected:
        raise ContractValidationError("invalid_provenance", message)


def _require_unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ContractValidationError(
            "duplicate_evidence_id",
            f"Duplicate {label} detected.",
        )
