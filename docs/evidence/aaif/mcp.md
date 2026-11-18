# AAIF evidence card: Model Context Protocol (MCP)

**Status: INTEGRATED / DEEP.** Evidence is local and synthetic.

## Problem addressed

Agents need bounded access to business-process facts without receiving arbitrary
shell or filesystem capability.

## Official source and version

- Specification: <https://modelcontextprotocol.io/>
- Python SDK used: `mcp` 2.3.0.
- Local implementation: `src/transformation_workbench/mcp_server.py`.

## What was actually run or built

A local stdio MCP server exposes exactly three read-only tools:

- `calculate_baseline_metrics`
- `list_case_exceptions`
- `get_case_details`

The resource `workbench://process-context` provides the fixed process context.
The A2A Evidence Specialist calls the tools through the SDK; tests and the CLI
exercise the same local path.

## One observed limitation

Read-only annotations are hints, not enforcement by the host. This demo enforces
read-only behavior in the server implementation and by exposing no write tool.
The MCP child still runs with the invoking user's OS permissions.

## Fit to Transformation Workbench

**Fit.** MCP is the evidence boundary for the Workbench: fixed tools, fixed
fixture, provenance on every measured fact, and no arbitrary command surface.

## Evidence links

- `src/transformation_workbench/mcp_server.py`
- `docs/tutorials/mcp-business-process-baseline.md`
- `tests/test_mcp_server.py`
- `tests/test_week3_acceptance.py`
