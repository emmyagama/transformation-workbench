# Transformation Workbench evaluation

**Snapshot:** 2026-11-18 local review snapshot at commit `d84203e`. The numbers
below describe this review state, not a production release.

## Automated checks

| Check | Command | Result |
| --- | --- | --- |
| Full test suite | `.\.venv\Scripts\python.exe -m pytest -q` | 249 passed |
| Dependency consistency | `.\.venv\Scripts\python.exe -m pip check` | No broken requirements |
| CLI smoke test | `python -m transformation_workbench ...` | Exit 0; clean stderr; markdown and JSON render |
| Approval default | CLI without a decision | `pending`; consequential action **no** |
| CLI error path | Unsafe intake or specialist failure | Bounded JSON error; exit 1 |

The retained A2A acceptance suite remains part of the full run. It includes
real local A2A card discovery, task exchange, MCP stdio, fixture reconciliation,
claim guards, replay handling, and loopback/proxy controls.

## End-to-end criteria

| Dimension | Result | Evidence |
| --- | --- | --- |
| Intake validation | Pass | Valid request accepted; blank/short outcome, path-like IDs, prompt injection, and excessive case sets rejected |
| Evidence completeness | Pass | 13 metrics, 4 exceptions, and 3 requested case observations in the demonstrated run |
| Numeric consistency | Pass | Coordinator compares received evidence with the fixed fixture |
| Traceability | Pass | A2A card discovery, task/context IDs, MCP tool provenance, and evidence IDs appear in the report |
| Read-only behavior | Pass | Only read-only MCP tools are exposed; no write or business-action endpoint exists |
| Approval pause | Pass | Default output is `pending`; approved output remains action-disabled |
| Failure behavior | Pass | Specialist failure and invalid intake return bounded errors |
| Public-language guard | Pass | Tests reject unsupported savings/ROI/guarantee claims in solution text |

## Safety tests added for the end-to-end path

`tests/test_week4_workflow.py` covers:

- complete report structure and all required metric fields;
- pending, approved, and declined decision paths;
- approval-reference mismatch, replay, and action-disabled behavior;
- unsupported claims, prompt injection, and path-like case IDs;
- fixed-evidence injection and contract mismatch handling;
- end-to-end local workflow;
- CLI markdown and JSON output;
- bounded specialist failure and invalid intake;
- coordinator and Evidence Specialist rejection of path-like IDs before network
  or MCP work.

## Clean-clone check

A fresh clone of commit `d84203e` was created in a temporary directory, with a
new Python 3.11 virtual environment and an editable install of
`.[dev,openresponses]`. In that clone:

- `pytest -q`: **249 passed**.
- `pip check`: no broken requirements.
- CLI JSON demo: exit 0, empty stderr, `status=complete`,
  `approval.status=pending`, `consequential_action_permitted=false`, 13 metrics,
  4 exceptions, and 3 case observations.

## Known limits

- The fixture is synthetic, fixed, and small. Results do not generalize.
- The acceptance environment is a single Windows workstation.
- No hosted model, gateway, sandbox, or environment-host path is exercised in
  the Workbench/A2A/MCP workflow. The separate optional Open Responses adapter
  had one documented Console validation run and a separate bare-route failure.
- The approval checkpoint is a demo state machine, not a production
  authorization system.
- The report is deterministic in content, but A2A task and context IDs vary per
  run.
- No latency, cost, throughput, savings, or productivity outcome is measured.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m transformation_workbench `
  --request-id sample-review-001 `
  --desired-outcome "Review the synthetic service-request intake and decide which evidence to inspect next." `
  --case-id C-009 --case-id C-006 --case-id C-014 `
  --format markdown
```
