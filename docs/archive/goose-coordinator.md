# Goose coordinator integration

## Scope

This gate exposes one narrow, read-only coordinator MCP tool to Goose:

```text
run_a2a_diagnosis
```

The acceptance session does not expose the Workbench metrics, exception, or
case-detail tools directly. Goose calls the coordinator MCP server; the
coordinator starts the two loopback A2A specialists; the Evidence Specialist
uses the official MCP SDK v2 client to read `workbench://process-context` and
call the existing read-only Workbench tools; the Solution Designer receives only
the validated, typed `EvidencePack`.

```text
Goose
  | MCP stdio, one tool: run_a2a_diagnosis
  v
Coordinator MCP server
  | A2A card discovery + SendMessage over loopback
  +--> Evidence Specialist
  |      | MCP SDK v2 stdio
  |      +--> transformation_workbench.mcp_server
  |            resources/list + resources/read
  |            calculate_baseline_metrics
  |            list_case_exceptions
  |            get_case_details
  |
  +--> Solution Designer
         consumes only the validated EvidencePack
```

All servers bind to `127.0.0.1` on ephemeral ports. No hosted model, API key,
cloud endpoint, filesystem path, write tool, business action, or fallback
`get_process_context` tool is used.

## Tool surface

`src/transformation_workbench/coordinator_mcp_server.py` registers only
`run_a2a_diagnosis`. The tool accepts:

- `request_id`: non-empty correlation ID;
- `case_ids`: optional JSON array or comma-separated string of synthetic IDs,
  limited to 20 unique IDs by the coordinator.

The response preserves the coordinator's typed result: measured facts,
calculations, assumptions, solution options, recommendations, and sanitized
A2A trace. Failures return a bounded `ToolError` with the coordinator error code.

The coordinator MCP server does not register the baseline Workbench tools or the
`workbench://process-context` resource. Those remain behind the Evidence
Specialist's own MCP client boundary.

## Local runtime

The local acceptance runtime is in `src/transformation_workbench/a2a/local_runtime.py`.
It starts both specialists on ephemeral loopback ports, runs one
`Phase2Coordinator` exchange, and stops both servers. The direct CLI is:

```powershell
.venv\Scripts\python.exe -m transformation_workbench.a2a.coordinator_cli `
  --request-id phase3-cli-001 `
  --case-id C-009 --case-id C-006 --case-id C-014 `
  --max-retries 0 `
  --format markdown
```

The CLI prints the deterministic user-facing report in Markdown with
`--format markdown`; the default is the sanitized coordinator result as JSON. It
is a local-only acceptance helper; it is not the Goose gate.

## Goose project-agent acceptance

Project agent: `.agents/agents/a2a-coordinator.md`.

Use Goose 1.59.0 with the already installed Ollama 0.40.16 and
`llama3.2:3b` model. No hosted model or API key is used. If `goose` is not on
`PATH`, invoke the installed `goose.exe` directly:

```powershell
goose run `
  --no-profile `
  --with-builtin summon `
  --with-extension "a2a-coordinator:.venv/Scripts/python.exe -m transformation_workbench.coordinator_mcp_server" `
  --provider ollama `
  --model llama3.2:3b `
  --max-turns 6 `
  --output-format json `
  --text 'Call the summon load tool with source a2a-coordinator. Then call a2a-coordinator__run_a2a_diagnosis with request_id goose-a2a-002 and case_ids as the JSON array ["C-009","C-006","C-014"]. Do not call delegate. Return the summary.rendered_markdown field verbatim as your final answer. Do not paraphrase or add a separate summary.'
```

The prompt explicitly requires Summon `load(source: "a2a-coordinator")`; an
`@` mention is not used as proof. The session export command is:

```powershell
goose session export --path <session-id> --format json -o <local-temp-path>
```

## Captured evidence

Evidence-status correction: the captured local sessions are local Ollama
sessions. Earlier owner-reported hosted Goose coordinator sessions also
succeeded: diagnostic `goose-a2a-live-8d618f6b9df94d6ebce302727ee1510e` and
wording-repeat `goose-a2a-repeat-019d021b50364edbaac6217df4f70ec5`. Only the
Goose inference was hosted; the A2A specialist exchanges remained local. No new
hosted Goose coordinator run occurred during the latest closeout verification. No
checked-in sanitized trace with those request IDs was found, so the earlier
outcomes are recorded as owner-reported, not independently verified from a
repository artifact.

Captured 2026-11-15 with Goose 1.59.0, provider `ollama`, model
`llama3.2:3b`. Session: `20261115_25`.

The exported session recorded:

- enabled extensions: `summon` (platform) and `a2a-coordinator` (stdio);
- advertised tools: `a2a-coordinator__run_a2a_diagnosis`, plus Summon
  `delegate`, `load`, and `load_skill`; no Workbench metrics, exception, or
  case-detail tools were advertised;
- `load` tool call with `{"source": "a2a-coordinator"}`;
- tool result beginning `# Loaded: a2a-coordinator (agent)` and containing the
  project agent instructions;
- `a2a-coordinator__run_a2a_diagnosis` call with
  `request_id = "goose-a2a-002"` and the three synthetic case IDs;
- successful structured tool result (`isError: false`) with:
  - `request_id = "goose-a2a-002"`;
  - `workbench_evidence` `TASK_STATE_COMPLETED`, task
    `bb27239d-b9a7-4d99-9583-effa045bd363`, context
    `01d07257-5385-4f63-a898-b0a3fa52b085`;
  - `solution_options` `TASK_STATE_COMPLETED`, task
    `eb2f7a6f-7ac2-4f6b-ab3d-99a5f81aaf92`, context
    `2c15355e-0435-4b77-b8b4-2b06f0a8597a`;
  - `input_rows = 15`, `measurable_closed = 9`, `sla_met_percent = 66.7`,
    `rework_rate_percent = 22.2`, `backlog_cases = 2`, `backlog_overdue = 1`,
    `excluded_count = 4`;
  - three evidence-linked options.

The local 3B model's final prose was unreliable: it described the returned JSON
as a file and did not follow the requested summary format. The runtime evidence
above is the tool-call and structured-result evidence, not the model's prose.
During closeout, the deterministic report was expanded with provenance and
evidence references, the CLI gained `--format markdown`, and the project agent
instruction now requires returning `summary.rendered_markdown` verbatim. No new
model run was performed, so the model-prose criterion remains unverified and is
not claimed as a pass. No hosted model was used to mask this limitation.

## Fixed synthetic evaluation

Full evaluation record: `docs/archive/a2a-acceptance-evaluation.md`.

| Dimension | Result | Evidence |
| --- | --- | --- |
| Traceability | Pass | Sanitized trace contains both card discoveries and both `send_task` exchanges with task/context IDs; every option rationale references a pack evidence ID. |
| Numeric correctness | Pass | All 13 metrics, exception rows, and case observations are compared with the fixed fixture, not only headline metrics. |
| Completeness | Pass | Normal run has 13 metrics, four exceptions, three requested case observations, three options, and no `tool_errors` or `missing_data`. |
| Safety | Pass | Read-only tool surface, loopback-only URLs, bounded failures, claim guards, request/case-set correlation, and no hosted model or business action. |

Persisted evidence:

- `docs/evidence/a2a-trace-20261115.json`
- `docs/archive/goose-session-excerpt.md`
- `docs/evidence/goose-summary-evaluation-20261115.json`

## Deterministic summary and Goose prose evaluation

The coordinator MCP response includes a schema-validated
`summary.rendered_markdown` produced by
`src/transformation_workbench/a2a/summary.py`. The renderer requires both card
discoveries and both completed task exchanges, includes data provenance and
per-fact evidence/source references, all metrics, calculations, exceptions,
requested case observations, assumptions, full option trade-offs and validation
steps, and limits. It rejects missing metrics, incomplete traces, unsupported
claims, and request-ID mismatches.

The local 3B model did not reproduce the earlier deterministic summary. In
session `20261115_26`, request `goose-a2a-003`, the coordinator tool call
succeeded and returned the deterministic summary, but the model's final prose
was a paraphrase/misinterpretation. The criterion
`goose_final_prose_must_reproduce_schema_validated_summary` is therefore
**not met by the model**. The deterministic report is authoritative, and the
agent instruction now requires verbatim output, but no post-change model run was
performed. The tool invocation alone is not reported as prose success. No hosted
model was used to mask this.

## Dispositions for remaining edge cases

- **Base-URL/path issue:** fixed. `require_loopback_url` now rejects non-root
  paths, query strings, fragments, and URL userinfo for all advertised and
  discovered interfaces.
- **Cancellation issue:** not on the supported acceptance path because the
  cards do not advertise cancellation and the coordinator only runs completed
  tasks. The executor now raises the SDK `UnsupportedOperationError` instead of
  `NotImplementedError`; no end-to-end `CancelTask` acceptance is claimed.
- **Hosted Goose coordinator sessions:** no new run occurred during the latest closeout
  verification. Earlier owner-reported diagnostic and wording-repeat hosted
  Goose sessions succeeded; only the Goose inference was hosted, and the A2A
  specialist exchanges remained local. No checked-in sanitized trace with those
  request IDs was found, so the earlier outcomes remain owner-reported.
- **Open Responses adapter Gate 3:** completed separately on 2026-11-17. The
  pinned suite passed 17/17 against the local adapter with Console upstream,
  using 19 operations and a conservative cumulative total of 50/56. The earlier
  direct Console route result (1 pass, 16 fail) remains a separate unchanged
  failure.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest tests\test_coordinator_mcp.py -q
.venv\Scripts\python.exe -m pytest tests\test_week3_acceptance.py tests\test_summary.py -q
```

The tests cover:

- the coordinator MCP surface exposes only `run_a2a_diagnosis`;
- string or JSON-array `case_ids` are normalized;
- coordinator errors become bounded MCP `ToolError`s;
- a real MCP stdio call routes through both loopback A2A specialists and the
  real Workbench MCP child;
- the local runtime preserves request IDs and completed task states.

## Limits

- The coordinator MCP server is read-only by implementation and exposes one
  tool; MCP annotations remain hints, not the enforcement mechanism.
- The local model run proves project-agent loading via Summon and coordinator
  tool execution, not answer quality.
- No new hosted Goose coordinator run was performed during the latest closeout
  verification. Earlier owner-reported hosted Goose sessions succeeded, but no
  checked-in sanitized trace with those request IDs was found.
- The Open Responses adapter Gate 3 is separate from this Goose/A2A workflow and
  covers only one adapter-plus-Console configuration. It is not general Open
  Responses conformance or provider-native compaction.
