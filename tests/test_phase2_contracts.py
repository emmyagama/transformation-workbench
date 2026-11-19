"""Phase 2 contract and validation tests."""

from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from transformation_workbench.a2a.contracts import (
    REQUIRED_METRIC_FIELDS,
    EvidencePack,
    SolutionOptions,
)
from transformation_workbench.a2a.solution_designer import design_options
from transformation_workbench.a2a.validation import (
    ContractValidationError,
    validate_evidence_pack,
    validate_solution_options,
    verify_evidence_against_fixture,
)

from .phase2_helpers import valid_evidence_pack


def test_evidence_pack_has_provenance_for_every_measured_fact() -> None:
    pack = valid_evidence_pack()
    assert set(pack.metrics) == set(REQUIRED_METRIC_FIELDS)
    for fact in pack.metrics.values():
        assert fact.provenance.reference == "calculate_baseline_metrics"
        assert fact.provenance.access == "read_only"
    for item in pack.exceptions:
        assert item.provenance.reference == "list_case_exceptions"
    for item in pack.case_observations:
        assert item.provenance.reference == "get_case_details"
    assert pack.process_context.provenance.reference == "workbench://process-context"
    assert len(pack.process_context.sha256) == 64


def test_missing_required_metric_is_rejected() -> None:
    pack = valid_evidence_pack()
    payload = pack.model_dump(mode="json")
    del payload["metrics"]["sla_met_percent"]
    broken = pack.model_validate(payload)
    with pytest.raises(ContractValidationError, match="missing_metric"):
        validate_evidence_pack(broken)


def test_metric_without_provenance_reference_is_rejected() -> None:
    pack = valid_evidence_pack()
    payload = pack.model_dump(mode="json")
    payload["metrics"]["input_rows"]["provenance"]["reference"] = "unknown_tool"
    broken = pack.model_validate(payload)
    with pytest.raises(ContractValidationError, match="invalid_provenance"):
        validate_evidence_pack(broken)


def test_untraceable_requested_case_is_rejected() -> None:
    pack = valid_evidence_pack()
    payload = pack.model_dump(mode="json")
    payload["requested_case_ids"].append("C-999")
    broken = pack.model_validate(payload)
    with pytest.raises(ContractValidationError, match="untraceable_case"):
        validate_evidence_pack(broken)


def test_solution_options_require_trade_offs_and_validation_steps() -> None:
    payload = design_options(valid_evidence_pack()).model_dump(mode="json")
    del payload["options"][0]["trade_offs"]
    with pytest.raises(ValidationError):
        SolutionOptions.model_validate(payload)

    payload = design_options(valid_evidence_pack()).model_dump(mode="json")
    payload["options"][0]["validation_steps"] = []
    with pytest.raises(ValidationError):
        SolutionOptions.model_validate(payload)


def test_unknown_evidence_reference_is_rejected() -> None:
    pack = valid_evidence_pack()
    options = design_options(pack)
    payload = options.model_dump(mode="json")
    payload["options"][0]["rationale"][0]["evidence_ids"] = ["metric.not_a_metric"]
    broken = SolutionOptions.model_validate(payload)
    with pytest.raises(
        ContractValidationError,
        match="unknown_evidence_reference",
    ):
        validate_solution_options(broken, pack)


def test_unsupported_savings_claim_is_rejected() -> None:
    pack = valid_evidence_pack()
    options = design_options(pack)
    payload = options.model_dump(mode="json")
    payload["options"][0]["description"] = (
        "This option will save $100,000 annually and guarantee a 30% cost reduction."
    )
    broken = SolutionOptions.model_validate(payload)
    with pytest.raises(ContractValidationError, match="unsupported_claim"):
        validate_solution_options(broken, pack)


def test_evidence_pack_request_mismatch_is_rejected() -> None:
    pack = valid_evidence_pack(request_id="different-request")
    with pytest.raises(ContractValidationError, match="request_mismatch"):
        validate_evidence_pack(pack, expected_request_id="expected-request")


def test_solution_options_request_mismatch_is_rejected() -> None:
    pack = valid_evidence_pack(request_id="phase2-request")
    payload = design_options(pack).model_dump(mode="json")
    payload["request_id"] = "different-request"
    broken = SolutionOptions.model_validate(payload)
    with pytest.raises(ContractValidationError, match="request_mismatch"):
        validate_solution_options(broken, pack)


@pytest.mark.parametrize(
    "claim",
    [
        "This option will reduce cycle time by 50%.",
        "Cut the backlog in half.",
        "Increase throughput 20%.",
        "Improve SLA attainment from 66.7% to 100%.",
    ],
)
def test_unsupported_percentage_impact_claims_are_rejected(claim: str) -> None:
    pack = valid_evidence_pack()
    payload = design_options(pack).model_dump(mode="json")
    payload["options"][0]["description"] = claim
    broken = SolutionOptions.model_validate(payload)
    with pytest.raises(ContractValidationError, match="unsupported_claim"):
        validate_solution_options(broken, pack)


def test_labeled_impact_hypothesis_is_allowed() -> None:
    pack = valid_evidence_pack()
    payload = design_options(pack).model_dump(mode="json")
    payload["options"][0]["description"] = (
        "This is an unvalidated hypothesis: reduce cycle time by 50%."
    )
    options = SolutionOptions.model_validate(payload)
    validate_solution_options(options, pack)


def test_hypothesis_label_is_scoped_to_the_claim_sentence() -> None:
    pack = valid_evidence_pack()
    payload = design_options(pack).model_dump(mode="json")
    payload["options"][0]["description"] = (
        "This is an unvalidated hypothesis. "
        "This option will reduce cycle time by 50%."
    )
    broken = SolutionOptions.model_validate(payload)
    with pytest.raises(ContractValidationError, match="unsupported_claim"):
        validate_solution_options(broken, pack)


def test_measured_percentage_reporting_is_allowed() -> None:
    pack = valid_evidence_pack()
    payload = design_options(pack).model_dump(mode="json")
    payload["options"][0]["rationale"][0]["explanation"] = (
        "The pack records 66.7% SLA attainment and a 22.2% rework rate."
    )
    options = SolutionOptions.model_validate(payload)
    validate_solution_options(options, pack)


def test_self_reported_context_hash_is_recomputed() -> None:
    pack = valid_evidence_pack()
    payload = pack.model_dump(mode="json")
    payload["process_context"]["sha256"] = "0" * 64
    broken = EvidencePack.model_validate(payload)
    with pytest.raises(ContractValidationError, match="context_hash_mismatch"):
        verify_evidence_against_fixture(broken)


def test_self_reported_context_text_must_match_fixture() -> None:
    pack = valid_evidence_pack()
    payload = pack.model_dump(mode="json")
    altered = "altered process context"
    payload["process_context"]["text"] = altered
    payload["process_context"]["sha256"] = hashlib.sha256(
        altered.encode("utf-8")
    ).hexdigest()
    broken = EvidencePack.model_validate(payload)
    with pytest.raises(ContractValidationError, match="context_mismatch"):
        verify_evidence_against_fixture(broken)


def test_stale_snapshot_is_rejected_against_fixture() -> None:
    pack = valid_evidence_pack()
    payload = pack.model_dump(mode="json")
    payload["snapshot"] = "2026-03-12T17:00:00Z"
    payload["process_context"]["snapshot"] = "2026-03-12T17:00:00Z"
    broken = EvidencePack.model_validate(payload)
    with pytest.raises(ContractValidationError, match="snapshot_mismatch"):
        verify_evidence_against_fixture(broken)


def test_exception_record_must_match_fixture() -> None:
    pack = valid_evidence_pack()
    payload = pack.model_dump(mode="json")
    payload["exceptions"][0]["reason"] = "TAMPERED_REASON"
    broken = EvidencePack.model_validate(payload)
    with pytest.raises(ContractValidationError, match="exception_mismatch"):
        verify_evidence_against_fixture(broken)


def test_case_observation_must_match_fixture() -> None:
    pack = valid_evidence_pack()
    payload = pack.model_dump(mode="json")
    payload["case_observations"][0]["cycle_time_hours"] = 999.0
    broken = EvidencePack.model_validate(payload)
    with pytest.raises(
        ContractValidationError,
        match="case_observation_mismatch",
    ):
        verify_evidence_against_fixture(broken)


def test_incomplete_evidence_is_rejected() -> None:
    pack = valid_evidence_pack()
    payload = pack.model_dump(mode="json")
    payload["missing_data"].append(
        {"field": "exceptions", "reason": "synthetic missing data"}
    )
    broken = EvidencePack.model_validate(payload)
    with pytest.raises(ContractValidationError, match="incomplete_evidence"):
        verify_evidence_against_fixture(broken)


def test_self_reported_metric_value_must_match_fixture() -> None:
    pack = valid_evidence_pack()
    payload = pack.model_dump(mode="json")
    payload["metrics"]["input_rows"]["value"] = 99
    broken = EvidencePack.model_validate(payload)
    with pytest.raises(ContractValidationError, match="metric_value_mismatch"):
        verify_evidence_against_fixture(broken)


def test_recommendation_cannot_carry_a_measured_value_field() -> None:
    pack = valid_evidence_pack()
    payload = design_options(pack).model_dump(mode="json")
    payload["options"][0]["measured_value"] = 15
    with pytest.raises(ValidationError):
        SolutionOptions.model_validate(payload)


def test_valid_solution_options_reference_only_pack_evidence() -> None:
    pack = valid_evidence_pack()
    options = design_options(pack)
    validate_solution_options(options, pack)
    known = pack.evidence_ids()
    for option in options.options:
        assert option.trade_offs
        assert option.validation_steps
        for link in option.rationale:
            assert link.evidence_ids
            assert set(link.evidence_ids) <= known
