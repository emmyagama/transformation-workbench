# Erratum for Level 2 evaluation pack v1

**Applies to:** `level2-evaluation-pack` v`1.0.0`
**Source commit:** `33f184d`
**Status:** historical clarification; V1 artifacts remain unchanged
**Superseded for scoring by:** `level2-evaluation-pack-v2` v`2.0.0`

## Finding

The V1 scorecard and comparison counted a case as passing when either the
expected terminal code **or** the expected cause code appeared in the observed
result. That union match is weaker than an exact terminal-code match. V1 also
routed most workflow-labeled variants through the coordinator entrypoint rather
than `run_workflow`.

V1 results are preserved as published. This erratum states the stricter reading
and points to V2 for corrected scoring.

## Strict-reading counts

| Measure | V1 published | Strict terminal-code reading |
| --- | --- | --- |
| Per-case scorecard | `24/24` | `23/24` |
| A2A comparison cases | `13/13` | `12/13` |
| Exact top-level comparison codes | not separated | `10/13` |

The three shared cases where the A2A path wraps an underlying code are:

| Variant | A2A observed | Direct baseline observed |
| --- | --- | --- |
| `L2-02a` | `task_failure` / `mcp_resource_unavailable` | `mcp_resource_unavailable` |
| `L2-03b` | `task_failure` / `mcp_tool_error` | `mcp_tool_error` |
| `L2-04b` | `task_failure` / `request_mismatch` | `request_mismatch` |

`L2-04b` is the V1 expectation defect: V1 expected the workflow terminal code to
be `request_mismatch`, with no cause. The observed workflow result is
`task_failure` with cause `request_mismatch`. V1 passed it only through union
matching.

## Workflow routing finding

V1 executed only `{L2-01a, L2-05b, L2-07a, L2-07b, L2-07c}` through the real
`run_workflow` entrypoint. Ten workflow-labeled variants were routed through the
coordinator path: `L2-02a/b`, `L2-03a/b`, `L2-04a/b/c`, `L2-05a`, and
`L2-06a/b`. V2 routes all 15 workflow variants through `run_workflow` and keeps
all 9 coordinator variants on the real coordinator.

## V2 treatment

- V1 pack files, scorecard, and comparison JSON/Markdown remain historical and
  are not relabeled.
- V2 adds `baseline_expected` for the 13 shared cases.
- V2 records `L2-04b` workflow as `task_failure` / `request_mismatch` and the
  direct baseline as `request_mismatch` / no cause.
- V2 scores terminal code, cause code, and semantic failure as separate
  dimensions and prohibits union matching.
- V2 adds the missing per-case fields: failure category, retry count,
  sanitized trace, and human-judgment flag.

## Scope

This erratum changes the scoring interpretation, not the fixture, the product
code, or the V1 observed results. No hosted model, provider, external system,
credential, or real data is involved.
