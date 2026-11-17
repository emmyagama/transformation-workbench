"""Deterministic local fake upstream for the Open Responses adapter spike."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from .responses import build_fake_response, build_fake_summary, error_payload

FakeMode = Literal[
    "ok",
    "http_error",
    "malformed_sse",
    "partial_sse",
    "invalid_response",
]


@dataclass
class FakeStats:
    requests: int = 0
    response_turns: int = 0
    compact_requests: int = 0
    paths: list[str] = field(default_factory=list)

    def reset(self) -> None:
        self.requests = 0
        self.response_turns = 0
        self.compact_requests = 0
        self.paths.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "response_turns": self.response_turns,
            "compact_requests": self.compact_requests,
            "paths": list(self.paths),
        }


def _has_missing_function_output(body: dict[str, Any]) -> bool:
    input_value = body.get("input")
    if not isinstance(input_value, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("type") == "function_call_output"
        and item.get("call_id") == "call_openresponses_missing"
        for item in input_value
    )


def _sse_event(event: dict[str, Any]) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event, separators=(',', ':'))}\n\n"


def build_fake_app(mode: FakeMode = "ok") -> Starlette:
    stats = FakeStats()

    async def responses(request: Request) -> Response:
        compaction_summary = request.headers.get("x-workbench-compaction") == "1"
        stats.requests += 1
        stats.response_turns += 1
        if compaction_summary:
            stats.compact_requests += 1
        stats.paths.append("/responses")

        if mode == "http_error":
            return JSONResponse(
                error_payload(
                    "fake_upstream_error",
                    "Synthetic upstream failure.",
                    error_type="upstream_error",
                ),
                status_code=503,
            )
        if mode == "invalid_response":
            return JSONResponse({"id": "bad", "object": "response"}, status_code=200)

        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                error_payload("invalid_json", "Request body is not JSON."),
                status_code=400,
            )
        if not isinstance(body, dict):
            return JSONResponse(
                error_payload("invalid_request", "Request body must be an object."),
                status_code=400,
            )
        if _has_missing_function_output(body):
            return JSONResponse(
                error_payload(
                    "invalid_function_call_output",
                    "No matching tool call exists in the previous response.",
                    param="input",
                ),
                status_code=400,
            )

        if mode == "malformed_sse" and body.get("stream") is True:
            payload = (
                "event: response.completed\n"
                "data: {not-json}\n\n"
                "data: [DONE]\n\n"
            )
            return StreamingResponse(iter([payload]), media_type="text/event-stream")
        if mode == "partial_sse" and body.get("stream") is True:
            payload = 'event: response.completed\ndata: {"type":"response.complet'
            return StreamingResponse(iter([payload]), media_type="text/event-stream")

        response = (
            build_fake_summary(body)
            if compaction_summary
            else build_fake_response(body)
        )
        if body.get("stream") is True:
            event = {"type": "response.completed", "response": response}
            payload = _sse_event(event) + "data: [DONE]\n\n"
            return StreamingResponse(iter([payload]), media_type="text/event-stream")
        return JSONResponse(response)

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", **stats.snapshot()})

    app = Starlette(
        routes=[
            Route("/responses", responses, methods=["POST"]),
            Route("/healthz", health, methods=["GET"]),
        ]
    )
    app.state.fake_stats = stats
    app.state.fake_mode = mode
    return app
