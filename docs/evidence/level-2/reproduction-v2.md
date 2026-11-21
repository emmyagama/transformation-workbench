# Level 2 reproduction and versions v2

**Pack:** `level2-evaluation-pack-v2` v2.0.0
**Final V2 evidence commit:** `a82d38f94735cbd6f476a11b6e843d9e02f375d1`
**Merge commit:** `c7c935cf0c948f24c016d4f6f4abf350dffbfd8f`
**Prior V2 evidence commit:** `cd4a3147a840c191dce6992618dc424523537824`
**Prior V2 evidence commit:** `f9ccce75262b72651887c6b7e7872b71d217669e`
**V2 source commit:** `33f184d`
**Evaluation date:** 2026-11-20
**Clean-clone status:** final evidence commit `a82d38f` and merge commit
`c7c935c` verified at those exact commits; prior commits `cd4a314` and
`f9ccce7` were also verified at their commits.

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

The fixture hash assumes LF line endings. On Windows, a default checkout with
`core.autocrlf=true` changes the file hash without changing the synthetic data.
Use `-c core.autocrlf=false` for byte-identical fixture verification.

## Full local suite

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Local result for the reconciliation content: **258 passed in 81.89s**, exit
`0`.

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Result: **No broken requirements found.** Exit `0`.

## V2 scorecard

```powershell
.\.venv\Scripts\python.exe -m tests.evaluation.run_level2_scorecard_v2
```

Reconciliation result, exit `0`:

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
coordinator variants through the real local `Phase2Coordinator`. It records
expected and observed fields, declared-invariant results, attempt count, retry
count, and retry limit. `L2-08c` records **2 attempts**, **1 retry**, and
**max_retries=1**. `L2-05b` records failure category **`intake_validation`**.

## V2 baseline-versus-A2A comparison

```powershell
.\.venv\Scripts\python.exe -m tests.evaluation.run_level2_comparison_v2
```

Reconciliation result, exit `0`:

- Shared variants: **13**
- A2A path-specific passes: **13 / 13**
- A2A literal terminal-code matches: **13 / 13**
- A2A literal cause-code matches: **13 / 13**
- Baseline path-specific passes: **13 / 13**
- Baseline literal terminal-code matches: **13 / 13**
- Baseline literal cause-code matches: **13 / 13**
- Cross-path exact terminal-code matches: **10 / 13**
- Cross-path exact cause-code matches: **10 / 13**
- Cross-path both-success matches: **1 / 13**
- Cross-path both-fail-closed matches: **12 / 13**
- Cross-path semantic matches: **13 / 13**

Semantic equality is defined from observed outcomes only. Both paths must have
the same observed status and either both complete with a successful result or
both terminate failure/refused with no successful result. It does not use
path-specific expectations, terminal codes, or cause codes.

Artifacts:

- `docs/evidence/level-2/comparison-v2.json`
- `docs/evidence/level-2/comparison-v2.md`

The three exact-code differences are A2A protocol wrapping of evidence-side
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

## Clean-clone check at reconciliation commit `cd4a314`

The committed reconciliation was checked from an isolated clone of the local
repository at the exact commit, without resetting or modifying the working tree:

```powershell
$dest = Join-Path $env:TEMP "aaif-level2-v2-cd4a314"
git -c core.autocrlf=false clone --quiet <repository> $dest
git -C $dest -c core.autocrlf=false checkout --quiet cd4a3147a840c191dce6992618dc424523537824
$env:PYTHONPATH = Join-Path $dest "src"
& <repository>\.venv\Scripts\python.exe -m pytest -q
```

Result at exact HEAD `cd4a314`: **258 passed in 99.54s**, exit `0`; fixture
SHA-256 `69136fc840591c811fac66153122a3b091a0bea13445d770dafa294e6874e272`.
Both V2 runners exited `0`; `pip check` exited `0`; scorecard **24/24**;
terminal/cause **24/24**; comparison path passes **13/13** per path; exact
cross-path terminal/cause **10/13**; both-success **1/13**; both-fail-closed
**12/13**; semantic **13/13**. Regenerated Markdown artifacts
(`scorecard-v2.md`, `comparison-v2.md`) matched the committed artifacts
byte-for-byte. `comparison-v2.json` matched after normalizing runtime `task_id`
and `context_id` values. `scorecard-v2.json` matched after the same
normalization, except for the timing-dependent `sanitized_trace` field of
`L2-09a` and `L2-09b`, whose optional `discover_card` event may be absent or
present under the 0.1 s fault-injection timeout; pass/fail, terminal codes,
cause codes, retry counts, and all declared invariants were identical.

The commit was pushed after this check, and `git ls-remote` confirmed the remote
branch ref at `cd4a314`. A separate network clone was attempted but was blocked
by repeated connection resets; the local clean clone and remote ref confirmation
are the recorded evidence.

## Final fix and merge clean-clone checks

The D1/D2 fix commit and the GitHub merge commit were each checked from an
isolated local clone at the exact commit:

```powershell
git -c core.autocrlf=false clone --no-local <repository> $dest
git -C $dest -c core.autocrlf=false checkout --quiet <exact-commit>
$env:PYTHONPATH = Join-Path $dest "src"
& <repository>\.venv\Scripts\python.exe -m pytest -q
```

| Checkout | Result | Runners | `pip check` |
| --- | --- | --- | --- |
| `a82d38f94735cbd6f476a11b6e843d9e02f375d1` | **258 passed in 75.88s** | scorecard and comparison exit `0` | exit `0` |
| `c7c935cf0c948f24c016d4f6f4abf350dffbfd8f` | **258 passed in 87.38s** | scorecard and comparison exit `0` | exit `0` |

Both runs reproduced scorecard **24/24**, terminal **24/24**, cause **24/24**,
no misses, all declared invariants scored; A2A **13/13**, baseline **13/13**,
exact cross-path terminal/cause **10/13**, both-success **1/13**,
both-fail-closed **12/13**, semantic **13/13**. The fixture SHA-256 remained
`69136fc840591c811fac66153122a3b091a0bea13445d770dafa294e6874e272`.

Markdown artifacts matched byte-for-byte; JSON artifacts matched after runtime
`task_id`/`context_id` normalization. `L2-09a` and `L2-09b` timeout traces
remained empty in these runs and are flagged `timing_dependent`; the optional
`discover_card` event is not cited as reproducible evidence. D1 (artifact
normalization claim) and D2 (timeout trace variance) are corrected in
`a82d38f`.

## Prior clean-clone check at `f9ccce7`

The prior evidence commit was checked from an isolated clone, without resetting
or modifying the working tree:

```powershell
$dest = Join-Path $env:TEMP "aaif-level2-v2-f9ccce7"
git -c core.autocrlf=false clone --quiet <repository> $dest
git -C $dest -c core.autocrlf=false checkout --quiet f9ccce75262b72651887c6b7e7872b71d217669e
$env:PYTHONPATH = Join-Path $dest "src"
& <repository>\.venv\Scripts\python.exe -m pytest -q
```

Result at exact HEAD `f9ccce7`: **258 passed in 104.62s**, exit `0`; fixture
SHA-256 `69136fc840591c811fac66153122a3b091a0bea13445d770dafa294e6874e272`.
Both V2 runners exited `0` and reproduced scorecard **24/24**, terminal/cause
**24/24**, and comparison path passes **13/13** per path, exact cross-path
terminal/cause **10/13**. This clean clone contains the pre-reconciliation
comparison definition; its semantic result is historical for that commit.

## Pre-commit clean-copy check

Before the reconciliation commit, the content was checked from an isolated
`git archive` copy with the current Level 2 evidence and evaluation tests
overlaid. The copy contained no `.git` directory and was not a commit or push.
The copy was built from the then-current `HEAD` with `git archive`, then the
current `docs/evidence/level-2`, `tests/evaluation`, and
`tests/test_level2_v2_harness.py` were copied over it; tests used `PYTHONPATH`
pointed at the copy's `src` directory.

Result: **258 passed in 102.53s**, exit `0`; both V2 runners exited `0` with
scorecard **24/24**, terminal/cause **24/24**, comparison path passes **13/13**
per path, both-success **1/13**, both-fail-closed **12/13**, semantic **13/13**,
and exact cross-path terminal/cause **10/13**.

Generated Markdown artifacts matched the then-working-tree Markdown
byte-for-byte. `comparison-v2.json` matched after removing runtime `task_id` and
`context_id` values; those IDs vary per run and are not evidence of a result
change. `scorecard-v2.json` matched after the same normalization, except for the
timing-dependent `sanitized_trace` field of `L2-09a` and `L2-09b`. These hashes
are historical to the pre-fix run.

| Artifact | Working tree | Clean copy |
| --- | --- | --- |
| `scorecard-v2.json` | `64e302e21e365bbcc93b6ab9be7af76c5150b8388f8dab97b38824d979cff02c` | `ff99d8d7b5b2b8411df8cee9524bc521206e5d526c2417b93ce3a8cbe8da8e41` |
| `scorecard-v2.md` | `0a1bc2ff34b69e2349816c11ca21c130cae5330615119f23eaa103e35f3cd525` | `0a1bc2ff34b69e2349816c11ca21c130cae5330615119f23eaa103e35f3cd525` |
| `comparison-v2.json` | `13a777b7631c51c58a5a0f2907ec07ab5f1008ccea73925c230a7d518e5bc721` | `4f182e6740bba99661867e2d53a63a066791b83504f6a73f6a4c4ad40a785196` |
| `comparison-v2.md` | `99cb6dba4691a3ae859b377298a699a498a48f3f5bda4e03738300e633a81c4c` | `99cb6dba4691a3ae859b377298a699a498a48f3f5bda4e03738300e633a81c4c` |

## Reproducibility notes

- The fixture is fixed and synthetic. Expected values apply only to this fixture
  and snapshot.
- Automated fault cases use deterministic local fakes and loopback servers.
- No hosted model, provider call, credential, external network, or real data is
  used.
- No latency, cost, savings, or productivity outcome is measured or claimed.
- V1 scorecard/comparison JSON and Markdown were preserved; V2 writes new
  `-v2` artifacts.
- The final evidence commit `a82d38f` and merge commit `c7c935c` are pushed and
  clean-clone verified. Owner review was completed and the Level 2 decision was
  recorded on 2026-11-20; this document does not restate the owner-authored
  closure state.
