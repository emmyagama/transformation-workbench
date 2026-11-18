# A2A specialists, typed handoffs, and failure handling

> **Current-status note:** this is a dated technical record. The later read-only
> end-to-end demo adds a code-enforced approval state in
> `src/transformation_workbench/approval.py`, but still has no write or business
> action path. See `docs/product/architecture.md` and
> `docs/product/threat-model.md`.

## Scope

The specialist stage extends the protocol slice with two narrow A2A specialists, a
coordinator, and typed handoffs. Everything runs on loopback with the fixed
synthetic fixture. There are no hosted model calls, API keys, cloud endpoints,
write tools, or business actions.

The protocol slice remains separate (`specialist.py`, `coordinator.py`,
`boundary.py`, `tests/test_a2a_integration.py`, and
`docs/archive/a2a-protocol-slice.md`). The specialist stage adds separate modules under
`src/transformation_workbench/a2a/`.

## Architecture

```text
coordinator
  |-- GET /.well-known/agent-card.json  (real HTTP) --> Evidence Specialist
  |-- POST / SendMessage (JSON-RPC) -----------------> Evidence Specialist
  |                                                     |
  |                                                     | MCP stdio (SDK 2.3.0)
  |                                                     v
  |                                          transformation_workbench.mcp_server
  |                                            resources/list + resources/read
  |                                            calculate_baseline_metrics
  |                                            list_case_exceptions
  |                                            get_case_details
  |
  |-- GET /.well-known/agent-card.json  (real HTTP) --> Solution Designer
  |-- POST / SendMessage (JSON-RPC) -----------------> Solution Designer
                                                        (consume EvidencePack only)
```

The coordinator validates the `EvidencePack`, sends it to the Solution Designer
over A2A, validates the returned `SolutionOptions`, and composes one structured
result. A direct Python call is never used in place of the A2A exchange.

## Modules

| Module | Purpose |
| --- | --- |
| `a2a/contracts.py` | Pydantic `EvidencePack`, `SolutionOptions`, trace, calculation, and result models. |
| `a2a/claims.py` | Deterministic guard against currency, savings, ROI, productivity, guarantee, implementation, and unsupported percentage/impact claims. Operational impact projections are allowed only when explicitly labeled as unvalidated hypotheses; financial/savings/ROI claims remain rejected. |
| `a2a/validation.py` | Coordinator validation for metrics, units, provenance, evidence references, trade-offs, and validation steps. |
| `a2a/evidence_source.py` | Read-only MCP client wrapper and `EvidencePack` builder. |
| `a2a/evidence_specialist.py` | Evidence Specialist Agent Card, executor, request parsing, and app. |
| `a2a/solution_designer.py` | Solution Designer Agent Card, deterministic option builder, and app. |
| `a2a/phase2_coordinator.py` | A2A discovery/task client, retries, replay guard, validation, and result composition. |

## Typed contracts

`EvidencePack` contains:

- `contract_version`, `evidence_pack_id`, `request_id`, `generated_by`;
- `snapshot` and `process_context` provenance (`uri`, MIME type, SHA-256,
  snapshot, SLA targets, synthetic/read-only flags);
- `metrics`: the 13 numeric baseline fields, each with an evidence ID, unit,
  value, and read-only tool provenance;
- `exceptions`: excluded rows with row number, reason, and tool provenance;
- `case_observations`: requested cases with classification, timestamps, cycle
  time, SLA/backlog fields, and `get_case_details` provenance;
- `requested_case_ids`, `missing_data`, and `tool_errors`.

`SolutionOptions` contains options with evidence-linked rationale, trade-offs,
assumptions, validation steps, and limitations. It has no measured-value field,
so a recommendation cannot be represented as a measured fact.

## A2A cards

Both cards advertise only loopback endpoints, JSONRPC binding, protocol version
`1.0`, `streaming=False`, `push_notifications=False`, and
`application/json` input/output.

| Agent | Skill ID |
| --- | --- |
| Evidence Specialist | `workbench_evidence` |
| Solution Designer | `solution_options` |

## MCP evidence path

`McpEvidenceSource` launches the existing server with
`StdioServerParameters(command=sys.executable, args=["-m",
"transformation_workbench.mcp_server"])` and the official MCP SDK `stdio_client`
transport. It calls `resources/list` and `resources/read` for
`workbench://process-context`, then calls only the three existing read-only
tools. No fallback context tool was added.

The resource text is hashed with SHA-256 and its parsed snapshot and SLA targets
are compared with the tool snapshot. A mismatch fails the task instead of
choosing one value silently. At the coordinator boundary, the received context
text must equal the fixed local `PROCESS_CONTEXT`, the SHA-256 is recomputed from
the received text, and the snapshot, SLA targets, metric status, and all 13
metric values are compared with deterministic fixture outputs. This verifies
integrity and fixture consistency, not remote attestation.

MCP failures are decomposed:

- resource unavailable/read failure â†’ task fails with `mcp_resource_unavailable`;
- metrics tool failure â†’ task fails with `mcp_tool_error`;
- exception-list failure â†’ `tool_errors` + `missing_data`, no invented rows;
- case-detail failure â†’ `tool_errors` + `missing_data` for that case.

The source accepts an injected session factory so failure tests use fakes and
never touch the filesystem or network.

## Coordinator behavior

- Discovers both cards over HTTP with `A2ACardResolver`.
- Validates skill ID, JSONRPC `1.0`, loopback URL, `application/json` modes, and
  non-streaming capability.
- Sends real `SendMessage` JSON-RPC tasks using the A2A SDK client.
- Ignores environment proxy variables for all loopback A2A HTTP clients.
- Validates `EvidencePack` schema, required metrics, units, provenance,
  requested-case traceability, duplicate evidence IDs, and the coordinator
  request ID.
- Recomputes and checks the process-context hash, then compares the context,
  snapshot, SLA targets, metric status, all metric values, every exception row,
  and every requested case observation with the fixed deterministic fixture.
  Packs with unresolved `tool_errors` or `missing_data` are rejected as
  `incomplete_evidence`.
- Validates `SolutionOptions` schema, request/evidence-pack correlation, known
  evidence IDs, trade-offs, validation steps, and unsupported claim patterns.
- Separates measured facts (`measured_facts`), derived calculations
  (`calculations`), assumptions, and recommendations (`solution_options`).
- Retries only transient transport/timeout failures, with a configurable bound.
  Malformed, invalid, failed-task, or unsupported outputs stop immediately.
- Caches completed work by `request_id`. A replay returns the cached result and
  a `duplicate_replay` trace event without a second A2A call. A replay with
  different inputs is rejected as `request_conflict`.
- Sanitizes the trace to method, path, skill ID, task ID, context ID, state, and
  attempt count. No headers, secrets, or usernames are recorded.

## Failure coverage

| Failure | Test expectation |
| --- | --- |
| Specialist unavailable | bounded `specialist_unavailable`, no result |
| A2A timeout | bounded `a2a_timeout` |
| Task failure/cancel | `task_failure` with the remote status message |
| Non-task response | `non_task_response` |
| Empty/wrong-MIME artifact | `malformed_result` |
| Invalid `EvidencePack` | `invalid_evidence_pack` |
| Missing metric | `missing_metric` |
| Invalid `SolutionOptions` | `invalid_solution_options` |
| Unknown evidence reference | `unknown_evidence_reference` |
| Duplicate request | cached result, one `SendMessage` per specialist |
| MCP resource unavailable | task failure crossing A2A, no artifact |
| MCP tool error | bounded tool error or `tool_errors`; coordinator rejects as `incomplete_evidence` |
| Request-ID mismatch at either handoff | `request_mismatch` |
| Requested case-set mismatch | `case_set_mismatch` |
| Self-reported hash/metric mismatch | `context_hash_mismatch` or `metric_value_mismatch` |
| Exception/case mismatch | `exception_mismatch` or `case_observation_mismatch` |
| Environment proxy variables | ignored for loopback A2A clients |
| Unsupported savings/percentage/impact claim | `unsupported_claim` |
| Labeled unvalidated impact hypothesis | allowed as a non-factual hypothesis |

Every failure path returns or raises a bounded explanatory error, creates no
record/metric, and performs no write or external side effect.

## Versions checked 2026-11-15

| Component | Version |
| --- | --- |
| Python | 3.11.9 |
| A2A protocol | 1.0 |
| `a2a-sdk` | 1.3.0 |
| `mcp` | 2.3.0 |
| `pydantic` | 2.14.3 |
| `httpx` | 0.28.1 |
| `starlette` | 1.10.0 |
| `uvicorn` | 0.54.0 |

## Commands

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pytest tests\test_phase2_integration.py -v
.venv\Scripts\python.exe -m pip check
git diff --check
```

For an immutable review snapshot that excludes `.venv`, set
`PYTHONPATH=<snapshot>\src`, `PYTHONDONTWRITEBYTECODE=1`, and run the shared
Python 3.11 interpreter with `-p no:cacheprovider`.

specialist stage-specific tests:

```powershell
.venv\Scripts\python.exe -m pytest `
  tests\test_phase2_contracts.py `
  tests\test_phase2_evidence_specialist.py `
  tests\test_phase2_solution_designer.py `
  tests\test_phase2_coordinator.py `
  tests\test_phase2_integration.py -q
```

## Integration evidence

The integration test starts two real Uvicorn servers bound to `127.0.0.1` with
ephemeral ports, uses the real MCP stdio server, and records HTTP requests. It
asserts:

- `GET /.well-known/agent-card.json` on both specialists;
- `POST /` with JSON-RPC `SendMessage` on both specialists;
- `input_rows = 15`, `measurable_closed = 9`, `sla_met_percent = 66.7`,
  `excluded_count = 4`, `backlog_cases = 2`;
- snapshot, resource hash, SLA targets, and per-fact tool provenance;
- four exceptions and measurable/invalid/duplicate case observations;
- every solution rationale references an evidence ID present in the pack;
- both task states are `TASK_STATE_COMPLETED` and include task/context IDs;
- a replayed request ID returns the cached result with no second `SendMessage`;
- mismatched `EvidencePack` and `SolutionOptions` request IDs are rejected;
- self-reported metrics, exception rows, and case observations are rejected
  when they differ from the fixture;
- loopback A2A calls succeed while environment proxy variables point at an
  unused proxy port.

Server-generated task and context identifiers are UUIDs and are not reproduced
in this document.

## Limitations and remaining work

- Deterministic rule-based specialists only. No hosted model, streaming,
  authentication, push notifications, or other protocol bindings are tested.
- The fixture, snapshot, and SLA targets are synthetic; no real savings,
  productivity, ROI, or deployment readiness is claimed.
- Human approval remains planned and is not implemented in this workflow.
- No new hosted Goose coordinator run occurred during the latest closeout verification.
  Earlier owner-reported diagnostic and wording-repeat hosted Goose sessions
  succeeded; only the Goose inference was hosted, while the A2A specialist
  exchanges remained local. No checked-in sanitized trace with those request IDs
  was found, so the earlier outcomes remain owner-reported. The separate Open
  Responses adapter Gate 3 is complete for one adapter-plus-Console
  configuration only (17/17, 19 operations, 50/56 conservative total); it is
  not a hosted A2A run and does not generalize to the bare Console route or all
  Open Responses implementations. The local Goose coordinator MCP integration
  is documented separately in `docs/archive/goose-coordinator.md`.
- A2A retry tests use local injected failures; they do not prove behavior under
  a real network partition.
- Context, metric, exception, and case-observation verification checks the fixed
  local fixture for integrity and consistency; it is not remote attestation of
  another agent's claims.
- Dependencies are bounded in `pyproject.toml`, but the project still has no
  lockfile or constraints file for fully reproducible installs.
