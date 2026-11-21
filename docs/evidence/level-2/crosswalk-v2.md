# Level 2 requirement-to-evidence crosswalk v2

**Pack:** `level2-evaluation-pack-v2` v2.0.0
**Final V2 evidence commit:** `a82d38f94735cbd6f476a11b6e843d9e02f375d1`
**Merge commit:** `c7c935cf0c948f24c016d4f6f4abf350dffbfd8f`
**Prior V2 evidence commit:** `cd4a3147a840c191dce6992618dc424523537824`
**Prior V2 evidence commit:** `f9ccce75262b72651887c6b7e7872b71d217669e`
**V2 source commit:** `33f184d`

V1 remains published as historical evidence. This crosswalk maps the current
remediated V2 state. See `erratum-v1.md` for the V1 strict-code correction and
`reproduction-v2.md` for the clean-clone results and the prior commit.

## Runbook and roadmap requirements

| Requirement | V2 evidence | Status |
| --- | --- | --- |
| Versioned corpus, rubric, expected manifest, and case definitions | `evaluation-pack-v2/corpus-v2.json`, `expected-manifest-v2.json`, `rubric-v2.md`, `thresholds-v2.json` | Complete |
| 10 core cases with parameterized variants | 24 variants; 15 workflow and 9 coordinator; `scorecard-v2.json` | Complete |
| Path-specific expected terminal and cause codes | `corpus-v2.json` `expected` / `baseline_expected`; no union policy in `thresholds-v2.json` | Complete |
| Per-case scorecard including misses | `scorecard-v2.md` / `.json`; 24/24 passed, no misses | Complete |
| Failure taxonomy and fault-injection evidence | `fault-injection-v2.md`; real workflow/coordinator paths | Complete |
| Sanitized protocol traces | Each row records step, agent/skill, method, path, task/context ID, state, and attempt only; `L2-09a`/`L2-09b` timeout traces are flagged timing-dependent | Complete |
| Baseline-versus-A2A comparison and limits | `comparison-v2.md` / `.json`; 13 shared variants with separate path expectations and explicit observed-outcome semantic definition | Complete |
| Exact commands, versions, and reproducibility | `reproduction-v2.md`; 258-test full suite and both V2 runners | `a82d38f` and merge commit `c7c935c` clean-clone verified |
| Requirement-to-evidence crosswalk | This document | Complete |
| Owner-reviewed summary separating facts, calculations, assumptions, recommendations, and future work | `owner-summary-v2.md` | Owner reviewed and Level 2 decision recorded 2026-11-20 |
| No secrets, private paths, or real data | Synthetic fixture only; evidence uses relative paths and synthetic case IDs | Satisfied |
| No write, business action, or approval bypass | `approval.py`; `action_method_raises` executed in V2; L2-05/L2-07 variants | Satisfied |
| Bounded failure, no partial-completion claim | `CoordinatorResult.status` only `complete`; failure variants assert no report/result | Satisfied |

## Safety and contract evidence

| Control | V2 evidence |
| --- | --- |
| Intake injection refusal | `L2-05b` -> `invalid_intake` / `instruction_override`; workflow did not start |
| Injected evidence-context rejection | `L2-05a` -> `context_mismatch` |
| Stale snapshot rejection | `L2-02b` -> `snapshot_mismatch` |
| Unknown case handling | `L2-03a` -> `incomplete_evidence` |
| MCP resource/tool failure containment | `L2-02a`, `L2-03b` -> bounded `task_failure` with cause |
| Metric, request, and case-set contradiction rejection | `L2-04a`, `L2-04b`, `L2-04c` |
| Unsupported savings/percentage claim rejection | `L2-06a`, `L2-06b` -> `unsupported_claim` |
| Action request remains read-only | `L2-07a` -> complete, approval pending, no action; action method raises |
| Approval bypass refusal | `L2-07b` -> `approval_id_required`; no report |
| Approved review state still cannot act | `L2-07c` -> approved state, `consequential_action_permitted=false`, action method raises |
| Duplicate replay and conflict | `L2-08a`, `L2-08b`; replay trace prefix and no extra specialist posts |
| Unavailable specialist | `L2-08c` -> `specialist_unavailable`; 2 attempts, 1 retry, `max_retries=1` |
| Timeout and bounded retries | `L2-09a`, `L2-09b` -> `a2a_timeout`; 1 and 2 attempts |
| Malformed JSON and wrong MIME | `L2-10a`, `L2-10b` -> `malformed_result` |
| Missing evidence field | `L2-10c` -> `invalid_evidence_pack` |
| Unknown evidence reference | `L2-10d` -> `unknown_evidence_reference` |

## Comparison evidence

The direct baseline reuses the same read-only evidence source, typed contracts,
validators, and deterministic solution designer without A2A discovery or task
exchange. On the 13 shared variants:

- A2A path: 13/13 path-specific passes, 13/13 literal terminal-code matches,
  13/13 cause-code matches.
- Baseline path: 13/13 path-specific passes, 13/13 literal terminal-code
  matches, 13/13 cause-code matches.
- Cross-path exact terminal-code matches: 10/13.
- Cross-path exact cause-code matches: 10/13.
- Cross-path semantic matches: 13/13 (1 both-success, 12 both-fail-closed).
- Semantic equality is defined from observed outcomes only: same observed
  status and either both complete with a successful result or both terminate
  fail-closed. It does not use path-specific expectations, terminal codes, or
  cause codes.
- The three differences are A2A wrapping of evidence-side failures as
  `task_failure` with a cause code; the baseline returns the underlying code.
- No latency, cost, savings, or productivity outcome is claimed.

## Gaps and limitations

- The final evidence commit `a82d38f` and merge commit `c7c935c` are pushed and
  clean-clone verified. Owner review was completed and the Level 2 decision was
  recorded on 2026-11-20; this crosswalk does not restate the owner-authored
  closure state.
- The sample is small and deterministic; it tests orchestration and contracts,
  not model reasoning or user-perceived answer quality.
- The baseline has no A2A protocol trace, discovery, retry, or timeout
  semantics; those cases are marked not applicable rather than fabricated.
- Hosted-model quality evidence is not part of the Level 2 gate and would
  require a separate owner-approved proposal.
