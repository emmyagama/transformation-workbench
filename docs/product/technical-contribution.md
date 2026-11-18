# Contribution 4: bounded, evidence-linked process diagnosis

**Status: reviewed technical contribution.** This document is part of the
repository merge. No separate external publication URL is claimed.

## Problem

Process diagnosis often separates a confident recommendation from the evidence
and data-quality gaps behind it. This contribution describes a small system that
keeps the chain visible:

- validate a synthetic intake request;
- read fixed evidence through read-only MCP tools;
- pass typed evidence to a local solution designer over A2A;
- render a deterministic report with provenance;
- stop at a review checkpoint that cannot execute an action.

## What is implemented

- A local MCP server with three bounded read-only tools and a fixed fixture.
- A local A2A workflow with two specialists and typed handoffs.
- Intake and case-ID validation, prompt-injection checks, fixture
  reconciliation, and unsupported-claim guards.
- A deterministic markdown/JSON report with evidence appendix and protocol trace.
- A demo approval state machine that fails closed; no write path exists.
- 249 automated tests at the current local review snapshot.

## What is intentionally not implemented

- Real business data, external systems, deployment, or production auth.
- Hosted model operation in the Workbench path.
- Write, ticket, email, browser, shell, or action tools.
- Identity-bound approval, durable audit, or a production write gate.
- Gateway, sandbox, environment-host, or router integrations.

## Evidence

- [Architecture](architecture.md)
- [Evaluation](evaluation.md)
- [Threat model](threat-model.md)
- [End-to-end sample report](../evidence/end-to-end-sample-report.md)
- [AAIF evidence-card index](../evidence/aaif/README.md)
- [Independent review findings](review-findings.md)

## Publication checklist

- Re-run the full local suite and `pip check` on the intended commit.
- Confirm the sample report and links resolve on the public branch.
- Keep blocked spike cards labeled blocked; do not claim 10/10 hands-on.
- Remove internal scheduling language from the public surface.
- Treat this repository merge as the publication event; obtain separate approval
  before submitting the material elsewhere.
