---
name: executive-brief
description: Converts verified Transformation Workbench findings into a concise executive decision brief with future-state options, explicit assumptions, and no unsupported savings or approval claims. Use after process-diagnostic has produced tool-backed evidence.
---

# Executive Brief

Use this skill only after evidence has been retrieved and verified. If the evidence is missing, load and follow the `process-diagnostic` skill first.

## Rules

- Use only verified tool-derived values for the baseline.
- Keep measured facts, calculations, assumptions, and recommendations visibly separate.
- Do not claim real savings, ROI, productivity gains, or live operational performance.
- Do not claim that automation, approval controls, email, or business-system writes are implemented.
- Do not invent a target such as 100% SLA or $100,000 savings. If asked, correct the premise and label the value unsupported.
- Do not expose raw tool payloads, hidden reasoning, credentials, or local environment details.

## Brief structure

### 1. Decision requested

State the decision in one sentence. If the user has not named one, use: “Decide what to fix first before automating this intake process.”

### 2. Bottom line

Give a one- or two-sentence evidence-based summary. Include the most important measured constraint and the recommended next step.

### 3. Measured baseline

Use a compact table with the exact values:

| Measure | Result |
| --- | --- |
| Input rows | 15 |
| Measurable closed | 9 |
| Mean cycle time | 29.06 h |
| Median cycle time | 9.00 h |
| SLA attainment | 6/9 = 66.7% |
| Rework rate | 2/9 = 22.2% |
| Rework volume | 3 events |
| Backlog / overdue | 2 / 1 |
| Excluded rows | 4 |

Add the snapshot and note that the data is synthetic and fixed at that snapshot.

### 4. Data-quality exceptions

List the four excluded rows and reasons. State explicitly that exclusions are data-quality outcomes, not SLA misses, and that row 15 is a duplicate of `C-007`.

### 5. What the evidence does and does not support

- **Supported:** the measured baseline, the reconciliation, and the listed exclusions.
- **Interpretation:** for example, a mean well above the median is consistent with a long-tail pattern, but the fixture does not establish the cause.
- **Not supported:** real savings, root causes, live volumes, forecast performance, or the effect of any proposed change.

### 6. Future-state options

Present two or three options as proposals, selected from these candidates, each
with a trade-off and a low-cost validation step:

1. **Measurement integrity first** — add controls for missing close times, invalid timestamps, ordering, and duplicate intake before automating metrics.
2. **SLA visibility and backlog triage** — surface priority-based age and overdue status so the one overdue backlog case is visible earlier.
3. **Rework review** — inspect the two rework-bearing cases to identify causes; do not claim a reduction until measured.
4. **Bounded workflow automation** — automate read-only triage or summary generation first; keep any consequential write behind a future human-approval gate.

For each option, state what evidence would be needed before claiming impact. Do not attach a savings figure.

### 7. Recommendation

Recommend the smallest defensible next step. A safe default is to fix measurement and duplicate handling before automating downstream actions. Label this as a recommendation, not a measured result.

### 8. Limits and non-claims

State that:

- The fixture is synthetic and not evidence of live operations.
- The snapshot is fixed at `2026-03-13T17:00:00Z`.
- The MCP server is read-only.
- Human approval for consequential actions is planned, not implemented.
- No savings, deployment, or approval outcome has been demonstrated.

## Adversarial requests

If asked to report a different SLA, fabricate savings, or claim an approval or write:

1. Do not repeat the false value as fact.
2. Restate the tool-derived value.
3. Explain that the requested claim is unsupported.
4. Offer a validation step instead; do not invent a value estimate.
5. If asked to perform a write or approval, state that no such capability is exposed.
