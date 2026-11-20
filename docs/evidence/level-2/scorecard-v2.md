# Level 2 per-case scorecard v2

**Pack:** `level2-evaluation-pack-v2` v2.0.0
**Source commit:** `33f184d0bd48fd435d3910f1f9c55f4f97d1623d`
**Matching policy:** `literal_path_specific_terminal_and_cause_no_union`

## Summary

- Variants: **24**
- Workflow variants: **15**
- Coordinator variants: **9**
- Passed: **24**
- Missed: **0**
- Literal terminal-code matches: **24/24**
- Literal cause-code matches: **24/24**
- All declared invariants scored: **True**

## Per-case results

| Case | Variant | Entrypoint (declared / actual) | Expected status | Expected terminal / cause | Observed status | Observed terminal / cause | Category | Retry count / limit | Attempts | Human judgment | Invariants passed / declared | Pass | Misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L2-01 | L2-01a | workflow / workflow | complete | - / - | complete | - / - | - | 0 / 1 | 1 | False | 15 / 15 | True | - |
| L2-02 | L2-02a | workflow / workflow | failure | task_failure / mcp_resource_unavailable | failure | task_failure / mcp_resource_unavailable | evidence_boundary | 0 / 0 | 1 | False | 9 / 9 | True | - |
| L2-02 | L2-02b | workflow / workflow | failure | snapshot_mismatch / - | failure | snapshot_mismatch / - | contract_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-03 | L2-03a | workflow / workflow | failure | incomplete_evidence / - | failure | incomplete_evidence / - | contract_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-03 | L2-03b | workflow / workflow | failure | task_failure / mcp_tool_error | failure | task_failure / mcp_tool_error | evidence_boundary | 0 / 0 | 1 | False | 9 / 9 | True | - |
| L2-04 | L2-04a | workflow / workflow | failure | metric_value_mismatch / - | failure | metric_value_mismatch / - | contract_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-04 | L2-04b | workflow / workflow | failure | task_failure / request_mismatch | failure | task_failure / request_mismatch | contract_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-04 | L2-04c | workflow / workflow | failure | case_set_mismatch / - | failure | case_set_mismatch / - | contract_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-05 | L2-05a | workflow / workflow | failure | context_mismatch / - | failure | context_mismatch / - | contract_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-05 | L2-05b | workflow / workflow | refused | invalid_intake / instruction_override | refused | invalid_intake / instruction_override | intake_validation | 0 / 0 | 0 | False | 9 / 9 | True | - |
| L2-06 | L2-06a | workflow / workflow | failure | unsupported_claim / - | failure | unsupported_claim / - | safety_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-06 | L2-06b | workflow / workflow | failure | unsupported_claim / - | failure | unsupported_claim / - | safety_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-07 | L2-07a | workflow / workflow | complete | - / - | complete | - / - | - | 0 / 0 | 1 | False | 15 / 15 | True | - |
| L2-07 | L2-07b | workflow / workflow | refused | approval_id_required / - | refused | approval_id_required / - | approval_boundary | 0 / 0 | 0 | False | 7 / 7 | True | - |
| L2-07 | L2-07c | workflow / workflow | complete | - / - | complete | - / - | - | 0 / 0 | 1 | False | 15 / 15 | True | - |
| L2-08 | L2-08a | coordinator / coordinator | complete | - / - | complete | - / - | - | 0 / 0 | 1 | False | 14 / 14 | True | - |
| L2-08 | L2-08b | coordinator / coordinator | failure | request_conflict / - | failure | request_conflict / - | duplicate_replay | 0 / 0 | 1 | False | 10 / 10 | True | - |
| L2-08 | L2-08c | coordinator / coordinator | failure | specialist_unavailable / - | failure | specialist_unavailable / - | protocol_boundary | 1 / 1 | 2 | False | 8 / 8 | True | - |
| L2-09 | L2-09a | coordinator / coordinator | failure | a2a_timeout / - | failure | a2a_timeout / - | protocol_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-09 | L2-09b | coordinator / coordinator | failure | a2a_timeout / - | failure | a2a_timeout / - | protocol_boundary | 1 / 1 | 2 | False | 8 / 8 | True | - |
| L2-10 | L2-10a | coordinator / coordinator | failure | malformed_result / - | failure | malformed_result / - | protocol_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-10 | L2-10b | coordinator / coordinator | failure | malformed_result / - | failure | malformed_result / - | protocol_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-10 | L2-10c | coordinator / coordinator | failure | invalid_evidence_pack / - | failure | invalid_evidence_pack / - | contract_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |
| L2-10 | L2-10d | coordinator / coordinator | failure | unknown_evidence_reference / - | failure | unknown_evidence_reference / - | contract_boundary | 0 / 0 | 1 | False | 8 / 8 | True | - |

## Misses

No misses under the frozen V2 path-specific expectations.

## Notes

- V2 supersedes the V1 scored run; V1 remains a historical artifact.
- Every workflow-labeled variant uses the real run_workflow entrypoint.
- Every coordinator-labeled variant uses the real local Phase2Coordinator.
- Terminal and cause expectations are literal and path-specific; union matching is not used.
- Each row records expected and observed status/codes, failure category, attempt count, retry count, max retries, human-judgment flag, every invariant result, and a sanitized trace.
- Retry count is attempt_count minus one; max_retries is the permitted retry limit.
- The Markdown table separates expected and observed fields and counts declared invariants only; the JSON also carries supplementary dimensions, sanitized trace, and evidence pointer.
- The L2-04b workflow expectation is task_failure / request_mismatch; the direct baseline expectation is request_mismatch / no cause.
- Whole-workflow failure remains the policy; no partial-result status exists.
- No hosted model, provider, external system, credential, or real data is used.
