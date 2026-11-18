# End-to-end sample report (sanitized excerpt)

Command:

```powershell
.\.venv\Scripts\python.exe -m transformation_workbench `
  --request-id sample-review-001 `
  --desired-outcome "Review the synthetic service-request intake and decide which evidence to inspect next." `
  --case-id C-009 --case-id C-006 --case-id C-014 `
  --format markdown
```

Observed 2026-11-18 on Windows with Python 3.11 and the project virtual
environment. Exit code 0; stderr empty. A2A task/context IDs vary per run; the
rest of the demonstrated content is deterministic for this request and case set.

```markdown
# Transformation Workbench decision brief

**Synthetic-data demonstration.** No real business, customer, or personal data is used. This report is not a production service.

- Request: `sample-review-001`
- Process: Synthetic email service-request intake
- Desired outcome: Review the synthetic service-request intake and decide which evidence to inspect next.
- Approval status: **pending**
- Approval reference: `apr-b4d505037db42e64`
- Consequential action permitted: **no**

## 1. Executive brief

The synthetic fixture contains 15 input rows. 9 closed cases are measurable; 6 met their SLA target (66.7%), and 3 missed. Mean cycle time is 29.06 hours and median cycle time is 9 hours. 2 measurable cases had rework (22.2%), with 3 rework events. At the snapshot, backlog is 2 cases; 1 overdue. 4 rows are excluded for data-quality reasons, including a duplicate and a missing close timestamp.

The evidence supports a review of backlog triage, data quality, and rework handling. It does not establish root cause or quantify any future outcome. The proposed future-state workflow keeps calculations deterministic and pauses at a human approval checkpoint. No external network, write, or business action exists in this demo.

Requested outcome: Review the synthetic service-request intake and decide which evidence to inspect next.

## 2. Observed facts

- 15 synthetic input rows.
- 9 measurable closed cases; 6 met SLA (66.7%).
- Mean cycle time 29.06 hours; median 9 hours.
- Rework: 2 cases (22.2%), 3 events.
- Backlog: 2 cases; 1 overdue at the snapshot.
- Excluded rows: 4; each has a recorded reason and tool provenance.

## 3. Calculations
- SLA misses among measurable closed cases: 3 count (measurable_closed - sla_met_count; evidence: metric.measurable_closed, metric.sla_met_count)
- Excluded rows as a share of input rows: 26.7 percent (excluded_count / input_rows * 100; evidence: metric.excluded_count, metric.input_rows)
- Overdue backlog cases as a share of backlog: 50 percent (backlog_overdue / backlog_cases * 100; evidence: metric.backlog_overdue, metric.backlog_cases)

## 4. Data-quality exceptions
- C-006 row 7: INCOMPLETE_MISSING_CLOSED_AT (evidence: exception.row.7; source: list_case_exceptions)
- C-010 row 11: INVALID_DATE (evidence: exception.row.11; source: list_case_exceptions)
- C-011 row 12: OUT_OF_ORDER (evidence: exception.row.12; source: list_case_exceptions)
- C-014 row 15: DUPLICATE_OF:C-007 (evidence: exception.row.15; source: list_case_exceptions)

## 5. Requested case observations
- C-009 row 10: measurable, status=closed, priority=P2, cycle_time_hours=24, sla_met=True (evidence: case.C-009; source: get_case_details)
- C-006 row 7: invalid, exclusion_reason=INCOMPLETE_MISSING_CLOSED_AT (evidence: case.C-006; source: get_case_details)
- C-014 row 15: duplicate, status=duplicate, priority=P2, duplicate_of=C-007, exclusion_reason=DUPLICATE_OF:C-007 (evidence: case.C-014; source: get_case_details)

## 7. Automation opportunities for review

- `option-triage-backlog`: Triage overdue backlog cases against published SLA targets
  - Review overdue backlog cases in a fixed order before considering any process change. This is a proposal, not a measured outcome.
  - Rationale: The pack records 2 backlog cases, 1 overdue, and 66.7% SLA attainment. (evidence: metric.backlog_cases, metric.backlog_overdue, metric.sla_met_percent)
  - Limits: This option is a proposal and has not been implemented.; No financial or productivity outcome is quantified.

- `option-data-quality`: Resolve data-quality exclusions before automation design
  - Treat excluded rows as a data-quality workstream so later automation is not designed against incomplete records.
  - Rationale: The pack reports 4 excluded rows, each with a reason and tool provenance. (evidence: metric.excluded_count, exception.row.7, exception.row.11, exception.row.12, exception.row.15)
  - Limits: No claim is made that exclusions will disappear.; This option is a proposal and has not been implemented.

- `option-rework-review`: Review rework cases for recurring handling steps
  - Use the measured rework counts to scope a manual review of repeated handling. The option does not assume a root cause.
  - Rationale: The pack records 2 rework cases at 22.2%, with 3 rework events. (evidence: metric.rework_cases, metric.rework_rate_percent, metric.rework_volume)
  - Limits: The pack does not identify root causes.; This option is a proposal and has not been implemented.

## 14. Human approval checkpoint
- Status: **pending**
- Approval reference: `apr-b4d505037db42e64`
- Consequential action permitted: **no**; this is a review state only.
The workflow is paused before any consequential action. A human reviewer must decide before review continues. No external network, write, or business action is performed.
```

The omitted sections contain the proposed future-state steps, risks and
controls, assumptions, prioritized roadmap, full evidence appendix, protocol
trace, and known limitations. They are included in the live report.

## What this sample does not show

- A real business process or real data.
- A production deployment, hosted model call, or external action.
- Financial savings, ROI, or a productivity outcome.
- A complete security assessment.
