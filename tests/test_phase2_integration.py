"""Phase 2 end-to-end integration: real MCP stdio plus two A2A servers."""

from __future__ import annotations

import pytest

from transformation_workbench.a2a.evidence_specialist import (
    EVIDENCE_SKILL_ID,
    build_app as build_evidence_app,
)
from transformation_workbench.a2a.phase2_coordinator import Phase2Coordinator
from transformation_workbench.a2a.solution_designer import (
    SOLUTION_SKILL_ID,
    build_app as build_solution_app,
)
from transformation_workbench.a2a.summary import render_summary

from .phase2_helpers import running_server


@pytest.mark.anyio
async def test_real_mcp_stdio_and_dual_a2a_round_trip() -> None:
    request_id = "phase2-integration"
    case_ids = ["C-009", "C-006", "C-014"]

    async with running_server(build_evidence_app) as (
        evidence_url,
        evidence_seen,
    ):
        async with running_server(build_solution_app) as (
            solution_url,
            solution_seen,
        ):
            coordinator = Phase2Coordinator(
                evidence_url,
                solution_url,
                timeout=30.0,
                max_retries=0,
            )
            result = await coordinator.run(request_id, case_ids)
            evidence_posts_after_first = [
                item for item in evidence_seen if item[0] == "POST"
            ]
            solution_posts_after_first = [
                item for item in solution_seen if item[0] == "POST"
            ]
            duplicate = await coordinator.run(request_id, case_ids)

    metrics = result.measured_facts.metrics
    assert metrics["input_rows"].value == 15
    assert metrics["measurable_closed"].value == 9
    assert metrics["sla_met_percent"].value == 66.7
    assert metrics["excluded_count"].value == 4
    assert metrics["backlog_cases"].value == 2
    assert result.measured_facts.snapshot == "2026-03-13T17:00:00Z"
    assert result.measured_facts.process_context.provenance.reference == (
        "workbench://process-context"
    )
    assert len(result.measured_facts.process_context.sha256) == 64
    assert result.measured_facts.process_context.sla_targets == {
        "P1": 8.0,
        "P2": 24.0,
        "P3": 72.0,
    }
    assert len(result.measured_facts.exceptions) == 4
    assert {
        (item.case_id, item.row_number, item.reason)
        for item in result.measured_facts.exceptions
    } == {
        ("C-006", 7, "INCOMPLETE_MISSING_CLOSED_AT"),
        ("C-010", 11, "INVALID_DATE"),
        ("C-011", 12, "OUT_OF_ORDER"),
        ("C-014", 15, "DUPLICATE_OF:C-007"),
    }
    observations = {
        item.case_id: item for item in result.measured_facts.case_observations
    }
    assert set(observations) == set(case_ids)
    assert observations["C-009"].classification == "measurable"
    assert observations["C-009"].row_number == 10
    assert observations["C-009"].cycle_time_hours == 24.0
    assert observations["C-009"].sla_met is True
    assert observations["C-006"].classification == "invalid"
    assert observations["C-006"].row_number == 7
    assert observations["C-006"].exclusion_reason == (
        "INCOMPLETE_MISSING_CLOSED_AT"
    )
    assert observations["C-014"].classification == "duplicate"
    assert observations["C-014"].row_number == 15
    assert observations["C-014"].duplicate_of == "C-007"
    assert result.measured_facts.tool_errors == []
    assert result.measured_facts.missing_data == []

    known = result.measured_facts.evidence_ids()
    assert result.solution_options.options
    for option in result.solution_options.options:
        assert option.trade_offs
        assert option.validation_steps
        for link in option.rationale:
            assert link.evidence_ids
            assert set(link.evidence_ids) <= known
            assert all(
                not evidence_id.startswith("metric.unknown")
                for evidence_id in link.evidence_ids
            )

    assert {item.calculation_id for item in result.calculations} == {
        "calc.sla_misses",
        "calc.excluded_share",
        "calc.backlog_overdue_share",
    }
    assert result.recommendations == result.solution_options.options

    discover = [event for event in result.trace if event.step == "discover_card"]
    send = [event for event in result.trace if event.step == "send_task"]
    assert {event.skill_id for event in discover} == {
        EVIDENCE_SKILL_ID,
        SOLUTION_SKILL_ID,
    }
    assert {event.skill_id for event in send} == {
        EVIDENCE_SKILL_ID,
        SOLUTION_SKILL_ID,
    }
    assert all(event.state == "TASK_STATE_COMPLETED" for event in send)
    assert all(event.task_id for event in send)
    assert all(event.context_id for event in send)

    assert ("GET", "/.well-known/agent-card.json", None, None) in evidence_seen
    assert ("GET", "/.well-known/agent-card.json", None, None) in solution_seen
    assert evidence_posts_after_first
    assert solution_posts_after_first
    assert all(item[2] == "SendMessage" for item in evidence_posts_after_first)
    assert all(item[2] == "SendMessage" for item in solution_posts_after_first)

    assert duplicate.trace[-1].step == "duplicate_replay"
    assert duplicate.trace[:-1] == result.trace
    assert [
        item for item in evidence_seen if item[0] == "POST"
    ] == evidence_posts_after_first
    assert [
        item for item in solution_seen if item[0] == "POST"
    ] == solution_posts_after_first

    summary = render_summary(result)
    assert summary.request_id == request_id
    assert len(summary.metrics) == 13
    assert len(summary.task_evidence) == 2
    assert summary.options == result.solution_options.options
    assert "Synthetic data only." in summary.rendered_markdown
    assert "No hosted model, deployment, or business action." in (
        summary.rendered_markdown
    )
    assert "TASK_STATE_COMPLETED" in summary.rendered_markdown
