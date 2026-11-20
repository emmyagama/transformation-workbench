# Level 2 reproduction and versions v1

> **Historical artifact.** V1 is superseded by `reproduction-v2.md` for the
> remediated evaluation. V1 used union matching and its clean clone covers only
> the baseline commit. The text below is preserved as published.

**Baseline commit:** `d5a6c973cae4ee17cd66ed01352a64c159ceb0f8`
**Evaluation date:** 2026-11-19

## Environment

| Component | Version |
| --- | --- |
| Python | 3.11.9 |
| pytest | 9.2.0 |
| a2a-sdk | 1.3.0 |
| mcp | 2.3.0 |
| httpx | 0.28.1 |
| pydantic | 2.14.3 |
| uvicorn | 0.54.0 |
| starlette | 1.10.0 |
| anyio | 4.16.0 |

All commands run from the repository root in Windows PowerShell. No package
was installed for this evaluation.

## Fixture identity

| Item | Value |
| --- | --- |
| Fixture | `src/transformation_workbench/data/synthetic_cases.csv` |
| Fixture SHA-256 | `69136fc840591c811fac66153122a3b091a0bea13445d770dafa294e6874e272` |
| Snapshot | `2026-03-13T17:00:00Z` |
| Process-context SHA-256 | `014d553995f902d4e102c7408166da1da668ce62e0d75854d463c35010973076` |

## Full local suite

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result: **253 passed in 100.26s**.

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Result: **No broken requirements found.**

## Frozen scorecard

```powershell
.\.venv\Scripts\python.exe -m tests.evaluation.run_level2_scorecard
```

Result:

```json
{
  "variant_count": 24,
  "passed": 24,
  "missed": 0
}
```

Artifacts:

- `docs/evidence/level-2/scorecard-v1.json`
- `docs/evidence/level-2/scorecard-v1.md`

The scorecard exercises the full workflow for workflow variants, the real local
A2A coordinator for coordinator variants, and the direct baseline only for the
shared comparison variants.

## Baseline-versus-A2A comparison

```powershell
.\.venv\Scripts\python.exe -m tests.evaluation.run_level2_comparison
```

Result:

- Shared variants: **13**
- A2A variants passing all measured invariants: **13**
- Baseline variants passing all measured invariants: **13**
- Same terminal status: **13**
- Exact error-code match: **10**

Artifacts:

- `docs/evidence/level-2/comparison-v1.json`
- `docs/evidence/level-2/comparison-v1.md`

The three exact-code differences are A2A wrapping of evidence-side failures as
`task_failure` with a cause code; the baseline returns the underlying code
directly. Both paths fail closed.

## Clean-clone check

A clean clone of the repository at the baseline commit was created outside the
workspace. No package install was performed. The existing locked virtual
environment was used, with `PYTHONPATH` pointed at the clone's `src` directory
so imports came from the clone.

```powershell
$dest = Join-Path $env:TEMP "aaif-level2-clean"
git clone --quiet <repository> $dest
$env:PYTHONPATH = Join-Path $dest "src"
& <repository>\.venv\Scripts\python.exe -m pytest -q
```

Result: **249 passed in 72.20s**.

This clean clone contains the baseline commit only. At evaluation time, the
Level 2 evaluation harness and evidence were uncommitted, so they were not
present in that clone. After an owner-approved commit, rerun the clean-clone
check against the committed Level 2 state.

## Reproducibility notes

- The fixture is fixed and synthetic. Expected values apply only to this fixture
  and snapshot.
- Automated fault cases use deterministic local fakes and loopback servers.
- No hosted model, provider call, credential, external network, or real data is
  used.
- No latency, cost, savings, or productivity outcome is measured or claimed.
- One harness comparison bug was corrected before the final scorecard: the
  workflow dimension initially compared all manifest cases for single-case
  variants. The final scorecard compares only the requested case set.
