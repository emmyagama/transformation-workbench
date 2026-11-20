# Level 2 baseline-versus-A2A comparison v2

**Pack:** `level2-evaluation-pack-v2` v2.0.0
**Source commit:** `33f184d0bd48fd435d3910f1f9c55f4f97d1623d`
**Matching policy:** `literal_path_specific_terminal_and_cause_no_union`

## Method

The A2A side uses the path selected by the corpus label: the real run_workflow entrypoint for workflow variants and the real local Phase2Coordinator for coordinator variants. The baseline side calls the same read-only evidence source and deterministic solution designer directly. Each path is scored against its own literal terminal and cause expectations. No union match is used.

## Result

- Shared cases: **13**
- A2A literal terminal-code matches: **13/13**
- A2A literal cause-code matches: **13/13**
- A2A semantic matches: **13/13**
- Baseline literal terminal-code matches: **13/13**
- Baseline literal cause-code matches: **13/13**
- Baseline semantic matches: **13/13**
- Cross-path exact terminal-code matches: **10/13**
- Cross-path exact cause-code matches: **10/13**
- Cross-path semantic matches: **13/13**

| Variant | Entrypoint | A2A status | A2A terminal / cause | A2A path pass | Baseline status | Baseline terminal / cause | Baseline path pass | Same status | Exact terminal | Exact cause | Semantic equal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L2-01a | workflow | complete | - / - | True | complete | - / - | True | True | True | True | True |
| L2-02a | workflow | failure | task_failure / mcp_resource_unavailable | True | failure | mcp_resource_unavailable / - | True | True | False | False | True |
| L2-02b | workflow | failure | snapshot_mismatch / - | True | failure | snapshot_mismatch / - | True | True | True | True | True |
| L2-03a | workflow | failure | incomplete_evidence / - | True | failure | incomplete_evidence / - | True | True | True | True | True |
| L2-03b | workflow | failure | task_failure / mcp_tool_error | True | failure | mcp_tool_error / - | True | True | False | False | True |
| L2-04a | workflow | failure | metric_value_mismatch / - | True | failure | metric_value_mismatch / - | True | True | True | True | True |
| L2-04b | workflow | failure | task_failure / request_mismatch | True | failure | request_mismatch / - | True | True | False | False | True |
| L2-04c | workflow | failure | case_set_mismatch / - | True | failure | case_set_mismatch / - | True | True | True | True | True |
| L2-05a | workflow | failure | context_mismatch / - | True | failure | context_mismatch / - | True | True | True | True | True |
| L2-06a | workflow | failure | unsupported_claim / - | True | failure | unsupported_claim / - | True | True | True | True | True |
| L2-06b | workflow | failure | unsupported_claim / - | True | failure | unsupported_claim / - | True | True | True | True | True |
| L2-10c | coordinator | failure | invalid_evidence_pack / - | True | failure | invalid_evidence_pack / - | True | True | True | True | True |
| L2-10d | coordinator | failure | unknown_evidence_reference / - | True | failure | unknown_evidence_reference / - | True | True | True | True | True |

## Observed code differences

Each path still matches its own V2 path-specific expectation; the differences are protocol wrappers, not union matches.

- **L2-02a:** The A2A path records the protocol wrapper task_failure with cause mcp_resource_unavailable; the direct baseline returns mcp_resource_unavailable without a cause. Each path matches its own V2 expected terminal/cause pair and both fail closed.
- **L2-03b:** The A2A path records the protocol wrapper task_failure with cause mcp_tool_error; the direct baseline returns mcp_tool_error without a cause. Each path matches its own V2 expected terminal/cause pair and both fail closed.
- **L2-04b:** The A2A path records the protocol wrapper task_failure with cause request_mismatch; the direct baseline returns request_mismatch without a cause. Each path matches its own V2 expected terminal/cause pair and both fail closed.

## Not applicable to the direct baseline

| Variant | Entrypoint | Reason |
| --- | --- | --- |
| L2-05b | workflow | This case depends on workflow/approval or A2A protocol behavior that the direct baseline does not implement. |
| L2-07a | workflow | This case depends on workflow/approval or A2A protocol behavior that the direct baseline does not implement. |
| L2-07b | workflow | This case depends on workflow/approval or A2A protocol behavior that the direct baseline does not implement. |
| L2-07c | workflow | This case depends on workflow/approval or A2A protocol behavior that the direct baseline does not implement. |
| L2-08a | coordinator | This case depends on workflow/approval or A2A protocol behavior that the direct baseline does not implement. |
| L2-08b | coordinator | This case depends on workflow/approval or A2A protocol behavior that the direct baseline does not implement. |
| L2-08c | coordinator | This case depends on workflow/approval or A2A protocol behavior that the direct baseline does not implement. |
| L2-09a | coordinator | This case depends on workflow/approval or A2A protocol behavior that the direct baseline does not implement. |
| L2-09b | coordinator | This case depends on workflow/approval or A2A protocol behavior that the direct baseline does not implement. |
| L2-10a | coordinator | This case depends on workflow/approval or A2A protocol behavior that the direct baseline does not implement. |
| L2-10b | coordinator | This case depends on workflow/approval or A2A protocol behavior that the direct baseline does not implement. |

## Bounded conclusion

On the shared synthetic cases, each path matched its own literal terminal code, cause code, and semantic failure checks. Cross-path terminal codes matched on 10 of 13 cases because the A2A protocol wraps evidence-side failures as `task_failure` with a cause code. The A2A path added protocol discovery and task evidence but did not improve correctness or safety on this sample. The sample is small and the baseline has no A2A protocol semantics, so this is not a general claim that A2A is or is not superior.

## Limits

- Small synthetic sample; not a general benchmark.
- Deterministic fakes test orchestration and contracts, not model reasoning.
- The baseline has no A2A protocol trace, discovery, retry, or timeout semantics.
- Cases that depend on A2A protocol behavior or the full report/approval workflow are not applicable to the baseline.
- No hosted model, provider, external system, credential, or real data is used.
- No latency, cost, savings, or productivity outcome is claimed.
