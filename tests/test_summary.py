"""Deterministic A2A summary rendering tests."""

from __future__ import annotations

import json

import pytest

from transformation_workbench.a2a import coordinator_cli
from transformation_workbench.a2a.claims import UnsupportedClaimError
from transformation_workbench.a2a.contracts import (
    Calculation,
    CoordinatorResult,
    ProtocolTraceEvent,
)
from transformation_workbench.a2a.solution_designer import design_options
from transformation_workbench.a2a.summary import SummaryError, render_summary

from .phase2_helpers import valid_evidence_pack


def _result(request_id: str = "summary-test") -> CoordinatorResult:
    pack = valid_evidence_pack(request_id=request_id, case_ids=["C-009"])
    options = design_options(pack)
    return CoordinatorResult(
        request_id=request_id,
        measured_facts=pack,
        calculations=[
            Calculation(
                calculation_id="calc.sla_misses",
                label="SLA misses",
                formula="measurable_closed - sla_met_count",
                value=3,
                unit="count",
                evidence_ids=[
                    "metric.measurable_closed",
                    "metric.sla_met_count",
                ],
            )
        ],
        assumptions=["Synthetic test result."],
        solution_options=options,
        trace=[
            ProtocolTraceEvent(
                step="discover_card",
                agent="Workbench Evidence Specialist",
                method="GET",
                path="/.well-known/agent-card.json",
                skill_id="workbench_evidence",
            ),
            ProtocolTraceEvent(
                step="send_task",
                agent="Workbench Evidence Specialist",
                method="POST",
                path="/",
                skill_id="workbench_evidence",
                task_id="task-evidence",
                context_id="context-evidence",
                state="TASK_STATE_COMPLETED",
            ),
            ProtocolTraceEvent(
                step="discover_card",
                agent="Workbench Solution Designer",
                method="GET",
                path="/.well-known/agent-card.json",
                skill_id="solution_options",
            ),
            ProtocolTraceEvent(
                step="send_task",
                agent="Workbench Solution Designer",
                method="POST",
                path="/",
                skill_id="solution_options",
                task_id="task-solution",
                context_id="context-solution",
                state="TASK_STATE_COMPLETED",
            ),
        ],
    )


def test_summary_is_deterministic_and_contains_required_content() -> None:
    result = _result()
    first = render_summary(result)
    second = render_summary(result)
    assert first == second
    assert first.schema_version == "1.0"
    assert first.request_id == "summary-test"
    assert {item.skill_id for item in first.discoveries} == {
        "workbench_evidence",
        "solution_options",
    }
    assert {item.skill_id for item in first.task_evidence} == {
        "workbench_evidence",
        "solution_options",
    }
    assert len(first.metrics) == 13
    assert first.calculations == result.calculations
    assert first.assumptions == result.assumptions
    assert first.options
    assert first.limitations
    rendered = first.rendered_markdown
    assert "# A2A diagnosis: summary-test" in rendered
    assert "card discovered" in rendered
    assert "task-evidence" in rendered
    assert "task-solution" in rendered
    assert "TASK_STATE_COMPLETED" in rendered
    assert "input_rows: 15 count" in rendered
    assert "sla_met_percent: 66.7 percent" in rendered
    assert (
        "SLA misses: 3 count (measurable_closed - sla_met_count; "
        "evidence: metric.measurable_closed, metric.sla_met_count)"
    ) in rendered
    assert "option-triage-backlog" in rendered
    assert "Synthetic data only." in rendered


def test_report_includes_complete_values_provenance_and_traceability() -> None:
    report = render_summary(_result()).rendered_markdown

    assert "## Data provenance" in report
    assert "Resource: workbench://process-context" in report
    assert "Resource SHA-256:" in report
    assert "evidence: metric.input_rows; source: calculate_baseline_metrics" in report
    assert "evidence: metric.sla_met_percent; source: calculate_baseline_metrics" in report
    assert "Exception C-006 row 7: INCOMPLETE_MISSING_CLOSED_AT" in report
    assert "evidence: exception.row.7; source: list_case_exceptions" in report
    assert "Case C-009 row 10, measurable" in report
    assert "evidence: case.C-009; source: get_case_details" in report
    assert "cycle_time_hours=24" in report
    assert "sla_met=True" in report
    assert "Trade-offs:" in report
    assert "Validation:" in report
    assert "Synthetic data only." in report
    assert "No hosted model, deployment, or business action." in report


def test_report_rejects_unsupported_business_claim() -> None:
    result = _result()
    option = result.solution_options.options[0].model_copy(
        update={"title": "Save 100% and reduce cost by $100,000"}
    )
    broken = result.model_copy(
        update={
            "solution_options": result.solution_options.model_copy(
                update={"options": [option]}
            )
        }
    )
    with pytest.raises(UnsupportedClaimError):
        render_summary(broken)


def test_cli_markdown_prints_the_deterministic_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _result("cli-report")

    async def fake_run(*args, **kwargs):
        return result

    monkeypatch.setattr(coordinator_cli, "run_local_diagnosis", fake_run)
    coordinator_cli.main(
        ["--request-id", "cli-report", "--format", "markdown"]
    )
    captured = capsys.readouterr()

    assert captured.out == render_summary(result).rendered_markdown
    assert captured.err == ""


def test_cli_markdown_reports_a_bounded_summary_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _result("cli-report")

    async def fake_run(*args, **kwargs):
        return result

    def fake_render(_result):
        raise SummaryError("incomplete_metrics", "Required metric is missing.")

    monkeypatch.setattr(coordinator_cli, "run_local_diagnosis", fake_run)
    monkeypatch.setattr(coordinator_cli, "render_summary", fake_render)
    with pytest.raises(SystemExit) as error:
        coordinator_cli.main(
            ["--request-id", "cli-report", "--format", "markdown"]
        )
    captured = capsys.readouterr()

    assert error.value.code == 1
    assert json.loads(captured.out) == {
        "error": {
            "code": "incomplete_metrics",
            "message": "Required metric is missing.",
        }
    }
    assert captured.err == ""


def test_summary_rejects_incomplete_trace() -> None:
    result = _result()
    broken = result.model_copy(
        update={
            "trace": [
                event
                for event in result.trace
                if not (
                    event.step == "send_task"
                    and event.skill_id == "solution_options"
                )
            ]
        }
    )
    with pytest.raises(SummaryError, match="incomplete_trace"):
        render_summary(broken)


def test_summary_rejects_missing_metric() -> None:
    result = _result()
    payload = result.measured_facts.model_dump(mode="json")
    del payload["metrics"]["sla_met_percent"]
    broken_pack = result.measured_facts.model_validate(payload)
    broken = result.model_copy(update={"measured_facts": broken_pack})
    with pytest.raises(SummaryError, match="incomplete_metrics"):
        render_summary(broken)


def test_summary_rejects_request_mismatch() -> None:
    result = _result()
    broken = result.model_copy(
        update={
            "solution_options": result.solution_options.model_copy(
                update={"request_id": "different"}
            )
        }
    )
    with pytest.raises(SummaryError, match="request_mismatch"):
        render_summary(broken)
