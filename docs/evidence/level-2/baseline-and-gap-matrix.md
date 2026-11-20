# Level 2 baseline and requirement-to-evidence matrix

> **Historical Package 0 snapshot.** This note records the pre-implementation
> baseline at `d5a6c97`. It is superseded for current evaluation status by the
> V2 artifacts in this directory, beginning with `README.md`,
> `evaluation-pack-v2/`, and `erratum-v1.md`. Do not read the "no implementation
> or scored evaluation has started" status below as current.

**Package:** 0 — Baseline and evidence crosswalk.

**Snapshot:** 2026-11-19 local check at `d5a6c97` on branch `main`.

**Status:** Package 0 inventory complete. No Level 2 implementation or scored
evaluation has started. Package 1 remains gated on owner review of this note.

## 1. Environment and independently rerun baseline

These results were independently rerun for this note, in the existing project
virtual environment, without hosted calls, credentials, or package installs.

| Item | Value |
| --- | --- |
| Commit | `d5a6c973cae4ee17cd66ed01352a64c159ceb0f8` |
| Branch | `main` |
| Python | 3.11.9 (`.\\.venv\\Scripts\\python.exe`) |
| pytest | 9.2.0 |
| Full suite | `.\\.venv\\Scripts\\python.exe -m pytest -q` -> **249 passed** in 70.74s |
| Dependency check | `.\\.venv\\Scripts\\python.exe -m pip check` -> **No broken requirements found** |

The suite completed without a hosted model/provider call. It exercises local
loopback A2A and local stdio MCP only.

### Working tree

The tree is not clean, and the user's changes were preserved:

- `M .agents/agents/transformation-analyst.md`
- `M .agents/skills/executive-brief/SKILL.md`
- Untracked owner documents, including `Expanded_Project_Roadmap.md`,
  `Level_2_Execution_Runbook.md`, week runbooks, product draft, and
  `docs/demos/screen-recording-run-of-show.md`.

`git diff --ignore-space-at-eol` produced no content diff for the two modified
tracked files, consistent with line-ending normalization only. No source or test
file is modified.

### Owner/OpenCode-reported, not independently reproduced here

- PR #3 merge at `d5a6c97`.
- Clean-clone verification with 249 passing tests and clean `pip check`.
- The original demo/clean-clone checks in `docs/product/evaluation.md` at
  `b0f2e3e`.

This note independently reproduced the current worktree suite and `pip check`,
not a clean clone. A clean-clone rerun is still required in Package 4.

## 2. Requirement-to-evidence matrix

Status values: `covered`, `partial`, `missing`, `blocked`.

### 2A. Evaluation system

| Requirement | Existing evidence | Status | Smallest gap |
| --- | --- | --- | --- |
| Versioned, fixed evaluation pack separate from unit tests | None. The 249 tests are unit/integration tests, not a frozen evaluation corpus. | **missing** | Add the 10-case corpus, expected manifest, rubric version, and deterministic runner. |
| Clean baseline request | `tests/test_week4_workflow.py:241` end-to-end path; `docs/evidence/end-to-end-sample-report.md` | **partial** | Record it as a frozen case with expected status and invariants, not only as a unit test. |
| Missing, stale, or unreadable context/resource | `tests/test_phase2_evidence_specialist.py:114` missing resource; `:123` metrics tool error; `:136` exception tool error | **covered** at code level | Add a scored case record and trace pointer. |
| Unknown case ID and tool error | `tests/test_mcp_server.py:361` unknown/path-like case; `tests/test_phase2_evidence_specialist.py:148` case tool error | **covered** at code level | Add a scored case record; confirm the expected outcome (missing case vs hard failure) is frozen. |
| Contradictory evidence or metric targets | `tests/test_phase2_coordinator.py:461` metric mismatch; `:362` request mismatch; `:417` case-set mismatch; `src/transformation_workbench/a2a/validation.py:43` | **covered** | Add scored cases and expected error codes. |
| Prompt injection embedded in source/evidence | `tests/test_week4_workflow.py:190` injected process-context text fails hash/fixture verification; `:170` intake injection rejection; `src/transformation_workbench/security.py:36` | **partial** | Add an evaluation case that distinguishes request-text injection from evidence/source injection and records the safe terminal state. |
| Unsupported SLA, savings, ROI, or certainty claim | `tests/test_phase2_coordinator.py:520` and `:553`; `tests/test_week4_workflow.py:152`; `src/transformation_workbench/a2a/claims.py:14` | **covered** | Add scored cases for ROI/guarantee/certainty wording, not only `$` and `%` examples. |
| Unauthorized write, approval, email, or ticket request | `tests/test_week4_workflow.py:101` pending/approved action disabled; `:107` approved still cannot execute; `:122` approval reference; `:433` role/tool/shell rejection; `src/transformation_workbench/approval.py:135` | **partial** | Add an explicit email/ticket/write request case. The code has no action capability, but the safe-refusal/limitation behavior is not directly scored. |
| Duplicate/replayed task and unavailable specialist | `tests/test_phase2_coordinator.py:42` duplicate replay; `:104` conflicting replay; `:126` unavailable specialist; `tests/test_coordinator_mcp.py:119` process cache | **covered** | Add separate scored variants so outcomes are attributable. |
| Slow response/timeout and bounded retry exhaustion | `tests/test_phase2_coordinator.py:141` timeout; `:162` retry exhaustion; `tests/test_a2a_integration.py:204` timeout | **covered** | Add scored cases with the exact configured timeout/retry values. |
| Malformed JSON, wrong MIME type, missing field, invalid provenance | `tests/test_phase2_coordinator.py:248` empty/wrong MIME; `:287` invalid evidence/solution schema; `:335` unknown evidence reference; `src/transformation_workbench/a2a/validation.py:97` | **covered** | Add scored cases for each variant and expected rejection code. |
| Per-case record: fixture/version, request, expected invariants, actual result, pass/fail, trace pointer, failure category, retry count, human judgment | None. | **missing** | Add the expected manifest and result record format in Package 1. |
| Deterministic evaluation runner | None separate from pytest. | **missing** | Add a local runner that reuses the deterministic core and emits a scorecard. |

### 2B. Measurable quality gates

| Threshold | Existing evidence | Status | Smallest gap |
| --- | --- | --- | --- |
| Numeric correctness: 100% exact match to independently tested fixture values | `tests/test_metrics.py:8`; `tests/test_week4_workflow.py:241`; `tests/test_week3_acceptance.py:53`; `docs/evidence/a2a-trace-20261115.json` | **covered** for the current fixture | Tie each scored case to an independent expected-value manifest. |
| Contract integrity: 100% schema validation; invalid results rejected, not repaired | `src/transformation_workbench/a2a/contracts.py:36` (`extra="forbid"`); `validation.py:43`; coordinator parse/reject tests | **covered** | Add per-case schema-validation outcomes to the scorecard. |
| Evidence traceability: every factual claim tied to evidence, or marked unknown/assumption | `src/transformation_workbench/report.py:467` evidence appendix; `validation.py` provenance checks; `tests/test_summary.py:118` | **covered** | Define and freeze the exact traceability rubric. |
| Safety: zero successful prohibited actions and zero unsupported financial claims accepted as facts | `approval.py:135` fail-closed action method; `claims.py:138`; tests above | **partial** | Add explicit unauthorized email/ticket/write case and score safe limitation/refusal. |
| Completeness: 100% required fields/sections for a complete result; partial must identify missing sections and cause | `report.py:72` report model; `summary.py:53` rejects incomplete evidence/options; `tests/test_week4_workflow.py:62` | **partial** | Freeze the required-section list and add per-case completeness scoring. There is no partial result status. |
| Failure containment: terminate inside deadline/retry bounds with truthful status and no fabricated success | `phase2_coordinator.py:282` bounded retries; `:325` task-state check; `evidence_source.py:129` MCP timeout; tests above | **covered** for tested failures | Add partial-completion, shutdown, and log-redaction cases. |
| Repeatability: same fixture metrics and pass/fail from a clean checkout | Current worktree rerun passes; clean-clone is owner-reported only | **partial** | Run the clean-clone check in Package 4 and record commands/results. |
| Latency/cost: only if actually captured; distinguish local elapsed time from provider latency and estimated from billed cost | Not captured. | **covered by omission** | Do not report latency/cost unless measured; no provider cost exists under the no-hosted-call boundary. |

### 2C. Reliability and resilience

| Requirement | Existing evidence | Status | Smallest gap |
| --- | --- | --- | --- |
| Explicit deadlines at coordinator and specialist boundaries | `phase2_coordinator.py:82` timeout; `:291` `asyncio.wait_for`; `evidence_source.py:95` MCP timeout; `local_runtime.py:58` shutdown wait | **covered** | Freeze exact values used by the scored run. |
| Bounded retries only for retryable failures | `phase2_coordinator.py:282`; `_transient_code` at `:571`; tests `:141`, `:162` | **covered** | Add retry-count assertions to scored cases. |
| Duplicate/replayed task idempotent or explicitly rejected | `phase2_coordinator.py:113` cache; `:117` conflicting-input rejection; `tests/test_phase2_coordinator.py:42`, `:104` | **covered** | Add scored variant and expected trace marker. |
| Partial completion: one specialist succeeds, other fails; never imply full completion | No partial result path. `CoordinatorResult.status` is only `complete` (`contracts.py:181`); a specialist failure raises `task_failure`. | **missing** | Owner decision: keep whole-workflow failure as the safe partial behavior and test it, or add a partial status/schema. Do not add partial success silently. |
| Cancellation/shutdown behavior | `evidence_specialist.py:109` cancel; `tests/test_phase2_coordinator.py:209` cancelling executor; `tests/test_a2a_integration.py:181` failed/cancelled bounded; `local_runtime.py:53` shutdown | **partial** | Add an explicit coordinator/runtime shutdown test and record terminal status. |
| Loopback-only service binding | `local_runtime.py:20`; `a2a/boundary.py:8`; `tests/test_a2a_integration.py:100`, `:123`, `:129`, `:149` | **covered** | Include the assertion in the scored safety evidence. |
| Logs useful but redact keys, secrets, usernames/paths, unnecessary prompt content | `tests/test_week3_acceptance.py:71` persisted trace has no secret markers; `tests/test_week4_workflow.py:544` logging level only; Open Responses adapter has its own log-leak test | **partial** | Add a Workbench log-redaction test covering request text, local paths, and credential-like values. |
| Task state transitions and retry counts; no hidden unbounded retries or duplicate hosted requests | `phase2_coordinator.py:266` state; `:267` trace attempt; tests `:141`, `:162`; no hosted path in Workbench | **covered** | Add per-case state/attempt expectations to the manifest. |

### 2D. Comparative experiment

| Requirement | Existing evidence | Status | Smallest gap |
| --- | --- | --- | --- |
| Identify a fair non-delegating baseline path | The only end-to-end path is the two-specialist A2A path (`workflow.py:29` -> `local_runtime.py:65` -> `phase2_coordinator.py`). `a2a/coordinator.py` is a protocol echo helper, not a diagnosis baseline. | **blocked** | Owner decision: authorize the smallest local comparison harness that reuses the deterministic core and read-only evidence, or record the comparison as blocked. |
| Run the same frozen cases, fixture, schema, and rubric through both paths | No baseline path and no frozen corpus yet. | **blocked** | Depends on the baseline decision and Package 1 freeze. |
| Report per-case differences and bounded conclusions | No comparison report. | **missing** | Produce after both paths exist and the corpus is frozen. |

### Level 2 deliverables and exit gate

| Deliverable | Status | Note |
| --- | --- | --- |
| Versioned corpus, rubric, runner, expected manifest | **missing** | Package 1. |
| Reproducible scorecard with per-case outcomes, taxonomy, misses | **missing** | Package 4. |
| Fault-injection suite covers timeouts, duplicate tasks, resource/tool errors, malformed outputs, partial agent failure, prompt injection | **partial** | Partial agent failure and explicit unauthorized-action cases are the main gaps. |
| Safety and numeric thresholds met, or documented remediation/defer decision | **not yet assessed** | Requires the scored run. |
| Controlled CLI comparison of baseline and A2A | **blocked** | No fair baseline path; owner decision required. |
| Local re-run without hosted access; tests use fakes | **covered** for the existing suite | Add the evaluation runner. |
| Owner reviews corpus and failure report; no cherry-picking or silent rubric changes | **pending** | Package 1 and Package 4 checkpoints. |

## 3. Package 0 conclusion

The current baseline is reproducible in the existing worktree: 249 tests pass,
`pip check` is clean, and no hosted call or install is needed. Most Level 2
safety, contract, and failure-containment behaviors already have code-level
evidence, so Package 2 should not re-implement them. The material Level 2 gaps
are the frozen evaluation pack/runner/scorecard, partial-completion and explicit
unauthorized-action coverage, Workbench log-redaction coverage, clean-clone
reproduction, and the 2D baseline comparator.

## 4. Owner review required before Package 1

1. Confirm this baseline and gap matrix, and confirm that the two line-ending-only
   tracked modifications and untracked owner documents should remain untouched.
2. Decide the 2D comparator: authorize a minimal local non-delegating harness, or
   record the comparison as blocked.
3. Decide the partial-completion policy: keep whole-workflow failure as the safe
   behavior and test it, or approve a partial-result schema.
4. Confirm that Package 1 may freeze the 10-case corpus, expected manifest,
   rubric, and thresholds using the runbook defaults.
