"""Phase 2 coordinator failure and protocol-boundary tests."""

from __future__ import annotations

import pytest
from a2a.helpers import new_text_message
from a2a.types import Role, SendMessageResponse

from transformation_workbench.a2a.contracts import ProtocolTraceEvent
from transformation_workbench.a2a.evidence_specialist import (
    EVIDENCE_SKILL_ID,
    build_agent_card as build_evidence_card,
    build_app as build_evidence_app,
)
from transformation_workbench.a2a.evidence_source import EvidenceSourceError
from transformation_workbench.a2a.phase2_coordinator import (
    CoordinatorError,
    Phase2Coordinator,
    _require_task,
)
from transformation_workbench.a2a.solution_designer import (
    build_agent_card as build_solution_card,
    build_app as build_solution_app,
)

from .phase2_helpers import (
    CancelingExecutor,
    EmptyArtifactExecutor,
    FailingExecutor,
    SlowExecutor,
    StaticArtifactExecutor,
    StaticEvidenceSource,
    build_specialist_app,
    free_loopback_port,
    running_server,
    valid_evidence_pack,
    valid_solution_payload,
)


@pytest.mark.anyio
async def test_dual_real_a2a_exchange_and_duplicate_replay() -> None:
    request_id = "phase2-protocol"
    pack = valid_evidence_pack(request_id=request_id)
    source = StaticEvidenceSource(pack)

    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, evidence_seen):
        async with running_server(build_solution_app) as (
            solution_url,
            solution_seen,
        ):
            coordinator = Phase2Coordinator(
                evidence_url,
                solution_url,
                timeout=5.0,
                max_retries=0,
            )
            first = await coordinator.run(
                request_id,
                ["C-009", "C-006", "C-014"],
            )
            evidence_posts = [
                item for item in evidence_seen if item[0] == "POST"
            ]
            solution_posts = [
                item for item in solution_seen if item[0] == "POST"
            ]
            second = await coordinator.run(
                request_id,
                ["C-009", "C-006", "C-014"],
            )

    assert source.calls == 1
    assert first.measured_facts.metrics["input_rows"].value == 15
    assert first.measured_facts.metrics["measurable_closed"].value == 9
    assert first.measured_facts.metrics["sla_met_percent"].value == 66.7
    assert first.measured_facts.metrics["excluded_count"].value == 4
    assert first.measured_facts.metrics["backlog_cases"].value == 2
    assert first.solution_options.options
    assert second.trace[-1].step == "duplicate_replay"
    assert second.trace[:-1] == first.trace
    assert [
        item for item in evidence_seen if item[0] == "POST"
    ] == evidence_posts
    assert [
        item for item in solution_seen if item[0] == "POST"
    ] == solution_posts
    assert ("GET", "/.well-known/agent-card.json", None, None) in evidence_seen
    assert ("GET", "/.well-known/agent-card.json", None, None) in solution_seen
    assert all(item[2] == "SendMessage" for item in evidence_posts)
    assert all(item[2] == "SendMessage" for item in solution_posts)
    skill_ids = {event.skill_id for event in first.trace if event.step == "send_task"}
    assert skill_ids == {EVIDENCE_SKILL_ID, "solution_options"}
    assert all(
        event.state == "TASK_STATE_COMPLETED"
        for event in first.trace
        if event.step == "send_task"
    )


@pytest.mark.anyio
async def test_duplicate_request_with_different_inputs_is_rejected() -> None:
    request_id = "phase2-conflict"
    pack = valid_evidence_pack(request_id=request_id, case_ids=["C-009"])
    source = StaticEvidenceSource(pack)
    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, _):
        async with running_server(build_solution_app) as (solution_url, _):
            coordinator = Phase2Coordinator(
                evidence_url,
                solution_url,
                timeout=5.0,
                max_retries=0,
            )
            await coordinator.run(request_id, ["C-009"])
            with pytest.raises(CoordinatorError) as excinfo:
                await coordinator.run(request_id, ["C-006"])
    assert excinfo.value.code == "request_conflict"
    assert source.calls == 1


@pytest.mark.anyio
async def test_specialist_unavailable_is_bounded() -> None:
    coordinator = Phase2Coordinator(
        f"http://127.0.0.1:{free_loopback_port()}",
        f"http://127.0.0.1:{free_loopback_port()}",
        timeout=5.0,
        max_retries=1,
    )
    with pytest.raises(CoordinatorError) as excinfo:
        await coordinator.run("phase2-unavailable", ["C-009"])
    assert excinfo.value.code == "specialist_unavailable"
    assert "2 attempt(s)" in excinfo.value.message
    assert excinfo.value.trace == ()


@pytest.mark.anyio
async def test_a2a_timeout_is_bounded() -> None:
    card = build_evidence_card("http://127.0.0.1:1")
    executor = SlowExecutor(delay=0.5)

    def evidence_factory(base_url: str):
        card.supported_interfaces[0].url = base_url
        return build_specialist_app(base_url, card, executor)

    async with running_server(evidence_factory) as (evidence_url, _):
        coordinator = Phase2Coordinator(
            evidence_url,
            f"http://127.0.0.1:{free_loopback_port()}",
            timeout=0.1,
            max_retries=0,
        )
        with pytest.raises(CoordinatorError) as excinfo:
            await coordinator.run("phase2-timeout", ["C-009"])
    assert excinfo.value.code == "a2a_timeout"


@pytest.mark.anyio
async def test_timeout_retries_are_bounded() -> None:
    card = build_evidence_card("http://127.0.0.1:1")
    executor = SlowExecutor(delay=0.5)

    def evidence_factory(base_url: str):
        card.supported_interfaces[0].url = base_url
        return build_specialist_app(base_url, card, executor)

    async with running_server(evidence_factory) as (evidence_url, _):
        coordinator = Phase2Coordinator(
            evidence_url,
            f"http://127.0.0.1:{free_loopback_port()}",
            timeout=0.1,
            max_retries=1,
        )
        with pytest.raises(CoordinatorError) as excinfo:
            await coordinator.run("phase2-timeout-retry", ["C-009"])
    assert excinfo.value.code == "a2a_timeout"
    assert "2 attempt(s)" in excinfo.value.message


@pytest.mark.anyio
async def test_incomplete_evidence_is_rejected_at_boundary() -> None:
    request_id = "phase2-incomplete"
    pack = valid_evidence_pack(request_id=request_id, case_ids=["C-009"])
    payload = pack.model_dump(mode="json")
    payload["missing_data"].append(
        {"field": "exceptions", "reason": "synthetic missing data"}
    )
    bad_pack = pack.model_validate(payload)
    source = StaticEvidenceSource(bad_pack)

    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, _):
        coordinator = Phase2Coordinator(
            evidence_url,
            f"http://127.0.0.1:{free_loopback_port()}",
            timeout=5.0,
            max_retries=0,
        )
        with pytest.raises(CoordinatorError) as excinfo:
            await coordinator.run(request_id, ["C-009"])
    assert excinfo.value.code == "incomplete_evidence"


@pytest.mark.anyio
async def test_solution_failure_after_evidence_success_is_whole_failure() -> None:
    request_id = "phase2-partial"
    pack = valid_evidence_pack(request_id=request_id, case_ids=["C-009"])
    source = StaticEvidenceSource(pack)

    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, evidence_seen):
        async with running_server(
            lambda url: build_specialist_app(
                url,
                build_solution_card(url),
                FailingExecutor("synthetic solution failure"),
            )
        ) as (solution_url, _):
            coordinator = Phase2Coordinator(
                evidence_url,
                solution_url,
                timeout=5.0,
                max_retries=0,
            )
            with pytest.raises(CoordinatorError) as excinfo:
                await coordinator.run(request_id, ["C-009"])

    assert excinfo.value.code == "task_failure"
    assert source.calls == 1
    assert any(item[0] == "POST" for item in evidence_seen)
    assert not any(
        event.step == "send_task"
        and event.skill_id == "solution_options"
        for event in excinfo.value.trace
    )


@pytest.mark.anyio
async def test_task_failure_and_cancel_stop_safely() -> None:
    for executor in (
        FailingExecutor("synthetic task failure"),
        CancelingExecutor(),
    ):
        card = build_evidence_card("http://127.0.0.1:1")

        def evidence_factory(base_url: str, executor=executor, card=card):
            card.supported_interfaces[0].url = base_url
            return build_specialist_app(base_url, card, executor)

        async with running_server(evidence_factory) as (evidence_url, _):
            coordinator = Phase2Coordinator(
                evidence_url,
                f"http://127.0.0.1:{free_loopback_port()}",
                timeout=5.0,
                max_retries=0,
            )
            with pytest.raises(CoordinatorError) as excinfo:
                await coordinator.run("phase2-task-failure", ["C-009"])
        assert excinfo.value.code == "task_failure"
        assert "TASK_STATE_" in excinfo.value.message


def test_non_task_response_is_rejected() -> None:
    response = SendMessageResponse()
    response.message.CopyFrom(
        new_text_message("not a task", role=Role.ROLE_AGENT)
    )
    with pytest.raises(CoordinatorError) as excinfo:
        _require_task(response, "workbench_evidence")
    assert excinfo.value.code == "non_task_response"

    with pytest.raises(CoordinatorError) as excinfo:
        _require_task(None, "workbench_evidence")
    assert excinfo.value.code == "non_task_response"


@pytest.mark.anyio
async def test_empty_and_wrong_mime_artifacts_are_rejected() -> None:
    card = build_evidence_card("http://127.0.0.1:1")

    def empty_factory(base_url: str):
        card.supported_interfaces[0].url = base_url
        return build_specialist_app(base_url, card, EmptyArtifactExecutor())

    async with running_server(empty_factory) as (evidence_url, _):
        coordinator = Phase2Coordinator(
            evidence_url,
            f"http://127.0.0.1:{free_loopback_port()}",
            timeout=5.0,
            max_retries=0,
        )
        with pytest.raises(CoordinatorError) as excinfo:
            await coordinator.run("phase2-empty", ["C-009"])
    assert excinfo.value.code == "malformed_result"

    def text_factory(base_url: str):
        card.supported_interfaces[0].url = base_url
        return build_specialist_app(
            base_url,
            card,
            StaticArtifactExecutor({"ok": True}, media_type="text/plain"),
        )

    async with running_server(text_factory) as (evidence_url, _):
        coordinator = Phase2Coordinator(
            evidence_url,
            f"http://127.0.0.1:{free_loopback_port()}",
            timeout=5.0,
            max_retries=0,
        )
        with pytest.raises(CoordinatorError) as excinfo:
            await coordinator.run("phase2-wrong-mime", ["C-009"])
    assert excinfo.value.code == "malformed_result"


@pytest.mark.anyio
async def test_invalid_evidence_and_solution_schemas_are_rejected() -> None:
    card = build_evidence_card("http://127.0.0.1:1")

    def bad_evidence_factory(base_url: str):
        card.supported_interfaces[0].url = base_url
        return build_specialist_app(
            base_url,
            card,
            StaticArtifactExecutor({"foo": "bar"}),
        )

    async with running_server(bad_evidence_factory) as (evidence_url, _):
        coordinator = Phase2Coordinator(
            evidence_url,
            f"http://127.0.0.1:{free_loopback_port()}",
            timeout=5.0,
            max_retries=0,
        )
        with pytest.raises(CoordinatorError) as excinfo:
            await coordinator.run("phase2-bad-evidence", ["C-009"])
    assert excinfo.value.code == "invalid_evidence_pack"

    pack = valid_evidence_pack(
        request_id="phase2-bad-solution",
        case_ids=["C-009"],
    )
    source = StaticEvidenceSource(pack)

    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, _):
        async with running_server(
            lambda url: build_specialist_app(
                url,
                build_solution_card(url),
                StaticArtifactExecutor({"foo": "bar"}),
            )
        ) as (solution_url, _):
            coordinator = Phase2Coordinator(
                evidence_url,
                solution_url,
                timeout=5.0,
                max_retries=0,
            )
            with pytest.raises(CoordinatorError) as excinfo:
                await coordinator.run("phase2-bad-solution", ["C-009"])
    assert excinfo.value.code == "invalid_solution_options"

    bad_solution_payload = valid_solution_payload(pack)
    bad_solution_payload["options"][0]["rationale"][0]["evidence_ids"] = [
        "metric.unknown"
    ]

    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, _):
        async with running_server(
            lambda url: build_specialist_app(
                url,
                build_solution_card(url),
                StaticArtifactExecutor(bad_solution_payload),
            )
        ) as (solution_url, _):
            coordinator = Phase2Coordinator(
                evidence_url,
                solution_url,
                timeout=5.0,
                max_retries=0,
            )
            with pytest.raises(CoordinatorError) as excinfo:
                await coordinator.run("phase2-bad-solution", ["C-009"])
    assert excinfo.value.code == "unknown_evidence_reference"


@pytest.mark.anyio
async def test_evidence_pack_request_mismatch_is_rejected_at_boundary() -> None:
    request_id = "phase2-evidence-mismatch"
    pack = valid_evidence_pack(request_id="different-request")
    card = build_evidence_card("http://127.0.0.1:1")

    def evidence_factory(base_url: str):
        card.supported_interfaces[0].url = base_url
        return build_specialist_app(
            base_url,
            card,
            StaticArtifactExecutor(pack.model_dump(mode="json")),
        )

    async with running_server(evidence_factory) as (evidence_url, _):
        coordinator = Phase2Coordinator(
            evidence_url,
            f"http://127.0.0.1:{free_loopback_port()}",
            timeout=5.0,
            max_retries=0,
        )
        with pytest.raises(CoordinatorError) as excinfo:
            await coordinator.run(request_id, ["C-009"])
    assert excinfo.value.code == "request_mismatch"


@pytest.mark.anyio
async def test_solution_options_request_mismatch_is_rejected_at_boundary() -> None:
    request_id = "phase2-solution-mismatch"
    pack = valid_evidence_pack(request_id=request_id, case_ids=["C-009"])
    source = StaticEvidenceSource(pack)
    bad_payload = valid_solution_payload(pack)
    bad_payload["request_id"] = "different-request"

    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, _):
        async with running_server(
            lambda url: build_specialist_app(
                url,
                build_solution_card(url),
                StaticArtifactExecutor(bad_payload),
            )
        ) as (solution_url, _):
            coordinator = Phase2Coordinator(
                evidence_url,
                solution_url,
                timeout=5.0,
                max_retries=0,
            )
            with pytest.raises(CoordinatorError) as excinfo:
                await coordinator.run(request_id, ["C-009"])
    assert excinfo.value.code == "request_mismatch"


@pytest.mark.anyio
async def test_requested_case_set_mismatch_is_rejected_at_boundary() -> None:
    request_id = "phase2-case-set-mismatch"
    pack = valid_evidence_pack(request_id=request_id, case_ids=["C-006"])
    source = StaticEvidenceSource(pack)

    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, _):
        coordinator = Phase2Coordinator(
            evidence_url,
            f"http://127.0.0.1:{free_loopback_port()}",
            timeout=5.0,
            max_retries=0,
        )
        with pytest.raises(CoordinatorError) as excinfo:
            await coordinator.run(request_id, ["C-009"])
    assert excinfo.value.code == "case_set_mismatch"


@pytest.mark.anyio
async def test_non_loopback_card_is_rejected_at_phase2_boundary() -> None:
    card = build_evidence_card("http://127.0.0.1:1")
    card.supported_interfaces[0].url = "http://192.0.2.10:9999"

    def evidence_factory(base_url: str):
        return build_specialist_app(
            base_url,
            card,
            StaticArtifactExecutor({"foo": "bar"}),
        )

    async with running_server(evidence_factory) as (evidence_url, _):
        coordinator = Phase2Coordinator(
            evidence_url,
            f"http://127.0.0.1:{free_loopback_port()}",
            timeout=5.0,
            max_retries=0,
        )
        with pytest.raises(CoordinatorError) as excinfo:
            await coordinator.run("phase2-non-loopback-card", ["C-009"])
    assert excinfo.value.code == "invalid_agent_card"


@pytest.mark.anyio
async def test_self_reported_metric_mismatch_is_rejected_at_boundary() -> None:
    request_id = "phase2-metric-mismatch"
    pack = valid_evidence_pack(request_id=request_id, case_ids=["C-009"])
    payload = pack.model_dump(mode="json")
    payload["metrics"]["input_rows"]["value"] = 99
    bad_pack = pack.model_validate(payload)
    source = StaticEvidenceSource(bad_pack)

    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, _):
        coordinator = Phase2Coordinator(
            evidence_url,
            f"http://127.0.0.1:{free_loopback_port()}",
            timeout=5.0,
            max_retries=0,
        )
        with pytest.raises(CoordinatorError) as excinfo:
            await coordinator.run(request_id, ["C-009"])
    assert excinfo.value.code == "metric_value_mismatch"


@pytest.mark.anyio
async def test_coordinator_ignores_environment_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_id = "phase2-proxy"
    pack = valid_evidence_pack(request_id=request_id, case_ids=["C-009"])
    source = StaticEvidenceSource(pack)
    proxy_url = f"http://127.0.0.1:{free_loopback_port()}"
    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.setenv(name, proxy_url)
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setenv("no_proxy", "")

    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, _):
        async with running_server(build_solution_app) as (solution_url, _):
            coordinator = Phase2Coordinator(
                evidence_url,
                solution_url,
                timeout=5.0,
                max_retries=0,
            )
            result = await coordinator.run(request_id, ["C-009"])

    assert result.measured_facts.request_id == request_id
    assert result.solution_options.request_id == request_id


@pytest.mark.anyio
async def test_unsupported_savings_claim_is_rejected_over_a2a() -> None:
    pack = valid_evidence_pack(
        request_id="phase2-claim",
        case_ids=["C-009"],
    )
    source = StaticEvidenceSource(pack)
    bad_payload = valid_solution_payload(pack)
    bad_payload["options"][0]["description"] = (
        "This option will save $100,000 annually."
    )

    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, _):
        async with running_server(
            lambda url: build_specialist_app(
                url,
                build_solution_card(url),
                StaticArtifactExecutor(bad_payload),
            )
        ) as (solution_url, _):
            coordinator = Phase2Coordinator(
                evidence_url,
                solution_url,
                timeout=5.0,
                max_retries=0,
            )
            with pytest.raises(CoordinatorError) as excinfo:
                await coordinator.run("phase2-claim", ["C-009"])
    assert excinfo.value.code == "unsupported_claim"


@pytest.mark.anyio
async def test_unsupported_percentage_claim_is_rejected_over_a2a() -> None:
    pack = valid_evidence_pack(
        request_id="phase2-percentage-claim",
        case_ids=["C-009"],
    )
    source = StaticEvidenceSource(pack)
    bad_payload = valid_solution_payload(pack)
    bad_payload["options"][0]["description"] = (
        "This option will reduce cycle time by 50%."
    )

    async with running_server(
        lambda url: build_evidence_app(url, source=source)
    ) as (evidence_url, _):
        async with running_server(
            lambda url: build_specialist_app(
                url,
                build_solution_card(url),
                StaticArtifactExecutor(bad_payload),
            )
        ) as (solution_url, _):
            coordinator = Phase2Coordinator(
                evidence_url,
                solution_url,
                timeout=5.0,
                max_retries=0,
            )
            with pytest.raises(CoordinatorError) as excinfo:
                await coordinator.run("phase2-percentage-claim", ["C-009"])
    assert excinfo.value.code == "unsupported_claim"


class _FailingEvidenceSource:
    async def collect(self, request_id: str, case_ids: list[str]):
        raise EvidenceSourceError(
            "mcp_resource_unavailable",
            "synthetic missing resource",
        )


@pytest.mark.anyio
async def test_mcp_resource_failure_crosses_a2a_as_task_failure() -> None:
    card = build_evidence_card("http://127.0.0.1:1")

    def factory(base_url: str):
        card.supported_interfaces[0].url = base_url
        return build_evidence_app(base_url, source=_FailingEvidenceSource())

    async with running_server(factory) as (evidence_url, _):
        coordinator = Phase2Coordinator(
            evidence_url,
            f"http://127.0.0.1:{free_loopback_port()}",
            timeout=5.0,
            max_retries=0,
        )
        with pytest.raises(CoordinatorError) as excinfo:
            await coordinator.run("phase2-mcp-failure", ["C-009"])
    assert excinfo.value.code == "task_failure"
    assert "mcp_resource_unavailable" in excinfo.value.message


def test_trace_event_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError):
        ProtocolTraceEvent(
            step="discover_card",
            agent="x",
            method="GET",
            path="/",
            skill_id="x",
            unexpected="value",
        )
