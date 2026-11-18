# Independent review findings and dispositions

**Review date:** 2026-11-18. **Scope:** the end-to-end demo, approval state,
safety tests, and product/evidence documentation. **Method:**
read-only code and document review, local test run, and targeted reproductions.

## Findings fixed

| Finding | Severity | Disposition |
| --- | --- | --- |
| Failed approval-note validation mutated the gate before raising | High | Fixed: note validation occurs before any state change; approve and decline both have regression tests |
| Newline/control input could inject fake sections into the rendered report | High | Fixed: display fields reject line breaks and controls at intake and approval; the renderer flattens any residual line controls; tests cover headings, fake approval lines, and notes |
| CLI accepted negative retries and raised an uncaught traceback | Medium | Fixed: `--timeout` and `--max-retries` have bounded argument validators and a regression test |
| Demo documented non-existent error codes | Medium | Fixed: the demo now documents the actual `invalid_intake` behavior |
| Documentation claimed credential detection without a credential guard | Medium | Fixed: a credential-material pattern and test were added |
| Documentation overstated environment-read and secret-scanning coverage | Medium | Fixed: docs now name the non-secret log-level variable and narrow the secret-marker claim |
| Gate 3 evidence omitted the dirty working tree and misstated the bare route | Medium | Fixed: README and evidence card now state the uncommitted `17faecf` snapshot and **1 pass, 16 fail** |
| Claim guard rejected legitimate claim-like user goals late | Medium | Fixed: generated-text guard redacts the operator's requested outcome and process label; a regression test covers a goal containing "reduce backlog by 50%" |
| Verbose logging relied on ambient handlers | Low | Fixed: the CLI installs and replaces its own stderr handler and sets the child log level explicitly |
| Blocked projects were labeled "hands-on spike" | Low | Fixed: the AAIF index now says "documentation review / blocked" |
| Owner-held Goose exports were not clearly distinguished from checked-in evidence | Low | Fixed: cards state that the exports are owner-held and not in the repository |
| Public AGENTS.md card linked to an unpublished internal runbook | Medium | Fixed: the card now links only committed public evidence |
| Public-language sweep left dated week/phase framing on public pages | Medium | Fixed: historical records moved under `docs/archive/` with product-oriented titles, and public pages point to current product docs |
| Hosted-model claim did not distinguish the optional adapter run | Medium | Fixed: README and evaluation scope the claim to the Workbench/A2A/MCP path and cross-reference the separate adapter result |
| Public documents contained encoding corruption | Medium | Fixed: mojibake and lost punctuation were replaced with UTF-8 characters, and links were rechecked |
| Timeout help text included a value the validator rejects | Low | Fixed: help and validation now both use 1–120 |
| Report text said “no network” although loopback HTTP/stdio is used | Low | Fixed: report text now says “no external network, write, or business action” |

## Residual limitations

- Approval is a **CLI-asserted review state**, not identity verification. The
  stable reference is deterministic from the request ID, and no durable pending
  state or random token exists.
- The Workbench remains read-only. A future write path would need identity,
  authorization, audit, idempotency, and rollback controls that are not present.
- The four remaining AAIF spikes are still blocked by missing binaries,
  container runtimes, packages, or approval to install.
- The fixture is synthetic and small; no financial, productivity, or
  production-readiness outcome is claimed.

## Verification

- Full local suite: **246 passed**.
- `pip check`: no broken requirements.
- Quiet CLI: exit 0, empty stderr.
- Verbose CLI: protocol/server logs on stderr.
- Approved CLI: `status=approved`, `consequential_action_permitted=False`,
  `decided_by=cli_assertion`.
- Clean clone of commit `d84203e`: **246 passed**, clean `pip check`, and a
  pending CLI JSON demo with empty stderr.
