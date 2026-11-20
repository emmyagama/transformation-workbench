# Level 2 baseline-versus-A2A comparison v1

**Pack:** `level2-evaluation-pack` v1.0.0
**Baseline commit:** `d5a6c973cae4ee17cd66ed01352a64c159ceb0f8`

## Method

The A2A path uses the real local coordinator and specialists. The baseline path calls the same read-only evidence source and deterministic solution designer directly. Both use the same fixture, contracts, validators, and expected manifest.

## Result

- Shared cases: **13**
- A2A cases passing all measured invariants: **13**
- Baseline cases passing all measured invariants: **13**
- Same terminal status: **13**
- Same failure semantics (both pass): **13**
- Exact error-code match: **10**

| Variant | A2A status | A2A code / cause | A2A pass | Baseline status | Baseline code | Baseline pass | Same status | Exact code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L2-01a | complete | - / - | True | complete | - | True | True | True |
| L2-02a | failure | task_failure / mcp_resource_unavailable | True | failure | mcp_resource_unavailable | True | True | False |
| L2-02b | failure | snapshot_mismatch / - | True | failure | snapshot_mismatch | True | True | True |
| L2-03a | failure | incomplete_evidence / - | True | failure | incomplete_evidence | True | True | True |
| L2-03b | failure | task_failure / mcp_tool_error | True | failure | mcp_tool_error | True | True | False |
| L2-04a | failure | metric_value_mismatch / - | True | failure | metric_value_mismatch | True | True | True |
| L2-04b | failure | task_failure / request_mismatch | True | failure | request_mismatch | True | True | False |
| L2-04c | failure | case_set_mismatch / - | True | failure | case_set_mismatch | True | True | True |
| L2-05a | failure | context_mismatch / - | True | failure | context_mismatch | True | True | True |
| L2-06a | failure | unsupported_claim / - | True | failure | unsupported_claim | True | True | True |
| L2-06b | failure | unsupported_claim / - | True | failure | unsupported_claim | True | True | True |
| L2-10c | failure | invalid_evidence_pack / - | True | failure | invalid_evidence_pack | True | True | True |
| L2-10d | failure | unknown_evidence_reference / - | True | failure | unknown_evidence_reference | True | True | True |
| L2-05b | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| L2-07a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| L2-07b | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| L2-07c | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| L2-08a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| L2-08b | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| L2-08c | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| L2-09a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| L2-09b | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| L2-10a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| L2-10b | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Observed code differences

Both paths still pass the expected failure semantics; the difference is where the failure is detected.

- **L2-02a:** The A2A path wraps the evidence failure as task_failure with cause mcp_resource_unavailable; the baseline returns mcp_resource_unavailable directly. Both fail closed.
- **L2-03b:** The A2A path wraps the evidence failure as task_failure with cause mcp_tool_error; the baseline returns mcp_tool_error directly. Both fail closed.
- **L2-04b:** The A2A evidence specialist rejects the request_id before the coordinator sees the pack, so the coordinator reports task_failure with cause request_mismatch. The baseline returns request_mismatch directly. Both fail closed.

## Not applicable to the direct baseline

| Variant | Reason |
| --- | --- |
| L2-05b | Intake refusal occurs before either evidence path starts. |
| L2-07a | Action-request safe limitation is a full report/approval behavior. |
| L2-07b | Approval bypass is a workflow/approval behavior. |
| L2-07c | Approved review state is a full report/approval behavior. |
| L2-08a | Duplicate replay is an A2A coordinator cache behavior. |
| L2-08b | Conflicting replay is an A2A coordinator cache behavior. |
| L2-08c | Unavailable specialist is an A2A discovery/transport behavior. |
| L2-09a | A2A timeout is a protocol-boundary behavior. |
| L2-09b | A2A retry exhaustion is a protocol-boundary behavior. |
| L2-10a | Malformed JSON artifact is an A2A artifact-boundary behavior. |
| L2-10b | Wrong MIME type is an A2A artifact-boundary behavior. |

## Bounded conclusion

On the shared synthetic cases, both paths passed every measured contract, traceability, completeness, safety, and failure invariant. Terminal status matched on all shared cases. Exact error codes matched on 10 of 13 cases; the differences are A2A wrapping of evidence-side failures as `task_failure` with a cause code, while the direct baseline returns the underlying code. The A2A path added protocol discovery and task evidence but did not improve correctness or safety on this sample. The sample is small and the baseline has no A2A protocol semantics, so this is not a general claim that A2A is or is not superior.

## Limits

- Small synthetic sample; not a general benchmark.
- Deterministic fakes test orchestration and contracts, not model reasoning.
- The baseline has no A2A protocol trace, discovery, retry, or timeout semantics.
- Cases that depend on A2A protocol behavior or the full report/approval workflow are not applicable to the baseline.
- No hosted model, provider, external system, credential, or real data is used.
- No latency, cost, savings, or productivity outcome is claimed.
