"""Week 3 Phase 1: real local A2A discovery and task round trip."""

import httpx
import pytest
from a2a.utils.errors import UnsupportedOperationError

from transformation_workbench.a2a.coordinator import (
    A2AError,
    discover_agent_card,
    run_echo_round_trip,
    send_echo_task,
)
from transformation_workbench.a2a.specialist import (
    ECHO_PREFIX,
    SPECIALIST_NAME,
    SPECIALIST_SKILL_ID,
    DeterministicEchoExecutor,
    build_agent_card,
    build_app,
)

from .phase2_helpers import (
    CancelingExecutor,
    FailingExecutor,
    SlowExecutor,
    StaticTextArtifactExecutor,
    build_specialist_app,
    free_loopback_port,
    running_server,
)


@pytest.mark.anyio
async def test_agent_card_discovery_over_loopback() -> None:
    async with running_server(build_app) as (base_url, seen_requests):
        agent_card = await discover_agent_card(base_url)

    assert (
        "GET",
        "/.well-known/agent-card.json",
        None,
        None,
    ) in seen_requests
    assert agent_card.name == SPECIALIST_NAME
    assert [skill.id for skill in agent_card.skills] == [SPECIALIST_SKILL_ID]
    assert agent_card.capabilities.streaming is False
    assert "text/plain" in agent_card.default_input_modes
    assert "text/plain" in agent_card.default_output_modes
    skill = agent_card.skills[0]
    assert "text/plain" in skill.input_modes
    assert "text/plain" in skill.output_modes
    assert [item.protocol_binding for item in agent_card.supported_interfaces] == [
        "JSONRPC"
    ]
    interface = agent_card.supported_interfaces[0]
    assert interface.url == base_url
    assert interface.protocol_version == "1.0"


@pytest.mark.anyio
async def test_real_a2a_task_round_trip() -> None:
    request_text = "phase1-preflight"
    async with running_server(build_app) as (base_url, seen_requests):
        agent_card = await discover_agent_card(base_url)
        exchange = await send_echo_task(agent_card, request_text)

    assert (
        "GET",
        "/.well-known/agent-card.json",
        None,
        None,
    ) in seen_requests
    assert ("POST", "/", "SendMessage", "2.0") in seen_requests
    assert exchange.agent_name == SPECIALIST_NAME
    assert exchange.task_id
    assert exchange.context_id
    assert exchange.state == "TASK_STATE_COMPLETED"
    assert exchange.artifact_text == f"{ECHO_PREFIX}{request_text}"


def _app_factory(card, executor):
    def factory(base_url: str):
        card.supported_interfaces[0].url = base_url
        return build_specialist_app(base_url, card, executor)

    return factory


@pytest.mark.anyio
async def test_direct_round_trip_helper_uses_real_a2a() -> None:
    async with running_server(build_app) as (base_url, seen_requests):
        exchange = await run_echo_round_trip(base_url, "phase1-direct")

    assert ("POST", "/", "SendMessage", "2.0") in seen_requests
    assert exchange.state == "TASK_STATE_COMPLETED"
    assert exchange.artifact_text == f"{ECHO_PREFIX}phase1-direct"


@pytest.mark.anyio
async def test_loopback_request_ignores_environment_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    async with running_server(build_app) as (base_url, _):
        exchange = await run_echo_round_trip(base_url, "phase1-proxy")

    assert exchange.artifact_text == f"{ECHO_PREFIX}phase1-proxy"


@pytest.mark.anyio
async def test_discover_rejects_non_loopback_argument() -> None:
    with pytest.raises(A2AError) as excinfo:
        await discover_agent_card("http://192.0.2.10:9999")
    assert excinfo.value.code == "invalid_endpoint"


def test_non_loopback_agent_card_is_rejected() -> None:
    with pytest.raises(ValueError, match="loopback"):
        build_agent_card("http://192.0.2.10:9999")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:9999/a2a",
        "http://127.0.0.1:9999/?x=1",
        "http://127.0.0.1:9999/#fragment",
        "http://user@127.0.0.1:9999",
    ],
)
def test_non_root_loopback_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="loopback root"):
        build_agent_card(url)


@pytest.mark.anyio
async def test_send_rejects_non_loopback_card_endpoint() -> None:
    card = build_agent_card("http://127.0.0.1:1")
    card.supported_interfaces[0].url = "http://192.0.2.10:9999"
    with pytest.raises(A2AError) as excinfo:
        await send_echo_task(card, "phase1-non-loopback")
    assert excinfo.value.code == "invalid_agent_card"


@pytest.mark.anyio
async def test_discovery_rejects_non_loopback_card_endpoint() -> None:
    card = build_agent_card("http://127.0.0.1:1")
    card.supported_interfaces[0].url = "http://192.0.2.10:9999"
    async with running_server(
        lambda url: build_specialist_app(
            url,
            card,
            DeterministicEchoExecutor(),
        )
    ) as (base_url, _):
        with pytest.raises(A2AError) as excinfo:
            await discover_agent_card(base_url)
    assert excinfo.value.code == "invalid_agent_card"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "executor",
    [
        FailingExecutor("synthetic task failure"),
        CancelingExecutor(),
    ],
)
async def test_failed_and_cancelled_tasks_are_bounded(executor) -> None:
    card = build_agent_card("http://127.0.0.1:1")
    async with running_server(_app_factory(card, executor)) as (base_url, _):
        with pytest.raises(A2AError) as excinfo:
            await send_echo_task(card, "phase1-task-state")
    assert excinfo.value.code == "task_failure"
    assert excinfo.value.state in {
        "TASK_STATE_FAILED",
        "TASK_STATE_CANCELED",
    }
    assert excinfo.value.task_id
    assert excinfo.value.context_id


@pytest.mark.anyio
async def test_connection_failure_is_bounded() -> None:
    card = build_agent_card(f"http://127.0.0.1:{free_loopback_port()}")
    with pytest.raises(A2AError) as excinfo:
        await send_echo_task(card, "phase1-unavailable")
    assert excinfo.value.code == "specialist_unavailable"


@pytest.mark.anyio
async def test_timeout_is_bounded() -> None:
    card = build_agent_card("http://127.0.0.1:1")
    async with running_server(
        _app_factory(card, SlowExecutor(delay=0.5))
    ) as (base_url, _):
        with pytest.raises(A2AError) as excinfo:
            await send_echo_task(card, "phase1-timeout", timeout=0.1)
    assert excinfo.value.code == "a2a_timeout"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("name", "media_type"),
    [
        ("not-result", "text/plain"),
        ("result", "application/json"),
    ],
)
async def test_wrong_artifact_name_or_media_type_is_rejected(
    name: str,
    media_type: str,
) -> None:
    card = build_agent_card("http://127.0.0.1:1")
    executor = StaticTextArtifactExecutor(
        "phase1-artifact",
        name=name,
        media_type=media_type,
    )
    async with running_server(_app_factory(card, executor)) as (base_url, _):
        with pytest.raises(A2AError) as excinfo:
            await send_echo_task(card, "phase1-artifact")
    assert excinfo.value.code == "missing_artifact"


@pytest.mark.anyio
async def test_jsonrpc_route_is_restricted_to_root() -> None:
    async with running_server(build_app) as (base_url, _):
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.post(
                f"{base_url}/v1",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "SendMessage",
                    "params": {},
                },
            )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_cancel_uses_a2a_unsupported_error() -> None:
    with pytest.raises(UnsupportedOperationError):
        await DeterministicEchoExecutor().cancel(None, None)
