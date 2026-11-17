"""Minimal deterministic A2A client used by the Week 3 coordinator slice."""

import asyncio
from contextlib import suppress
from dataclasses import dataclass

import httpx
from a2a.client import (
    A2ACardResolver,
    A2AClientError,
    A2AClientTimeoutError,
    AgentCardResolutionError,
    ClientConfig,
    create_client,
)
from a2a.helpers import get_message_text, new_text_message
from a2a.types import AgentCard, Role, SendMessageRequest, Task, TaskState

from .boundary import require_loopback_url

ECHO_SKILL_ID = "deterministic_echo"
ECHO_ARTIFACT_NAME = "result"
TEXT_MEDIA_TYPE = "text/plain"


class A2AError(RuntimeError):
    """Bounded, explanatory Phase 1 A2A failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        task_id: str | None = None,
        context_id: str | None = None,
        state: str | None = None,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.task_id = task_id
        self.context_id = context_id
        self.state = state


@dataclass(frozen=True)
class A2AExchange:
    """Sanitized result of one completed A2A task exchange."""

    agent_name: str
    task_id: str
    context_id: str
    state: str
    artifact_text: str


async def discover_agent_card(
    base_url: str,
    *,
    timeout: float = 10.0,
) -> AgentCard:
    """Fetch the Agent Card over the real well-known HTTP endpoint."""
    try:
        require_loopback_url(base_url)
    except ValueError as exc:
        raise A2AError("invalid_endpoint", str(exc)) from exc
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            trust_env=False,
            follow_redirects=False,
        ) as http_client:
            resolver = A2ACardResolver(
                httpx_client=http_client,
                base_url=base_url,
            )
            card = await resolver.get_agent_card()
    except AgentCardResolutionError as exc:
        raise _card_resolution_error(exc) from exc
    except (
        A2AClientTimeoutError,
        httpx.TimeoutException,
        asyncio.TimeoutError,
        TimeoutError,
    ) as exc:
        raise A2AError(
            "a2a_timeout",
            "The agent card request timed out.",
        ) from exc
    except httpx.HTTPError as exc:
        raise A2AError(
            "specialist_unavailable",
            "The local specialist could not be reached.",
        ) from exc

    try:
        _validate_echo_card(card)
    except ValueError as exc:
        raise A2AError("invalid_agent_card", str(exc)) from exc
    return card


async def send_echo_task(
    agent_card: AgentCard,
    text: str,
    *,
    timeout: float = 10.0,
) -> A2AExchange:
    """Send one A2A message and parse the final task response."""
    try:
        _validate_echo_card(agent_card)
    except ValueError as exc:
        raise A2AError("invalid_agent_card", str(exc)) from exc

    try:
        return await asyncio.wait_for(
            _send_echo_once(agent_card, text, timeout),
            timeout=timeout,
        )
    except A2AError:
        raise
    except (
        A2AClientTimeoutError,
        httpx.TimeoutException,
        asyncio.TimeoutError,
        TimeoutError,
    ) as exc:
        raise A2AError(
            "a2a_timeout",
            "The A2A task request timed out.",
        ) from exc
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise A2AError(
            "specialist_unavailable",
            "The local specialist could not be reached.",
        ) from exc
    except httpx.TransportError as exc:
        raise A2AError(
            "specialist_unavailable",
            "The A2A transport failed.",
        ) from exc
    except A2AClientError as exc:
        raise _client_error(exc) from exc
    except Exception as exc:
        raise A2AError(
            "protocol_error",
            f"The A2A request failed ({type(exc).__name__}).",
        ) from exc


async def _send_echo_once(
    agent_card: AgentCard,
    text: str,
    timeout: float,
) -> A2AExchange:
    async with httpx.AsyncClient(
        timeout=timeout,
        trust_env=False,
        follow_redirects=False,
    ) as http_client:
        client = await create_client(
            agent=agent_card,
            client_config=ClientConfig(
                streaming=False,
                httpx_client=http_client,
            ),
        )
        try:
            request = SendMessageRequest(
                message=new_text_message(text, role=Role.ROLE_USER)
            )
            response = None
            async for chunk in client.send_message(request):
                response = chunk
        finally:
            with suppress(Exception):
                await client.close()

    if response is None:
        raise A2AError("non_task_response", "A2A request returned no response.")
    if response.WhichOneof("payload") != "task":
        raise A2AError(
            "non_task_response",
            "Expected an A2A Task response.",
        )

    task = response.task
    state = TaskState.Name(task.status.state)
    if task.status.state != TaskState.TASK_STATE_COMPLETED:
        detail = _status_message(task)
        suffix = f": {detail}" if detail else "."
        raise A2AError(
            "task_failure",
            f"Task ended in {state}{suffix}",
            task_id=task.id,
            context_id=task.context_id,
            state=state,
        )

    artifact_text = _result_artifact_text(task)
    return A2AExchange(
        agent_name=agent_card.name,
        task_id=task.id,
        context_id=task.context_id,
        state=state,
        artifact_text=artifact_text,
    )


def _validate_echo_card(card: AgentCard) -> None:
    if ECHO_SKILL_ID not in {skill.id for skill in card.skills}:
        raise ValueError(f"Card {card.name!r} does not advertise the echo skill.")
    if card.capabilities.streaming:
        raise ValueError(f"Card {card.name!r} advertises unexpected streaming.")
    if TEXT_MEDIA_TYPE not in card.default_input_modes:
        raise ValueError(f"Card {card.name!r} does not accept text/plain.")
    if TEXT_MEDIA_TYPE not in card.default_output_modes:
        raise ValueError(f"Card {card.name!r} does not emit text/plain.")

    interfaces = [
        item
        for item in card.supported_interfaces
        if item.protocol_binding == "JSONRPC"
    ]
    if not interfaces or any(
        item.protocol_version != "1.0" for item in interfaces
    ):
        raise ValueError(f"Card {card.name!r} does not advertise JSONRPC 1.0.")
    for interface in card.supported_interfaces:
        require_loopback_url(interface.url)


def _result_artifact_text(task: Task) -> str:
    artifacts = [
        artifact
        for artifact in task.artifacts
        if artifact.name == ECHO_ARTIFACT_NAME
    ]
    text = "\n".join(
        part.text
        for artifact in artifacts
        for part in artifact.parts
        if part.WhichOneof("content") == "text"
        and part.media_type == TEXT_MEDIA_TYPE
    )
    if not text:
        raise A2AError(
            "missing_artifact",
            "Task completed without the expected text/plain result artifact.",
            task_id=task.id,
            context_id=task.context_id,
            state=TaskState.Name(task.status.state),
        )
    return text


def _status_message(task: Task) -> str:
    message = task.status.message
    if message is None or not message.parts:
        return ""
    return get_message_text(message).strip()


def _client_error(exc: A2AClientError) -> A2AError:
    cause = exc.__cause__
    if isinstance(cause, (httpx.ConnectError, httpx.ConnectTimeout)):
        return A2AError(
            "specialist_unavailable",
            "The local specialist could not be reached.",
        )
    if isinstance(cause, (A2AClientTimeoutError, httpx.TimeoutException)):
        return A2AError(
            "a2a_timeout",
            "The A2A task request timed out.",
        )
    return A2AError(
        "protocol_error",
        "The A2A client reported a protocol error.",
    )


def _card_resolution_error(exc: AgentCardResolutionError) -> A2AError:
    cause = exc.__cause__
    if isinstance(cause, (httpx.ConnectError, httpx.ConnectTimeout)):
        return A2AError(
            "specialist_unavailable",
            "The local specialist could not be reached.",
        )
    if isinstance(cause, (A2AClientTimeoutError, httpx.TimeoutException)):
        return A2AError(
            "a2a_timeout",
            "The agent card request timed out.",
        )
    if exc.status_code is not None:
        return A2AError(
            "agent_card_unavailable",
            f"The agent card endpoint returned HTTP {exc.status_code}.",
        )
    return A2AError(
        "specialist_unavailable",
        "The local specialist could not be reached.",
    )


async def run_echo_round_trip(
    base_url: str,
    text: str,
    *,
    timeout: float = 10.0,
) -> A2AExchange:
    """Discover the local specialist and complete one real A2A task."""
    agent_card = await discover_agent_card(base_url, timeout=timeout)
    return await send_echo_task(agent_card, text, timeout=timeout)
