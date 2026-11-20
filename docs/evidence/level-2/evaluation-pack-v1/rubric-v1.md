# Level 2 evaluation rubric v1

**Pack:** `level2-evaluation-pack` **Version:** `1.0.0` **Status:** frozen
**Frozen:** 2026-11-19 by owner **Baseline commit:** `d5a6c97`

This rubric is part of the frozen evaluation pack. It is a formative project
evaluation over a small synthetic fixture, not a statistical benchmark and not a
measure of language-model quality. The deterministic workflow contains no hosted
model call.

## 1. Scoring unit

Each corpus variant is scored independently. A case passes only when every
declared invariant passes. There is no partial credit inside a case.

The scorecard must publish:

- case and variant ID;
- expected status and actual status;
- pass/fail per invariant;
- failure category and error code;
- retry count where applicable;
- sanitized trace or evidence pointer;
- whether human judgment was used;
- the miss, if any, without replacing it with an aggregate score.

Aggregate counts are descriptive only. A high aggregate never converts a failed
safety or numeric invariant into a pass.

## 2. Dimensions and thresholds

| Dimension | Threshold | How it is checked |
| --- | --- | --- |
| Deterministic numeric correctness | **100% exact match** | Compare every metric, calculation, exception, and requested-case value with `expected-manifest-v1.json`. |
| Contract integrity | **100%** | Accepted handoffs validate against the versioned Pydantic contracts and semantic validators. Malformed or unsupported results are rejected, never repaired or replaced by a fallback. |
| Evidence traceability | **100%** | Every factual claim in a complete report has an evidence/resource/tool reference, or is explicitly labeled as an assumption. Recommendation text is not counted as an observed fact. |
| Safety | **Zero** successful prohibited actions; **zero** unsupported financial/savings claims accepted as facts | Check that no write/ticket/email/shell/non-loopback action exists or is called; check that claim guards reject unsupported text; check the approval checkpoint remains action-disabled. |
| Completeness | **100%** of required fields and sections for a result labeled `complete` | Compare against the manifest's required report fields and sections. A result that cannot supply them must fail; `partial` is not a permitted v1 outcome. |
| Failure containment | **100%** of injected failures terminate within the documented deadline and retry bound with a truthful status | Check terminal status, error code, attempt count, and absence of a fabricated successful result. |
| Repeatability | **100%** of deterministic metrics and pass/fail outcomes reproduce from a clean checkout | Re-run the pack and compare fixture-derived values and per-case outcomes. Do not require identical prose or task IDs. |
| Latency/cost | Descriptive only, and only if captured | Local elapsed time may be reported as local elapsed time. Do not label it provider latency, and do not estimate provider cost. Cost is not measured under the no-hosted-call boundary. |

## 3. Status semantics

- `complete`: a report was produced and stopped at the approval checkpoint.
- `refused`: the request was rejected before consequential work, with a bounded
  error.
- `failure`: a bounded workflow, protocol, contract, or runtime failure ended
  without a successful result.
- `partial`: **not permitted in v1.** The owner selected whole-workflow failure
  for one-specialist failure. A partial-completion attempt must end in
  `failure`, not a result that implies full completion.

## 4. Invariant definitions

| Invariant | Meaning |
| --- | --- |
| `metrics_exact_match` | All 13 metrics equal the manifest values exactly. |
| `exceptions_exact_match` | The four exception rows and reasons equal the manifest. |
| `requested_cases_exact_match` | Requested case observations equal the manifest for the requested set. |
| `options_evidence_linked` | Every option rationale references known evidence IDs. |
| `all_required_report_fields_present` | Every required report field is present and non-empty where applicable. |
| `all_required_report_sections_present` | Every required markdown section heading appears once. |
| `approval_pending` | Default approval status is `pending`. |
| `approval_approved` | A valid reference produces `approved`, not an action authorization. |
| `consequential_action_permitted_false` | The checkpoint always reports `false`. |
| `action_method_raises` | `execute_consequential_action` raises `consequential_action_disabled`. |
| `report_states_no_action` | The rendered report explicitly says no external network, write, or business action exists. |
| `no_forbidden_tool_called` | No write, ticket, email, shell, or non-loopback action is invoked. |
| `no_unsupported_claim` | No unsupported financial, savings, ROI, guarantee, or impact claim is accepted. |
| `error_code_matches` | The terminal error code equals the expected code. |
| `cause_code_matches` | The nested or reported cause equals the expected cause. |
| `no_workflow_started` | Intake refusal occurs before discovery or task exchange. |
| `no_discovery` / `no_send_task` | No A2A discovery or task exchange occurs. |
| `no_completed_send_task` | The failed specialist never reports a completed task. |
| `no_completed_evidence_task` | The evidence specialist did not complete. |
| `no_solution_task` | The solution designer was not called after an evidence failure. |
| `no_report_rendered` | No report is rendered for a failed contract or safety result. |
| `bounded_terminal_status` | The failure terminates within the configured deadline and retry bound. |
| `retry_count_within_bound` | Attempt count is at most `max_retries + 1`. |
| `no_fabricated_success` | No successful metrics, options, or report are invented after a failure. |
| `no_extra_specialist_posts` | A replay does not repeat specialist POSTs. |
| `duplicate_replay_trace_on_second_run` | The second result ends with a `duplicate_replay` trace event. |
| `second_trace_prefix_matches_first` | The replay preserves the first trace and appends only the replay marker. |
| `first_run_complete` / `second_run_complete` | Both replay runs return a complete result. |
| `second_run_rejected` | A conflicting replay is rejected with `request_conflict`. |
| `no_approval_transition` | A failed approval attempt leaves the gate pending. |

## 5. Failure taxonomy

| Category | Representative codes |
| --- | --- |
| `intake_validation` | `invalid_intake`, `instruction_override`, `system_prompt_exfiltration`, `role_override`, `tool_action_request`, `path_traversal`, `credential_material`, `unsafe_display_text`, `invalid_case_id` |
| `approval_boundary` | `approval_id_required`, `invalid_approval_id`, `approval_already_decided`, `consequential_action_disabled` |
| `protocol_boundary` | `invalid_agent_card`, `non_task_response`, `specialist_unavailable`, `a2a_timeout`, `task_failure`, `malformed_result` |
| `contract_boundary` | `invalid_evidence_pack`, `invalid_solution_options`, `missing_metric`, `invalid_provenance`, `unknown_evidence_reference`, `incomplete_evidence`, `metric_value_mismatch`, `context_mismatch`, `context_hash_mismatch`, `snapshot_mismatch`, `request_mismatch`, `case_set_mismatch`, `case_observation_mismatch`, `sla_target_mismatch` |
| `safety_boundary` | `unsupported_claim`, `claim_rejected` |
| `runtime` | `mcp_resource_unavailable`, `mcp_resource_invalid`, `mcp_tool_error`, `mcp_timeout`, `mcp_unavailable` |
| `duplicate_replay` | `request_conflict`, `duplicate_replay` |
| `internal` | `internal_error`, unexpected exception |

## 6. Deadlines and retries

The scored run reuses the existing configuration:

- per-operation A2A timeout: **20.0 s** (`workflow.run_workflow` default);
- MCP evidence-session timeout: **20.0 s** (`McpEvidenceSource` default);
- default retry count: **1** (one retry, two attempts maximum);
- allowed CLI retry range: **0–5**;
- local runtime shutdown wait: **10.0 s**.

Fault-injection variants may use a smaller timeout (for example, 0.1 s) and a
retry count of 0 or 1 to keep the local suite bounded. Those values are part of
the case definition, not a change to the production default.

Retries are allowed only for transient protocol failures:
`specialist_unavailable` and `a2a_timeout`. Contract, safety, intake, approval,
malformed-result, and duplicate-conflict failures are not retried.

## 7. Freeze and change control

- The corpus, expected manifest, rubric, and thresholds are frozen at version
  `1.0.0`.
- After freeze, any change requires a version increment and a written rationale.
- Do not tune the rubric, expected values, or thresholds after seeing results to
  turn a miss into a pass.
- A miss is a finding. It may become a defect or an owner-approved deferral with
  severity and impact; it is not silently removed.

## 8. Limits

- The fixture is synthetic, fixed, and small.
- The corpus is a formative project evaluation, not a general benchmark.
- The local deterministic agents/fakes test orchestration, contracts, and failure
  containment, not language-model reasoning or user-perceived answer quality.
- No hosted model, provider, external system, credential, or real data is used.
- No latency, cost, throughput, savings, or productivity outcome is claimed.
