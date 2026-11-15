# AGENTS.md

Working agreement for contributors and AI agents in this repository.

## Project scope

Transformation Workbench is a portfolio demo for AI automation and
transformation roles. It will:

1. Calculate baseline KPIs from synthetic business-process data using
   deterministic Python.
2. Expose a bounded set of tools through an MCP server.
3. Demonstrate a real A2A task exchange at a later stage.
4. Require human approval before any consequential write or action.

## Data policy

- Use synthetic data only.
- Never add real business, customer, employee, or personal data.
- Never add secrets, credentials, tokens, or populated environment files.
- Keep generated datasets reproducible and clearly labeled as synthetic.

## Human approval gate

- Obtain explicit human approval before any consequential write or action,
  including external side effects, file or data mutation outside the approved
  scope, network writes, and repository commits or pushes.
- The approval workflow must be enforceable in code, not only documented.
- Default to read-only or dry-run behavior when approval is absent or unclear.

## Prohibited actions

- No real business data, secrets, or unsupported claims.
- No arbitrary shell or command-execution tools exposed to agents or models.
- No unbounded MCP tools or unrestricted filesystem access.
- No installing packages, committing, pushing, publishing, or creating remotes
  without explicit human approval.
- No bypassing, weakening, or silently disabling the human approval gate.

## Working conventions

- Use Python 3.11 via `py -3.11` and the local `.venv`.
- Keep changes small, reviewable, and within the requested scope.
- Add tests for new behavior and run them with the project virtual environment.
- Do not modify global Git or Python configuration.
- State assumptions and distinguish implemented behavior from planned behavior.
