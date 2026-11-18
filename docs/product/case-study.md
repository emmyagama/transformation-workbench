# Case study: making the evidence path visible

**Status: portfolio case study based on synthetic data.** No savings,
productivity, or production-readiness outcome is claimed.

## Situation

A process baseline can look precise while its exclusions, duplicates, and
missing fields are hidden. A recommendation can then sound more certain than the
underlying evidence permits. The demo tests a bounded alternative: make the
evidence path visible and remove action capability from the review path.

## Approach

1. Start with one synthetic service-request intake request.
2. Validate the request and bounded case IDs before analysis.
3. Read fixed metrics, exceptions, and case details through read-only MCP tools.
4. Send typed evidence to a local Solution Designer over A2A.
5. Reconcile the returned evidence with the packaged fixture.
6. Render a deterministic decision brief with an evidence appendix.
7. Pause at a review checkpoint with no write or action endpoint.

## Observed demonstration

For the fixed fixture and request in the sample report:

- 15 input rows;
- 9 measurable closed cases;
- 6 met SLA (66.7%);
- mean cycle time 29.06 hours; median 9 hours;
- 2 rework cases (22.2%) and 3 rework events;
- 2 backlog cases, 1 overdue;
- 4 excluded rows, each with a recorded reason.

These are measurements of a synthetic fixture, not an operating result.

## What the demo shows

- A typed, provenance-linked evidence chain can be rendered deterministically.
- Local A2A specialists can exchange and validate structured work.
- Unsafe input, fixture mismatches, and unsupported claims can fail closed.
- The report can present proposals, risks, assumptions, and limits separately.
- Approval can be a recorded review state without creating an action path.

## What remains unsolved

- No identity-bound approval or durable audit.
- No integration with a governed data source or business system.
- No production deployment, authentication, or write gate.
- No measured cost, latency, savings, or productivity outcome.
- Four AAIF spikes remain blocked because the required tooling or approvals are
  unavailable.

## Decision

Use this as evidence of a working approach to bounded, evidence-linked process
diagnosis. Do not use it as evidence of a financial outcome or production
readiness.
