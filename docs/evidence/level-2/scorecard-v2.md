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

| Case | Variant | Entrypoint | Status | Terminal / cause | Category | Attempts | Human judgment | Pass | Failed invariants |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L2-01 | L2-01a | workflow | complete | - / - | - | 1 | False | True | - |
| L2-02 | L2-02a | workflow | failure | task_failure / mcp_resource_unavailable | evidence_boundary | 1 | False | True | - |
| L2-02 | L2-02b | workflow | failure | snapshot_mismatch / - | contract_boundary | 1 | False | True | - |
| L2-03 | L2-03a | workflow | failure | incomplete_evidence / - | contract_boundary | 1 | False | True | - |
| L2-03 | L2-03b | workflow | failure | task_failure / mcp_tool_error | evidence_boundary | 1 | False | True | - |
| L2-04 | L2-04a | workflow | failure | metric_value_mismatch / - | contract_boundary | 1 | False | True | - |
| L2-04 | L2-04b | workflow | failure | task_failure / request_mismatch | contract_boundary | 1 | False | True | - |
| L2-04 | L2-04c | workflow | failure | case_set_mismatch / - | contract_boundary | 1 | False | True | - |
| L2-05 | L2-05a | workflow | failure | context_mismatch / - | contract_boundary | 1 | False | True | - |
| L2-05 | L2-05b | workflow | refused | invalid_intake / instruction_override | unclassified | 0 | False | True | - |
| L2-06 | L2-06a | workflow | failure | unsupported_claim / - | safety_boundary | 1 | False | True | - |
| L2-06 | L2-06b | workflow | failure | unsupported_claim / - | safety_boundary | 1 | False | True | - |
| L2-07 | L2-07a | workflow | complete | - / - | - | 1 | False | True | - |
| L2-07 | L2-07b | workflow | refused | approval_id_required / - | approval_boundary | 0 | False | True | - |
| L2-07 | L2-07c | workflow | complete | - / - | - | 1 | False | True | - |
| L2-08 | L2-08a | coordinator | complete | - / - | - | 1 | False | True | - |
| L2-08 | L2-08b | coordinator | failure | request_conflict / - | duplicate_replay | 1 | False | True | - |
| L2-08 | L2-08c | coordinator | failure | specialist_unavailable / - | protocol_boundary | 2 | False | True | - |
| L2-09 | L2-09a | coordinator | failure | a2a_timeout / - | protocol_boundary | 1 | False | True | - |
| L2-09 | L2-09b | coordinator | failure | a2a_timeout / - | protocol_boundary | 2 | False | True | - |
| L2-10 | L2-10a | coordinator | failure | malformed_result / - | protocol_boundary | 1 | False | True | - |
| L2-10 | L2-10b | coordinator | failure | malformed_result / - | protocol_boundary | 1 | False | True | - |
| L2-10 | L2-10c | coordinator | failure | invalid_evidence_pack / - | contract_boundary | 1 | False | True | - |
| L2-10 | L2-10d | coordinator | failure | unknown_evidence_reference / - | contract_boundary | 1 | False | True | - |

## Misses

No misses under the frozen V2 path-specific expectations.

## Notes

- V2 supersedes the V1 scored run; V1 remains a historical artifact.
- Every workflow-labeled variant uses the real run_workflow entrypoint.
- Every coordinator-labeled variant uses the real local Phase2Coordinator.
- Terminal and cause expectations are literal and path-specific; union matching is not used.
- Each row records terminal code, cause code, failure category, retry count, human-judgment flag, and a sanitized trace.
- The L2-04b workflow expectation is task_failure / request_mismatch; the direct baseline expectation is request_mismatch / no cause.
- Whole-workflow failure remains the policy; no partial-result status exists.
- No hosted model, provider, external system, credential, or real data is used.
