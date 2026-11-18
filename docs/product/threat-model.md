# Transformation Workbench threat model

**Scope:** the read-only synthetic Workbench demo and its local CLI/A2A/MCP
path. This is not a production security assessment.

## Assets

- Integrity of the fixed synthetic fixture and computed baseline metrics.
- Integrity of the typed evidence-to-options handoff.
- The review boundary between a report and any future action.
- The repository and local environment, which must not receive secrets or real
  business data.

## Trust boundaries

1. **Caller to CLI:** request text and case IDs are untrusted.
2. **Coordinator to A2A specialists:** loopback HTTP; both sides are local
   processes but messages are still validated.
3. **Evidence Specialist to MCP server:** stdio child process; tool results are
   fixed-fixture evidence.
4. **Report to human:** the report is a decision aid, not an authorization.
5. **Future action boundary:** not implemented; must fail closed.

## Threats and controls

| Threat | Control | Evidence | Residual risk |
| --- | --- | --- | --- |
| Prompt injection in request text | Reject instruction-override, credential, and action-request patterns before analysis | `src/transformation_workbench/security.py:33`, `tests/test_week4_workflow.py` | Pattern matching is not a complete semantic defense |
| Path traversal or arbitrary file selection through a case ID | Accept only short identifier-shaped IDs; reject path separators and traversal | `security.py:90`, `phase2_coordinator.py:610`, `evidence_source.py:476` | A future file-based adapter would need its own allowlist |
| Caller supplies an arbitrary server command or path | MCP child uses a fixed module entry point; no caller-supplied command or path | `src/transformation_workbench/a2a/evidence_source.py:96` | The child still runs with the invoking user's OS permissions |
| Fixture or evidence tampering | Recompute from the packaged fixture and compare metrics, exceptions, case observations, and context hash | `src/transformation_workbench/a2a/validation.py` | Local files remain writable by the invoking user |
| Fabricated savings, ROI, or implementation claims | Reject unsupported claim terms; label proposals as proposals | `src/transformation_workbench/a2a/claims.py` | A human can still read qualified text incorrectly |
| Request-ID or case-set confusion | Correlate IDs and require exact case-set matches | `phase2_coordinator.py`, `tests/test_phase2_coordinator.py` | A same-user replay can reuse a cache entry by design |
| Approval bypass | Stable reference required; terminal states; action method always raises | `src/transformation_workbench/approval.py:58-151` | The checkpoint is not identity-bound or a real authorization system |
| Malformed or failed specialist result | Bounded errors; no unvalidated fallback artifact | `phase2_coordinator.py`, `tests/test_week3_acceptance.py` | Denial of service by a local process is out of scope |
| Non-loopback or proxied A2A traffic | Require loopback root URLs; clients use `trust_env=False` | `src/transformation_workbench/a2a/boundary.py` | A local process can still connect to loopback ports |
| Secret or real-data leakage into evidence/logs | No credential or business-data environment reads; only a non-secret log-level variable is read; synthetic fixture only; selected evidence fields are checked for secret-like markers | `tests/test_week3_acceptance.py`, data policy | Operators can still paste sensitive text into CLI arguments; checks are not a general secret scanner |
| Unbounded resource use | Bounded case count, timeouts, retry cap, and argument validation | `intake.py`, `workflow_cli.py` | No hard CPU/memory sandbox |

## Approval boundary

The demo approval gate is enforceable in code for the behavior it actually has:
no consequential action exists, and the action method fails closed even after an
approved decision. This is deliberately weaker than a production authorization
system. Before adding any write path, define and test:

- action scope and target allowlist;
- reviewer identity and separation of duties;
- durable audit records;
- idempotency and replay protection;
- rollback and incident handling;
- a fail-closed policy for missing or ambiguous approval.

## Out of scope

- Hosted model or gateway security.
- Multi-tenant isolation.
- Supply-chain attestation.
- OS-level sandboxing or container isolation.
- Network attack simulation.
- Real business data, credentials, or production systems.
