# Week 3 Phase 1 — local A2A vertical slice

## Scope

One deterministic test specialist is served on an explicit loopback HTTP endpoint.
The coordinator uses the official A2A Python client to fetch the Agent Card from
`/.well-known/agent-card.json`, then sends one non-streaming JSON-RPC message and
parses the completed task response. No hosted model, API key, MCP tool, Goose
integration, cloud endpoint, business action, or global configuration is used.

The repository keeps the `workbench://process-context` MCP resource only. No
`get_process_context` fallback tool was added.

## Versions checked 2026-11-15

| Component | Version |
| --- | --- |
| Python | 3.11.9 |
| A2A protocol specification | 1.0.0 latest released (1.0.1 patch also published) |
| `a2a-sdk` | 1.3.0 (released 2026-10-27; implements A2A 1.0 with 0.3 compatibility) |
| `a2a-sdk` Python requirement | >= 3.10 |
| `starlette` | 1.10.0 |
| `uvicorn` | 0.54.0 |
| `httpx` | 0.28.1 |
| `sse-starlette` | 3.7.0 |

`a2a-sdk[http-server]==1.3.0`, `httpx>=0.28.1,<0.29`, and
`uvicorn>=0.30,<1` are runtime dependencies. `uvicorn` serves the local A2A
runtime and the integration test server.

## Reproducible check

From the working repository:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_a2a_integration.py -v
```

For an immutable review snapshot that excludes `.venv`, use a shared Python
3.11 interpreter with the snapshot source path:

```powershell
$env:PYTHONPATH = "<snapshot>\src"
$env:PYTHONDONTWRITEBYTECODE = "1"
& "<shared-python-3.11>\python.exe" -m pytest -q -p no:cacheprovider
```

The test starts a real Uvicorn server bound to `127.0.0.1` on an ephemeral port,
records request method/path pairs, and asserts:

- `GET /.well-known/agent-card.json` was served.
- The discovered card advertises `JSONRPC` and protocol version `1.0`.
- The card advertises only the `deterministic_echo` skill with text I/O and
  `streaming=False`.
- `POST /` was received with JSON-RPC 2.0 method `SendMessage`.
- The returned task has non-empty `task_id` and `context_id`, state
  `TASK_STATE_COMPLETED`, and artifact text
  `deterministic-echo:phase1-preflight`.
- Failed and cancelled tasks raise a bounded `A2AError` instead of being
  returned as completed exchanges.
- Non-loopback card endpoints, non-root loopback paths, query strings,
  fragments, URL userinfo, connection failures, timeouts, and missing or wrong
  `result` artifacts are rejected with bounded error codes.
- Environment proxy variables cannot route the loopback card or task request
  through a proxy.
- The JSON-RPC route is restricted to `/`; a POST to `/v1` returns 404.
- The direct `run_echo_round_trip` helper completes a real A2A exchange.

Server-generated task/context identifiers are UUIDs and are not reproduced here.

## Boundary

This proves the standalone SDK client can discover and exchange one real
JSON-RPC A2A task with a local specialist. It does not prove Goose resource
exposure, streaming, authentication, push notifications, multi-turn tasks,
other protocol bindings, or full specification conformance. The tests assert
the SDK card's `protocol_version = "1.0"`; they do not independently prove every
A2A 1.0 requirement. Cancellation is not advertised and is outside the accepted
task-completion path; the executor raises the SDK `UnsupportedOperationError`
rather than a bare `NotImplementedError`. No end-to-end `CancelTask` acceptance
is claimed.
