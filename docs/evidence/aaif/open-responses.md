# AAIF evidence card: Open Responses

**Status: HANDS-ON SPIKE COMPLETE for the tested adapter + Console combination.**
The bare Console route remains a separate failure.

## Problem addressed

A Workbench-owned adapter needs to accept Open Responses-shaped requests and
return compatible streaming/error behavior while testing an optional compaction
state.

## Official source and version

- Specification: <https://openresponses.org/>
- Acceptance suite pinned at commit `dce9ddb91921427c2ba06901c7dfaf0cc7056799`.
- Adapter: `src/transformation_workbench/openresponses_adapter/`.

## What was actually run or built

- Gate 2: local fake upstream; adapter tests and suite harness exercised.
- Gate 3: one run against the local adapter with OpenCode Console upstream;
  **17 passed, 0 failed**, **19** suite operations, **50/56** conservative
  cumulative total.
- The adapter implements adapter-owned AES-256-GCM compaction state with a
  versioned token and bounded spec-shaped errors.

## One observed limitation

The separate bare Console route recorded **1 pass, 16 fail**. Gate 3 ran from
an uncommitted working tree at `17faecf`, not from a clean committed revision,
and does not make the bare Console route conformant. Compaction is
adapter-owned, not provider-native or portable, and one adapter + Console
configuration is not general Open Responses conformance.

## Fit to Transformation Workbench

**Conditional fit.** The adapter is a useful interoperability experiment, but it
is optional, adds a second protocol surface, and is not required for the local
A2A demo. Keep it out of the flagship path unless an integration need is
demonstrated.

## Evidence links

- `docs/archive/openresponses-adapter.md`
- `docs/archive/openresponses-gate3-runbook.md`
- `docs/evidence/openresponses-gate2.json`
- `docs/evidence/openresponses-gate3.json`
- `tests/test_openresponses_adapter.py`
