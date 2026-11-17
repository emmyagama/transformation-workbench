"""Shared Phase 2 test builders for synthetic A2A and MCP fakes."""

from __future__ import annotations

import asyncio
import hashlib
import json
import socket
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import uvicorn
from a2a.helpers import (
    new_data_part,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCard, Role
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from transformation_workbench.a2a.contracts import (
    EVIDENCE_SOURCE,
    PROCESS_CONTEXT_URI,
    REQUIRED_METRIC_FIELDS,
    CaseObservation,
    EvidencePack,
    ExceptionRecord,
    MetricFact,
    ProcessContext,
    Provenance,
)
from transformation_workbench.a2a.solution_designer import design_options
from transformation_workbench.mcp_server import PROCESS_CONTEXT

SNAPSHOT = "2026-03-13T17:00:00Z"

METRIC_VALUES: dict[str, int | float] = {
    "input_rows": 15,
    "measurable_closed": 9,
    "cycle_time_sum_hours": 261.5,
    "mean_cycle_time_hours": 29.06,
    "median_cycle_time_hours": 9.0,
    "sla_met_count": 6,
    "sla_met_percent": 66.7,
    "rework_cases": 2,
    "rework_rate_percent": 22.2,
    "rework_volume": 3,
    "backlog_cases": 2,
    "backlog_overdue": 1,
    "excluded_count": 4,
}

METRICS_PROVENANCE = Provenance(
    source=EVIDENCE_SOURCE,
    kind="mcp_tool",
    reference="calculate_baseline_metrics",
)
EXCEPTIONS_PROVENANCE = Provenance(
    source=EVIDENCE_SOURCE,
    kind="mcp_tool",
    reference="list_case_exceptions",
)
CASE_PROVENANCE = Provenance(
    source=EVIDENCE_SOURCE,
    kind="mcp_tool",
    reference="get_case_details",
)


class RequestRecorder(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        seen: list[tuple[str, str, str | None, str | None]],
    ) -> None:
        super().__init__(app)
        self.seen = seen

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        rpc_method: str | None = None
        rpc_version: str | None = None
        if request.method == "POST":
            try:
                payload = json.loads(await request.body())
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                rpc_method = payload.get("method")
                rpc_version = payload.get("jsonrpc")
        self.seen.append(
            (request.method, request.url.path, rpc_method, rpc_version)
        )
        return await call_next(request)


def free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _bind_loopback_socket() -> tuple[socket.socket, int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    return sock, int(sock.getsockname()[1])


@asynccontextmanager
async def running_server(
    app_factory: Callable[[str], Starlette],
    *,
    record: bool = True,
) -> AsyncIterator[
    tuple[str, list[tuple[str, str, str | None, str | None]]]
]:
    sock, port = _bind_loopback_socket()
    base_url = f"http://127.0.0.1:{port}"
    seen: list[tuple[str, str, str | None, str | None]] = []
    app = app_factory(base_url)
    if record:
        app.add_middleware(RequestRecorder, seen=seen)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
        )
    )
    server_task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        while not server.started:
            if server_task.done():
                await server_task
            await asyncio.sleep(0.01)
        yield base_url, seen
    finally:
        server.should_exit = True
        await asyncio.wait_for(server_task, timeout=10)
        sock.close()


def build_specialist_app(
    base_url: str,
    card: AgentCard,
    executor: AgentExecutor,
) -> Starlette:
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    routes = create_agent_card_routes(card)
    routes.extend(create_jsonrpc_routes(handler, "/"))
    return Starlette(routes=routes)


def _start_task(
    context: RequestContext,
    event_queue: EventQueue,
) -> tuple[Any, TaskUpdater]:
    task = context.current_task
    if task is None:
        task = new_task_from_user_message(context.message)
    updater = TaskUpdater(
        event_queue=event_queue,
        task_id=task.id,
        context_id=task.context_id,
    )
    return task, updater


class StaticArtifactExecutor(AgentExecutor):
    def __init__(
        self,
        payload: dict[str, Any],
        *,
        name: str = "artifact",
        media_type: str = "application/json",
    ) -> None:
        self.payload = payload
        self.name = name
        self.media_type = media_type

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task, updater = _start_task(context, event_queue)
        await event_queue.enqueue_event(task)
        await updater.add_artifact(
            parts=[
                new_data_part(
                    self.payload,
                    media_type=self.media_type,
                )
            ],
            name=self.name,
        )
        await updater.complete(
            message=new_text_message("static artifact", role=Role.ROLE_AGENT)
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        return None


class StaticTextArtifactExecutor(AgentExecutor):
    def __init__(
        self,
        text: str,
        *,
        name: str = "result",
        media_type: str = "text/plain",
    ) -> None:
        self.text = text
        self.name = name
        self.media_type = media_type

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task, updater = _start_task(context, event_queue)
        await event_queue.enqueue_event(task)
        await updater.add_artifact(
            parts=[new_text_part(text=self.text, media_type=self.media_type)],
            name=self.name,
        )
        await updater.complete(
            message=new_text_message("static text artifact", role=Role.ROLE_AGENT)
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        return None


class EmptyArtifactExecutor(AgentExecutor):
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task, updater = _start_task(context, event_queue)
        await event_queue.enqueue_event(task)
        await updater.complete(
            message=new_text_message("empty result", role=Role.ROLE_AGENT)
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        return None


class FailingExecutor(AgentExecutor):
    def __init__(self, detail: str = "synthetic task failure") -> None:
        self.detail = detail

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task, updater = _start_task(context, event_queue)
        await event_queue.enqueue_event(task)
        await updater.failed(
            message=new_text_message(self.detail, role=Role.ROLE_AGENT)
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        return None


class CancelingExecutor(AgentExecutor):
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task, updater = _start_task(context, event_queue)
        await event_queue.enqueue_event(task)
        await updater.cancel(
            message=new_text_message("synthetic cancel", role=Role.ROLE_AGENT)
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        return None


class SlowExecutor(AgentExecutor):
    def __init__(self, delay: float = 0.5) -> None:
        self.delay = delay

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        task, updater = _start_task(context, event_queue)
        await event_queue.enqueue_event(task)
        await asyncio.sleep(self.delay)
        await updater.complete(
            message=new_text_message("slow result", role=Role.ROLE_AGENT)
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        return None


class StaticEvidenceSource:
    def __init__(self, pack: EvidencePack) -> None:
        self.pack = pack
        self.calls = 0

    async def collect(
        self,
        request_id: str,
        case_ids: list[str],
    ) -> EvidencePack:
        self.calls += 1
        return self.pack


def valid_evidence_pack(
    request_id: str = "phase2-test",
    case_ids: list[str] | None = None,
) -> EvidencePack:
    requested = case_ids or ["C-009", "C-006", "C-014"]
    text = PROCESS_CONTEXT
    context = ProcessContext(
        uri=PROCESS_CONTEXT_URI,
        mime_type="text/markdown",
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        text=text,
        snapshot=SNAPSHOT,
        sla_targets={"P1": 8.0, "P2": 24.0, "P3": 72.0},
        synthetic_only=True,
        read_only=True,
        provenance=Provenance(
            source=EVIDENCE_SOURCE,
            kind="mcp_resource",
            reference=PROCESS_CONTEXT_URI,
        ),
    )
    metrics = {
        name: MetricFact(
            evidence_id=f"metric.{name}",
            name=name,
            value=METRIC_VALUES[name],
            unit=unit,
            provenance=METRICS_PROVENANCE,
        )
        for name, unit in REQUIRED_METRIC_FIELDS.items()
    }
    exceptions = [
        ExceptionRecord(
            evidence_id="exception.row.7",
            case_id="C-006",
            row_number=7,
            reason="INCOMPLETE_MISSING_CLOSED_AT",
            provenance=EXCEPTIONS_PROVENANCE,
        ),
        ExceptionRecord(
            evidence_id="exception.row.11",
            case_id="C-010",
            row_number=11,
            reason="INVALID_DATE",
            provenance=EXCEPTIONS_PROVENANCE,
        ),
        ExceptionRecord(
            evidence_id="exception.row.12",
            case_id="C-011",
            row_number=12,
            reason="OUT_OF_ORDER",
            provenance=EXCEPTIONS_PROVENANCE,
        ),
        ExceptionRecord(
            evidence_id="exception.row.15",
            case_id="C-014",
            row_number=15,
            reason="DUPLICATE_OF:C-007",
            provenance=EXCEPTIONS_PROVENANCE,
        ),
    ]
    observations = [
        CaseObservation(
            evidence_id="case.C-009",
            case_id="C-009",
            row_number=10,
            classification="measurable",
            status="closed",
            priority="P2",
            received_at="2026-03-09T09:00:00Z",
            acknowledged_at="2026-03-09T09:30:00Z",
            closed_at="2026-03-10T09:00:00Z",
            rework_count=0,
            duplicate_of=None,
            exclusion_reason=None,
            cycle_time_hours=24.0,
            sla_target_hours=24.0,
            sla_met=True,
            backlog_age_hours=None,
            backlog_overdue=None,
            provenance=CASE_PROVENANCE,
        ),
        CaseObservation(
            evidence_id="case.C-006",
            case_id="C-006",
            row_number=7,
            classification="invalid",
            status=None,
            priority=None,
            received_at=None,
            acknowledged_at=None,
            closed_at=None,
            rework_count=None,
            duplicate_of=None,
            exclusion_reason="INCOMPLETE_MISSING_CLOSED_AT",
            cycle_time_hours=None,
            sla_target_hours=None,
            sla_met=None,
            backlog_age_hours=None,
            backlog_overdue=None,
            provenance=CASE_PROVENANCE,
        ),
        CaseObservation(
            evidence_id="case.C-014",
            case_id="C-014",
            row_number=15,
            classification="duplicate",
            status="duplicate",
            priority="P2",
            received_at="2026-03-05T11:04:00Z",
            acknowledged_at="2026-03-05T11:15:00Z",
            closed_at="2026-03-05T20:00:00Z",
            rework_count=0,
            duplicate_of="C-007",
            exclusion_reason="DUPLICATE_OF:C-007",
            cycle_time_hours=None,
            sla_target_hours=None,
            sla_met=None,
            backlog_age_hours=None,
            backlog_overdue=None,
            provenance=CASE_PROVENANCE,
        ),
    ]
    return EvidencePack(
        evidence_pack_id=f"evidence-{request_id}",
        request_id=request_id,
        generated_by="test-evidence",
        metric_status="ok",
        snapshot=SNAPSHOT,
        process_context=context,
        metrics=metrics,
        exceptions=exceptions,
        case_observations=[
            item for item in observations if item.case_id in requested
        ],
        requested_case_ids=requested,
        missing_data=[],
        tool_errors=[],
    )


def valid_solution_payload(pack: EvidencePack) -> dict[str, Any]:
    return design_options(pack).model_dump(mode="json")


def call_result(
    payload: dict[str, Any] | None = None,
    *,
    is_error: bool = False,
    text: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        is_error=is_error,
        structured_content=payload,
        content=[SimpleNamespace(text=text)] if text else [],
    )


class FakeMcpSession:
    def __init__(
        self,
        *,
        resources: list[str] | None = None,
        resource_text: str = PROCESS_CONTEXT,
        tool_results: dict[str, Any] | None = None,
        tool_errors: dict[str, str] | None = None,
    ) -> None:
        self.resources = resources if resources is not None else [PROCESS_CONTEXT_URI]
        self.resource_text = resource_text
        self.tool_results = tool_results or {}
        self.tool_errors = tool_errors or {}

    async def initialize(self) -> None:
        return None

    async def list_resources(self) -> SimpleNamespace:
        return SimpleNamespace(
            resources=[SimpleNamespace(uri=uri) for uri in self.resources]
        )

    async def read_resource(self, uri: str) -> SimpleNamespace:
        return SimpleNamespace(
            contents=[
                SimpleNamespace(
                    uri=uri,
                    mime_type="text/markdown",
                    text=self.resource_text,
                )
            ]
        )

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> SimpleNamespace:
        if name in self.tool_errors:
            return call_result(is_error=True, text=self.tool_errors[name])
        result = self.tool_results.get(name, {})
        if callable(result):
            result = result(arguments or {})
        return call_result(result)


def fake_session_factory(
    session: FakeMcpSession,
) -> Callable[[], Any]:
    @asynccontextmanager
    async def factory() -> AsyncIterator[FakeMcpSession]:
        yield session

    return factory
