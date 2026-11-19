# Level 2 per-case scorecard v1

**Pack:** `level2-evaluation-pack` v1.0.0
**Baseline commit:** `d5a6c973cae4ee17cd66ed01352a64c159ceb0f8`

## Summary

- Variants: **24**
- Passed: **24**
- Missed: **0**

## Per-case results

| Case | Variant | Entrypoint | Status | Code / cause | Pass | Failed dimensions |
| --- | --- | --- | --- | --- | --- | --- |
| L2-01 | L2-01a | workflow | complete | - / - | True | - |
| L2-02 | L2-02a | workflow | failure | task_failure / mcp_resource_unavailable | True | - |
| L2-02 | L2-02b | workflow | failure | snapshot_mismatch / - | True | - |
| L2-03 | L2-03a | workflow | failure | incomplete_evidence / - | True | - |
| L2-03 | L2-03b | workflow | failure | task_failure / mcp_tool_error | True | - |
| L2-04 | L2-04a | workflow | failure | metric_value_mismatch / - | True | - |
| L2-04 | L2-04b | workflow | failure | task_failure / request_mismatch | True | - |
| L2-04 | L2-04c | workflow | failure | case_set_mismatch / - | True | - |
| L2-05 | L2-05a | workflow | failure | context_mismatch / - | True | - |
| L2-05 | L2-05b | workflow | refused | invalid_intake / instruction_override | True | - |
| L2-06 | L2-06a | workflow | failure | unsupported_claim / - | True | - |
| L2-06 | L2-06b | workflow | failure | unsupported_claim / - | True | - |
| L2-07 | L2-07a | workflow | complete | - / - | True | - |
| L2-07 | L2-07b | workflow | refused | approval_id_required / - | True | - |
| L2-07 | L2-07c | workflow | complete | - / - | True | - |
| L2-08 | L2-08a | coordinator | complete | - / - | True | - |
| L2-08 | L2-08b | coordinator | failure | request_conflict / - | True | - |
| L2-08 | L2-08c | coordinator | failure | specialist_unavailable / - | True | - |
| L2-09 | L2-09a | coordinator | failure | a2a_timeout / - | True | - |
| L2-09 | L2-09b | coordinator | failure | a2a_timeout / - | True | - |
| L2-10 | L2-10a | coordinator | failure | malformed_result / - | True | - |
| L2-10 | L2-10b | coordinator | failure | malformed_result / - | True | - |
| L2-10 | L2-10c | coordinator | failure | invalid_evidence_pack / - | True | - |
| L2-10 | L2-10d | coordinator | failure | unknown_evidence_reference / - | True | - |

## Misses

No misses in the frozen local corpus.

## Notes

- The scorecard covers all frozen corpus variants, not only the shared baseline comparison.
- Workflow variants are exercised through the full intake-to-approval workflow.
- Coordinator variants are exercised through the real local A2A coordinator and specialists.
- The direct baseline is compared only where it is applicable; other variants are A2A-specific or workflow/approval-specific.
- No hosted model, provider, external system, credential, or real data is used.
