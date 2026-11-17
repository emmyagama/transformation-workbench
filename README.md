# Transformation Workbench

Portfolio demo for AI automation and transformation roles. The workbench uses
synthetic business-process data to calculate baseline KPIs deterministically in
Python and exposes a bounded set of read-only tools through an MCP server.
Consequential write actions are not implemented. Approval controls for future
consequential actions are planned, not implemented.

## Status

Week 1 baseline is implemented: deterministic KPI calculations over a packaged
synthetic fixture and read-only MCP tools. Week 2 adds a goose custom agent, two
project skills, and a repeatable diagnosis workflow. Ten sanitized Goose exports
captured on 2026-11-15 show Summon loading the agent, both skills loading where
required, matching baselines across two runs, and safe handling of the duplicate,
unknown-lookup, contradictory-claim, and action-request scenarios. The
`workbench://process-context` read path was unavailable in those sessions, and
provider/model and latency metadata were not captured.

Week 3 implements two local A2A phases over loopback only: a real card-discovery
and task round trip, then an Evidence Specialist and Solution Designer with
typed handoffs, bounded failures, request-ID correlation, and claim guards.
A Goose-facing coordinator MCP gate exposes only `run_a2a_diagnosis`; Goose
loads the project agent through Summon and the coordinator performs both A2A
exchanges. The local A2A specialist exchanges use no hosted model, API key,
cloud endpoint, or business action. Earlier owner-reported hosted Goose
coordinator sessions also succeeded, including a diagnostic run and a
wording-repeat; only the Goose inference was hosted, while the A2A specialist
exchanges remained local. No new hosted Goose coordinator run occurred during
the latest closeout verification, and no checked-in sanitized trace of those
earlier sessions was found. Human approval controls for future consequential actions
remain planned. The deterministic report is the authoritative user-facing
output; the local 3B model's free-form prose remains unreliable and is not
counted as a pass.

## Scope

- Deterministic baseline KPI calculations over synthetic data
- Bounded MCP tools with no arbitrary shell access
- Planned human-in-the-loop approval for consequential actions
- Local A2A card discovery, task exchange, and typed specialist handoffs
- Clear separation between demonstrated behavior and planned behavior

## Safety and data policy

- Synthetic data only. Never use real business, customer, or personal data.
- Never commit secrets, credentials, or environment files.
- OpenCode is one host application; Goose is the agent host used by the Week 2
  and Week 3 workflows. Their MCP client components launch the local server.
  Current MCP tools are read-only by implementation in the server. Neither host
  nor `opencode.json` enforces read-only behavior.
- Add enforceable human-approval controls before any future consequential write
  or action.
- Do not claim capabilities that the demo does not actually demonstrate.

See `AGENTS.md` for the full working agreement.

## Layout

```text
.agents/agents/                    Project-scoped Goose agents
.agents/skills/                    Project-scoped Agent Skills
src/transformation_workbench/      Python package
src/transformation_workbench/data/ Packaged synthetic fixture
tests/                             Automated tests
scripts/                           Local validation harnesses
docs/workflows/                    Repeatable workflows
docs/demos/                        Demo and evaluation documentation
docs/evidence/                     Sanitized evaluation evidence
opencode.json                      Optional local-only MCP config; not committed
```

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,openresponses]"
.\.venv\Scripts\python.exe -m pytest
```

See the [MCP baseline tutorial](docs/tutorials/mcp-business-process-baseline.md)
for Windows and macOS/Linux setup, OpenCode configuration, tool examples, and
the synthetic-data boundary.

## Week 2 Goose workflow

The project-scoped `transformation-analyst` agent uses `AGENTS.md`, the
`process-diagnostic` and `executive-brief` skills, and only the read-only
Transformation Workbench MCP extension.

- [Repeatable diagnosis workflow](docs/workflows/week2-transformation-diagnostic.md)
- [Demo and evaluation](docs/demos/week2-demo-and-evaluation.md)

The workflow keeps measured facts separate from recommendations and makes no
business-system writes. Provider credentials belong outside the repository.
Goose 1.59.0 has no `--agent` CLI flag; the workflow explicitly enables the
Summon platform extension so the project agent can be loaded with
`--no-profile`. The Python tests do not prove that the agent or skills were
loaded; the sanitized runtime exports provide that evidence. Provider/model and
latency metadata and the `workbench://process-context` read path remain
documented gaps.

## Week 3 local A2A

- [Phase 1 protocol slice](docs/week3-phase1-a2a.md)
- [Phase 2 specialists and typed handoffs](docs/week3-phase2-a2a.md)
- [Goose coordinator integration](docs/week3-goose-coordinator.md)
- [Week 3 acceptance evaluation](docs/week3-acceptance-evaluation.md)
- [Technical contribution](docs/week3-technical-contribution.md)
- [Sanitized A2A trace](docs/evidence/week3-a2a-trace-20261115.json)

## Open Responses adapter (optional, separate from A2A)

The optional Workbench-owned adapter under
`src/transformation_workbench/openresponses_adapter/` translates Open Responses
requests and implements adapter-owned AES-256-GCM compaction state. Gate 2 ran
the pinned suite against a local fake upstream. Gate 3 then ran the same pinned
suite once against the local adapter with OpenCode Console upstream: 17 passed,
0 failed, 19 suite operations, and a conservative cumulative total of 50/56.
This is one adapter-plus-Console configuration, not proof that the bare Console
route is conformant, not general Open Responses conformance, and not
provider-native or cross-provider portable compaction. The earlier direct
Console route result (1 pass, 16 fail) remains a separate unchanged failure.

- [Adapter walkthrough and limits](docs/week4-openresponses-local-adapter.md)
- [Gate 3 runbook and evidence](docs/week4-openresponses-gate3-runbook.md)
- [Gate 3 JSON evidence](docs/evidence/week4-openresponses-gate3.json)
