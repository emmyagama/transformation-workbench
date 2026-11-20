# Level 2 fault-injection evidence v1

> **Historical artifact.** V1 is superseded by `fault-injection-v2.md` for the
> remediated evaluation. V1 used union matching and did not route all
> workflow-labeled variants through `run_workflow`. See `erratum-v1.md`. The
> table below is preserved as published.

**Pack:** `level2-evaluation-pack` v1.0.0
**Baseline commit:** `d5a6c973cae4ee17cd66ed01352a64c159ceb0f8`

All cases below are local and synthetic. Faults are injected through fixed
fixtures, static A2A artifacts, bounded fake MCP sources, or deterministic
executors. No hosted model or external system is used.

## Injected faults and observed results

| Variant | Injected fault | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| L2-02a | MCP process-context resource is not listed | `task_failure` / `mcp_resource_unavailable` | `task_failure` / `mcp_resource_unavailable` | Pass |
| L2-02b | Evidence pack and context carry a stale snapshot | `snapshot_mismatch` | `snapshot_mismatch` | Pass |
| L2-03a | Requested case `C-999` does not exist | `incomplete_evidence` | `incomplete_evidence` | Pass |
| L2-03b | `calculate_baseline_metrics` raises a bounded error | `task_failure` / `mcp_tool_error` | `task_failure` / `mcp_tool_error` | Pass |
| L2-04a | Evidence reports `input_rows=99` | `metric_value_mismatch` | `metric_value_mismatch` | Pass |
| L2-04b | Evidence carries a different request ID | `request_mismatch` | `task_failure` / `request_mismatch` | Pass |
| L2-04c | Evidence returns a different case set | `case_set_mismatch` | `case_set_mismatch` | Pass |
| L2-05a | Instruction text appended to process context | `context_mismatch` | `context_mismatch` | Pass |
| L2-05b | Instruction-override text in the desired outcome | `invalid_intake` / `instruction_override` | `invalid_intake` / `instruction_override` | Pass |
| L2-06a | Option claims $100,000 annual savings | `unsupported_claim` | `unsupported_claim` | Pass |
| L2-06b | Option claims 50% cycle-time reduction | `unsupported_claim` | `unsupported_claim` | Pass |
| L2-07b | Approved decision without an approval reference | `approval_id_required` | `approval_id_required` | Pass |
| L2-08b | Same request ID replayed with a different case set | `request_conflict` | `request_conflict` | Pass |
| L2-08c | Specialist endpoint unavailable | `specialist_unavailable` | `specialist_unavailable` | Pass |
| L2-09a | Slow specialist, retries disabled | `a2a_timeout` | `a2a_timeout` | Pass |
| L2-09b | Slow specialist, one retry exhausted | `a2a_timeout` | `a2a_timeout` | Pass |
| L2-10a | JSON text that does not parse | `malformed_result` | `malformed_result` | Pass |
| L2-10b | `text/plain` artifact instead of `application/json` | `malformed_result` | `malformed_result` | Pass |
| L2-10c | Evidence result omits a required field | `invalid_evidence_pack` | `invalid_evidence_pack` | Pass |
| L2-10d | Option references an unknown evidence ID | `unknown_evidence_reference` | `unknown_evidence_reference` | Pass |

## Safe-limitation and approval cases

| Variant | Behavior | Observed | Result |
| --- | --- | --- | --- |
| L2-07a | Action request is not executed; report stays read-only | Complete, approval pending, `consequential_action_permitted=false`, report states no action | Pass |
| L2-07c | Approved review state still cannot act | Complete, approval approved, `consequential_action_permitted=false`, action method raises `consequential_action_disabled` | Pass |

## Sanitized trace policy

Published trace evidence is projected to these fields only:

- protocol step (`discover_card`, `send_task`, `duplicate_replay`);
- agent or skill identifier;
- HTTP method and fixed path;
- task ID, context ID, task state, and attempt number.

The evidence bundle does not include raw request payloads, raw response
payloads, loopback URLs, environment values, server logs, credentials, private
paths, or synthetic case contents beyond the fixed fixture identifiers.

## Trace expectations observed

- `L2-08c` fails during discovery, before a discovery event is appended; the
  trace is empty.
- `L2-08b` raises `request_conflict` before a second discovery; the attached
  trace is the first successful run's trace.
- `L2-09a` can record a successful discovery, then fails during the bounded
  send; no completed `send_task` event is recorded.
- `L2-10c` records evidence discovery and send completion, then rejects the
  artifact during parsing; no solution task is started.
- `L2-10d` records both specialist discoveries and sends, then rejects the
  option during evidence-reference validation; no report is rendered.

## Reproduction

The full case set is exercised by:

```powershell
.\.venv\Scripts\python.exe -m tests.evaluation.run_level2_scorecard
```

The frozen per-case results are in `scorecard-v1.json` and `scorecard-v1.md`.
