# Week 4 Open Responses adapter: Gates 1-3 with genuine compaction

## Snapshot

- Branch: `feat/week3-goose-a2a`
- HEAD: `17faecf55318b7474237f9cfa939855e4d6ec16e`
- Date: 2026-11-16; Gate 3 completed 2026-11-17
- Pinned suite commit: `dce9ddb91921427c2ba06901c7dfaf0cc7056799`
- Focused adapter tests: **35 passed**
- Full local tests at closeout: **214 passed**
- Gate 2 pinned suite result: **17 passed, 0 failed**
- Gate 2 evidence: `docs/evidence/week4-openresponses-gate2.json`
- Gate 3 result: **17 passed, 0 failed**, **19** suite operations,
  **50/56** conservative total
- Gate 3 evidence: `docs/evidence/week4-openresponses-gate3.json`

## Scope and boundaries

This implements the local adapter, genuine adapter-owned encrypted compaction
state, Gate 2 local validation, and one Gate 3 hosted-acceptance run:

- Optional Workbench-owned adapter package under
  `src/transformation_workbench/openresponses_adapter/`.
- Local fake upstream for tests; no hosted model, Console, API key, or public
  endpoint is used in Gate 1 or Gate 2.
- Gate 3 was executed once on 2026-11-17 against the local adapter with Console
  as its upstream. No rerun is authorized.
- No deployment, stage, commit, push, publish, or pinned-suite modification
  was performed.
- The core Workbench, MCP, and A2A packages do not import the adapter.

The adapter is a transport and schema shim. It does not add model capability or
claim real model behavior. The encrypted compaction state is adapter-owned; it
is not OpenAI/Console-native encrypted state and is not claimed to be portable
to another provider or adapter.

## Implemented behavior

- HTTP `POST /responses` translation and deterministic response normalization.
- HTTP `POST /responses/compact` with required-model preflight and pinned
  compaction-schema validation.
- For a valid compact request, the adapter asks its configured upstream
  Responses endpoint for a concise summary, extracts the output text, and
  encrypts the summary into adapter-owned state.
- The supported compaction input subset is message items with `system`, `user`,
  or `assistant` text content, `function_call`, `function_call_output`, and
  existing adapter compaction items. Other item types are rejected locally.
- Top-level `instructions` are preserved in the summary request, and the
  summary prompt treats the transcript as data rather than executable
  instructions.
- HTTP streaming with Open Responses SSE event names, sequence numbers, and
  `data: [DONE]`.
- WebSocket `response.create` turns with per-turn events and connection-scoped
  continuation state.
- `store: false` WebSocket continuation reconstructs the prior request and
  assistant output locally instead of forwarding `previous_response_id`.
- Pinned response and compaction JSON schemas generated from the suite Zod
  sources.
- Loopback-only fail-closed configuration for local mode:
  - `http` only
  - loopback host only
  - explicit port
  - no credentials, path, query, or fragment
  - hosted credential environment variables rejected
- Hosted mode requires explicit opt-in, HTTPS, an explicit upstream host
  allowlist, and the dedicated upstream key variable.
- The adapter uses its own upstream authorization header; suite/local
  authorization is not forwarded upstream.
- Upstream errors are mapped to bounded local errors without leaking request
  bodies.
- Malformed or partial upstream SSE fails with a bounded
  `upstream_protocol_error`.
- WebSocket HTTP-only fields are rejected.
- Missing predecessors return `previous_response_not_found`.
- A failed continuation evicts its predecessor.
- The per-connection cache is bounded to 32 entries.
- Loopback-only `/__local/health`, `/__local/stats`, and
  `/__local/stats/reset` endpoints support operation accounting.

## Genuine compaction state

`compaction.py` implements adapter-owned authenticated encryption:

- AES-256-GCM from `cryptography`, with a random 96-bit nonce per token.
- Dedicated 32-byte key from `OPENRESPONSES_COMPACTION_KEY`, base64url encoded.
- No key derivation from or reuse of the Console API key.
- Missing, invalid, or wrong-size keys fail closed at startup.
- Versioned token prefix `twb1.`.
- Authenticated associated data binds the protocol and adapter context.
- Payload binds format version, adapter protocol, key ID, creation/expiry time,
  model, source item count, and summary.
- Default lifetime is 24 hours; expired state is rejected.
- Plaintext, ciphertext, and token sizes are bounded.
- Up to four compaction items and 48 KiB of reconstructed compacted context
  are accepted per request.
- Tampered, wrong-key, wrong-model, malformed, oversized, expired, and
  unsupported-version state is rejected with bounded spec-shaped errors.
- Error messages and logs do not include the summary, key, authorization
  header, or exception plaintext.

The upstream key and compaction key are read at startup and removed from the
adapter process environment after use. The PowerShell launcher clears the
transient values from its own process immediately after starting the adapter.
The suite runner process does not inherit either secret.

## Local-only fake upstream

`fake_upstream.py` provides an independently startable local app with:

- `GET /healthz`
- `POST /responses`
- modes: `ok`, `http_error`, `malformed_sse`, `partial_sse`,
  `invalid_response`
- request, response-turn, and compaction counters

There is no fake `/responses/compact` route. A fake summary is requested through
`POST /responses` with the local-only `x-workbench-compaction: 1` header. The
fake returns deterministic summary text, and the production adapter exercises
the same AEAD encode/decode path with a test-only key. No test marker or test
key is a normal runtime default.

## Gate 1 tests

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_openresponses_adapter.py -q
```

Result: **35 passed**.

Coverage includes request-value preservation, pinned-schema validation, tool
defaults, HTTP streaming, malformed and partial SSE handling, invalid upstream
responses, upstream error mapping without body leakage, WebSocket multi-turn
continuation, missing-predecessor behavior, failed-continuation eviction,
compacted-output new-chain recovery, HTTP-only field rejection, bounded cache
eviction, compaction preflight, loopback/credential fail-closed behavior,
fake-upstream counters, encrypted compaction round trip, ciphertext
randomization, tamper detection, wrong-key rejection, invalid version, expiry,
missing and invalid key, malformed/oversized payload, model mismatch,
compaction-item limits, error/log redaction, and upstream authorization
separation.

## Gate 2 pinned-suite run

Harness:

```powershell
.\.venv\Scripts\python.exe scripts\run_openresponses_gate2.py
```

The harness:

1. Verifies the pinned suite commit and clean status.
2. Verifies the pinned CLI filter code path.
3. Rejects configured hosted credentials.
4. Starts the fake upstream and gateway on ephemeral loopback ports.
5. Generates a test-only compaction key.
6. Runs exactly one suite test per Bun invocation.
7. Records the result, fake-upstream counts, and adapter operation counts
   without storing request or response bodies.
8. Writes `docs/evidence/week4-openresponses-gate2.json`.

Per-test CLI shape:

```powershell
bun run bin\compliance-test.ts `
  --base-url http://127.0.0.1:<port> `
  --api-key local-dummy-key `
  --model local-fake-model `
  --filter <test-id> `
  --json
```

No retries are performed.

| Test ID | Result | Fake requests | Turns | Compactions | Adapter operations |
| --- | --- | ---: | ---: | ---: | ---: |
| `basic-response` | Passed | 1 | 1 | 0 | 1 |
| `assistant-phase` | Passed | 1 | 1 | 0 | 1 |
| `response-output-phase-schema` | Passed | 0 | 0 | 0 | 0 |
| `streaming-response` | Passed | 1 | 1 | 0 | 1 |
| `websocket-response` | Passed | 1 | 1 | 0 | 1 |
| `websocket-sequential-responses` | Passed | 2 | 2 | 0 | 2 |
| `websocket-continuation` | Passed | 2 | 2 | 0 | 2 |
| `websocket-reconnect-store-false-recovery` | Passed | 2 | 2 | 0 | 2 |
| `websocket-previous-response-not-found` | Passed | 0 | 0 | 0 | 0 |
| `websocket-failed-continuation-evicts-cache` | Passed | 2 | 2 | 0 | 2 |
| `websocket-compact-new-chain` | Passed | 2 | 2 | 1 | 2 |
| `system-prompt` | Passed | 1 | 1 | 0 | 1 |
| `tool-calling` | Passed | 1 | 1 | 0 | 1 |
| `image-input` | Passed | 1 | 1 | 0 | 1 |
| `multi-turn` | Passed | 1 | 1 | 0 | 1 |
| `compact-response` | Passed | 1 | 1 | 1 | 1 |
| `compact-missing-model` | Passed | 0 | 0 | 0 | 0 |

Total adapter upstream operations: **19**. The evidence file records the
per-test and summary counts. Each invocation returned exactly one result
matching the requested test ID, so the pinned filter was isolated for every
run.

## Gate 3

The owner-run harness is split into:

- `scripts/Start-OpenResponses-Gate3.ps1`: prompts for the Console key with
  `Read-Host -AsSecureString`, generates the compaction key, starts the
  adapter with the dedicated upstream key environment, clears transient
  PowerShell secrets, waits for local health, runs the suite runner, and stops
  the adapter.
- `scripts/run_openresponses_gate3.py`: verifies the pinned suite, filters one
  test at a time, calls only the loopback adapter, records operation counts,
  enforces the 23-operation suite allocation, and writes
  `docs/evidence/week4-openresponses-gate3.json`.

The completed Gate 3 configuration used model `gpt-6.1-sol`, one complete run
of the 17 pinned tests, and no retries. The accounting was `31` prior operations
plus `19` suite operations, for `50` total against the `56` ceiling. Two of the
remaining six operations are held as contingency, leaving four above the
reserve. The runner stopped within the 23-operation suite allocation.

Gate 3 result: **17 passed, 0 failed, 0 harness errors**, with **19** actual
suite operations. The evidence records the per-test outcomes, durations, and
operation counts without credentials. No rerun is authorized. See
[the Gate 3 runbook](week4-openresponses-gate3-runbook.md).

A local dry-run of the Gate 3 runner against the fake upstream previously
passed all 17 tests with 19 adapter operations. That validated the harness and
accounting only; it is not hosted-provider compatibility evidence.

## Interpretation

- `response-output-phase-schema` is a client-side schema check and made no
  upstream request.
- `compact-missing-model` was rejected before the upstream call.
- `websocket-previous-response-not-found` was rejected from connection-local
  state without an upstream call.
- `tool-calling`, `image-input`, `system-prompt`, `multi-turn`, and
  `assistant-phase` prove protocol and schema plumbing against deterministic
  fixtures. They do not prove real model quality or semantic understanding.
- The Gate 2 results are local adapter conformance results. Gate 3 exercised the
  same adapter against the Console upstream, but one suite pass is not a general
  provider-conformance or model-quality claim.
- The earlier direct Console route result (1 pass, 16 fail) remains a separate,
  unchanged failure. Gate 3 does not make the bare Console route conformant.
- Encrypted compaction is adapter-owned state around a model-produced summary.
  It is not native provider state, and cross-provider or cross-adapter
  portability is not claimed.

## Limits

- Continuation state is in-memory and connection-scoped; there is no durable
  response store.
- The cache is cleared when a WebSocket connection closes.
- Compaction state is portable only within this adapter and key. Cross-provider
  and cross-adapter portability is not claimed.
- Key rotation is identified by a key ID but there is no online rotation or
  multi-key decrypt support. Rotating the key invalidates outstanding state.
- The fake upstream emits a fixed one-event completion stream; it does not
  emulate provider latency, rate limits, or real tokenization.
- WebSocket support requires `wsproto` (or `websockets`) for uvicorn; `wsproto`
  is included in the `openresponses` extra.
- `cryptography` is included in the `openresponses` extra.
- No new hosted Goose coordinator run was performed during closeout; earlier
  owner-reported diagnostic and wording-repeat sessions are not re-verified
  here. No additional hosted Open Responses probe beyond the single completed
  Gate 3 run was performed.

## Disposition

- Gate 1: complete for the local adapter.
- Gate 2: complete for the pinned suite against the local fake upstream.
- Genuine compaction: complete for local implementation and tests.
- Gate 3: complete; **17 passed, 0 failed**, **19** suite operations, **50/56**
  conservative total.
- No repository commit or push was performed.
