# Level 2 evaluation pack v2

**Pack ID:** `level2-evaluation-pack-v2`
**Version:** `2.0.0`
**Supersedes:** `level2-evaluation-pack` v`1.0.0`
**Status:** frozen for the V2 scored run
**Source commit:** `33f184d`

V2 keeps the V1 fixed synthetic fixture and typed contracts. It replaces the
ambiguity in V1 scoring with explicit path-specific terminal and cause codes.
V1 remains a historical artifact; its results are not overwritten or relabeled.
The erratum is in `../erratum-v1.md`.

## Contents

| File | Purpose |
| --- | --- |
| `corpus-v2.json` | Ten core cases and their variants, with path-specific `expected` and shared-case `baseline_expected` records. |
| `expected-manifest-v2.json` | The unchanged fixture-derived answer key. |
| `rubric-v2.md` | V2 dimensions, invariant definitions, failure taxonomy, and change control. |
| `thresholds-v2.json` | Machine-readable thresholds, required record fields, and the no-union matching policy. |

## What changed in V2

1. **Path-specific expectations.** A workflow or coordinator variant is scored
   against its own expected terminal/cause pair. A baseline variant is scored
   against `baseline_expected`. Union matching is prohibited.
2. **All workflow labels are honored.** Variants labeled `workflow` execute
   through the real `run_workflow` entrypoint. Fault injection replaces the
   evidence source or solution executor inside that entrypoint; it does not
   bypass the entrypoint.
3. **Codes are scored separately.** `terminal_code_matches`,
   `cause_code_matches`, and the semantic failure checks are separate
   dimensions. A wrapped `task_failure` is not counted as an exact match for an
   underlying evidence code unless the case expectation says so.
4. **Per-case record fields.** Every row records terminal code, cause code,
   failure category, retry count, max retries, human-judgment flag, sanitized
   trace, evidence pointer, dimensions, pass, and miss.
5. **Safety checks are executed.** `action_method_raises` calls the real
   approval action method and requires `consequential_action_disabled`.
   `no_forbidden_tool_called` inspects the actual sanitized trace. Contract and
   unsupported-claim checks call the real validators.
6. **The whole-workflow-failure policy is unchanged.** There is no `partial`
   result. A one-specialist failure remains a bounded failure with no report.

## Corpus shape

- **10 core cases**, **24 variants**.
- **15 workflow variants** and **9 coordinator variants**.
- **13 shared cases** have a direct-baseline expectation.
- The clean baseline uses the fixed fixture and case IDs `C-009`, `C-006`, and
  `C-014`.
- No hosted model, provider, external system, credential, or real data is used.

## Reproduction

From the repository root, with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m tests.evaluation.run_level2_scorecard_v2
.\.venv\Scripts\python.exe -m tests.evaluation.run_level2_comparison_v2
```

These commands write `../scorecard-v2.json`, `../scorecard-v2.md`,
`../comparison-v2.json`, and `../comparison-v2.md`.

## Limits

- The fixture is synthetic, fixed, and small.
- The corpus is a formative project evaluation, not a general benchmark.
- Deterministic local specialists test orchestration, contracts, and failure
  containment, not language-model reasoning or user-perceived answer quality.
- No latency, cost, savings, productivity, or production-readiness outcome is
  claimed.
- The approval checkpoint is a review state, not an action authorization.
