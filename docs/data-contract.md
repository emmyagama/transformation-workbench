# Synthetic data contract — Transformation Workbench

## Purpose and boundary

This is a fictional email-based service-request process. All records and values are synthetic. The fixture is for deterministic metric calculations only; it supports no claims about real savings, productivity, or enterprise deployment.

Use `src/transformation_workbench/data/synthetic_cases.csv` as the single canonical fixture, included as package data and read with `importlib.resources` so it works from a source checkout or an installed wheel. All valid timestamps are ASCII-digit UTC ISO 8601 with `Z`; reject Unicode lookalike digits and non-canonical numeric fields. The one deliberately invalid date is retained to test row-level data-quality handling. The snapshot time is **2026-03-13T17:00:00Z**.

## Minimal v1 schema

- `case_id`: unique stable identifier.
- `received_at`, `acknowledged_at`: UTC timestamps; required and must parse.
- `closed_at`: required when `status=closed`; blank for open/awaiting-information cases.
- `priority`: exactly `P1`, `P2`, or `P3` (no default).
- `status`: `closed`, `open`, `awaiting_info`, or `duplicate`.
- `rework_count`: non-negative integer.
- `duplicate_of`: required for `duplicate`, otherwise blank.

Do not add arbitrary input paths, network access, write tools, or real business data. The MCP server will use this bundled fixture only. `notes`, email addresses, assignees, pause deductions, and rework narratives are intentionally out of v1.

## Rules

1. SLA targets: P1 = 8 h; P2 = 24 h; P3 = 72 h.
2. A case is measurable only when `status=closed`, all required timestamps parse, `received_at <= acknowledged_at <= closed_at`, priority is valid, and it is not a duplicate.
3. Cycle time is wall-clock `closed_at - received_at`, in hours. No pause deductions in v1.
4. SLA is met when cycle time `<=` the priority target (inclusive boundary).
5. Rework rate is the share of measurable closed cases with `rework_count >= 1`; rework volume is the sum of `rework_count` over those cases.
6. Open and `awaiting_info` cases are backlog at the stated snapshot. Backlog age is snapshot minus received time; overdue iff age is strictly greater than the priority target. No pause adjustment.
7. Excluded rows must be counted with a reason, never silently dropped or counted as an SLA miss. For this fixture: C-006 = `INCOMPLETE_MISSING_CLOSED_AT`; C-010 = `INVALID_DATE`; C-011 = `OUT_OF_ORDER`; C-014 = `DUPLICATE_OF:C-007`.
8. The snapshot is the reporting boundary. If any valid event timestamp on a case is later than the snapshot, exclude the whole case as `FUTURE_OF_SNAPSHOT`; do not count a future closure as completed or infer an earlier backlog state from a current-status row.
9. If multiple validation faults occur on one row, report the first by this documented precedence: identifier checks → status/priority → timestamp syntax/calendar validity → rework count → duplicate relationship → timestamp ordering → status/closed_at consistency → future-of-snapshot check. Add tests for representative collisions so precedence remains stable.
10. An internal blank CSV record is a malformed input row (`EMPTY_ROW`) and must be visible in row-level issues/reconciliation. A normal final newline is not an extra record. Do not silently discard whitespace-only records.
11. If no cases are measurable, return “no measurable cases,” not 0% or NaN.
12. Compute from full precision and round only for presentation: hours to 2 decimals, percentages to 1 decimal, using decimal half-up rounding.

## Hand-checkable expected output

- Input rows: 15.
- Measurable closed cases: 9; cycle times sum to 261.50 h.
- Mean cycle time: 29.06 h; median: 9.00 h.
- SLA met: 6/9 = 66.7%; exactly 24 h for C-009 is met.
- Rework: 2/9 cases = 22.2%; 3 total rework events.
- Backlog at snapshot: 2 cases (C-012, C-013); overdue: 1 (C-012, age 32 h vs 8 h target).
- Excluded rows: 4, with the four reason codes above.
- Reconciliation: 9 measurable + 4 excluded + 2 backlog = 15 input rows.

## Core must-test cases

- Exact expected rollups above.
- Inclusive SLA boundary (C-009).
- Invalid calendar date (C-010); no locale guessing.
- Out-of-order timestamps (C-011); no negative cycle time.
- Missing close timestamp (C-006); not counted as an SLA miss.
- Duplicate excluded from denominators (C-014).
- Empty data / only excluded data does not produce NaN, a crash, or fake 0% attainment.
- Unknown status/priority, malformed/non-ASCII rework count, and missing/duplicate identifiers are rejected or reported with an explicit reason.
- Non-ASCII lookalike digits in timestamps are rejected; an invalid first row does not prevent a corrected later row with the same ID from being accepted; a valid duplicate ID is still rejected.
- Internal blank record is surfaced as `EMPTY_ROW`; an ordinary final newline does not create a phantom row.
- A future received/acknowledged/closed timestamp is excluded as `FUTURE_OF_SNAPSHOT`.
- Median for an even-sized measurable set is the mean of the two middle values; an open case exactly at its SLA age is not overdue (overdue is strict `>`).
- Missing required fields and conflicting status/timestamp fields follow the documented reason precedence.

Do not implement filesystem path-traversal handling for the baseline: no tool takes a path, and no tool writes. Assert that tool schemas expose no path or write/action parameter. Defer a broad filesystem threat matrix to a later phase if the architecture ever adds such capability.
