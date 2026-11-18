# AGENTS.md

Working agreement for contributors and AI agents in this repository.

## Project scope

Transformation Workbench is a portfolio demo for AI automation and
transformation roles. It currently:

1. Calculates baseline KPIs from synthetic business-process data using
   deterministic Python.
2. Exposes a bounded set of read-only tools through an MCP server.
3. Demonstrates a real local A2A task exchange and typed handoffs.
4. Pauses at an enforceable demonstration approval checkpoint before any future
   consequential action.

It does not implement a write, business-action, deployment, or production
authorization path.

## Data policy

- Use synthetic data only.
- Never add real business, customer, employee, or personal data.
- Never add secrets, credentials, tokens, or populated environment files.
- Keep generated datasets reproducible and clearly labeled as synthetic.

## Human approval gate

- Obtain explicit human approval before any consequential write or action,
  including external side effects, file or data mutation outside the approved
  scope, network writes, and repository commits or pushes.
- The approval workflow must be enforceable in code, not only documented. The
  demo gate is implemented in `src/transformation_workbench/approval.py`; it
  records review state and has no action capability.
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
