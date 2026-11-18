# Transformation Workbench business case

**This is a portfolio demonstration, not an investment case.** It contains no
financial forecast, savings commitment, ROI claim, or production-readiness claim.

## Problem framing

Transformation work often begins with a process baseline that is hard to inspect:
metrics come from different places, exclusions are buried, and recommendations
are separated from the evidence that supports them. A decision brief can look
confident while the underlying data is incomplete or unreconciled.

The Workbench tests a narrower proposition: can a small, bounded system produce
a traceable baseline and an evidence-linked set of options, then stop at a human
review point without taking action?

## What the demo shows

- A fixed synthetic service-request process is measured deterministically.
- Every metric and exception carries a tool/resource reference.
- A local Evidence Specialist and Solution Designer exchange typed artifacts.
- The final report separates observed facts, calculations, proposals, risks,
  assumptions, and limitations.
- The default state is a review pause, and no consequential action exists.

## Why the boundary matters

The useful control is not a promise that a model will behave. It is the removal
of action capability from the path plus validation that the evidence matches a
known fixture. In this demo:

- there is no write tool, shell tool, or business-system integration;
- the MCP child has a fixed entry point;
- case IDs are validated and the evidence is reconciled;
- unsupported financial claims are rejected;
- approval is a review state, not an action authorization.

## What would be needed before a real pilot

1. Replace the synthetic fixture with an approved, governed data source.
2. Define the exact decision and the evidence needed to support it.
3. Add identity, authorization, durable audit, and separation of duties.
4. Define an action scope and a fail-closed write gate.
5. Add idempotency, rollback, and incident handling.
6. Agree on evaluation measures and a baseline before claiming an outcome.
7. Re-run the safety and failure tests against the integrated environment.

## Decision requested

Treat this repository as evidence of a working approach to bounded,
evidence-linked process diagnosis. Do not treat it as evidence of savings,
production readiness, or fitness for a real business process.

## Related documents

- [Architecture](architecture.md)
- [Evaluation](evaluation.md)
- [Threat model](threat-model.md)
- [End-to-end demo](../demos/end-to-end-demo.md)
