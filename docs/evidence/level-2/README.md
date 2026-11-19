# Level 2 evidence bundle

**Status:** deferred/conditional. The local evidence is complete, but at the
time of this evaluation these Level 2 artifacts were uncommitted and therefore
were not part of the clean-clone verification. Owner review and an explicit
commit decision are still required.

**Baseline commit:** `d5a6c973cae4ee17cd66ed01352a64c159ceb0f8`

**Scope:** local, synthetic, read-only evaluation of the CLI/A2A/MCP workflow.
No hosted model, provider call, credential, external system, deployment, UI, or
ODI feasibility work is included.

## Contents

| Artifact | Purpose |
| --- | --- |
| `baseline-and-gap-matrix.md` | Baseline inventory, gap matrix, and package decisions. |
| `evaluation-pack-v1/` | Frozen corpus, expected manifest, rubric, and thresholds. |
| `scorecard-v1.md` / `.json` | Per-case results for all 24 frozen variants. |
| `comparison-v1.md` / `.json` | Baseline-versus-A2A comparison on 13 shared variants. |
| `fault-injection-v1.md` | Fault cases, observed codes, and trace-sanitization policy. |
| `crosswalk-v1.md` | Requirement-to-evidence mapping. |
| `reproduction-v1.md` | Exact commands, versions, full-suite result, and clean-clone result. |
| `owner-summary-v1.md` | Concise decision summary separating facts, calculations, assumptions, recommendations, and future work. |

## Verification summary

- Full local suite: **253 passed**.
- Frozen scorecard: **24 of 24 variants passed**.
- Shared baseline comparison: **13 of 13 shared variants passed** all measured
  invariants; terminal status matched on all 13; exact error codes matched on
  10 of 13.
- Clean clone at the baseline commit: **249 passed**, using the existing locked
  virtual environment without installing packages.
- `pip check`: **No broken requirements found.**

## Bounded conclusion

On the frozen synthetic cases, the two-specialist A2A path and the direct
baseline both satisfied the measured correctness, traceability, schema,
completeness, safety, and failure-containment checks. The A2A path added
protocol discovery and task evidence, but it did not improve correctness or
safety on this small sample. Three failure cases differ only in error wrapping:
the A2A path reports `task_failure` with a cause code where the baseline returns
the underlying code directly.

This is not evidence of general A2A superiority, model quality, cost, latency,
savings, or production readiness. The sample is small and deterministic, and
the baseline has no A2A protocol semantics.

## Decision boundary

Level 2 is not declared passed here. The runbook's final gate requires owner
review of the evidence and a recorded decision. Because the Level 2 harness and
evidence were uncommitted at evaluation time, the clean-clone check covers only
the baseline commit. After an owner-approved commit, rerun the clean-clone
commands in `reproduction-v1.md` against the committed Level 2 state.
