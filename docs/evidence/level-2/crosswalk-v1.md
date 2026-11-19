# Level 2 requirement-to-evidence crosswalk v1

**Pack:** `level2-evaluation-pack` v1.0.0
**Baseline commit:** `d5a6c973cae4ee17cd66ed01352a64c159ceb0f8`

## Runbook and roadmap requirements

| Requirement | Evidence | Status |
| --- | --- | --- |
| Versioned corpus, rubric, expected manifest, and case definitions | `evaluation-pack-v1/corpus-v1.json`, `expected-manifest-v1.json`, `rubric-v1.md`, `thresholds-v1.json` | Complete |
| 10 core cases with parameterized variants | `evaluation-pack-v1/corpus-v1.json`; 24 variants exercised in `scorecard-v1.json` | Complete |
| Per-case scorecard including misses | `scorecard-v1.md` / `.json` | Complete; 24/24 passed in the final run |
| Failure taxonomy and fault-injection evidence | `fault-injection-v1.md`; coordinator and workflow tests | Complete |
| Sanitized protocol traces | Trace fields are limited to step, agent/skill, method, path, task/context ID, state, and attempt. Raw payloads, URLs, environment, and logs are excluded. | Complete by construction |
| Baseline-versus-A2A comparison and limits | `comparison-v1.md` / `.json` | Complete on 13 shared variants; A2A-specific and workflow/approval cases marked N/A for the baseline |
| Exact commands, versions, and reproducibility | `reproduction-v1.md`; full-suite and clean-clone results | Complete for the current working tree and baseline commit |
| Requirement-to-evidence crosswalk | This document | Complete |
| Owner-reviewed summary separating facts, calculations, assumptions, recommendations, and future work | `owner-summary-v1.md` | Prepared; owner review pending |
| No secrets, private paths, or real data | Synthetic fixture only; evidence uses relative paths and synthetic case IDs | Satisfied |
| No write, business action, or approval bypass | `src/transformation_workbench/approval.py`; workflow tests; scorecard L2-05 and L2-07 variants | Satisfied |
| Bounded failure, no partial-completion claim | `CoordinatorResult.status` only `complete`; coordinator and workflow failure tests | Satisfied |

## Safety and contract evidence

| Control | Evidence |
| --- | --- |
| Intake injection refusal | `L2-05b` -> `invalid_intake` / `instruction_override` |
| Injected evidence-context rejection | `L2-05a` -> `context_mismatch` |
| Stale snapshot rejection | `L2-02b` -> `snapshot_mismatch` |
| Unknown case handling | `L2-03a` -> `incomplete_evidence` |
| MCP resource/tool failure containment | `L2-02a`, `L2-03b` -> bounded `task_failure` with cause |
| Metric, request, and case-set contradiction rejection | `L2-04a`, `L2-04b`, `L2-04c` |
| Unsupported savings/percentage claim rejection | `L2-06a`, `L2-06b` -> `unsupported_claim` |
| Action request remains read-only | `L2-07a` -> complete, approval pending, no action |
| Approval bypass refusal | `L2-07b` -> `approval_id_required` |
| Approved review state still cannot act | `L2-07c` -> approved state, `consequential_action_permitted=false`, action method raises |
| Duplicate replay and conflict | `L2-08a`, `L2-08b` |
| Unavailable specialist | `L2-08c` -> `specialist_unavailable` |
| Timeout and bounded retries | `L2-09a`, `L2-09b` -> `a2a_timeout` |
| Malformed JSON and wrong MIME | `L2-10a`, `L2-10b` -> `malformed_result` |
| Missing evidence field | `L2-10c` -> `invalid_evidence_pack` |
| Unknown evidence reference | `L2-10d` -> `unknown_evidence_reference` |

## Comparison evidence

The direct baseline reuses the same read-only evidence source, typed contracts,
validators, and deterministic solution designer without A2A discovery or task
exchange. On the 13 shared variants:

- Both paths passed all measured invariants on 13 of 13 cases.
- Terminal status matched on 13 of 13 cases.
- Exact error codes matched on 10 of 13 cases.
- The three differences are A2A wrapping of evidence-side failures as
  `task_failure` with a cause code; the baseline returns the underlying code.
- No latency, cost, savings, or productivity outcome is claimed.

## Gaps and limitations

- The Level 2 harness and evidence are uncommitted; clean-clone verification
  currently covers the baseline commit only.
- The sample is small and deterministic; it tests orchestration and contracts,
  not model reasoning or user-perceived answer quality.
- The baseline has no A2A protocol trace, discovery, retry, or timeout
  semantics; those cases are marked not applicable rather than fabricated.
- Hosted-model quality evidence is not part of the Level 2 gate and would
  require a separate owner-approved proposal.
