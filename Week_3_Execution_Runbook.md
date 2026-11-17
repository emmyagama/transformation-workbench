# Week 3 Execution Runbook — A2A Collaboration + Open Responses

**Project:** [Transformation Workbench](https://github.com/emmyagama/transformation-workbench)
**Starting point:** Week 1 and Week 2 are public on `main` at `17faecf55318b7474237f9cfa939855e4d6ec16e`.
**Schedule:** Start the resource preflight immediately; pull Week 3 forward rather than waiting for the original Nov 27–29 window. Preserve the 24–32 focused-hour budget; do not compress safety/evaluation to hit a calendar date.
**Branch proposal:** `feat/week3-goose-a2a`, branched from current `origin/main`.
**Primary data:** The existing fixed synthetic fixture only. No production/business/customer/personal data.
**Owner-confirmed choices:** Goose integration is core (not stretch); use a bounded number of hosted Console calls after a spend limit is set; preflight proper MCP resource reading and add a read-only context-tool fallback only if that path proves necessary.

## Objective

Build a small, genuine multi-agent workflow in which a coordinator discovers and delegates tasks to two specialist agents over the A2A protocol, validates typed results, and produces an evidence-backed transformation brief. Resolve or explicitly defer the `workbench://process-context` resource-access issue in a short preflight. Run one deliberately small Open Responses compatibility experiment and document its exact boundary.

This is a substantive extension of the working Goose + MCP Week 2 workflow. A Python function call between two functions is **not** A2A. A successful OpenAI Responses request is **not**, by itself, proof of full Open Responses compatibility.

## Week 3 exit deliverables

1. **MCP resource preflight result** documenting whether a standard MCP client can list and read `workbench://process-context`, whether Goose exposes it, and the resulting design decision.
2. **Two A2A specialist agents and one coordinator**, using the current official A2A specification and official Python SDK where suitable. Each specialist has a discoverable Agent Card and a narrow task boundary.
3. **A real protocol exchange**: the coordinator discovers both Agent Cards, sends A2A messages/tasks to the Evidence Specialist and Solution Designer, receives typed results, validates them, and composes the final output. Capture task IDs/statuses or equivalent protocol evidence. Do not describe direct Python calls or Goose Summon delegation as A2A.
4. **MCP evidence retrieval in the Evidence Specialist** using the official MCP SDK v2 client, preferably reading `workbench://process-context` with MCP `resources/list`/`resources/read` and calling the existing read-only metrics/exception tools. Do not add a duplicate context tool unless the preflight justifies it and the owner approves.
5. **Typed handoff contracts**, at minimum an `EvidencePack` and `SolutionOptions` schema. Every measured fact carries a source/tool reference; recommendations carry trade-offs and validation steps. The coordinator rejects malformed, unsupported, or untraceable outputs rather than filling gaps from memory.
6. **Failure handling and tests** for specialist unavailable, A2A timeout, task failure/cancel, malformed/empty result, invalid schema, duplicate/replayed task, MCP resource unavailable, MCP tool error, and unsupported savings/impact claims. Retries must be bounded and must not create side effects.
7. **One small Open Responses interoperability experiment** using a synthetic-only, non-streaming request. Record the exact specification version, provider/model/endpoint, request/response shape, what worked, what did not, and whether the test demonstrates only endpoint compatibility or broader spec compatibility. Use the OpenCode Console credential only in a process-scoped local environment, never in source, prompts, logs, screenshots, or chat. Set a Console spend limit before live calls. Unit tests use fakes and make no API calls.
8. **Evaluation evidence** for normal completion and safe failure, with reproducible commands, measured latency/cost only if actually captured, test results, and limitations.
9. **Public contribution 3**: a concise technical walkthrough of real A2A task exchange, typed handoffs, failure behavior, and limits. No claims of live business operations, savings, deployment readiness, or implemented approval controls.

## Proposed specialist boundaries

### Evidence Specialist

- Reads the fixed `workbench://process-context` resource when a standard MCP client can access it.
- Uses only the existing bounded Transformation Workbench MCP tools for metrics, exceptions, and case details.
- Returns an `EvidencePack`: snapshot, exact metric fields, exception list, requested case observations, provenance references, and explicit missing-data/tool-error states.
- Does not make recommendations, estimate savings, modify data, or use shell/filesystem/browser/action tools.

### Solution Designer

- Receives only the coordinator-validated `EvidencePack`; it does not independently retrieve or alter process data.
- Returns a `SolutionOptions` object: proposed options, rationale tied to evidence IDs, trade-offs, assumptions, and validation steps.
- Does not claim an option is implemented, does not invent savings/ROI, and does not ask another system to act.

### Coordinator

- Discovers the specialist Agent Cards using the A2A client/SDK and sends genuine A2A tasks/messages over a local protocol endpoint.
- Passes the validated evidence package to the Solution Designer and validates the returned schema and evidence references.
- Handles timeouts, task failures, duplicate task submissions, and unsupported outputs with bounded retries and safe stop behavior.
- Produces a concise result separating measured facts, calculations, assumptions, and recommendations.

**Owner-confirmed architecture:** Goose remains the user-facing host. For the Week 3 A2A workflow, Goose exposes only a new, narrowly scoped read-only coordinator MCP extension/tool (e.g. `run_a2a_diagnosis`); it must not also expose the underlying Workbench tools directly in that acceptance session, so the path necessarily crosses the coordinator. The coordinator discovers the two local A2A specialists and sends real A2A tasks/messages. The Evidence Specialist uses the official MCP SDK v2 client to launch/connect to the existing Workbench MCP server over stdio, read the process-context resource and call the existing read-only data tools. It returns a typed evidence package to the coordinator, which passes it over A2A to the Solution Designer and validates the result. All processes bind to loopback; no shell/developer/general-filesystem extension is enabled. This preserves a clear proof of both protocol boundaries: Goose-to-coordinator MCP and coordinator-to-specialists A2A.

## Preflight: `workbench://process-context`

The public MCP server currently registers `workbench://process-context` as an MCP resource. MCP resources are application/client-read data, not model-callable tools. Goose's Week 2 sessions did not expose the resource contents to the agent; the agent used its documented fallback and disclosed the limitation.

1. From a clean project checkout, use the official MCP Inspector or a small test using the installed MCP SDK v2 `Client` with `StdioServerParameters` to connect to the existing server.
2. Verify `resources/list` includes exactly `workbench://process-context`, then call `resources/read` for that URI. Confirm it returns the fixed snapshot, SLA thresholds, process definitions, synthetic-only policy, and read-only boundary.
3. Record the exact client/version, result, and sanitized trace. Keep protocol diagnostics on stderr; never contaminate stdio JSON-RPC stdout.
4. Separately check whether Goose's intended MCP integration exposes resource contents to the host/model. Do not infer Goose resource support solely from a successful standalone-client read.
5. Decision:
   - If the standalone MCP client cannot list/read it, diagnose/fix the server or SDK registration first and add a regression test.
   - If standalone works but Goose does not expose it, treat that as a host/client integration boundary. Prefer having the Evidence Specialist's explicit MCP client read it; document the Goose limitation. Only consider a bounded `get_process_context` read-only tool if needed for compatibility and approved after review.
   - If it reads successfully in both, remove the fallback limitation only after a captured Goose/A2A run proves it.

**Preflight gate:** Do not begin multi-agent implementation until the server-side resource status is known. A Goose limitation alone does not block the independent A2A specialist from using a proper MCP client.

## Protocol and implementation rules

- Check current official A2A docs and SDK release/version before pinning; use the current A2A protocol version. Record exact versions in `pyproject.toml`/lockfile and docs.
- Agent Cards must advertise only the narrow skills actually implemented, accepted input/output media types, and local endpoints. Do not publish user-specific paths, credentials, or LAN/public endpoints.
- Coordinator must perform an actual A2A discovery plus message/task exchange with each specialist. Include a sanitized trace proving the task crosses the protocol boundary.
- Use JSON/Pydantic models for internal validated handoffs. If A2A artifact content is text or JSON, validate the declared MIME type and schema before use.
- Keep the computation core deterministic; model agents may interpret evidence and propose options, but must not replace the tested metrics calculation.
- Bind local development services to loopback. Do not add remote access, cloud hosting, or deployment.
- Do not enable Goose developer, shell, general filesystem, browser, or business-action tools for this workflow.
- MCP annotation hints remain hints, not enforcement. Read-only behavior must be enforced by the tool surface/server implementation and narrow client configuration.
- No writes, approvals, emails, tickets, or other external/business actions. Human approval remains planned work for a later phase, not implemented in Week 3.

## Open Responses experiment boundary

Use at most one small, synthetic-only non-streaming request for the experiment unless the owner approves more budget. Prefer the existing OpenCode Console pay-as-you-go route with a process-scoped key, and do not use `api.openai.com` with the Console key. Confirm the current Console endpoint and model availability before sending.

Record:

- Open Responses specification version/revision used;
- provider/model and exact endpoint (no secret headers or key values);
- whether the request was authored to the Open Responses schema or merely sent to an OpenAI Responses-compatible endpoint;
- response status, item types, parsed output, and any translation/compatibility differences;
- what this test does **not** prove.

Do not label the endpoint or provider “Open Responses compliant” on the basis of a successful text response alone. No multi-provider abstraction, streaming, tool execution, persistent conversation state, or production integration is required. If the compatibility boundary is unclear or the endpoint rejects the schema, preserve the sanitized error and document the result instead of silently changing APIs.

## Evaluation plan

### Deterministic/local tests (no hosted calls)

- Unit-test metric and handoff-schema validation using the existing synthetic fixture and test doubles.
- A2A protocol integration test: card discovery, Evidence Specialist task, Solution Designer task, coordinator validates and composes result.
- Verify the agent outputs reference evidence IDs and never convert a recommendation into a measured fact.
- Failure injection: missing resource, unavailable agent, timeout, task error, duplicate task, malformed JSON/MIME, missing metric, unknown case, contradictory target, and empty output.
- Assert all failures return a bounded, explanatory result with no fabricated record/metric and no side effect.

### Hosted smoke evaluation (only after local tests pass and budget is set)

1. One normal end-to-end request; confirm both A2A specialists participate and the coordinator validates their typed handoffs.
2. One repeat run to compare deterministic tool-derived metrics; wording/options may vary, baseline values may not.
3. One adversarial/safety request combining an unsupported 100% SLA/$100,000 savings claim with a request to perform an action; verify correction and refusal. The tools have no write capability, and no action is performed.
4. Keep the Open Responses experiment separate from the A2A acceptance test so the two protocol results are not conflated.

Capture calls, task IDs/statuses, model usage/latency only if available, and sanitized final outputs. No raw keys, headers, provider configs, local usernames/paths, or full internal reasoning in public evidence.

## Schedule and time budget

- **Phase 0 — preflight and design gate (3–4 h):** resource read verification, official A2A/SDK version check, Open Responses endpoint/spec boundary, architecture decision.
- **Phase 1 — A2A protocol vertical slice (4–5 h):** one local agent card, coordinator discovery, one real task/message round trip, protocol trace.
- **Phase 2 — specialists and typed handoffs (7–9 h):** Evidence Specialist, Solution Designer, coordinator; MCP evidence retrieval; schema validation.
- **Phase 3 — safety/failures/evaluation (4–6 h):** local integration tests, fault injection, one bounded hosted run and repeat if approved.
- **Phase 4 — Open Responses spike (2–3 h):** one minimal request, compatibility notes, no production integration.
- **Phase 5 — docs/review/public contribution (4–5 h):** architecture diagram/sequence, tested setup, evidence, limitations, code review, public technical walkthrough draft.

Target total: **24–32 focused hours**. If the official SDK or provider blocks the chosen approach, capture the error, reduce implementation scope safely, and document the boundary—do not replace A2A with direct function calls and call it done.

## Definition of done

- [x] Resource preflight result recorded; Goose-host limitation versus server behavior correctly distinguished.
- [x] Two specialist Agent Cards are discoverable on local endpoints.
- [x] Coordinator makes actual A2A protocol calls to both specialists and receives task/results.
- [x] Evidence Specialist uses the fixed synthetic MCP evidence source; exact tool/resource provenance retained.
- [x] Solution Designer receives validated evidence and returns typed options tied to evidence IDs.
- [x] Coordinator validates outputs and fails safely on bad schema, failed agent, timeout, duplicate task, or missing evidence.
- [x] No business writes/actions or unsupported financial claims are possible in the demonstrated tool scope.
- [x] Local deterministic tests pass; evaluation outcomes and failures are recorded.
- [x] Open Responses adapter experiment reported narrowly; the direct Console failure and the adapter-plus-Console pass are kept separate.
- [x] Walkthrough draft includes a sequence diagram, tested commands, protocol trace, limits, and no secrets.
- [x] README separates demonstrated behavior from future plans; human approval remains labeled planned/not implemented.
- [x] Contribution 3 is scoped to the authorized complete Week 3 PR to `main`; merge and release remain separate approvals.
- [x] Earlier owner-reported hosted Goose coordinator diagnostic and wording-repeat sessions are recorded; no new hosted run was made for the latest closeout verification.

## Closeout status (2026-11-17)

- Local A2A acceptance: complete; closeout suite **214 passed**.
- Goose/A2A evidence: captured local Ollama sessions plus earlier owner-reported
  hosted Goose diagnostic and wording-repeat sessions. Only the Goose inference
  was hosted; A2A specialist exchanges remained local. The model-prose criterion
  remains not met, and the deterministic report is authoritative.
- Open Responses adapter Gate 3: complete for one adapter-plus-Console
  configuration; **17 passed, 19 operations, 50/56** conservative total. The
  direct Console route failure remains separate and unchanged.
- Contribution 3: reviewed and scoped to the authorized complete Week 3 PR to
  `main`; merge and release are separate approvals.
- Hosted Goose coordinator sessions: earlier owner-reported diagnostic and
  wording-repeat hosted Goose sessions succeeded; no new hosted run was made for the latest closeout
  verification. No checked-in sanitized trace with those request IDs was found.

## Confirmed execution decisions

The owner selected:

1. **Goose integration is core.** Goose calls only the Week 3 coordinator MCP tool in the A2A acceptance session; the coordinator uses actual A2A protocol exchanges with both specialists. Do not downgrade this to a standalone-only CLI demonstration.
2. **Bounded hosted use.** All automated tests use local fakes. After the owner sets a spend limit in Console, allow at most one live A2A diagnostic, one repeat, and one separate Open Responses smoke request. Budget target: at most four hosted Goose inference requests across the two earlier hosted runs, plus one separate Open Responses request, five total. The A2A specialist exchanges remain local. If the design requires more, pause and get the owner's decision before spending more. Credentials stay process-scoped and out of files/logs.
3. **Resource handling.** First test proper `resources/list` / `resources/read` with the MCP SDK v2 client. Have the Evidence Specialist read the resource if available. Add a bounded read-only `get_process_context` tool only if preflight proves the actual client path needs this compatibility fallback; do not add it pre-emptively.
4. **Schedule.** Start the preflight now and pull implementation forward, retaining the full 24–32 hour budget and safety/evaluation gates.

## Official references

- [A2A Protocol — current specification and Python SDK tutorials](https://a2a-protocol.org/latest/)
- [A2A Python client: Agent Card discovery and message/task exchange](https://a2a-protocol.org/latest/tutorials/python/6-interact-with-server/)
- [A2A Python server and Agent Card](https://a2a-protocol.org/latest/tutorials/python/5-start-server/)
- [MCP Python SDK: resource declaration](https://py.sdk.modelcontextprotocol.io/servers/resources/)
- [MCP Python SDK: resource-reading client](https://py.sdk.modelcontextprotocol.io/client/)
- [MCP Python SDK: stdio client transport](https://py.sdk.modelcontextprotocol.io/client/transports/)
- [Open Responses specification](https://www.openresponses.org/specification)
- [Open Responses reference](https://www.openresponses.org/reference)
- [OpenCode Console endpoints for other harnesses](https://opencode.ai/docs/console/harnesses/)
- [OpenCode Console model catalog](https://opencode.ai/docs/console/models/)
