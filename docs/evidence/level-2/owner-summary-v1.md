# Level 2 owner summary v1

> **Historical artifact.** V1 is superseded for scoring by
> `level2-evaluation-pack-v2` v2.0.0 and `owner-summary-v2.md`. V1 used union
> matching; the strict terminal-code reading is `23/24` on the scorecard and
> `12/13` on the A2A comparison. See `erratum-v1.md`. The text below is
> preserved as published.

**Status:** deferred/conditional. The local evidence is complete, but the final
gate is not declared passed because the Level 2 harness and evidence were
uncommitted at evaluation time and the clean-clone check covers only the
baseline commit.

**Baseline commit:** `d5a6c973cae4ee17cd66ed01352a64c159ceb0f8`
**Evaluation date:** 2026-11-19

## Measured facts

- Full local suite: **253 passed**.
- Frozen scorecard: **24 of 24 variants passed**.
- Shared baseline comparison: **13 of 13 variants passed** all measured
  correctness, traceability, schema, completeness, safety, and failure
  invariants.
- Terminal status matched on **13 of 13** shared variants.
- Exact error codes matched on **10 of 13** shared variants.
- Clean clone at the baseline commit: **249 passed**, using the existing locked
  virtual environment without installing packages.
- `pip check`: **No broken requirements found**.
- No product misses were observed in the final frozen scorecard.

## Calculations

- Shared comparison pass rate: **13 / 13 = 100%**.
- Exact error-code match rate: **10 / 13 = 76.9%**.
- The three exact-code differences are A2A wrapping of evidence-side failures
  as `task_failure` with a cause code; the baseline returns the underlying code
  directly. Both paths fail closed.
- No latency, cost, savings, or productivity outcome is measured.

## Assumptions

- The fixture is synthetic, fixed, and the only data source.
- The expected manifest is the answer key for this fixture and snapshot only.
- The direct baseline is a fair comparator for evidence/options correctness and
  contract handling, but it has no A2A discovery, retry, timeout, or protocol
  trace semantics.
- Deterministic fakes test orchestration and contracts, not model reasoning or
  user-perceived answer quality.
- The owner-approved whole-workflow failure policy remains in force; there is no
  partial-result schema.
- Hosted-model quality evidence is outside the Level 2 gate and was not run.

## Recommendations

1. Owner review the baseline comparator description and the bounded conclusion.
2. Approve committing the Level 2 harness and evidence if the current state is
   acceptable; do not treat the uncommitted state as a passed clean-clone gate.
3. After commit, rerun the full suite, scorecard, comparison, and clean-clone
   commands in `reproduction-v1.md` against the committed Level 2 state.
4. Decide whether the A2A `task_failure` wrapping of evidence-side failures is
   accepted behavior or should be normalized in a later, separately scoped
   change. Do not change the frozen expected manifest after seeing results.
5. Keep Level 2 CLI-first. No UI, ODI feasibility, deployment, or production
   readiness work begins until the Level 2 decision is recorded.

## Future work

- Commit and clean-clone verify the Level 2 artifacts after owner approval.
- Optionally add an error-taxonomy normalization proposal if exact error-code
  parity is required.
- Prepare a separate bounded proposal only if hosted-model quality evidence is
  later judged necessary; do not execute it under the Level 2 runbook alone.

## Unresolved findings

- Level 2 artifacts were uncommitted at evaluation time; clean-clone
  verification covers only the baseline commit.
- A2A wraps evidence-side failures as `task_failure` with a cause code in three
  cases; this is documented, not hidden.
- No general A2A superiority, model-quality, cost, latency, savings, or
  production-readiness claim is supported.
