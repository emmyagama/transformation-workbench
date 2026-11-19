# Level 2 evaluation pack v1

**Pack ID:** `level2-evaluation-pack`
**Version:** `1.0.0`
**Status:** frozen for the Level 2 scored run
**Frozen:** 2026-11-19 by owner
**Baseline commit:** `d5a6c97`

This pack is a versioned, fixed evaluation corpus separate from the unit test
suite. It covers the ten scenario families in the Level 2 roadmap with
parameterized variants for distinct failure modes. It is synthetic-only and
local-only.

## Contents

| File | Purpose |
| --- | --- |
| `corpus-v1.json` | Ten core cases and their parameterized variants, including expected status, invariants, permitted tools, and retry bounds. |
| `expected-manifest-v1.json` | Fixture identity, expected metrics, exceptions, requested cases, options, required report fields, and required sections. |
| `rubric-v1.md` | Scoring dimensions, invariant definitions, failure taxonomy, deadlines, and change control. |
| `thresholds-v1.json` | Machine-readable thresholds, deadlines, retry policy, and partial-completion policy. |

## Freeze statement

The corpus, expected manifest, rubric, and thresholds were frozen before the
scored run. The owner approved the Package 1 freeze on 2026-11-19. After freeze,
any change requires a version increment and a written rationale. The rubric must
not be tuned after seeing results to turn a miss into a pass.

## Corpus shape

- **10 core cases**, one for each required scenario family.
- **Parameterized variants** isolate distinct failure modes; they are not
  near-duplicate scored cases.
- The clean baseline uses the fixed fixture and the default case IDs
  `C-009`, `C-006`, and `C-014`.
- Failure cases use deterministic local fakes or bounded fault injection.
- No hosted model, provider, external system, credential, or real data is used.

## Required result record

The scorer records, for every variant:

- case and variant ID;
- expected and actual status;
- pass/fail per invariant;
- failure category and error code;
- retry count where applicable;
- sanitized trace or evidence pointer;
- whether human judgment was used;
- the miss, if any.

The scorecard publishes every miss. It does not replace misses with an aggregate
score or a single average.

## Status vocabulary

- `complete`: a report was produced and stopped at the approval checkpoint.
- `refused`: the request was rejected before consequential work.
- `failure`: a bounded workflow, protocol, contract, or runtime failure ended
  without a successful result.
- `partial`: not permitted in v1. A one-specialist failure must be a whole
  workflow failure.

## Limits

- The fixture is synthetic, fixed, and small.
- The corpus is a formative project evaluation, not a general benchmark.
- Deterministic fakes test orchestration, contracts, and failure containment,
  not language-model reasoning or user-perceived answer quality.
- No latency, cost, savings, productivity, or production-readiness outcome is
  claimed.
- The approval checkpoint is a review state, not an action authorization.

## Reproduction

The local evaluation runner is added under `tests/evaluation/`. It uses the
existing deterministic core and local fakes, and it does not require hosted
access. The exact command and environment are recorded in the Package 4 evidence
bundle.
