---
name: process-diagnostic
description: Retrieves and verifies the synthetic Transformation Workbench service-request baseline, exceptions, and case details using the read-only MCP tools. Use when diagnosing the intake process, checking metric reconciliation, or inspecting an excluded or duplicate row.
---

# Process Diagnostic

Use this skill to gather evidence before interpreting results or writing a brief. The MCP server is read-only and uses one fixed synthetic fixture.

## Preconditions

- Read and follow `AGENTS.md`.
- Use only the Transformation Workbench MCP server for process data.
- Do not use shell, developer, filesystem, browser, or action tools.
- Do not pass file paths. The MCP tools accept no path arguments.
- Treat the fixture as synthetic. It is not live operational evidence.

## Procedure

### 1. Read process context

Read the `workbench://process-context` MCP resource when the session exposes resources. Confirm:

- Snapshot: `2026-03-13T17:00:00Z`
- SLA targets: P1 = 8 h, P2 = 24 h, P3 = 72 h
- Cycle time is wall-clock `closed_at - received_at`
- Backlog is open or `awaiting_info` at the snapshot
- Read-only; synthetic data only

If the resource is unavailable, use the tool descriptions, this skill, and `AGENTS.md`. Do not invent context.

### 2. Retrieve baseline metrics

Call `calculate_baseline_metrics` with no arguments. Record these fields exactly:

- `status`, `snapshot_at`, `input_rows`, `measurable_closed`
- `cycle_time_sum_hours`, `mean_cycle_time_hours`, `median_cycle_time_hours`
- `sla_met_count`, `sla_met_percent`
- `rework_cases`, `rework_rate_percent`, `rework_volume`
- `backlog_cases`, `backlog_overdue`, `excluded_count`

Do not recompute from memory. If `status` is `no measurable cases`, report that literal state and do not show 0% or NaN.

### 3. Retrieve exclusions

Call `list_case_exceptions` with no arguments. For each item, record:

- `row_number`
- `case_id` (may be `null`)
- `reason`

The expected fixture exclusions are:

| Row | Case | Reason |
| --- | --- | --- |
| 7 | C-006 | `INCOMPLETE_MISSING_CLOSED_AT` |
| 11 | C-010 | `INVALID_DATE` |
| 12 | C-011 | `OUT_OF_ORDER` |
| 15 | C-014 | `DUPLICATE_OF:C-007` |

Treat these as verification targets, not a substitute for tool output.

### 4. Inspect the duplicate by row number

Call `get_case_details` with `row_number=15` to inspect `C-014`.

- Use `row_number` when an ID is duplicated, blank, or ambiguous.
- Do not call `get_case_details` with both `case_id` and `row_number`.
- Do not call it with neither selector.
- Row numbers start at 2; the CSV header is row 1.

Expected classification: `duplicate`, with `duplicate_of` `C-007` and exclusion reason `DUPLICATE_OF:C-007`.

### 5. Verify reconciliation and boundaries

Check the arithmetic independently:

- `measurable_closed + excluded_count + backlog_cases == input_rows`
- `sla_met_count / measurable_closed` equals `sla_met_percent`
- `rework_cases / measurable_closed` equals `rework_rate_percent`
- `cycle_time_sum_hours / measurable_closed` equals `mean_cycle_time_hours`

Expected fixture values:

| Measure | Expected |
| --- | --- |
| Input rows | 15 |
| Measurable closed | 9 |
| Cycle-time sum | 261.50 h |
| Mean cycle time | 29.06 h |
| Median cycle time | 9.00 h |
| SLA met | 6/9 = 66.7% |
| Rework | 2/9 = 22.2%; 3 events |
| Backlog | 2; 1 overdue |
| Excluded | 4 |

Boundary checks:

- `C-009` is exactly 24 h on P2 and is SLA-met.
- `C-012` is backlog for 32 h against an 8 h P1 target and is overdue.
- `C-013` is backlog for 55 h against a 72 h P3 target and is not overdue.
- `C-006` is excluded for missing close time. It is not an SLA miss.
- `C-014` is excluded as a duplicate and is not in the measurable denominator.

If tool output differs from these targets, report the discrepancy. Do not force reconciliation or invent a correction.

### 6. Handle tool errors safely

The `C-700` and blank-ID examples are illustrative test inputs, not shipped
fixture rows. The shipped fixture exposes IDs `C-001` through `C-015`.

- Unknown case ID: report the tool error and the allowed IDs it lists. Do not invent a record.
- Unknown row number: report the tool error and known rows. Do not map it to another row.
- Ambiguous case ID: use `row_number` as the error instructs, then retry once.
- Blank case ID: use `row_number` to inspect blank-ID rows. Do not treat blank as a valid ID.
- Invalid classification: report the row as excluded with its reason; do not calculate cycle time or SLA.
- Tool unavailable: stop and report the failure. Do not substitute memory or a web source.

### 7. Separate evidence from interpretation

Present findings in four labeled groups:

1. **Measured facts** — direct tool fields.
2. **Calculations** — arithmetic derived from measured fields.
3. **Assumptions** — explicit, limited, and unverified.
4. **Recommendations** — proposals that are not implemented.

Do not infer real savings, productivity gains, deployment readiness, or live performance. Do not claim that a write or approval occurred.

## Handoff to the brief

Pass only verified findings to the `executive-brief` skill. Include the exact baseline, the exception table, the duplicate inspection, reconciliation status, and any tool errors. Preserve the distinction between measured facts and recommendations.
