"""Local loopback runtime for the coordinator and A2A specialists."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import AsyncExitStack, asynccontextmanager

import uvicorn
from starlette.applications import Starlette

from .contracts import CoordinatorResult
from .evidence_source import EvidenceSource
from .evidence_specialist import build_app as build_evidence_app
from .phase2_coordinator import Phase2Coordinator
from .solution_designer import build_app as build_solution_app


def _bind_loopback_socket() -> tuple[socket.socket, int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    return sock, int(sock.getsockname()[1])


@asynccontextmanager
async def serve_loopback(
    app_factory: Callable[[str], Starlette],
) -> AsyncIterator[str]:
    """Serve one app on an ephemeral loopback URL and yield its base URL."""
    sock, port = _bind_loopback_socket()
    base_url = f"http://127.0.0.1:{port}"
    server: uvicorn.Server | None = None
    task: asyncio.Task[None] | None = None
    try:
        app = app_factory(base_url)
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                log_level="warning",
                access_log=False,
            )
        )
        task = asyncio.create_task(server.serve(sockets=[sock]))
        while not server.started:
            if task.done():
                await task
            await asyncio.sleep(0.01)
        yield base_url
    finally:
        if server is not None:
            server.should_exit = True
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=10)
            except Exception:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        sock.close()


async def run_local_diagnosis(
    request_id: str,
    case_ids: Sequence[str],
    *,
    timeout: float = 20.0,
    max_retries: int = 1,
    evidence_source: EvidenceSource | None = None,
) -> CoordinatorResult:
    """Start both specialists on loopback and run one A2A diagnosis."""
    async with AsyncExitStack() as stack:
        evidence_url = await stack.enter_async_context(
            serve_loopback(
                lambda base_url: build_evidence_app(
                    base_url,
                    source=evidence_source,
                )
            )
        )
        solution_url = await stack.enter_async_context(
            serve_loopback(build_solution_app)
        )
        coordinator = Phase2Coordinator(
            evidence_url,
            solution_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        return await coordinator.run(request_id, case_ids)
