# Level 2 owner summary v2

**Status:** V2 evidence commit `f9ccce7` is pushed and clean-clone verified at
that commit. The current reconciliation changes are uncommitted. Owner final
review and sign-off remain pending. Level 2 is not passed.

**Pack:** `level2-evaluation-pack-v2` v2.0.0
**Pushed V2 evidence commit:** `f9ccce75262b72651887c6b7e7872b71d217669e`
**V2 source commit:** `33f184d`
**Evaluation date:** 2026-11-20

## Measured facts

### Pushed commit `f9ccce7`

- Clean clone at the exact pushed commit: **258 passed in 104.62s** using
  Python 3.11.9 and the existing environment.
- V2 scorecard: **24 of 24 variants passed** under path-specific expectations.
- V2 literal terminal-code matches: **24 of 24**; cause-code matches:
  **24 of 24**; all declared invariants scored.
- Workflow variants routed through the real `run_workflow` entrypoint: **15 of
  15**.
- Coordinator variants routed through the real local coordinator: **9 of 9**.
- Shared comparison: **13 of 13** A2A and **13 of 13** baseline path-specific
  passes; cross-path exact terminal-code and cause-code matches **10 of 13**.
- The pushed commit's comparison harness uses the pre-reconciliation semantic
  definition; its `13 of 13` semantic result is historical for this commit, not
  the corrected definition.

### Current uncommitted reconciliation

- Full local suite: **258 passed in 81.89s**.
- Clean-copy of the uncommitted reconciliation: **258 passed in 102.53s**; both
  V2 runners exited `0` and reproduced the counts below.
- V2 scorecard: **24 of 24**, no misses; terminal and cause matches **24 of 24**.
- Cross-path semantic matches under the corrected observed-outcome definition:
  **13 of 13** (**1** both-success, **12** both-fail-closed).
- Cross-path exact terminal-code and cause-code matches remain **10 of 13**.
- Retry records now distinguish attempts from retries: `L2-08c` records
  **2 attempts**, **1 retry**, **max_retries=1**.
- `L2-05b` failure category is now **`intake_validation`**, not
  `unclassified`.
- V1 erratum under strict terminal-code reading: scorecard **23 of 24**, A2A
  comparison **12 of 13**, exact top-level comparison codes **10 of 13**.
- V1 scorecard and comparison result artifacts were not overwritten or
  relabeled; V1 status docs carry historical banners.

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

1. Owner review the current reconciliation of the V2 pack, erratum, literal-code
   scorecard, and observed-outcome comparison.
2. If acceptable, authorize a new scoped commit of the reconciliation and then a
   clean-clone run at that new commit. Do not describe the reconciliation as
   clean-clone verified before that run.
3. Decide whether the A2A `task_failure` wrapping of evidence-side failures is
   accepted behavior or should be normalized in a later, separately scoped
   change. Do not change V2 expected values after seeing results without a
   version increment and written rationale.
4. Keep Level 2 CLI-first. No UI, ODI feasibility, deployment, or production
   readiness work begins until the Level 2 decision is recorded.

## Future work

- Commit and clean-clone verify the reconciliation after owner authorization.
- Optionally add an error-taxonomy normalization proposal if exact cross-path
  terminal-code parity is required.
- Prepare a separate bounded proposal only if hosted-model quality evidence is
  later judged necessary; do not execute it under the Level 2 runbook alone.

## Unresolved findings

- The reconciliation is uncommitted; its clean-clone verification is pending a
  new owner-authorized commit. The pushed `f9ccce7` clean clone covers the
  pre-reconciliation harness.
- A2A wraps evidence-side failures as `task_failure` with a cause code in three
  shared cases; this is documented, not hidden.
- No general A2A superiority, model-quality, cost, latency, savings, or
  production-readiness claim is supported.
