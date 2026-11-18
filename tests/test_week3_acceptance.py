"""Persisted Week 3 acceptance evidence checks."""

from __future__ import annotations

import json
from pathlib import Path

from transformation_workbench.a2a.contracts import REQUIRED_METRIC_FIELDS

TRACE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "evidence"
    / "a2a-trace-20261115.json"
)


def _trace() -> dict:
    return json.loads(TRACE_PATH.read_text(encoding="utf-8"))


def test_persisted_trace_proves_discovery_and_both_task_exchanges() -> None:
    trace = _trace()
    events = trace["trace"]
    assert trace["request_id"] == "goose-a2a-002"
    assert trace["summon_load"] == {
        "source": "a2a-coordinator",
        "loaded": True,
    }
    assert "a2a-coordinator__run_a2a_diagnosis" in trace["advertised_tools"]
    assert "calculate_baseline_metrics" not in trace["advertised_tools"]
    assert "list_case_exceptions" not in trace["advertised_tools"]
    assert "get_case_details" not in trace["advertised_tools"]

    discovers = [item for item in events if item["step"] == "discover_card"]
    sends = [item for item in events if item["step"] == "send_task"]
    assert {item["skill_id"] for item in discovers} == {
        "workbench_evidence",
        "solution_options",
    }
    assert {item["skill_id"] for item in sends} == {
        "workbench_evidence",
        "solution_options",
    }
    assert all(item["method"] == "GET" for item in discovers)
    assert all(item["method"] == "POST" for item in sends)
    assert all(item["state"] == "TASK_STATE_COMPLETED" for item in sends)
    assert all(item["task_id"] for item in sends)
    assert all(item["context_id"] for item in sends)
    assert trace["tool_result_is_error"] is False


def test_persisted_trace_metrics_are_complete_and_fixture_backed() -> None:
    trace = _trace()
    assert set(trace["metrics"]) == set(REQUIRED_METRIC_FIELDS)
    assert trace["metrics"]["input_rows"] == 15
    assert trace["metrics"]["measurable_closed"] == 9
    assert trace["metrics"]["sla_met_percent"] == 66.7
    assert trace["metrics"]["rework_rate_percent"] == 22.2
    assert trace["metrics"]["backlog_cases"] == 2
    assert trace["metrics"]["backlog_overdue"] == 1
    assert trace["metrics"]["excluded_count"] == 4
    assert trace["options"] == [
        "option-triage-backlog",
        "option-data-quality",
        "option-rework-review",
    ]
    assert any("No hosted model" in item for item in trace["limitations"])


def test_persisted_trace_contains_no_secret_material() -> None:
    text = TRACE_PATH.read_text(encoding="utf-8").lower()
    for marker in ("api_key", "api-key", "bearer ", "password", "secret", "sk-"):
        assert marker not in text


def test_goose_summary_evaluation_is_honestly_failed_pending() -> None:
    path = TRACE_PATH.with_name(
        "goose-summary-evaluation-20261115.json"
    )
    evaluation = json.loads(path.read_text(encoding="utf-8"))
    assert evaluation["tool_call_succeeded"] is True
    assert evaluation["final_text_equals_summary"] is False
    assert evaluation["final_text_contains_summary"] is False
    assert evaluation["hosted_model_used"] is False
    assert evaluation["outcome"] == "failed_pending_stronger_local_model"
