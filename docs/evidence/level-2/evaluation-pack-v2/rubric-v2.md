# Level 2 evaluation rubric v2

**Pack:** `level2-evaluation-pack-v2` **Version:** `2.0.0` **Status:** frozen
**Frozen:** 2026-11-19 by owner **Source commit:** `33f184d`

This rubric supersedes the V1 scoring interpretation. V1 remains a historical
artifact. V2 uses explicit path-specific terminal and cause codes and does not
use union matching. This is a formative project evaluation over a small
synthetic fixture, not a statistical benchmark and not a measure of
language-model quality.

## 1. Scoring unit

Each corpus variant is scored independently. A case passes only when every
declared invariant passes. There is no partial credit inside a case.

Every row publishes:

- case and variant ID;
- entrypoint and actual runner entrypoint;
- expected and actual status;
- expected and actual terminal code;
- expected and actual cause code;
- failure category;
- retry count and max retries;
- human-judgment flag;
- sanitized trace or evidence pointer;
- pass/fail per invariant and the miss, if any.

Aggregate counts are descriptive only. A high aggregate never converts a failed
safety or numeric invariant into a pass.

## 2. Matching policy

- **Terminal code:** observed terminal code must equal the expected terminal code
  for the same path.
- **Cause code:** observed cause code must equal the expected cause code for the
  same path.
- **Semantic failure:** status, absence of a successful result, bounded
  termination, retry bound, and trace checks are reported separately.
- **No union match:** matching either the terminal code or the cause code does
  not count as an exact terminal-code pass.
- **No post-result tuning:** a V2 miss is reported. Changing an expectation after
  seeing a result requires a version increment and written rationale.

## 3. Dimensions and thresholds

| Dimension | Threshold | How it is checked |
| --- | --- | --- |
| Deterministic numeric correctness | **100% exact match** | Compare every metric, calculation, exception, and requested-case value with `expected-manifest-v2.json`. |
| Contract integrity | **100%** | Accepted handoffs validate against the versioned Pydantic contracts and semantic validators. Malformed or unsupported results are rejected, never repaired or replaced by a fallback. |
| Evidence traceability | **100%** | Every factual claim in a complete result has an evidence/resource/tool reference, or is explicitly labeled as an assumption. |
| Safety | **Zero** successful prohibited actions; **zero** unsupported financial/savings claims accepted as facts | Call the real approval action method and require `consequential_action_disabled`; inspect the actual trace; call the real claim/contract validators. |
| Completeness | **100%** of required fields and sections for a result labeled `complete` | Compare against the manifest's required report fields and sections. `partial` is not permitted. |
| Failure containment | **100%** of injected failures terminate within the documented deadline and retry bound with a truthful status | Check literal terminal code, cause code, attempt count, and absence of a fabricated successful result. |
| Repeatability | **100%** of deterministic metrics and pass/fail outcomes reproduce from a clean checkout | Re-run the pack and compare fixture-derived values and per-case outcomes. Do not require identical prose or task IDs. |
| Latency/cost | Descriptive only, and only if captured | Local elapsed time may be reported as local elapsed time. Do not label it provider latency, and do not estimate provider cost. |

## 4. Status semantics

- `complete`: a report or coordinator result was produced; the workflow remains
  at the approval checkpoint.
- `refused`: the request was rejected before consequential work, with a bounded
  error.
- `failure`: a bounded workflow, protocol, contract, or runtime failure ended
  without a successful result.
- `partial`: **not permitted in V2.** The whole-workflow-failure policy is
  unchanged. A one-specialist failure must end in `failure`, not a result that
  implies full completion.

## 5. Invariant definitions

| Invariant | Meaning |
| --- | --- |
| `terminal_status_matches` | Actual status equals the expected status. |
| `terminal_code_matches` | Actual terminal code equals the expected terminal code for the same path. |
| `cause_code_matches` | Actual cause code equals the expected cause code for the same path. |
| `metrics_exact_match` | All 13 metrics equal the manifest values exactly. |
| `exceptions_exact_match` | The exception rows and reasons equal the manifest. |
| `requested_cases_exact_match` | Requested case observations equal the manifest for the requested set. |
| `options_exact_match` | Option IDs equal the manifest option IDs. |
| `traceability` | Every option rationale references known evidence IDs. |
| `completeness` | Required metrics and option fields are present. |
| `contract_valid` | Evidence and options pass the real validators. |
| `all_required_report_fields_present` | Every required report field is present. |
| `all_required_report_sections_present` | Every required markdown section heading appears. |
| `approval_matches` | Approval status equals the expected `pending` or `approved` value. |
| `consequential_action_permitted_false` | The checkpoint always reports `false`. |
| `report_states_no_action` | The rendered report explicitly says no external network, write, or business action exists. |
| `action_method_raises` | The real `execute_consequential_action` call raises `consequential_action_disabled`. |
| `no_forbidden_tool_called` | The trace contains only allowed discovery, task, and replay events. |
| `no_unsupported_claim` | The real validator rejects unsupported financial, savings, ROI, guarantee, or impact claims. |
| `retry_count_within_bound` | Attempt count is at most `max_retries + 1`. |
| `no_fabricated_success` | No successful result or report exists after a failure. |
| `bounded_terminal_status` | The failure terminates with `failure` or `refused`. |
| `no_workflow_started` | Intake refusal occurs before discovery or task exchange. |
| `no_discovery` / `no_send_task` | No A2A discovery or task exchange occurs. |
| `no_completed_send_task` | The failed specialist never reports a completed task. |
| `no_completed_evidence_task` | The evidence specialist did not complete. |
| `no_solution_task` | The solution designer was not called after an evidence failure. |
| `no_report_rendered` | No report is rendered for a failed contract or safety result. |
| `no_approval_transition` | A failed approval attempt leaves no approved report. |
| `trace_complete` | Two card discoveries and two completed specialist tasks are present. |
| `first_run_complete` / `second_run_complete` | Replay runs return complete results. |
| `duplicate_replay_trace_on_second_run` | The second result ends with a `duplicate_replay` event. |
| `second_trace_prefix_matches_first` | The replay preserves the first trace and appends only the replay marker. |
| `no_extra_specialist_posts` | A replay or conflict does not add specialist posts. |
| `second_run_rejected` | A conflicting replay is rejected with `request_conflict`. |

## 6. Failure taxonomy

| Category | Representative codes |
| --- | --- |
| `intake_validation` | `invalid_intake`, `instruction_override`, `system_prompt_exfiltration`, `role_override`, `tool_action_request`, `path_traversal`, `credential_material`, `unsafe_display_text`, `invalid_case_id` |
| `approval_boundary` | `approval_id_required`, `invalid_approval_id`, `approval_already_decided`, `consequential_action_disabled` |
| `protocol_boundary` | `invalid_agent_card`, `non_task_response`, `specialist_unavailable`, `a2a_timeout`, `task_failure`, `malformed_result` |
| `contract_boundary` | `invalid_evidence_pack`, `invalid_solution_options`, `missing_metric`, `invalid_provenance`, `unknown_evidence_reference`, `incomplete_evidence`, `metric_value_mismatch`, `context_mismatch`, `context_hash_mismatch`, `snapshot_mismatch`, `request_mismatch`, `case_set_mismatch`, `case_observation_mismatch`, `sla_target_mismatch` |
| `safety_boundary` | `unsupported_claim`, `claim_rejected` |
| `evidence_boundary` | `mcp_resource_unavailable`, `mcp_resource_invalid`, `mcp_tool_error`, `mcp_timeout`, `mcp_unavailable` |
| `duplicate_replay` | `request_conflict`, `duplicate_replay` |
| `internal` | `internal_error`, unexpected exception |

## 7. Deadlines and retries

The scored run reuses the existing configuration:

- per-operation A2A timeout: **20.0 s** (`workflow.run_workflow` default);
- MCP evidence-session timeout: **20.0 s** (`McpEvidenceSource` default);
- default retry count: **1** (one retry, two attempts maximum);
- local runtime shutdown wait: **10.0 s**.

Fault-injection variants may use a smaller timeout (for example, 0.1 s) and a
retry count of 0 or 1 to keep the local suite bounded. Those values are part of
the case definition, not a change to the production default.

Retries are allowed only for transient protocol failures:
`specialist_unavailable` and `a2a_timeout`. Contract, safety, intake, approval,
malformed-result, and duplicate-conflict failures are not retried.

## 8. V1 erratum and V2 rationale

The V1 scorecard used union matching between expected and observed codes. Under a
strict terminal-code reading, V1 is `23/24` on the scorecard and `12/13` on the
A2A comparison. V2 records the path-specific expectations explicitly. In
particular, `L2-04b` workflow is `task_failure` / `request_mismatch`, while the
direct baseline is `request_mismatch` / no cause.

## 9. Freeze and change control

- The V2 corpus, expected manifest, rubric, and thresholds are frozen at version
  `2.0.0`.
- After freeze, any change requires a version increment and a written rationale.
- Do not tune the rubric, expected values, or thresholds after seeing results to
  turn a miss into a pass.
- A miss is a finding. It may become a defect or an owner-approved deferral with
  severity and impact; it is not silently removed.

## 10. Limits

- The fixture is synthetic, fixed, and small.
- The corpus is a formative project evaluation, not a general benchmark.
- The local deterministic agents/fakes test orchestration, contracts, and failure
  containment, not language-model reasoning or user-perceived answer quality.
- No hosted model, provider, external system, credential, or real data is used.
- No latency, cost, throughput, savings, or productivity outcome is claimed.
