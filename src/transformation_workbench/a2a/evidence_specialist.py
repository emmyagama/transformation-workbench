"""A2A Evidence Specialist backed by the read-only Workbench MCP server."""

from __future__ import annotations

import json
import logging

from a2a.helpers import (
    get_data_parts,
    get_message_text,
    new_data_part,
    new_task_from_user_message,
    new_text_message,
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
)
from starlette.applications import Starlette

from .boundary import require_loopback_url
from .evidence_source import EvidenceSource, EvidenceSourceError, McpEvidenceSource
from .validation import ContractValidationError, validate_evidence_pack

logger = logging.getLogger(__name__)

EVIDENCE_SPECIALIST_NAME = "Workbench Evidence Specialist"
EVIDENCE_SPECIALIST_VERSION = "0.2.0"
EVIDENCE_SKILL_ID = "workbench_evidence"
EVIDENCE_ARTIFACT_NAME = "evidence_pack"


class EvidenceExecutor(AgentExecutor):
    """Collect read-only MCP evidence and return a typed EvidencePack."""

    def __init__(self, source: EvidenceSource | None = None) -> None:
        self.source = source or McpEvidenceSource()

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
        await updater.start_work(
            message=new_text_message(
                "Reading read-only MCP evidence.",
                role=Role.ROLE_AGENT,
            )
        )
        try:
            request_id, case_ids = parse_evidence_request(context.message)
            pack = await self.source.collect(request_id, case_ids)
            validate_evidence_pack(pack, expected_request_id=request_id)
        except (EvidenceSourceError, ValueError, ContractValidationError) as exc:
            code = getattr(exc, "code", "invalid_request")
            message = getattr(exc, "message", str(exc))
            logger.warning("Evidence task failed: %s", code)
            await updater.failed(
                message=new_text_message(
                    f"Evidence collection failed: {code}: {message}",
                    role=Role.ROLE_AGENT,
                )
            )
            return
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.warning("Evidence task failed: %s", type(exc).__name__)
            await updater.failed(
                message=new_text_message(
                    "Evidence collection failed: internal_error.",
                    role=Role.ROLE_AGENT,
                )
            )
            return

        await updater.add_artifact(
            parts=[
                new_data_part(
                    pack.model_dump(mode="json"),
                    media_type="application/json",
                )
            ],
            name=EVIDENCE_ARTIFACT_NAME,
        )
        await updater.complete(
            message=new_text_message(
                "Evidence pack completed.",
                role=Role.ROLE_AGENT,
            )
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task = context.current_task
        if task is None:
            return
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.cancel(
            message=new_text_message(
                "Evidence collection cancelled.",
                role=Role.ROLE_AGENT,
            )
        )


def parse_evidence_request(message: object) -> tuple[str, list[str]]:
    """Read request_id and case_ids from a data or text A2A message."""
    payload: object | None = None
    data_parts = get_data_parts(message.parts)
    if data_parts:
        payload = data_parts[0]

    if payload is None:
        text = get_message_text(message).strip()
        if text:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {"case_ids": text.split(",")}

    if not isinstance(payload, dict):
        raise EvidenceSourceError(
            "invalid_request",
            "Evidence request must be a JSON object.",
        )

    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise EvidenceSourceError(
            "invalid_request",
            "Evidence request must include a non-empty request_id.",
        )

    raw_case_ids = payload.get("case_ids", [])
    if isinstance(raw_case_ids, str):
        case_ids = [item.strip() for item in raw_case_ids.split(",")]
    elif isinstance(raw_case_ids, list):
        case_ids = [_require_text(item, "case_ids") for item in raw_case_ids]
    else:
        raise EvidenceSourceError(
            "invalid_request",
            "case_ids must be a string or list of strings.",
        )
    return request_id.strip(), [item for item in case_ids if item]


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise EvidenceSourceError(
            "invalid_request",
            f"{field} entries must be strings.",
        )
    return value.strip()


def build_agent_card(base_url: str) -> AgentCard:
    """Build the narrow loopback Agent Card for the Evidence Specialist."""
    require_loopback_url(base_url)
    return AgentCard(
        name=EVIDENCE_SPECIALIST_NAME,
        description=(
            "Read-only Evidence Specialist for a fixed synthetic service-request "
            "fixture. Returns provenance-linked metrics, exceptions, and case "
            "observations. It makes no recommendations and has no write tools."
        ),
        version=EVIDENCE_SPECIALIST_VERSION,
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
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
                id=EVIDENCE_SKILL_ID,
                name="Workbench evidence",
                description=(
                    "Reads workbench://process-context and calls only the "
                    "read-only metrics, exception, and case-detail tools."
                ),
                tags=["week3", "phase2", "evidence", "mcp", "synthetic"],
                examples=["Collect evidence for C-009 and C-014."],
                input_modes=["application/json"],
                output_modes=["application/json"],
            )
        ],
    )


def build_app(
    base_url: str,
    *,
    source: EvidenceSource | None = None,
) -> Starlette:
    """Build a loopback Starlette app serving the card and JSON-RPC."""
    agent_card = build_agent_card(base_url)
    request_handler = DefaultRequestHandler(
        agent_executor=EvidenceExecutor(source=source),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    routes = create_agent_card_routes(agent_card)
    routes.extend(create_jsonrpc_routes(request_handler, "/"))
    return Starlette(routes=routes)
