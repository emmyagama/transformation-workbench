"""Open Responses gateway with loopback and explicit hosted-upstream modes."""

from __future__ import annotations

import json
from collections import OrderedDict
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from .compaction import CompactionCipher, CompactionError, replace_compaction_items
from .responses import (
    build_compaction_resource,
    build_compaction_summary_request,
    build_compaction_transcript,
    error_payload,
    extract_output_text,
    normalize_response,
    response_events,
    response_events_as_sse,
    streaming_error_event,
    websocket_error,
)
from .schema import SchemaValidationError

JSON = dict[str, Any]
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_CACHE_ENTRIES = 32
MAX_UPSTREAM_EVENT_BYTES = 4 * 1024 * 1024
MAX_CONTEXT_BYTES = 1536 * 1024
SCHEMA_ERROR_MESSAGE = "The upstream response did not match the required schema."


class ConfigurationError(ValueError):
    pass


class UpstreamError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        param: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.param = param


class UpstreamProtocolError(RuntimeError):
    pass


class ContinuationError(ValueError):
    pass


@dataclass
class GatewayStats:
    upstream_requests: int = 0
    response_requests: int = 0
    compact_summary_requests: int = 0

    def record_response(self) -> None:
        self.upstream_requests += 1
        self.response_requests += 1

    def record_compaction(self) -> None:
        self.upstream_requests += 1
        self.compact_summary_requests += 1

    def snapshot(self) -> JSON:
        return {
            "upstream_requests": self.upstream_requests,
            "response_requests": self.response_requests,
            "compact_summary_requests": self.compact_summary_requests,
        }

    def reset(self) -> None:
        self.upstream_requests = 0
        self.response_requests = 0
        self.compact_summary_requests = 0


@dataclass
class CacheEntry:
    response: JSON
    request: JSON


class BoundedResponseCache:
    def __init__(self, max_entries: int = MAX_CACHE_ENTRIES) -> None:
        self.max_entries = max_entries
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, response_id: str) -> CacheEntry | None:
        entry = self._entries.get(response_id)
        if entry is not None:
            self._entries.move_to_end(response_id)
        return entry

    def put(self, response_id: str, response: JSON, request: JSON) -> None:
        self._entries[response_id] = CacheEntry(
            response=response,
            request=request,
        )
        self._entries.move_to_end(response_id)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def pop(self, response_id: str) -> None:
        self._entries.pop(response_id, None)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)


def assert_loopback_url(value: str, *, field: str = "upstream") -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http":
        raise ConfigurationError(f"{field} URL must use http on loopback")
    if parsed.username or parsed.password:
        raise ConfigurationError(f"{field} URL must not include credentials")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ConfigurationError(f"{field} URL must target loopback only")
    if parsed.query or parsed.fragment:
        raise ConfigurationError(f"{field} URL must not include query or fragment")
    if parsed.path not in {"", "/"}:
        raise ConfigurationError(f"{field} URL must not include a path")
    if parsed.port is None:
        raise ConfigurationError(f"{field} URL must include an explicit port")
    return value.rstrip("/")


def assert_upstream_url(
    value: str,
    *,
    allow_hosted: bool = False,
    allowed_host: str | None = None,
) -> str:
    if not allow_hosted:
        return assert_loopback_url(value)
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise ConfigurationError("hosted upstream URL must use https")
    if parsed.username or parsed.password:
        raise ConfigurationError("hosted upstream URL must not include credentials")
    if not parsed.hostname:
        raise ConfigurationError("hosted upstream URL must include a host")
    if not allowed_host or parsed.hostname != allowed_host:
        raise ConfigurationError("hosted upstream host is not allowed")
    if parsed.query or parsed.fragment:
        raise ConfigurationError("hosted upstream URL must not include query or fragment")
    return value.rstrip("/")


def translate_http_request(body: Mapping[str, Any]) -> JSON:
    translated = json.loads(json.dumps(body))
    translated.pop("type", None)
    translated["stream"] = body.get("stream") is True
    return translated


async def _read_json(request: Request) -> JSON:
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        raise ValueError("request body too large")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("request body is not JSON") from exc
    if not isinstance(body, dict):
        raise ValueError("request body must be an object")
    return body


def _upstream_error(status_code: int, body: Any) -> UpstreamError:
    code = "upstream_http_error"
    message = f"Upstream returned HTTP {status_code}."
    param: str | None = None
    if isinstance(body, Mapping):
        error = body.get("error")
        if isinstance(error, Mapping):
            if isinstance(error.get("code"), str):
                code = error["code"]
            if isinstance(error.get("message"), str):
                message = error["message"]
            if isinstance(error.get("param"), str) or error.get("param") is None:
                param = error.get("param")
    return UpstreamError(status_code, code, message, param=param)


async def _post_upstream(
    client: httpx.AsyncClient,
    upstream_url: str,
    path: str,
    body: JSON,
    *,
    headers: Mapping[str, str] | None = None,
) -> Any:
    try:
        response = await client.post(f"{upstream_url}{path}", json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise UpstreamError(
            502,
            "upstream_unavailable",
            "The upstream is unavailable.",
        ) from exc
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if response.status_code >= 400:
        raise _upstream_error(response.status_code, payload)
    if payload is None:
        raise UpstreamProtocolError("Upstream response was not JSON.")
    return payload


async def _read_stream_final(
    client: httpx.AsyncClient,
    upstream_url: str,
    body: JSON,
    *,
    headers: Mapping[str, str] | None = None,
) -> JSON:
    try:
        async with client.stream(
            "POST",
            f"{upstream_url}/responses",
            json=body,
            headers=headers,
        ) as response:
            if response.status_code >= 400:
                raw = await response.aread()
                try:
                    payload = json.loads(raw)
                except ValueError:
                    payload = None
                raise _upstream_error(response.status_code, payload)

            data_lines: list[str] = []
            final_response: Any = None
            total_bytes = 0
            async for line in response.aiter_lines():
                total_bytes += len(line.encode("utf-8"))
                if total_bytes > MAX_UPSTREAM_EVENT_BYTES:
                    raise UpstreamProtocolError("Upstream SSE exceeded the byte limit.")
                if line == "":
                    if not data_lines:
                        continue
                    data = "\n".join(data_lines)
                    data_lines = []
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError as exc:
                        raise UpstreamProtocolError(
                            "Upstream SSE contained malformed JSON."
                        ) from exc
                    if (
                        isinstance(event, Mapping)
                        and event.get("type") == "response.completed"
                    ):
                        final_response = event.get("response")
                    continue
                if line.startswith("data:"):
                    value = line[5:]
                    if value.startswith(" "):
                        value = value[1:]
                    data_lines.append(value)
            if final_response is None:
                raise UpstreamProtocolError(
                    "Upstream SSE ended without a terminal response."
                )
            if not isinstance(final_response, Mapping):
                raise UpstreamProtocolError(
                    "Upstream terminal response was not an object."
                )
            return dict(final_response)
    except httpx.HTTPError as exc:
        raise UpstreamError(
            502,
            "upstream_unavailable",
            "The upstream is unavailable.",
        ) from exc


async def _stream_sse(final_response: Mapping[str, Any]) -> AsyncIterator[str]:
    for chunk in response_events_as_sse(response_events(final_response)):
        yield chunk


async def _stream_error_sse(code: str, message: str) -> AsyncIterator[str]:
    yield (
        "event: error\n"
        f"data: {json.dumps(streaming_error_event(0, code, message), separators=(',', ':'))}\n\n"
        "data: [DONE]\n\n"
    )


def _stream_headers() -> dict[str, str]:
    return {
        "cache-control": "no-cache",
        "x-accel-buffering": "no",
    }


def _input_items(value: Any) -> list[Any]:
    if isinstance(value, str):
        return [{"type": "message", "role": "user", "content": value}]
    if isinstance(value, list):
        return [json.loads(json.dumps(item)) for item in value]
    return []


def _message_item_text(item: Mapping[str, Any]) -> str:
    content = item.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if (
            isinstance(block, Mapping)
            and block.get("type") in {"output_text", "text"}
            and isinstance(block.get("text"), str)
        ):
            parts.append(block["text"])
    return "\n".join(parts)


def _response_context_items(response: Mapping[str, Any]) -> list[JSON]:
    items: list[JSON] = []
    output = response.get("output")
    if not isinstance(output, list):
        return items
    for item in output:
        if not isinstance(item, Mapping):
            continue
        item_type = item.get("type")
        if item_type == "message":
            text = _message_item_text(item)
            if text:
                items.append(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": text,
                    }
                )
        elif item_type == "function_call":
            items.append(json.loads(json.dumps(item)))
    return items


def build_store_false_continuation_request(
    new_request: Mapping[str, Any],
    previous: CacheEntry,
) -> JSON:
    previous_request = previous.request
    context = (
        _input_items(previous_request.get("input"))
        + _response_context_items(previous.response)
        + _input_items(new_request.get("input"))
    )
    upstream = json.loads(json.dumps(dict(new_request)))
    upstream["input"] = context
    upstream.pop("previous_response_id", None)
    for key in ("model", "tools", "tool_choice", "instructions", "parallel_tool_calls"):
        if key not in upstream or upstream.get(key) is None:
            value = previous_request.get(key)
            if value is not None:
                upstream[key] = json.loads(json.dumps(value))
    if len(json.dumps(context, separators=(",", ":")).encode("utf-8")) > MAX_CONTEXT_BYTES:
        raise ContinuationError("Reconstructed continuation context is too large.")
    return upstream


def build_gateway_app(
    upstream_url: str,
    *,
    timeout: float = 30.0,
    max_cache_entries: int = MAX_CACHE_ENTRIES,
    client_factory: Callable[[], httpx.AsyncClient] | None = None,
    compaction_cipher: CompactionCipher | None = None,
    upstream_headers: Mapping[str, str] | None = None,
    allow_hosted_upstream: bool = False,
    allowed_upstream_host: str | None = None,
) -> Starlette:
    upstream_url = assert_upstream_url(
        upstream_url,
        allow_hosted=allow_hosted_upstream,
        allowed_host=allowed_upstream_host,
    )
    cipher = compaction_cipher or CompactionCipher.from_env()
    client_headers = dict(upstream_headers or {})
    stats = GatewayStats()
    compaction_marker = not allow_hosted_upstream

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        if client_factory is None:
            app.state.http = httpx.AsyncClient(
                trust_env=False,
                timeout=timeout,
            )
        else:
            app.state.http = client_factory()
        app.state.http.headers.update(client_headers)
        try:
            yield
        finally:
            await app.state.http.aclose()

    async def responses(request: Request) -> Response:
        try:
            body = await _read_json(request)
        except ValueError as exc:
            return JSONResponse(
                error_payload("invalid_request", str(exc)),
                status_code=400,
            )
        translated = translate_http_request(body)
        try:
            upstream_request, _ = replace_compaction_items(translated, cipher)
        except CompactionError as exc:
            return JSONResponse(
                error_payload(exc.code, exc.message),
                status_code=400,
            )
        streaming = translated.get("stream") is True
        client: httpx.AsyncClient = request.app.state.http

        if streaming:
            stats.record_response()
            try:
                upstream = await _read_stream_final(
                    client,
                    upstream_url,
                    upstream_request,
                )
                final = normalize_response(upstream, translated)
            except UpstreamError as exc:
                return JSONResponse(
                    error_payload(
                        exc.code,
                        exc.message,
                        error_type="upstream_error",
                        param=exc.param,
                    ),
                    status_code=502 if exc.status_code >= 500 else 400,
                )
            except SchemaValidationError:
                return StreamingResponse(
                    _stream_error_sse("upstream_protocol_error", SCHEMA_ERROR_MESSAGE),
                    media_type="text/event-stream",
                    headers=_stream_headers(),
                )
            except UpstreamProtocolError as exc:
                return StreamingResponse(
                    _stream_error_sse("upstream_protocol_error", str(exc)),
                    media_type="text/event-stream",
                    headers=_stream_headers(),
                )
            return StreamingResponse(
                _stream_sse(final),
                media_type="text/event-stream",
                headers=_stream_headers(),
            )

        stats.record_response()
        try:
            upstream = await _post_upstream(
                client,
                upstream_url,
                "/responses",
                upstream_request,
            )
            final = normalize_response(upstream, translated)
        except UpstreamError as exc:
            return JSONResponse(
                error_payload(
                    exc.code,
                    exc.message,
                    error_type="upstream_error",
                    param=exc.param,
                ),
                status_code=502 if exc.status_code >= 500 else 400,
            )
        except SchemaValidationError:
            return JSONResponse(
                error_payload(
                    "upstream_protocol_error",
                    SCHEMA_ERROR_MESSAGE,
                    error_type="upstream_error",
                ),
                status_code=502,
            )
        except UpstreamProtocolError as exc:
            return JSONResponse(
                error_payload(
                    "upstream_protocol_error",
                    str(exc),
                    error_type="upstream_error",
                ),
                status_code=502,
            )
        return JSONResponse(final)

    async def compact(request: Request) -> Response:
        try:
            body = await _read_json(request)
        except ValueError as exc:
            return JSONResponse(
                error_payload("invalid_request", str(exc)),
                status_code=400,
            )
        if not isinstance(body.get("model"), str) or not body["model"]:
            return JSONResponse(
                error_payload(
                    "missing_model",
                    "The model field is required.",
                    param="model",
                ),
                status_code=400,
            )
        try:
            transcript, source_item_count = build_compaction_transcript(body, cipher)
            summary_request = build_compaction_summary_request(body, transcript)
        except CompactionError as exc:
            return JSONResponse(
                error_payload(exc.code, exc.message),
                status_code=400,
            )
        client: httpx.AsyncClient = request.app.state.http
        stats.record_compaction()
        summary_headers = {"x-workbench-compaction": "1"} if compaction_marker else None
        try:
            upstream = await _post_upstream(
                client,
                upstream_url,
                "/responses",
                summary_request,
                headers=summary_headers,
            )
            summary = extract_output_text(upstream)
            response = build_compaction_resource(
                cipher=cipher,
                model=body["model"],
                summary=summary,
                source_item_count=source_item_count,
                transcript=transcript,
                usage=upstream.get("usage") if isinstance(upstream, Mapping) else None,
            )
        except UpstreamError as exc:
            return JSONResponse(
                error_payload(
                    exc.code,
                    exc.message,
                    error_type="upstream_error",
                    param=exc.param,
                ),
                status_code=502 if exc.status_code >= 500 else 400,
            )
        except SchemaValidationError:
            return JSONResponse(
                error_payload(
                    "upstream_protocol_error",
                    "The upstream response did not match the required schema.",
                    error_type="upstream_error",
                ),
                status_code=502,
            )
        except (UpstreamProtocolError, CompactionError) as exc:
            return JSONResponse(
                error_payload(
                    "upstream_protocol_error",
                    str(exc),
                    error_type="upstream_error",
                ),
                status_code=502,
            )
        return JSONResponse(response)

    async def websocket_responses(websocket: WebSocket) -> None:
        await websocket.accept()
        cache = BoundedResponseCache(max_entries=max_cache_entries)
        client: httpx.AsyncClient = websocket.app.state.http
        try:
            while True:
                try:
                    raw = await websocket.receive_text()
                except WebSocketDisconnect:
                    break
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json(
                        websocket_error(
                            "invalid_json",
                            "WebSocket message was not valid JSON.",
                        )
                    )
                    continue
                if not isinstance(event, dict):
                    await websocket.send_json(
                        websocket_error(
                            "invalid_request",
                            "WebSocket message must be an object.",
                        )
                    )
                    continue
                if event.get("type") != "response.create":
                    await websocket.send_json(
                        websocket_error(
                            "invalid_request",
                            "Expected a response.create event.",
                            param="type",
                        )
                    )
                    continue
                if any(key in event for key in ("stream", "stream_options", "background")):
                    await websocket.send_json(
                        websocket_error(
                            "invalid_request",
                            "HTTP-only fields are not allowed in response.create.",
                        )
                    )
                    continue

                client_request = json.loads(json.dumps(event))
                client_request.pop("type", None)
                previous_id = client_request.get("previous_response_id")
                previous_entry = (
                    cache.get(previous_id) if isinstance(previous_id, str) else None
                )
                if isinstance(previous_id, str) and previous_entry is None:
                    await websocket.send_json(
                        websocket_error(
                            "previous_response_not_found",
                            f"Previous response with id '{previous_id}' not found.",
                            param="previous_response_id",
                        )
                    )
                    continue

                try:
                    upstream_request, _ = replace_compaction_items(client_request, cipher)
                    if (
                        previous_entry is not None
                        and client_request.get("store") is False
                    ):
                        upstream_request = build_store_false_continuation_request(
                            upstream_request,
                            previous_entry,
                        )
                except CompactionError as exc:
                    await websocket.send_json(
                        websocket_error(exc.code, exc.message)
                    )
                    continue
                except ContinuationError as exc:
                    await websocket.send_json(
                        websocket_error("invalid_request", str(exc), param="input")
                    )
                    continue

                stats.record_response()
                try:
                    upstream = await _post_upstream(
                        client,
                        upstream_url,
                        "/responses",
                        upstream_request,
                    )
                    final = normalize_response(upstream, client_request)
                except UpstreamError as exc:
                    if isinstance(previous_id, str):
                        cache.pop(previous_id)
                    await websocket.send_json(
                        websocket_error(
                            exc.code,
                            exc.message,
                            status=exc.status_code
                            if 400 <= exc.status_code < 500
                            else 502,
                            error_type="upstream_error",
                            param=exc.param,
                        )
                    )
                    continue
                except SchemaValidationError:
                    if isinstance(previous_id, str):
                        cache.pop(previous_id)
                    await websocket.send_json(
                        websocket_error(
                            "upstream_protocol_error",
                            SCHEMA_ERROR_MESSAGE,
                            status=502,
                            error_type="upstream_error",
                        )
                    )
                    continue
                except UpstreamProtocolError as exc:
                    if isinstance(previous_id, str):
                        cache.pop(previous_id)
                    await websocket.send_json(
                        websocket_error(
                            "upstream_protocol_error",
                            str(exc),
                            status=502,
                            error_type="upstream_error",
                        )
                    )
                    continue

                cache.put(final["id"], final, upstream_request)
                for response_event in response_events(final):
                    await websocket.send_json(response_event)
        finally:
            cache.clear()

    async def local_health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", **stats.snapshot()})

    async def local_stats(request: Request) -> JSONResponse:
        return JSONResponse(stats.snapshot())

    async def local_stats_reset(request: Request) -> JSONResponse:
        stats.reset()
        return JSONResponse(stats.snapshot())

    app = Starlette(
        lifespan=lifespan,
        routes=[
            Route("/responses", responses, methods=["POST"]),
            Route("/responses/compact", compact, methods=["POST"]),
            WebSocketRoute("/responses", websocket_responses),
            Route("/__local/health", local_health, methods=["GET"]),
            Route("/__local/stats", local_stats, methods=["GET"]),
            Route("/__local/stats/reset", local_stats_reset, methods=["POST"]),
        ],
    )
    app.state.gateway_stats = stats
    return app
