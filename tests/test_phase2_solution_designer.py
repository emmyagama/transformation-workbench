"""Phase 2 Solution Designer tests."""

from __future__ import annotations

import pytest
from a2a.helpers import new_data_message, new_text_message
from a2a.types import Role

from transformation_workbench.a2a.solution_designer import (
    SolutionDesignError,
    design_options,
    parse_evidence_pack,
)

from .phase2_helpers import valid_evidence_pack


def test_design_options_are_deterministic_and_evidence_linked() -> None:
    pack = valid_evidence_pack()
    first = design_options(pack)
    second = design_options(pack)
    assert first == second
    known = pack.evidence_ids()
    assert first.evidence_pack_id == pack.evidence_pack_id
    assert [option.option_id for option in first.options] == [
        "option-triage-backlog",
        "option-data-quality",
        "option-rework-review",
    ]
    for option in first.options:
        assert option.trade_offs
        assert option.assumptions
        assert option.validation_steps
        assert option.limitations
        for link in option.rationale:
            assert link.explanation
            assert set(link.evidence_ids) <= known


def test_solution_options_do_not_echo_measured_metric_fields() -> None:
    options = design_options(valid_evidence_pack())
    for option in options.options:
        assert "value" not in option.model_dump()
        assert "measured_value" not in option.model_dump()


def test_parse_evidence_pack_from_data_and_text() -> None:
    pack = valid_evidence_pack()
    data_message = new_data_message(
        pack.model_dump(mode="json"),
        media_type="application/json",
        role=Role.ROLE_USER,
    )
    assert parse_evidence_pack(data_message) == pack

    text_message = new_text_message(
        pack.model_dump_json(),
        role=Role.ROLE_USER,
    )
    assert parse_evidence_pack(text_message) == pack


def test_parse_evidence_pack_rejects_empty_or_invalid_payload() -> None:
    with pytest.raises(SolutionDesignError, match="no EvidencePack"):
        parse_evidence_pack(new_text_message("", role=Role.ROLE_USER))

    with pytest.raises(SolutionDesignError, match="invalid_evidence_pack"):
        parse_evidence_pack(
            new_data_message(
                {"request_id": "only"},
                media_type="application/json",
                role=Role.ROLE_USER,
            )
        )
