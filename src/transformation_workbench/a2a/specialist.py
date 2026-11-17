"""Deterministic A2A test specialist and its local Agent Card."""

from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Role,
    TaskState,
)
from a2a.utils.errors import UnsupportedOperationError
from starlette.applications import Starlette

from .boundary import require_loopback_url

SPECIALIST_NAME = "Deterministic Echo Specialist"
SPECIALIST_VERSION = "0.1.0"
SPECIALIST_SKILL_ID = "deterministic_echo"
ECHO_PREFIX = "deterministic-echo:"


class DeterministicEchoAgent:
    """Pure, deterministic test agent with no model or network dependency."""

    async def invoke(self, user_request: str) -> str:
        if not user_request:
            return "No text input was provided."
        return f"{ECHO_PREFIX}{user_request}"


class DeterministicEchoExecutor(AgentExecutor):
    """A2A executor that returns the deterministic agent result as an artifact."""

    def __init__(self) -> None:
        self.agent = DeterministicEchoAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task = context.current_task
        if task is None:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message(
                "Processing deterministic request.",
                role=Role.ROLE_AGENT,
            ),
        )

        result = await self.agent.invoke(get_message_text(context.message))
        await updater.add_artifact(
            parts=[new_text_part(text=result, media_type="text/plain")],
            name="result",
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message(
                "Completed deterministic request.",
                role=Role.ROLE_AGENT,
            ),
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise UnsupportedOperationError(
            "The Phase 1 deterministic specialist does not support cancellation."
        )


def build_agent_card(base_url: str) -> AgentCard:
    """Build the narrow local Agent Card advertised by the specialist."""
    require_loopback_url(base_url)
    return AgentCard(
        name=SPECIALIST_NAME,
        description=(
            "Deterministic, synthetic-only echo specialist used to prove the "
            "local A2A protocol boundary."
        ),
        version=SPECIALIST_VERSION,
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
        ),
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                url=base_url,
                protocol_version="1.0",
            )
        ],
        skills=[
            AgentSkill(
                id=SPECIALIST_SKILL_ID,
                name="Deterministic echo",
                description=(
                    "Returns a deterministic prefixed echo. No model calls, "
                    "network calls, or side effects."
                ),
                tags=["phase1", "deterministic", "synthetic"],
                examples=["phase1 protocol check"],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            )
        ],
    )


def build_app(base_url: str) -> Starlette:
    """Build a loopback Starlette app serving the Agent Card and JSON-RPC."""
    agent_card = build_agent_card(base_url)
    request_handler = DefaultRequestHandler(
        agent_executor=DeterministicEchoExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    routes = create_agent_card_routes(agent_card)
    routes.extend(create_jsonrpc_routes(request_handler, "/"))
    return Starlette(routes=routes)
