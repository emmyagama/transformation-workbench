# Level 2 evidence bundle

**Current status:** V2 remediation complete locally; owner review and commit
approval are pending. V1 is historical and remains published. Clean-clone
verification of V2 is pending an owner-approved commit.

**V2 pack:** `level2-evaluation-pack-v2` v2.0.0
**Source commit:** `33f184d`
**V1 baseline commit:** `d5a6c973cae4ee17cd66ed01352a64c159ceb0f8`

**Scope:** local, synthetic, read-only evaluation of the CLI/A2A/MCP workflow.
No hosted model, provider call, credential, external system, deployment, UI, or
ODI feasibility work is included.

## Current V2 evidence

| Artifact | Purpose |
| --- | --- |
| `evaluation-pack-v2/` | Frozen V2 corpus, expected manifest, rubric, and thresholds. |
| `scorecard-v2.md` / `.json` | Per-case V2 results for all 24 variants with literal terminal/cause codes. |
| `comparison-v2.md` / `.json` | Path-specific baseline-versus-A2A comparison on 13 shared variants. |
| `fault-injection-v2.md` | V2 fault cases, observed codes, retries, and trace policy. |
| `crosswalk-v2.md` | V2 requirement-to-evidence mapping. |
| `reproduction-v2.md` | V2 commands, versions, full-suite result, and pending clean-clone note. |
| `owner-summary-v2.md` | V2 decision summary separating facts, calculations, assumptions, recommendations, and future work. |
| `erratum-v1.md` | V1 strict-code correction and the `L2-04b` expectation defect. |

## V2 verification summary

- Full local suite: **258 passed**.
- V2 scorecard: **24 of 24 variants passed** under path-specific expectations.
- V2 literal terminal-code matches: **24 of 24**.
- V2 literal cause-code matches: **24 of 24**.
- All 15 workflow variants routed through the real `run_workflow` entrypoint.
- All 9 coordinator variants routed through the real local coordinator.
- Shared comparison: A2A **13/13** and baseline **13/13** against their own
  expectations.
- Cross-path exact terminal-code matches: **10 of 13**.
- Cross-path semantic matches: **13 of 13**.
- `pip check`: **No broken requirements found.**
- Clean-clone verification of V2: **pending commit**.

## V1 historical status

V1 result artifacts are preserved as published; V1 status docs carry historical
banners. Its union matching produced a `24/24` scorecard
and `13/13` A2A comparison. Under strict terminal-code reading, V1 is `23/24`
on the scorecard and `12/13` on the A2A comparison; exact top-level comparison
codes match on `10/13`. V1 also routed 10 workflow-labeled variants through the
coordinator and omitted several required record fields. The erratum records
those findings without overwriting V1 results.

Historical V1 artifacts:

| Artifact | Purpose |
| --- | --- |
| `baseline-and-gap-matrix.md` | Package 0 historical inventory and gap matrix. |
| `evaluation-pack-v1/` | Historical frozen V1 corpus, manifest, rubric, and thresholds. |
| `scorecard-v1.md` / `.json` | Historical V1 per-case results. |
| `comparison-v1.md` / `.json` | Historical V1 baseline-versus-A2A comparison. |
| `fault-injection-v1.md` | Historical V1 fault evidence. |
| `crosswalk-v1.md` | Historical V1 requirement-to-evidence mapping. |
| `reproduction-v1.md` | Historical V1 commands and clean-clone result. |
| `owner-summary-v1.md` | Historical V1 owner summary. |

## Bounded conclusion

On the frozen synthetic cases, each path matched its own V2 literal terminal
code, cause code, and semantic failure checks. The A2A path added protocol
discovery and task evidence, but it did not improve correctness or safety on
this small sample. Three shared cases differ only in protocol wrapping: the A2A
path reports `task_failure` with a cause code where the baseline returns the
underlying code directly.

This is not evidence of general A2A superiority, model quality, cost, latency,
savings, or production readiness. The sample is small and deterministic, and the
baseline has no A2A protocol semantics.

## Decision boundary

Level 2 is not declared passed here. The runbook's final gate requires owner
review of the V2 evidence and a recorded decision. V2 artifacts are uncommitted;
after an owner-approved commit, rerun the full suite, both V2 runners, and the
clean-clone commands in `reproduction-v2.md`.
