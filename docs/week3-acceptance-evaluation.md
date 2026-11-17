# Week 3 acceptance evaluation

## Snapshot under test

- Branch: `feat/week3-goose-a2a`
- HEAD: `17faecf55318b7474237f9cfa939855e4d6ec16e`
- Original acceptance date: 2026-11-15; closeout verification: 2026-11-17
- Local command: `.venv\Scripts\python.exe -m pytest -q`
- Closeout result: **214 passed** (the original Week 3 snapshot recorded
  **175 passed**; the closeout suite also includes the separate Open Responses
  adapter tests)

## Fixed synthetic evaluation

| Dimension | Result | Evidence |
| --- | --- | --- |
| Traceability | Pass | `test_real_mcp_stdio_and_dual_a2a_round_trip` verifies both card discoveries, both `send_task` events, task/context IDs, completed states, request IDs, and evidence-linked options. |
| Numeric correctness | Pass | The same integration test compares all 13 metrics and exact exception/case-observation values with the fixed fixture. |
| Completeness | Pass | Normal run has 13 metrics, four exceptions, three requested case observations, three options, and no `tool_errors` or `missing_data`. |
| Safety | Pass | Loopback-only root URLs, read-only coordinator MCP surface, bounded failures, request/case-set correlation, claim guards, and no hosted model or business action. |

## Failure and edge coverage

| Scenario | Test evidence | Observed behavior |
| --- | --- | --- |
| A2A timeout | `test_a2a_timeout_is_bounded`, `test_timeout_retries_are_bounded` | bounded `a2a_timeout`; retry stops at the configured bound |
| Unavailable specialist | `test_specialist_unavailable_is_bounded` | bounded `specialist_unavailable`, two attempts at `max_retries=1` |
| Duplicate/completed replay | `test_dual_real_a2a_exchange_and_duplicate_replay`, `test_coordinator_mcp_replay_uses_process_cache`, MCP end-to-end replay | cached result; MCP-level replay returns `duplicate_replay` without a second run |
| Duplicate request with different inputs | `test_duplicate_request_with_different_inputs_is_rejected` | `request_conflict` |
| Failed/cancelled task | `test_task_failure_and_cancel_stop_safely` | bounded `task_failure` |
| Malformed/empty/wrong-MIME artifact | `test_empty_and_wrong_mime_artifacts_are_rejected`, Phase 1 artifact tests | `malformed_result` or `missing_artifact` |
| Invalid evidence/solution schema | `test_invalid_evidence_and_solution_schemas_are_rejected` | schema-specific bounded errors |
| MCP resource failure | `test_mcp_resource_failure_crosses_a2a_as_task_failure` | task failure crosses A2A; no artifact |
| MCP tool error / missing data | `test_incomplete_evidence_is_rejected_at_boundary` | coordinator rejects `incomplete_evidence` |
| Request-ID mismatch | `test_evidence_pack_request_mismatch_is_rejected_at_boundary`, `test_solution_options_request_mismatch_is_rejected_at_boundary` | `request_mismatch` |
| Case-set mismatch | `test_requested_case_set_mismatch_is_rejected_at_boundary` | `case_set_mismatch` |
| Exception-row tampering | `test_exception_record_must_match_fixture` | `exception_mismatch` |
| Case-observation tampering | `test_case_observation_must_match_fixture` | `case_observation_mismatch` |
| Unsupported percentage/impact claim | claim-guard contract tests and A2A tests | `unsupported_claim`; labeled unvalidated operational hypothesis allowed |
| Non-loopback or non-root endpoint | Phase 1 tests | `invalid_agent_card` / `ValueError` |
| Proxy environment variables | Phase 1 and Phase 2 proxy tests | loopback calls still go direct |

## Goose/A2A/MCP evidence

Evidence-status correction: the captured local sessions are local Ollama
sessions. Earlier owner-reported hosted Goose coordinator sessions also
succeeded:

- Diagnostic request `goose-a2a-live-8d618f6b9df94d6ebce302727ee1510e`.
- Wording-repeat request `goose-a2a-repeat-019d021b50364edbaac6217df4f70ec5`.

Only the Goose inference was hosted; the A2A specialist exchanges remained
local. No new hosted Goose coordinator run occurred during the latest closeout
verification. No checked-in sanitized trace with these request IDs was found,
so the earlier outcomes are recorded as owner-reported, not independently
verified from a repository artifact.

- Goose 1.59.0, Ollama 0.40.16, `llama3.2:3b`, no API key.
- Session `20261115_25` loaded project agent `a2a-coordinator` through Summon
  `load`, then called only the coordinator MCP tool.
- The tool result shows both A2A specialists completed with task/context IDs.
- Sanitized trace: `docs/evidence/week3-a2a-trace-20261115.json`.
- Sanitized session excerpt: `docs/evidence/week3-goose-session-excerpt.md`.

## Goose final-prose criterion

The coordinator returns a deterministic, schema-validated
`summary.rendered_markdown`. During closeout, the renderer was expanded to
include data provenance and per-fact evidence/source references, all 13
metrics, calculations, exceptions, requested case observations, assumptions,
and full option trade-offs, validation steps, and limits. The CLI can print it
with `--format markdown`, and the project agent instruction now requires the
model to return that report verbatim. The pre-closeout renderer's hash is kept
below as historical evidence; it does not describe the current report.

In session `20261115_26`, the tool call and structured summary succeeded, but
the local 3B model paraphrased and misinterpreted the result instead of
reproducing the summary. No rerun was performed after the closeout instruction
change, so no model behavior is claimed for it.

- Historical pre-closeout summary SHA-256:
  `6e2181ec04b63ac44c4f3a365d7f13a8d477e69e35b6266ceec5488dd3672d3a`
- Final model prose SHA-256:
  `338e4d02dd3f59883bfc326b109a07e6ed64e80821e62a23c98ac21fac2d761a`
- Outcome: **model-prose criterion not met**. The deterministic report is the
  authoritative user-facing output; tool invocation alone is not counted as
  prose success.

Evidence: `docs/evidence/week3-goose-summary-evaluation-20261115.json`.

## Dispositions

- **Base-URL/path:** fixed. Loopback URLs must be root HTTP URLs; paths, query
  strings, fragments, and userinfo are rejected.
- **Cancellation:** outside the supported task-completion path; cards do not
  advertise cancellation. The executor raises the SDK
  `UnsupportedOperationError`; no end-to-end `CancelTask` acceptance is claimed.
- **JSON-RPC persisted trace:** closed with the sanitized trace artifact. It
  covers discovery and both task/result exchanges, though it does not retain raw
  JSON-RPC request IDs or response headers.
- **Hosted Goose coordinator sessions:** no new run occurred during the latest closeout
  verification. Earlier owner-reported diagnostic and wording-repeat hosted
  Goose sessions succeeded; only the Goose inference was hosted, and the A2A
  specialist exchanges remained local. No checked-in sanitized trace with those
  request IDs was found, so the earlier outcomes remain owner-reported.
- **Open Responses adapter Gate 3:** completed separately on 2026-11-17. The
  pinned suite passed 17/17 against the local adapter with OpenCode Console
  upstream, using 19 operations and a conservative cumulative total of 50/56.
  The earlier direct Console route result (1 pass, 16 fail) remains a separate,
  unchanged failure.
- **Dependency reproducibility:** `anyio` is declared; no lockfile or constraints
  file is present.

## Limits

- Local deterministic specialists only; no hosted Goose inference quality claim.
- No real network-partition, streaming, authentication, or push-notification
  testing.
- No deployment, business action, approval workflow, or real data.
- The Open Responses adapter Gate 3 is one adapter-plus-Console configuration,
  not the bare Console route, general Open Responses conformance, or a hosted
  A2A run.
