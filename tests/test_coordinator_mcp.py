"""Tests for the Goose-facing coordinator MCP surface and local runtime."""

from __future__ import annotations

import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.mcpserver.exceptions import ToolError

from transformation_workbench import coordinator_mcp_server
from transformation_workbench.a2a.contracts import (
    CoordinatorResult,
    ProtocolTraceEvent,
)
from transformation_workbench.a2a.local_runtime import run_local_diagnosis
from transformation_workbench.a2a.phase2_coordinator import CoordinatorError
from transformation_workbench.a2a.solution_designer import design_options

from .phase2_helpers import StaticEvidenceSource, valid_evidence_pack


def _fake_result(request_id: str, case_ids: list[str]) -> CoordinatorResult:
    pack = valid_evidence_pack(request_id=request_id, case_ids=case_ids)
    return CoordinatorResult(
        request_id=request_id,
        measured_facts=pack,
        calculations=[],
        assumptions=[],
        solution_options=design_options(pack),
        trace=[
            ProtocolTraceEvent(
                step="discover_card",
                agent="Evidence",
                method="GET",
                path="/.well-known/agent-card.json",
                skill_id="workbench_evidence",
            ),
            ProtocolTraceEvent(
                step="send_task",
                agent="Evidence",
                method="POST",
                path="/",
                skill_id="workbench_evidence",
                task_id=f"evidence-task-{request_id}",
                context_id="evidence-context",
                state="TASK_STATE_COMPLETED",
            ),
            ProtocolTraceEvent(
                step="discover_card",
                agent="Solution",
                method="GET",
                path="/.well-known/agent-card.json",
                skill_id="solution_options",
            ),
            ProtocolTraceEvent(
                step="send_task",
                agent="Solution",
                method="POST",
                path="/",
                skill_id="solution_options",
                task_id=f"solution-task-{request_id}",
                context_id="solution-context",
                state="TASK_STATE_COMPLETED",
            ),
        ],
    )


@pytest.mark.anyio
async def test_local_runtime_routes_real_a2a_with_fake_evidence_source() -> None:
    request_id = "local-fake"
    pack = valid_evidence_pack(request_id=request_id, case_ids=["C-009"])
    result = await run_local_diagnosis(
        request_id,
        ["C-009"],
        timeout=5.0,
        max_retries=0,
        evidence_source=StaticEvidenceSource(pack),
    )

    assert result.request_id == request_id
    assert result.measured_facts.request_id == request_id
    assert result.measured_facts.metrics["input_rows"].value == 15
    assert result.solution_options.request_id == request_id
    skills = {
        event.skill_id
        for event in result.trace
        if event.step == "send_task"
    }
    assert skills == {"workbench_evidence", "solution_options"}
    assert all(
        event.state == "TASK_STATE_COMPLETED"
        for event in result.trace
        if event.step == "send_task"
    )


def test_coordinator_mcp_accepts_string_case_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[str]] = []
    fake_result = _fake_result("mcp-string", ["C-009", "C-006", "C-014"])

    async def fake_run(request_id, case_ids):
        captured.append(list(case_ids))
        return fake_result

    monkeypatch.setattr(coordinator_mcp_server, "run_local_diagnosis", fake_run)
    result = coordinator_mcp_server.run_a2a_diagnosis(
        "mcp-string",
        "['C-009', 'C-006', 'C-014']",
    )
    assert result.request_id == "mcp-string"
    assert captured == [["C-009", "C-006", "C-014"]]


def test_coordinator_mcp_replay_uses_process_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    async def fake_run(request_id, case_ids):
        calls.append(list(case_ids))
        return _fake_result(request_id, list(case_ids))

    monkeypatch.setattr(coordinator_mcp_server, "run_local_diagnosis", fake_run)
    first = coordinator_mcp_server.run_a2a_diagnosis(
        "mcp-replay",
        ["C-009"],
    )
    second = coordinator_mcp_server.run_a2a_diagnosis(
        "mcp-replay",
        ["C-009"],
    )

    assert calls == [["C-009"]]
    assert first.request_id == second.request_id == "mcp-replay"
    assert second.trace[-1].step == "duplicate_replay"

    with pytest.raises(ToolError, match="request_conflict"):
        coordinator_mcp_server.run_a2a_diagnosis(
            "mcp-replay",
            ["C-006"],
        )


def test_coordinator_mcp_maps_bounded_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail(*args, **kwargs):
        raise CoordinatorError("a2a_timeout", "synthetic timeout")

    monkeypatch.setattr(coordinator_mcp_server, "run_local_diagnosis", fail)
    with pytest.raises(ToolError, match="a2a_timeout"):
        coordinator_mcp_server.run_a2a_diagnosis("mcp-failure", ["C-009"])


@pytest.mark.anyio
async def test_coordinator_mcp_exposes_only_one_tool_and_runs_end_to_end() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "transformation_workbench.coordinator_mcp_server"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert [tool.name for tool in tools.tools] == ["run_a2a_diagnosis"]

            result = await session.call_tool(
                "run_a2a_diagnosis",
                {
                    "request_id": "mcp-e2e",
                    "case_ids": ["C-009"],
                },
            )
            replay = await session.call_tool(
                "run_a2a_diagnosis",
                {
                    "request_id": "mcp-e2e",
                    "case_ids": ["C-009"],
                },
            )

    assert not result.is_error
    assert not replay.is_error
    assert replay.structured_content["trace"][-1]["step"] == "duplicate_replay"
    assert isinstance(result.structured_content, dict)
    payload = result.structured_content
    assert payload["request_id"] == "mcp-e2e"
    assert payload["measured_facts"]["request_id"] == "mcp-e2e"
    assert payload["measured_facts"]["metrics"]["input_rows"]["value"] == 15
    assert payload["solution_options"]["request_id"] == "mcp-e2e"
    skills = {
        event["skill_id"]
        for event in payload["trace"]
        if event["step"] == "send_task"
    }
    assert skills == {"workbench_evidence", "solution_options"}
    assert payload["summary"]["schema_version"] == "1.0"
    assert payload["summary"]["request_id"] == "mcp-e2e"
    rendered = payload["summary"]["rendered_markdown"]
    assert "task" in rendered
    assert "TASK_STATE_COMPLETED" in rendered
    assert "input_rows: 15 count" in rendered
    assert "option-triage-backlog" in rendered
