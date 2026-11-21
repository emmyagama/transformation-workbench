# Level 2 owner summary v2

**Status:** V2 evidence was merged into `main` by PR #4 in merge commit
`c7c935cf0c948f24c016d4f6f4abf350dffbfd8f`. Owner review was completed and
the Level 2 decision was recorded on 2026-11-20. This summary records evidence
and does not restate the owner-authored closure state or declare a new pass.

**Pack:** `level2-evaluation-pack-v2` v2.0.0
**Final V2 evidence commit:** `a82d38f94735cbd6f476a11b6e843d9e02f375d1`
**Merge commit:** `c7c935cf0c948f24c016d4f6f4abf350dffbfd8f`
**Prior V2 evidence commit:** `cd4a3147a840c191dce6992618dc424523537824`
**Prior V2 evidence commit:** `f9ccce75262b72651887c6b7e7872b71d217669e`
**V2 source commit:** `33f184d`
**Evaluation date:** 2026-11-20

## Measured facts

### Final evidence commit `a82d38f` and merge commit `c7c935c`

- PR #4 merged the branch into `main` with merge commit `c7c935c`; the merge
  commit has two parents and was not squashed or rebased.
- Clean-clone at `a82d38f`: **258 passed in 75.88s**; both V2 runners and
  `pip check` exited `0`.
- Clean-clone at merge commit `c7c935c`: **258 passed in 87.38s**; both V2
  runners and `pip check` exited `0`.
- Both runs reproduced scorecard **24/24**, terminal **24/24**, cause **24/24**,
  no misses, all declared invariants scored; A2A **13/13**, baseline **13/13**,
  exact cross-path terminal/cause **10/13**, semantic **13/13**.
- Independent-review corrections D1 and D2 are included in `a82d38f`. The
  timeout traces for `L2-09a`/`L2-09b` are flagged `timing_dependent` and are
  not cited as reproducible evidence.

### Prior reconciliation commit `cd4a314`

- Clean clone at the exact pushed commit: **258 passed in 99.54s** using Python
  3.11.9 and the existing environment.
- V2 scorecard: **24 of 24 variants passed** under path-specific expectations;
  terminal and cause matches **24 of 24**; all declared invariants scored.
- Workflow variants routed through the real `run_workflow` entrypoint: **15 of
  15**.
- Coordinator variants routed through the real local coordinator: **9 of 9**.
- Shared comparison: **13 of 13** A2A and **13 of 13** baseline path-specific
  passes; cross-path exact terminal-code and cause-code matches **10 of 13**.
- Cross-path semantic matches under the corrected observed-outcome definition:
  **13 of 13** (**1** both-success, **12** both-fail-closed).
- `pip check`: no broken requirements.
- Regenerated Markdown matched byte-for-byte. JSON matched after runtime ID
  normalization except for the timing-dependent `L2-09a`/`L2-09b` timeout
  trace field, which is disclosed and not cited as reproducible evidence.
- Retry records distinguish attempts from retries: `L2-08c` records **2
  attempts**, **1 retry**, **max_retries=1**.
- `L2-05b` failure category is **`intake_validation`**, not `unclassified`.
- V1 erratum under strict terminal-code reading: scorecard **23 of 24**, A2A
  comparison **12 of 13**, exact top-level comparison codes **10 of 13**.
- V1 scorecard and comparison result artifacts were not overwritten or
  relabeled; V1 status docs carry historical banners.

### Prior evidence commit `f9ccce7`

- Clean clone at `f9ccce7`: **258 passed in 104.62s**; scorecard and
  path-specific comparison counts match the current evidence.
- Its comparison harness uses the pre-reconciliation semantic definition, so
  its semantic result is historical for that commit.

## Calculations

- V2 shared path-specific pass rate: **13 / 13 = 100%** for each path.
- Cross-path exact terminal-code rate: **10 / 13 = 76.9%**.
- Cross-path semantic rate: **13 / 13 = 100%** under the explicit
  observed-outcome definition.
- Semantic equality means same observed status and either both paths complete
  with a successful result or both terminate failure/refused with no successful
  result. It does not use path-specific expectations, terminal codes, or cause
  codes.
- The three cross-path code differences are A2A protocol wrappers:
  `L2-02a` and `L2-03b` are `task_failure` with the underlying cause;
  `L2-04b` is `task_failure` with cause `request_mismatch` on the workflow path
  and `request_mismatch` with no cause on the direct baseline.
- No latency, cost, savings, or productivity outcome is measured.

## What V2 corrected

1. V1 union matching is replaced by literal path-specific terminal and cause
   scoring.
2. V1 routed most workflow-labeled variants through the coordinator; V2 routes
   every workflow variant through `run_workflow`.
3. V1 omitted failure category, retry count, sanitized trace, and
   human-judgment fields; V2 records them for every case.
4. V1 passed some safety checks by constant; V2 calls the real approval action
   method, inspects the actual trace, and calls the real contract/claim
   validators.
5. V2 documents the V1 `L2-04b` expectation defect in `erratum-v1.md`.
6. The reconciliation changes cross-path semantic equality from a conjunction of
   each path's own pass flag to an explicit observed-outcome comparison.
7. The reconciliation records attempt count separately from retry count, so a
   two-attempt, one-retry case is no longer presented as two retries.
8. The reconciliation maps intake-safety causes to `intake_validation` instead
   of `unclassified` and makes the Markdown record distinguish expected from
   observed fields.

## Assumptions

- The fixture is synthetic, fixed, and the only data source.
- The expected manifest is the answer key for this fixture and snapshot only.
- The direct baseline is a fair comparator for evidence/options correctness and
  contract handling, but it has no A2A discovery, retry, timeout, or protocol
  trace semantics.
- Deterministic fakes test orchestration and contracts, not model reasoning or
  user-perceived answer quality.
- The owner-approved whole-workflow-failure policy remains in force; there is no
  partial-result schema.
- Hosted-model quality evidence is outside the Level 2 gate and was not run.

## Recommendations

1. Owner review of the merged V2 pack, erratum, literal-code scorecard, and
   observed-outcome comparison was completed and the Level 2 decision was
   recorded on 2026-11-20.
2. Decide whether the A2A `task_failure` wrapping of evidence-side failures is
   accepted behavior or should be normalized in a later, separately scoped
   change. Do not change V2 expected values after seeing results without a
   version increment and written rationale.
3. Keep Level 2 CLI-first. No UI, ODI feasibility, deployment, or production
   readiness work begins without separate owner authorization.

## Future work

- Keep owner-authored status documents aligned with the recorded Level 2
  decision.
- Optionally add an error-taxonomy normalization proposal if exact cross-path
  terminal-code parity is required.
- Prepare a separate bounded proposal only if hosted-model quality evidence is
  later judged necessary; do not execute it under the Level 2 runbook alone.

## Unresolved findings

- The technical evidence is merged at `c7c935c` and clean-clone verified.
  Owner review was completed and the Level 2 decision was recorded on
  2026-11-20; this summary does not restate the owner-authored closure state.
- A2A wraps evidence-side failures as `task_failure` with a cause code in three
  shared cases; this is documented, not hidden.
- The `L2-09a`/`L2-09b` timeout traces are timing-dependent and are not cited as
  reproducible evidence.
- No general A2A superiority, model-quality, cost, latency, savings, or
  production-readiness claim is supported.
