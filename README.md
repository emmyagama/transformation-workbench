# Transformation Workbench

Portfolio demo for AI automation and transformation roles. The workbench uses
synthetic business-process data to calculate baseline KPIs deterministically in
Python and exposes a bounded set of read-only tools through an MCP server.
Consequential write actions are not implemented. Approval controls for future
consequential actions are planned, not implemented.

## Status

Week 1 baseline is implemented: deterministic KPI calculations over a packaged
synthetic fixture and read-only MCP tools. A2A exchange and approval controls for
future consequential actions remain planned.

## Scope

- Deterministic baseline KPI calculations over synthetic data
- Bounded MCP tools with no arbitrary shell access
- Planned human-in-the-loop approval for consequential actions
- A later, real A2A task-exchange demonstration
- Clear separation between demonstrated behavior and planned behavior

## Safety and data policy

- Synthetic data only. Never use real business, customer, or personal data.
- Never commit secrets, credentials, or environment files.
- Current MCP tools are read-only by implementation. The OpenCode configuration
  itself does not enforce read-only behavior.
- Add enforceable human-approval controls before any future consequential write
  or action.
- Do not claim capabilities that the demo does not actually demonstrate.

See `AGENTS.md` for the full working agreement.

## Layout

```text
src/transformation_workbench/       Python package
src/transformation_workbench/data/  Packaged synthetic fixture
tests/                              Automated tests
opencode.json                       Optional local-only MCP config; not committed
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
