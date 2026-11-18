# AAIF evidence card: Agent2Agent (A2A)

**Status: INTEGRATED / DEEP.** Local loopback exchanges are verified by a
checked-in trace and tests.

## Problem addressed

Two specialists need to exchange typed work over a protocol boundary instead of
sharing process memory or free-form model text.

## Official source and version

- Protocol: <https://a2a-protocol.org/>
- SDK: `a2a-sdk[http-server]` 1.3.0.
- Implementation: `src/transformation_workbench/a2a/`.

## What was actually run or built

The coordinator discovers two Agent Cards over loopback HTTP, sends JSON-RPC
tasks, and validates typed `EvidencePack` and `SolutionOptions` artifacts. The
Evidence Specialist crosses a second boundary back to the read-only MCP server.
A checked-in sanitized trace records both card discoveries, both task sends,
task/context IDs, completed states, request IDs, and evidence-linked options.
Failure tests cover timeout, unavailable specialist, task failure, malformed
artifacts, request mismatch, case-set mismatch, fixture tampering, and replay.

## One observed limitation

The verification is local and loopback-only. It does not prove hosted A2A,
authenticated agents, network partitions, streaming, cancellation, or remote
attestation. Earlier hosted Goose coordinator sessions are owner-reported, not
independently traced.

## Fit to Transformation Workbench

**Fit.** A2A is the collaboration boundary between evidence collection and
solution design. It keeps the roles separate and makes failure states visible.

## Evidence links

- `docs/evidence/a2a-trace-20261115.json`
- `docs/archive/a2a-protocol-slice.md`
- `docs/archive/a2a-specialists.md`
- `docs/archive/a2a-acceptance-evaluation.md`
- `tests/test_a2a_integration.py`
- `tests/test_week3_acceptance.py`
