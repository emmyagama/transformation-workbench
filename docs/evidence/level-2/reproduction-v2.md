# Level 2 reproduction and versions v2

**Pack:** `level2-evaluation-pack-v2` v2.0.0
**Source commit:** `33f184d`
**Evaluation date:** 2026-11-20
**Clean-clone status:** pending owner-approved commit

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

All commands run from the repository root in Windows PowerShell. No package was
installed for this evaluation.

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

Result: **258 passed in 184.59s**.

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Result: **No broken requirements found.**

## V2 scorecard

```powershell
.\.venv\Scripts\python.exe -m tests.evaluation.run_level2_scorecard_v2
```

Result:

```json
{
  "variant_count": 24,
  "passed": 24,
  "missed": 0,
  "terminal_code_matches": 24,
  "cause_code_matches": 24,
  "all_declared_invariants_scored": true
}
```

Artifacts:

- `docs/evidence/level-2/scorecard-v2.json`
- `docs/evidence/level-2/scorecard-v2.md`

The scorecard routes all 15 workflow variants through `run_workflow` and all 9
coordinator variants through the real local `Phase2Coordinator`.

## V2 baseline-versus-A2A comparison

```powershell
.\.venv\Scripts\python.exe -m tests.evaluation.run_level2_comparison_v2
```

Result:

- Shared variants: **13**
- A2A literal terminal-code matches: **13 / 13**
- A2A literal cause-code matches: **13 / 13**
- A2A semantic matches: **13 / 13**
- Baseline literal terminal-code matches: **13 / 13**
- Baseline literal cause-code matches: **13 / 13**
- Baseline semantic matches: **13 / 13**
- Cross-path exact terminal-code matches: **10 / 13**
- Cross-path exact cause-code matches: **10 / 13**
- Cross-path semantic matches: **13 / 13**

Artifacts:

- `docs/evidence/level-2/comparison-v2.json`
- `docs/evidence/level-2/comparison-v2.md`

The three cross-path differences are A2A protocol wrapping of evidence-side
failures as `task_failure` with a cause code. Each path still matches its own V2
expectation and both fail closed.

## V1 historical reference

V1 result artifacts remain published and unchanged; V1 status docs carry
historical banners:

- V1 scorecard: `24 / 24` under union matching; strict terminal-code reading:
  `23 / 24`.
- V1 A2A comparison: `13 / 13` under union matching; strict reading:
  `12 / 13`.
- V1 exact top-level comparison codes: `10 / 13`.
- V1 clean clone at baseline `d5a6c97`: **249 passed**.

The strict V1 reading and the `L2-04b` expectation defect are documented in
`erratum-v1.md`.

## Clean-clone check

A clean-clone check of the V2 state has **not** been run because V2 has not been
committed. The historical V1 clean clone contained the baseline commit only.
After an owner-approved commit, rerun:

```powershell
$dest = Join-Path $env:TEMP "aaif-level2-v2-clean"
git clone --quiet <repository> $dest
$env:PYTHONPATH = Join-Path $dest "src"
& <repository>\.venv\Scripts\python.exe -m pytest -q
```

Then run both V2 runners with `PYTHONPATH` pointed at the clone's `src`
directory, and confirm the fixture hash and V2 counts above.

## Reproducibility notes

- The fixture is fixed and synthetic. Expected values apply only to this fixture
  and snapshot.
- Automated fault cases use deterministic local fakes and loopback servers.
- No hosted model, provider call, credential, external network, or real data is
  used.
- No latency, cost, savings, or productivity outcome is measured or claimed.
- V1 scorecard/comparison JSON and Markdown were preserved; V2 writes new
  `-v2` artifacts.
