# Week 3 technical contribution: local A2A collaboration

**Status: WEEK 3 CONTRIBUTION — prepared for the complete Week 3 PR.** This
document records the Week 3 A2A implementation and evidence. Earlier
owner-reported hosted Goose diagnostic and wording-repeat sessions succeeded;
no new hosted Goose coordinator run occurred during the latest closeout verification.
Only the Goose inference was hosted; the A2A specialist exchanges remained
local. No checked-in sanitized trace with those request IDs was found, so those
outcomes are recorded as owner-reported. Hosted Goose inference cost/latency was not
measured. The separate Open Responses adapter Gate 3 result is recorded as a
distinct result, not as A2A evidence. Nothing here proves production readiness.

## Scope and boundary

This is a technical walkthrough of a small, real multi-agent workflow built over
the existing Transformation Workbench synthetic fixture:

- Goose loads the project coordinator agent through Summon, not an `@` mention.
- Goose sees one narrow coordinator MCP tool, not the Workbench tools.
- The coordinator discovers two A2A specialists and sends real A2A tasks.
- The Evidence Specialist uses an MCP SDK v2 client to read a resource and call
  the existing read-only Workbench tools.
- Typed, correlated results are validated before the Solution Designer receives
  them.
- The coordinator returns a deterministic summary and a sanitized protocol trace.

The workflow uses synthetic data only. It has no write or business-action tool,
no hosted model call in the captured local run, no deployment, no approval
workflow, and no real business data. Human approval for consequential actions
remains planned work, not implemented behavior. No new hosted Goose coordinator run
occurred during the latest closeout verification; earlier owner-reported hosted
Goose diagnostic and wording-repeat sessions succeeded while the A2A specialist
exchanges remained local. The separate Open Responses adapter Gate 3 run is not
A2A evidence and is described only in its own bounded section.

## End-to-end flow

```text
Goose host
  | Summon load(source: "a2a-coordinator")
  | MCP stdio, one advertised tool: run_a2a_diagnosis
  v
Coordinator MCP server
  | real HTTP GET /.well-known/agent-card.json
  | real JSON-RPC POST / SendMessage
  +--> Evidence Specialist (loopback A2A)
  |      | MCP SDK v2 stdio
  |      +--> transformation_workbench.mcp_server
  |            resources/list + resources/read
  |            workbench://process-context
  |            calculate_baseline_metrics
  |            list_case_exceptions
  |            get_case_details
  |      |
  |      +--> typed EvidencePack
  |
  +--> Coordinator validates the pack and fixture
  |
  +--> Solution Designer (loopback A2A)
         consumes only the validated EvidencePack
         returns typed SolutionOptions
  |
  +--> deterministic summary + sanitized trace
```

The important boundary is that the A2A exchange is not a Python function call.
The coordinator uses the official A2A client to fetch each Agent Card and send
JSON-RPC `SendMessage` tasks over loopback HTTP. The Evidence Specialist then
crosses a second protocol boundary with its own MCP SDK v2 client. The
coordinator does not expose the Workbench tools to Goose and does not add a
fallback `get_process_context` tool.

Relevant implementation points:

- `src/transformation_workbench/coordinator_mcp_server.py:81` registers
  `run_a2a_diagnosis`.
- `src/transformation_workbench/coordinator_mcp_server.py:66-72` describes the
  read-only coordinator surface.
- `src/transformation_workbench/a2a/local_runtime.py:19-52` starts both
  specialists on ephemeral `127.0.0.1` ports.
- `src/transformation_workbench/a2a/phase2_coordinator.py:95-192` runs
  discovery, both A2A sends, fixture validation, and result composition.
- `src/transformation_workbench/a2a/evidence_source.py:248-302` lists and reads
  `workbench://process-context`; `:320-375` calls the existing bounded tools.
- `src/transformation_workbench/a2a/summary.py:52` renders the deterministic,
  schema-validated summary.

## Typed and correlated handoffs

The handoffs are not free-form model text. They are Pydantic contracts:

- `EvidencePack` carries contract/version identifiers, `request_id`, generated-by
  metadata, process-context provenance, metrics with evidence IDs and tool
  provenance, exceptions, case observations, requested case IDs, missing-data
  markers, and tool-error markers.
- `SolutionOptions` carries proposed options with evidence-linked rationale,
  trade-offs, assumptions, validation steps, and limitations. It has no measured
  value field, so a recommendation cannot become a measured fact by schema
  accident.

Key validation behavior:

- Every measured fact must have provenance.
- The coordinator recomputes the process-context hash and compares the received
  context text, snapshot, SLA targets, metric status, all 13 metric values, every
  exception row, and every requested case observation with the fixed local
  fixture.
- The Evidence Specialist's requested case set must match the coordinator's
  request with set equality and matching length.
- Duplicate case observations are rejected.
- Unknown evidence references in solution rationale are rejected.
- Request-ID mismatches at either handoff are rejected.
- Unsupported savings, ROI, currency, guarantee, and implementation claims are
  rejected; a clearly labeled operational hypothesis is allowed.
- The coordinator caches completed work by `request_id`. A replay with the same
  case set returns the cached result with a `duplicate_replay` trace event; a
  replay with different inputs raises `request_conflict`.

Relevant implementation points:

- `src/transformation_workbench/a2a/contracts.py` defines the typed contracts.
- `src/transformation_workbench/a2a/validation.py:43` validates `EvidencePack`.
- `src/transformation_workbench/a2a/validation.py:206` verifies evidence against
  the fixed fixture.
- `src/transformation_workbench/a2a/validation.py:316` validates
  `SolutionOptions`.
- `src/transformation_workbench/a2a/phase2_coordinator.py:160-192` performs
  request/case-set validation and solution validation.
- `src/transformation_workbench/a2a/claims.py:129-170` implements the
  deterministic claim guard.
- `tests/test_phase2_contracts.py` covers provenance, missing metrics, unknown
  evidence, request mismatches, fixture tampering, and unsupported claims.
- `tests/test_phase2_coordinator.py` covers handoff mismatches and replay
  behavior.

This validation proves consistency with the packaged fixture and the local
contracts. It is not remote attestation of another agent's claims, and it does
not prove the fixture itself reflects a real business process.

## Read-only boundary

The acceptance session exposes only:

```text
a2a-coordinator__run_a2a_diagnosis
```

plus Summon's `delegate`, `load`, and `load_skill` tools. The Workbench metrics,
exception, and case-detail tools are not advertised to Goose.

Safety properties:

- All A2A servers bind to `127.0.0.1` on ephemeral ports.
- A2A endpoint validation requires explicit loopback root HTTP URLs; paths,
  query strings, fragments, and URL userinfo are rejected.
- Loopback HTTP clients use `trust_env=False`, so proxy environment variables do
  not redirect the exchange.
- The coordinator starts local specialists and the Workbench MCP child; it does
  not accept caller-supplied paths or arbitrary commands.
- There are no write, ticket, email, approval, shell, browser, or business-action
  tools in the workflow.
- MCP read-only annotations are only hints. Read-only behavior is enforced by the
  narrow server/tool surface and implementation, not by client annotations alone.

Relevant implementation points:

- `src/transformation_workbench/coordinator_mcp_server.py:66-72`
- `src/transformation_workbench/a2a/local_runtime.py:19-52`
- `src/transformation_workbench/a2a/boundary.py:5-24`
- `src/transformation_workbench/a2a/phase2_coordinator.py:216-220,324-335`
- `tests/test_coordinator_mcp.py` asserts the one-tool surface.
- `tests/test_week3_acceptance.py:22-50` asserts the Workbench tools are absent
  from the advertised tools.

The boundary is read-only by design and implementation. It is not a hardened
operating-system sandbox, and the local MCP child still runs with the invoking
user's filesystem permissions.

## Bounded failure behavior

The local tests exercise these paths without fabricating metrics or performing a
side effect:

| Failure path | Observed bounded behavior |
| --- | --- |
| Specialist unavailable | `specialist_unavailable` |
| A2A timeout | `a2a_timeout`; retries stop at the configured bound |
| Task failure or cancellation | `task_failure`; no completed artifact |
| Non-task response | `non_task_response` |
| Empty or wrong-MIME artifact | `malformed_result` or `missing_artifact` |
| Invalid evidence or solution schema | schema-specific bounded error |
| Missing metric or provenance | `missing_metric` or provenance error |
| Duplicate request with different inputs | `request_conflict` |
| Duplicate replay with same inputs | cached result and `duplicate_replay` |
| Request-ID mismatch | `request_mismatch` |
| Requested case-set mismatch | `case_set_mismatch` |
| MCP resource unavailable | task failure crosses A2A; no artifact |
| MCP tool error or missing data | bounded tool error or `incomplete_evidence` |
| Fixture mismatch | `context_hash_mismatch`, `metric_value_mismatch`, `exception_mismatch`, or `case_observation_mismatch` |
| Unsupported savings/impact claim | `unsupported_claim`; labeled hypothesis allowed |

Retries are bounded to `max_retries + 1` attempts and apply only to transient
transport/timeout failures. Malformed, invalid, failed-task, or unsupported
outputs stop immediately.

Relevant tests:

- `tests/test_phase2_coordinator.py:126-184` for unavailable, timeout, and
  retry bounds.
- `tests/test_phase2_coordinator.py:209-287` for task failure, non-task
  responses, and malformed artifacts.
- `tests/test_phase2_coordinator.py:362-433` for request and case-set
  mismatches.
- `tests/test_phase2_coordinator.py:594-611` for MCP resource failure crossing
  A2A.
- `tests/test_coordinator_mcp.py:119-146` and `:161-189` for process-level and
  real MCP stdio replay.
- `tests/test_week3_acceptance.py:22-86` for persisted evidence assertions.

## Local deterministic evaluation

### Fixture and expected shape

The fixture is `src/transformation_workbench/data/synthetic_cases.csv`. The
normal local exchange requests three synthetic cases: `C-009`, `C-006`, and
`C-014`.

The local integration test verifies:

- All 13 required metric fields.
- Four excluded rows:
  - `C-006`, row 7, `INCOMPLETE_MISSING_CLOSED_AT`
  - `C-010`, row 11, `INVALID_DATE`
  - `C-011`, row 12, `OUT_OF_ORDER`
  - `C-014`, row 15, `DUPLICATE_OF:C-007`
- The three requested case observations, including `C-009` as measurable,
  `C-006` as invalid, and `C-014` as a duplicate.
- Three solution options, each with trade-offs, validation steps, and rationale
  that references only known evidence IDs.
- Three deterministic calculations:
  - `calc.sla_misses`
  - `calc.excluded_share`
  - `calc.backlog_overdue_share`
- No `tool_errors` and no `missing_data` on the normal path.
- Both specialist task states are `TASK_STATE_COMPLETED` with non-empty task and
  context IDs.

### Actual local results

The captured sanitized trace records:

| Metric | Value |
| --- | ---: |
| `input_rows` | 15 |
| `measurable_closed` | 9 |
| `cycle_time_sum_hours` | 261.5 |
| `mean_cycle_time_hours` | 29.06 |
| `median_cycle_time_hours` | 9.0 |
| `sla_met_count` | 6 |
| `sla_met_percent` | 66.7 |
| `rework_cases` | 2 |
| `rework_rate_percent` | 22.2 |
| `rework_volume` | 3 |
| `backlog_cases` | 2 |
| `backlog_overdue` | 1 |
| `excluded_count` | 4 |

The captured options are:

- `option-triage-backlog`
- `option-data-quality`
- `option-rework-review`

The original Week 3 A2A snapshot recorded **175 passed**. The closeout suite
now records **214 passed**; that full count includes the separate Open Responses
adapter tests. These are local, synthetic-fixture results. They do not establish
hosted Goose inference quality, real operational performance, savings, or production
readiness.

Evidence:

- `docs/week3-acceptance-evaluation.md`
- `docs/evidence/week3-a2a-trace-20261115.json`
- `tests/test_phase2_integration.py:22-153`
- `tests/test_week3_acceptance.py:22-86`
- `tests/test_phase2_contracts.py`
- `tests/test_summary.py`

## Goose local evidence and the prose failure

### Captured local sessions

The captured local evidence uses Goose `1.59.0`, Ollama `0.40.16`, and
`llama3.2:3b`; no hosted model or API key was used.

Session `20261115_25`:

- Summon `load` request: `{"source": "a2a-coordinator"}`.
- Result begins `# Loaded: a2a-coordinator (agent)`.
- The session advertised only the coordinator tool plus Summon
  `delegate`, `load`, and `load_skill`; no Workbench tools.
- The coordinator tool returned `isError: false`.
- Both A2A tasks completed:
  - Evidence task `bb27239d-b9a7-4d99-9583-effa045bd363`, context
    `01d07257-5385-4f63-a898-b0a3fa52b085`.
  - Solution task `eb2f7a6f-7ac2-4f6b-ab3d-99a5f81aaf92`, context
    `2c15355e-0435-4b77-b8b4-2b06f0a8597a`.

Session `20261115_26`, request `goose-a2a-003`:

- The coordinator tool call succeeded and returned the deterministic summary.
- The local 3B model's final prose did **not** equal or contain the summary.
- Historical pre-closeout summary SHA-256:
  `6e2181ec04b63ac44c4f3a365d7f13a8d477e69e35b6266ceec5488dd3672d3a`
  (length 1181). This hash describes the old renderer, not the current report.
- Final model prose SHA-256:
  `338e4d02dd3f59883bfc326b109a07e6ed64e80821e62a23c98ac21fac2d761a`
  (length 1952).
- `hosted_model_used: false`.
- Outcome: `model_prose_criterion_not_met`.

The closeout expanded the deterministic report with data provenance, per-fact
evidence and source references, exceptions, requested case observations, and
full option trade-offs and validation steps. The CLI can print it with
`--format markdown`, and the project agent instruction now requires returning
`summary.rendered_markdown` verbatim. No new model run was performed, so no
post-change model behavior is claimed.

### What the local failure proves

- The coordinator MCP tool invoked successfully.
- The structured, schema-validated deterministic summary was produced.
- The local 3B model's final prose was unreliable and did not reproduce that
  summary.
- The result is honestly recorded as a model-prose failure, not as a prose
  success. The deterministic report remains the authoritative output.

### What it does not prove

- It does not prove that a stronger local model will fail.
- It does not prove that a stronger model will reproduce the summary.
- It does not prove hosted model quality, latency, or cost.
- It does not establish that free-form model prose is safe without additional
  review. The deterministic summary remains the authoritative structured output.

Evidence:

- `docs/evidence/week3-goose-session-excerpt.md`
- `docs/evidence/week3-goose-summary-evaluation-20261115.json`
- `docs/week3-goose-coordinator.md`
- `docs/week3-acceptance-evaluation.md`
- `tests/test_summary.py`

## Separate Open Responses adapter result

This result is not A2A evidence. On 2026-11-17, the pinned official suite
(`dce9ddb91921427c2ba06901c7dfaf0cc7056799`) passed 17/17 against the local
Workbench-owned adapter configured with OpenCode Console upstream. The run used
19 operations, no retries, and a conservative cumulative total of 50/56. The
adapter's AES-256-GCM compaction state is adapter-owned; it is not
provider-native or cross-provider portable. The earlier direct Console route
result (1 pass, 16 fail) remains a separate, unchanged failure. This single
adapter-plus-Console pass is not general Open Responses conformance or
model-quality evidence.

Evidence:

- `docs/evidence/week4-openresponses-gate3.json`
- `docs/week4-openresponses-gate3-runbook.md`
- `docs/week4-openresponses-local-adapter.md`

## Claims and evidence

Statuses used here:

- **VERIFIED LOCAL**: supported by this repository's tests or captured local
  evidence.
- **CAPTURED LOCAL**: recorded in a sanitized local artifact, not independently
  reproduced by this review.
- **CAPTURED HOSTED**: recorded in a sanitized single-run hosted artifact, not
  independently rerun.
- **OWNER-REPORTED**: asserted by the owner in the closeout instructions; no
  checked-in sanitized artifact was found for independent verification.
- **VERIFIED LOCAL ARTIFACTS**: supported by repository artifacts and tests, not
  an external audit.
- **NOT PERFORMED**: no run was performed; do not infer a result.

| # | Claim | Status | Evidence | Boundary |
| ---: | --- | --- | --- | --- |
| 1 | Goose loaded the project coordinator agent through Summon `load`, not an `@` mention | **CAPTURED LOCAL** | `docs/evidence/week3-goose-session-excerpt.md`; `docs/evidence/week3-a2a-trace-20261115.json`; `docs/week3-goose-coordinator.md` | Sanitized, self-authored excerpt; no raw export hash |
| 2 | Earlier hosted Goose diagnostic and wording-repeat sessions succeeded | **OWNER-REPORTED** | Request IDs `goose-a2a-live-8d618f6b9df94d6ebce302727ee1510e` and `goose-a2a-repeat-019d021b50364edbaac6217df4f70ec5` in the closeout instructions; no checked-in sanitized trace found | Only Goose inference was hosted; A2A specialist exchanges remained local; no new hosted run during closeout |
| 3 | The Goose session advertised only the coordinator tool plus Summon tools | **CAPTURED LOCAL** | `advertised_tools` in `docs/evidence/week3-a2a-trace-20261115.json`; `tests/test_week3_acceptance.py:22-50` | Based on the captured export |
| 4 | The coordinator MCP surface exposes one tool and no Workbench tools | **VERIFIED LOCAL** | `src/transformation_workbench/coordinator_mcp_server.py`; `tests/test_coordinator_mcp.py`; `tests/test_week3_acceptance.py` | MCP annotations are hints; surface enforcement is implementation-level |
| 5 | The coordinator performs real A2A discovery and sends tasks to both specialists | **VERIFIED LOCAL** | `src/transformation_workbench/a2a/phase2_coordinator.py:148-192`; `tests/test_phase2_integration.py:22-153`; trace artifact | Loopback only; local deterministic specialists |
| 6 | The Evidence Specialist reads `workbench://process-context` and calls the existing read-only tools through MCP SDK v2 | **VERIFIED LOCAL** | `src/transformation_workbench/a2a/evidence_source.py:248-375`; `tests/test_phase2_integration.py:22-92`; `docs/week3-phase2-a2a.md` | Local MCP stdio; no Goose resource-exposure claim |
| 7 | Typed handoffs, request/case-set correlation, provenance, and schema validation are enforced | **VERIFIED LOCAL** | `src/transformation_workbench/a2a/contracts.py`; `validation.py:43-340`; `phase2_coordinator.py:160-192`; `tests/test_phase2_contracts.py`; `tests/test_phase2_coordinator.py` | Local contracts; not remote attestation |
| 8 | Exception rows and requested case observations are verified against the fixed fixture | **VERIFIED LOCAL** | `src/transformation_workbench/a2a/validation.py:206-313`; `tests/test_phase2_integration.py:49-92`; `tests/test_phase2_contracts.py:191-229` | Synthetic fixture only |
| 9 | The workflow is read-only and loopback-bounded in the demonstrated path | **VERIFIED LOCAL** | `coordinator_mcp_server.py:66-146`; `boundary.py:5-24`; `local_runtime.py:19-52`; `tests/test_coordinator_mcp.py` | Not a hardened OS sandbox |
| 10 | Timeout/retry, unavailable specialist, duplicate replay/conflict, malformed artifacts, MCP failures, and unsupported claims have bounded behavior | **VERIFIED LOCAL** | `tests/test_phase2_coordinator.py:126-611`; `tests/test_coordinator_mcp.py:119-189`; `docs/week3-acceptance-evaluation.md` | Local fault injection; no real network partition |
| 11 | A deterministic, schema-validated user-facing report with provenance and evidence references is produced and tested | **VERIFIED LOCAL** | `src/transformation_workbench/a2a/summary.py`; `tests/test_summary.py`; `tests/test_phase2_integration.py:144-153`; `coordinator_cli.py --format markdown` | Deterministic local output; not model prose quality |
| 12 | The local deterministic suite passed | **VERIFIED LOCAL** | `docs/week3-acceptance-evaluation.md`; closeout suite **214 passed**; original snapshot **175 passed** | Recorded local result; the 214 count includes the separate adapter tests |
| 13 | The local Goose final prose failed to reproduce the summary | **CAPTURED LOCAL** | `docs/evidence/week3-goose-summary-evaluation-20261115.json`; `docs/week3-goose-coordinator.md` | Failure of the 3B local model, not of the coordinator tool; no post-change model run |
| 14 | Hosted Goose inference cost and latency | **NOT PERFORMED** | No measured token, request, latency, or price evidence exists | Do not infer values or budget consumption |
| 15 | Earlier hosted Goose wording-repeat | **OWNER-REPORTED** | Request ID `goose-a2a-repeat-019d021b50364edbaac6217df4f70ec5` in the closeout instructions; no checked-in sanitized trace found | Only Goose inference was hosted; A2A specialist exchanges remained local; no new hosted run during closeout |
| 16 | Open Responses adapter Gate 3 against one adapter-plus-Console configuration | **CAPTURED HOSTED** | `docs/evidence/week4-openresponses-gate3.json`; `docs/week4-openresponses-gate3-runbook.md` | 17/17, 19 operations, 50/56; the direct Console route's 1-pass/16-fail result remains separate and unchanged; not general Open Responses conformance |
| 17 | The demonstrated workflow uses no real business data, secrets, or business action | **VERIFIED LOCAL ARTIFACTS** | `AGENTS.md`; tests; sanitized evidence; `docs/week3-acceptance-evaluation.md` | This is a repository/evidence review, not an external audit |
| 18 | The adapter's encrypted compaction state is adapter-owned AES-256-GCM state | **VERIFIED LOCAL** | `src/transformation_workbench/openresponses_adapter/compaction.py`; `tests/test_openresponses_adapter.py` | Not provider-native, not OpenAI/Console-native, and not cross-provider or cross-adapter portable |

## Separate A2A repeat command

The repository contains a documented **local** A2A CLI, not a hosted A2A repeat
command. The exact safe local repeat command is:

```powershell
.venv\Scripts\python.exe -m transformation_workbench.a2a.coordinator_cli `
  --request-id phase3-cli-002 `
  --case-id C-009 --case-id C-006 --case-id C-014 `
  --max-retries 0 `
  --format markdown
```

Why this is the safe documented form:

- It uses a fresh `request_id` (`phase3-cli-002`) rather than the documented
  first-run example `phase3-cli-001`.
- It keeps the same three synthetic cases used by the acceptance evidence, so the
  deterministic metrics can be compared.
- `--max-retries 0` avoids retries for the repeat.
- It starts only local loopback specialists and does not consume hosted budget.

Request count for that command:

- **2 A2A task requests**: one `SendMessage` to the Evidence Specialist and one
  `SendMessage` to the Solution Designer.
- **2 A2A discovery requests**: one `GET /.well-known/agent-card.json` to each
  specialist.
- **0 hosted model requests**.

Inside the Evidence Specialist, the local exchange also performs one
`resources/read` and the Workbench tool calls needed to build the evidence pack
(metrics, exceptions, and case details for the requested cases). Those are MCP
calls, not additional A2A task requests.

An earlier **hosted** wording-repeat session
(`goose-a2a-repeat-019d021b50364edbaac6217df4f70ec5`) is owner-reported as
successful, but no checked-in sanitized trace or hosted repeat command/result
exists in this repository. The A2A specialist exchanges in that session remained
local. Do not represent the local command above as a hosted repeat.

## Egg-info inspection

The stale generated package metadata is **not tracked** in Git.

Observed state:

- `src/transformation_workbench.egg-info/` exists in the working tree.
- `.gitignore:4` contains `*.egg-info/`.
- `git ls-files -- "src/transformation_workbench.egg-info"` returns no files.
- `git check-ignore -v "src/transformation_workbench.egg-info/PKG-INFO"` matches
  the `.gitignore` rule.
- `git status --short --ignored -- "src/transformation_workbench.egg-info"`
  reports it as ignored (`!!`), not staged or untracked for commit.
- The files are generated setuptools/editable-install metadata; `PKG-INFO` is
  older than the corrected README and still contains an earlier description.
- The directory is present in the frozen snapshot
  `AAIF-Journey-review-week3-final2-20261115` because the snapshot copied
  `src/` without excluding `*.egg-info`; its files are listed in that snapshot's
  `SHA256SUMS.txt` lines 44-48.

Safest later cleanup, during a future working-tree cleanup:

1. Do not edit or delete anything inside the frozen review snapshot.
2. In a future working-tree cleanup, remove only the ignored generated
   `src/transformation_workbench.egg-info/` directory, or leave it in place; it
   is not repository content.
3. If editable-install metadata is needed afterward, regenerate it from the
   project environment with the documented install command; do not hand-edit
   `PKG-INFO`.
4. When creating a future snapshot, exclude `*.egg-info` (and other build/cache
   artifacts) in the copy script. Create a new snapshot rather than modifying an
   existing frozen one.

No deletion, regeneration, or metadata edit was performed during this closeout.

## Known limits and remaining work

- **No new hosted Goose coordinator run during closeout**: earlier owner-reported
  diagnostic (`goose-a2a-live-8d618f6b9df94d6ebce302727ee1510e`) and
  wording-repeat (`goose-a2a-repeat-019d021b50364edbaac6217df4f70ec5`) sessions
  succeeded. Only Goose inference was hosted; A2A specialist exchanges remained
  local. No checked-in sanitized trace with those request IDs was found.
- **Hosted Goose inference cost/latency not measured**: no token, request, latency, or price
  evidence has been captured for A2A.
- **Open Responses adapter Gate 3 is separate**: one adapter-plus-Console run
  passed 17/17 with 19 operations and a conservative 50/56 total. The earlier
  direct Console route result (1 pass, 16 fail) remains separate and unchanged.
  This is not general Open Responses conformance, model-quality evidence, or
  A2A evidence.
- **Publication scope**: this contribution is included in the complete Week 3 PR
  to `main`, with the implementation, tests, docs, and sanitized evidence needed
  for reproducibility. Merge and release are separate approvals.
- **Local deterministic only**: the specialists are rule-based; the captured
  Goose run used `llama3.2:3b` locally; no hosted model quality is claimed.
- **No streaming, authentication, push notifications, multi-turn behavior, or
  real network-partition testing.**
- **Cancellation is outside the supported completion path**: cards do not
  advertise cancellation; no end-to-end `CancelTask` acceptance is claimed.
  Phase 1 raises the SDK `UnsupportedOperationError`; Phase 2 executors send
  cancellation updates rather than providing an end-to-end acceptance path.
- **Sanitized trace**: the trace records discovery and both task/result
  exchanges, but not raw JSON-RPC request IDs, parameter bodies, or response
  headers.
- **Sanitized Goose trace/excerpt**: the trace and excerpt are owner-authored
  sanitized artifacts derived from the sessions; no independently verified
  raw-export hash is checked in.
- **No lockfile or constraints file**: dependencies are bounded in
  `pyproject.toml`, but installs are not fully reproducible from a lock.
- **Case-set replay fingerprint is order-sensitive** in the MCP cache: the same
  set in a different order can be treated as a request conflict.
- **The MCP process cache is unbounded for the server lifetime**: acceptable for
  this read-only local demo, not a production cache policy.
- **IPv6 allowlist vs IPv4 bind**: `::1` is accepted by the URL guard while the
  local runtime binds IPv4; no accepted path currently uses `::1`.
- **Stale generated egg-info is present in the frozen snapshot**: repository
  tracking is unaffected; older snapshot evidence includes the generated file.
- **No human approval workflow**: consequential actions are not implemented, and
  future approval controls remain planned rather than enforced here.

## Publication checklist

Before this contribution is published:

- Keep every **NOT PERFORMED** item explicit; replace it only with captured,
  sanitized evidence.
- Keep earlier hosted Goose sessions marked **OWNER-REPORTED** until a sanitized
  trace is checked in; do not invent task IDs or outcomes.
- Do not publish any hosted Goose inference cost/latency value unless it was actually
  measured.
- Keep the Open Responses claim limited to the one adapter-plus-Console Gate 3
  run; do not generalize it to the bare Console route, other providers, or full
  specification conformance.
- Keep the local Goose prose failure visible; do not convert tool-call success
  into prose-quality success.
- The closeout local suite recorded **214 passed** on 2026-11-17; record any
  future rerun separately rather than reusing this result.
- Review the final text for secrets, local paths, usernames, provider
  credentials, and unsupported business or savings claims.
- Publish only as the reviewed complete Week 3 PR to `main`; do not merge or
  release in the same step.
