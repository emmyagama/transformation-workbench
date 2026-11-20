# Level 2 fault-injection evidence v2

**Pack:** `level2-evaluation-pack-v2` v2.0.0
**Source commit:** `33f184d`

All cases are local and synthetic. Faults are injected through fixed fixtures,
static A2A artifacts, bounded fake MCP sources, or deterministic executors. Every
workflow-labeled variant is executed through the real `run_workflow` entrypoint;
fault injection replaces the evidence source or solution executor inside that
entrypoint. No hosted model or external system is used. "Attempts" is the total
number of tries; retry count is attempts minus one.

## Injected faults and observed results

| Variant | Entrypoint | Injected fault | Expected terminal / cause | Observed terminal / cause | Attempts | Result |
| --- | --- | --- | --- | --- | --- | --- |
| L2-02a | workflow | MCP process-context resource is not listed | `task_failure` / `mcp_resource_unavailable` | `task_failure` / `mcp_resource_unavailable` | 1 | Pass |
| L2-02b | workflow | Evidence pack and context carry a stale snapshot | `snapshot_mismatch` / none | `snapshot_mismatch` / none | 1 | Pass |
| L2-03a | workflow | Requested case `C-999` does not exist | `incomplete_evidence` / none | `incomplete_evidence` / none | 1 | Pass |
| L2-03b | workflow | `calculate_baseline_metrics` raises a bounded error | `task_failure` / `mcp_tool_error` | `task_failure` / `mcp_tool_error` | 1 | Pass |
| L2-04a | workflow | Evidence reports `input_rows=99` | `metric_value_mismatch` / none | `metric_value_mismatch` / none | 1 | Pass |
| L2-04b | workflow | Evidence carries a different request ID | `task_failure` / `request_mismatch` | `task_failure` / `request_mismatch` | 1 | Pass |
| L2-04c | workflow | Evidence returns a different case set | `case_set_mismatch` / none | `case_set_mismatch` / none | 1 | Pass |
| L2-05a | workflow | Instruction text appended to process context | `context_mismatch` / none | `context_mismatch` / none | 1 | Pass |
| L2-05b | workflow | Instruction-override text in the desired outcome | `invalid_intake` / `instruction_override` | `invalid_intake` / `instruction_override` | 0 | Pass |
| L2-06a | workflow | Option claims $100,000 annual savings | `unsupported_claim` / none | `unsupported_claim` / none | 1 | Pass |
| L2-06b | workflow | Option claims 50% cycle-time reduction | `unsupported_claim` / none | `unsupported_claim` / none | 1 | Pass |
| L2-07b | workflow | Approved decision without an approval reference | `approval_id_required` / none | `approval_id_required` / none | 0 | Pass |
| L2-08b | coordinator | Same request ID replayed with a different case set | `request_conflict` / none | `request_conflict` / none | 1 | Pass |
| L2-08c | coordinator | Specialist endpoint unavailable | `specialist_unavailable` / none | `specialist_unavailable` / none | 2 | Pass |
| L2-09a | coordinator | Slow specialist, retries disabled | `a2a_timeout` / none | `a2a_timeout` / none | 1 | Pass |
| L2-09b | coordinator | Slow specialist, one retry exhausted | `a2a_timeout` / none | `a2a_timeout` / none | 2 | Pass |
| L2-10a | coordinator | JSON text that does not parse | `malformed_result` / none | `malformed_result` / none | 1 | Pass |
| L2-10b | coordinator | `text/plain` artifact instead of `application/json` | `malformed_result` / none | `malformed_result` / none | 1 | Pass |
| L2-10c | coordinator | Evidence result omits a required field | `invalid_evidence_pack` / none | `invalid_evidence_pack` / none | 1 | Pass |
| L2-10d | coordinator | Option references an unknown evidence ID | `unknown_evidence_reference` / none | `unknown_evidence_reference` / none | 1 | Pass |

## Safe-limitation and approval cases

| Variant | Behavior | Observed | Result |
| --- | --- | --- | --- |
| L2-07a | Action request is not executed; report stays read-only | Complete, approval pending, `consequential_action_permitted=false`, report states no action, action method raises | Pass |
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

- `L2-02a` and `L2-03b` fail while sending the evidence task; no completed
  evidence task is recorded and the solution designer is not called.
- `L2-05b` refuses at intake; the workflow does not start and the trace is empty.
- `L2-08c` fails during discovery; the trace is empty and two attempts are
  recorded under `max_retries=1`.
- `L2-08b` raises `request_conflict` before a second discovery; the attached
  trace is the first successful run's trace. The replay check passes because the
  trace is unchanged and no extra specialist POST is added.
- `L2-09a` can record a successful discovery, then fails during the bounded
  send; no completed `send_task` event is recorded.
- `L2-10c` records evidence discovery and send completion, then rejects the
  artifact during parsing; no solution task is started.
- `L2-10d` records both specialist discoveries and sends, then rejects the
  option during evidence-reference validation; no report is rendered.

## Reproduction

```powershell
.\.venv\Scripts\python.exe -m tests.evaluation.run_level2_scorecard_v2
```

The frozen per-case results are in `scorecard-v2.json` and `scorecard-v2.md`.
