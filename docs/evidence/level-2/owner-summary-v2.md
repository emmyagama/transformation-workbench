# Level 2 owner summary v2

**Status:** local V2 remediation complete; owner review and commit approval
pending. V1 is historical and remains published. Clean-clone verification of V2
is pending an owner-approved commit.

**Pack:** `level2-evaluation-pack-v2` v2.0.0
**Source commit:** `33f184d`
**Evaluation date:** 2026-11-20

## Measured facts

- V2 scorecard: **24 of 24 variants passed** under path-specific expectations.
- V2 literal terminal-code matches: **24 of 24**.
- V2 literal cause-code matches: **24 of 24**.
- All declared invariants were scored: **true**.
- Workflow variants routed through the real `run_workflow` entrypoint: **15 of
  15**.
- Coordinator variants routed through the real local coordinator: **9 of 9**.
- V2 shared comparison: **13 of 13** A2A cases passed their own expectations;
  **13 of 13** baseline cases passed their own expectations.
- Cross-path exact terminal-code matches: **10 of 13**.
- Cross-path exact cause-code matches: **10 of 13**.
- Cross-path semantic matches: **13 of 13**.
- V1 erratum under strict terminal-code reading: scorecard **23 of 24**, A2A
  comparison **12 of 13**, exact top-level comparison codes **10 of 13**.
- No V2 misses were observed.
- V1 scorecard and comparison result artifacts were not overwritten or
  relabeled; V1 status docs carry historical banners.

## Calculations

- V2 shared path-specific pass rate: **13 / 13 = 100%** for each path.
- Cross-path exact terminal-code rate: **10 / 13 = 76.9%**.
- The three cross-path differences are A2A protocol wrappers:
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

1. Owner review the V2 pack, erratum, literal-code scorecard, and path-specific
   comparison.
2. Approve a scoped commit of the V2 harness and evidence if acceptable; do not
   describe V2 as clean-clone verified before that commit.
3. After the approved commit, rerun the full suite, both V2 runners, and the
   clean-clone commands in `reproduction-v2.md` against the committed state.
4. Decide whether the A2A `task_failure` wrapping of evidence-side failures is
   accepted behavior or should be normalized in a later, separately scoped
   change. Do not change V2 expected values after seeing results without a
   version increment and written rationale.
5. Keep Level 2 CLI-first. No UI, ODI feasibility, deployment, or production
   readiness work begins until the Level 2 decision is recorded.

## Future work

- Commit and clean-clone verify the V2 artifacts after owner approval.
- Optionally add an error-taxonomy normalization proposal if exact cross-path
  terminal-code parity is required.
- Prepare a separate bounded proposal only if hosted-model quality evidence is
  later judged necessary; do not execute it under the Level 2 runbook alone.

## Unresolved findings

- V2 artifacts are uncommitted at the time of this summary; clean-clone
  verification covers only the historical V1 baseline commit.
- A2A wraps evidence-side failures as `task_failure` with a cause code in three
  shared cases; this is documented, not hidden.
- No general A2A superiority, model-quality, cost, latency, savings, or
  production-readiness claim is supported.
