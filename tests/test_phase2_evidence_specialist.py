"""Phase 2 Evidence Specialist and MCP source tests."""

from __future__ import annotations

import pytest
from a2a.helpers import new_data_message, new_text_message
from a2a.types import Role

from transformation_workbench.a2a.evidence_source import (
    EvidenceSourceError,
    McpEvidenceSource,
)
from transformation_workbench.a2a.evidence_specialist import parse_evidence_request

from .phase2_helpers import (
    METRIC_VALUES,
    SNAPSHOT,
    FakeMcpSession,
    fake_session_factory,
    valid_evidence_pack,
)

CASE_FIELDS = (
    "case_id",
    "row_number",
    "classification",
    "status",
    "priority",
    "received_at",
    "acknowledged_at",
    "closed_at",
    "rework_count",
    "duplicate_of",
    "exclusion_reason",
    "cycle_time_hours",
    "sla_target_hours",
    "sla_met",
    "backlog_age_hours",
    "backlog_overdue",
)


def _tool_results() -> dict[str, object]:
    pack = valid_evidence_pack()
    cases = {
        item.case_id: {
            field: getattr(item, field)
            for field in CASE_FIELDS
        }
        for item in pack.case_observations
    }
    return {
        "calculate_baseline_metrics": {
            "status": "ok",
            "snapshot_at": SNAPSHOT,
            **METRIC_VALUES,
        },
        "list_case_exceptions": {
            "input_rows": 15,
            "count": len(pack.exceptions),
            "exceptions": [
                {
                    "case_id": item.case_id,
                    "reason": item.reason,
                    "row_number": item.row_number,
                }
                for item in pack.exceptions
            ],
        },
        "get_case_details": lambda arguments: cases[arguments["case_id"]],
    }


async def _collect(
    session: FakeMcpSession,
    case_ids: list[str] | None = None,
):
    source = McpEvidenceSource(
        session_factory=fake_session_factory(session),
        timeout=5,
    )
    return await source.collect(
        "phase2-evidence-test",
        case_ids or ["C-009", "C-006", "C-014"],
    )


@pytest.mark.anyio
async def test_mcp_source_builds_provenance_linked_evidence_pack() -> None:
    session = FakeMcpSession(tool_results=_tool_results())
    pack = await _collect(session)

    assert pack.metric_status == "ok"
    assert pack.snapshot == SNAPSHOT
    assert pack.metrics["input_rows"].value == 15
    assert pack.metrics["measurable_closed"].value == 9
    assert pack.metrics["sla_met_percent"].value == 66.7
    assert pack.metrics["excluded_count"].value == 4
    assert pack.metrics["backlog_cases"].value == 2
    assert len(pack.exceptions) == 4
    assert [item.case_id for item in pack.case_observations] == [
        "C-009",
        "C-006",
        "C-014",
    ]
    assert pack.process_context.snapshot == SNAPSHOT
    assert pack.process_context.sla_targets == {"P1": 8.0, "P2": 24.0, "P3": 72.0}
    assert len(pack.process_context.sha256) == 64
    assert pack.tool_errors == []
    assert pack.missing_data == []


@pytest.mark.anyio
async def test_missing_mcp_resource_is_bounded_and_explanatory() -> None:
    session = FakeMcpSession(resources=[], tool_results=_tool_results())
    with pytest.raises(EvidenceSourceError) as excinfo:
        await _collect(session)
    assert excinfo.value.code == "mcp_resource_unavailable"
    assert "not listed" in excinfo.value.message


@pytest.mark.anyio
async def test_metrics_tool_error_stops_without_fabricating_values() -> None:
    results = _tool_results()
    session = FakeMcpSession(
        tool_results=results,
        tool_errors={"calculate_baseline_metrics": "synthetic tool failure"},
    )
    with pytest.raises(EvidenceSourceError) as excinfo:
        await _collect(session)
    assert excinfo.value.code == "mcp_tool_error"
    assert "synthetic tool failure" in excinfo.value.message


@pytest.mark.anyio
async def test_exception_tool_error_is_recorded_without_inventing_rows() -> None:
    session = FakeMcpSession(
        tool_results=_tool_results(),
        tool_errors={"list_case_exceptions": "synthetic exception failure"},
    )
    pack = await _collect(session)
    assert pack.exceptions == []
    assert pack.tool_errors[0].tool == "list_case_exceptions"
    assert pack.missing_data[0].field == "exceptions"


@pytest.mark.anyio
async def test_case_tool_error_is_recorded_and_marked_missing() -> None:
    session = FakeMcpSession(
        tool_results=_tool_results(),
        tool_errors={"get_case_details": "unknown synthetic case"},
    )
    pack = await _collect(session, ["C-999"])
    assert pack.case_observations == []
    assert pack.missing_data[0].field == "case.C-999"
    assert pack.tool_errors[0].case_id == "C-999"


def test_parse_evidence_request_from_data_and_text() -> None:
    data_message = new_data_message(
        {"request_id": "req-1", "case_ids": ["C-009", "C-014"]},
        media_type="application/json",
        role=Role.ROLE_USER,
    )
    assert parse_evidence_request(data_message) == (
        "req-1",
        ["C-009", "C-014"],
    )

    text_message = new_text_message(
        '{"request_id": "req-2", "case_ids": "C-006,C-009"}',
        role=Role.ROLE_USER,
    )
    assert parse_evidence_request(text_message) == (
        "req-2",
        ["C-006", "C-009"],
    )
