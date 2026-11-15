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
provider/model and latency metadata were not captured. A2A exchange and approval
controls for future consequential actions remain planned.

## Scope

- Deterministic baseline KPI calculations over synthetic data
- Bounded MCP tools with no arbitrary shell access
- Planned human-in-the-loop approval for consequential actions
- A later, real A2A task-exchange demonstration
- Clear separation between demonstrated behavior and planned behavior

## Safety and data policy

- Synthetic data only. Never use real business, customer, or personal data.
- Never commit secrets, credentials, or environment files.
- OpenCode is the host application; its built-in MCP client component launches
  the local server. Current MCP tools are read-only by implementation in the
  server. Neither the OpenCode host nor `opencode.json` enforces read-only
  behavior.
- Add enforceable human-approval controls before any future consequential write
  or action.
- Do not claim capabilities that the demo does not actually demonstrate.

See `AGENTS.md` for the full working agreement.

## Layout

```text
.agents/agents/                    Project-scoped goose agent
.agents/skills/                    Project-scoped Agent Skills
src/transformation_workbench/      Python package
src/transformation_workbench/data/ Packaged synthetic fixture
tests/                             Automated tests
docs/workflows/                    Repeatable workflows
docs/demos/                        Demo and evaluation documentation
opencode.json                      Optional local-only MCP config; not committed
```

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
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
