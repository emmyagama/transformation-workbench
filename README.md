# Transformation Workbench

A portfolio demonstration of bounded, evidence-linked process diagnosis for AI
automation and transformation roles. The Workbench calculates baseline KPIs from
a fixed synthetic fixture, exposes only read-only tools through MCP, runs a local
A2A evidence-to-options workflow, and renders a deterministic decision brief.

The demo is intentionally read-only. It has no business-system integration, no
write or action endpoint, and no hosted model in the Workbench path. The human
review checkpoint is a real code-enforced state, but it is not a production
authorization system.

## Current status

- End-to-end CLI: synthetic intake -> local A2A specialists -> read-only MCP
  evidence -> deterministic report -> review pause.
- Three bounded MCP tools over the packaged synthetic fixture.
- Local A2A card discovery, task exchange, typed handoffs, validation, and
  bounded failures.
- Intake and case-ID safety checks, fixed-evidence verification, and claim
  guards.
- Demo approval state machine that fails closed; approval does not create an
  action capability.
- Local verification snapshot: **246 passed** and clean `pip check` on
  2026-11-18.
- Not implemented: write actions, real data, deployment, hosted model operation
  in the Workbench/A2A/MCP path, production authentication, or any
  financial/savings claim. The separate optional Open Responses adapter had one
  documented Console validation run, described below.

## Scope

- Deterministic baseline KPI calculations over synthetic data.
- Read-only MCP tools with no arbitrary shell or filesystem surface.
- A local A2A evidence-to-options workflow with typed handoffs.
- A code-enforced review checkpoint before any future consequential action.
- Clear separation between demonstrated behavior, proposals, assumptions, and
  planned work.

## Safety and data policy

- Synthetic data only. Never use real business, customer, employee, or personal
  data.
- Never commit secrets, credentials, or environment files.
- OpenCode is one host application; Goose is the agent host used in the earlier
  agent-host workflows. Their MCP client components launch the local server.
  Current MCP tools are read-only by server implementation. Neither host nor
  `opencode.json` is relied on for read-only enforcement.
- Approval is code-enforced for the demo behavior: no action endpoint exists,
  and the action method raises even after an approved decision. The review
  decision is a CLI assertion, not identity verification.
- Do not claim capabilities that the demo does not actually demonstrate.

See `AGENTS.md` for the full working agreement.

## Layout

```text
.agents/agents/                    Project-scoped Goose agents
.agents/skills/                    Project-scoped Agent Skills
src/transformation_workbench/      Python package
src/transformation_workbench/data/ Packaged synthetic fixture
tests/                             Automated tests
scripts/                           Local validation harnesses
docs/product/                      Architecture, threat model, evaluation, business case
docs/demos/                        Demo scripts and evaluation notes
docs/evidence/                     Sanitized evidence and sample output
docs/evidence/aaif/                One evidence card per AAIF project
docs/workflows/                    Repeatable historical workflows
docs/tutorials/                    Setup and MCP tutorial
opencode.json                      Optional local-only MCP config; not committed
```

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,openresponses]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

See the [MCP baseline tutorial](docs/tutorials/mcp-business-process-baseline.md)
for Windows and macOS/Linux setup, OpenCode configuration, tool examples, and
the synthetic-data boundary.

## Run the demo

```powershell
.\.venv\Scripts\python.exe -m transformation_workbench `
  --request-id demo-review-001 `
  --desired-outcome "Review the synthetic service-request intake and decide which evidence to inspect next." `
  --case-id C-009 --case-id C-006 --case-id C-014 `
  --format markdown
```

- [End-to-end demo script](docs/demos/end-to-end-demo.md)
- [Sanitized sample report](docs/evidence/end-to-end-sample-report.md)
- [Architecture](docs/product/architecture.md)
- [Evaluation](docs/product/evaluation.md)
- [Threat model](docs/product/threat-model.md)
- [Business case](docs/product/business-case.md)
- [Contribution 4: bounded, evidence-linked process diagnosis](docs/product/technical-contribution.md)
- [Case study](docs/product/case-study.md)
- [Independent review findings](docs/product/review-findings.md)

The CLI prints a clean report by default. Use `--verbose` to keep protocol and
server logs on stderr. `--format json` returns the structured report.

## Capability areas

### Read-only MCP evidence

The local MCP server exposes `calculate_baseline_metrics`,
`list_case_exceptions`, and `get_case_details` over the fixed synthetic fixture,
plus the `workbench://process-context` resource. Every measured fact carries
tool/resource provenance.

### Agent-host workflow

The project agent uses `AGENTS.md`, the `process-diagnostic` and
`executive-brief` skills, and only the read-only Workbench MCP extension. Earlier
agent-host evidence is preserved separately, including its recorded gaps:
`workbench://process-context` was unavailable in the captured sessions, and
provider/model and latency metadata were not captured.

- [Contribution 4](docs/product/technical-contribution.md)
- [Case study](docs/product/case-study.md)

### Local A2A collaboration

The coordinator discovers two local A2A specialists and validates typed
artifacts before rendering. The exchange is loopback-only. Earlier hosted Goose
coordinator sessions are owner-reported, not independently traced, and no new
hosted run is part of this snapshot.

- [A2A protocol slice](docs/archive/a2a-protocol-slice.md)
- [Typed specialists and handoffs](docs/archive/a2a-specialists.md)
- [Acceptance evaluation](docs/archive/a2a-acceptance-evaluation.md)
- [A2A evidence card](docs/evidence/aaif/a2a.md)

### Open Responses adapter (optional)

The optional adapter implements adapter-owned AES-256-GCM compaction state. The
pinned suite passed 17/17 against the local adapter with OpenCode Console
upstream in one run, with 19 operations and a conservative cumulative total of
50/56. Gate 3 ran from an uncommitted working tree at `17faecf`, not from a
clean committed revision. The separate bare Console route recorded **1 pass,
16 fail**. This is not general Open Responses conformance and not
provider-native or portable compaction.

- [Adapter walkthrough and limits](docs/archive/openresponses-adapter.md)
- [Gate 3 runbook and evidence](docs/archive/openresponses-gate3-runbook.md)

### AAIF project coverage

- [Evidence-card index](docs/evidence/aaif/README.md)

Five projects have integrated evidence with limitations recorded, Open Responses
has a bounded hands-on result, and four spikes are explicitly blocked because the
required binaries, container runtime, packages, or approvals were unavailable.
The index does **not** claim 10/10 hands-on coverage.

## Dated technical records

These records are retained for provenance and should be read as dated
evidence, not as current product claims.

- [Local A2A technical contribution](docs/archive/a2a-technical-contribution.md)
- [Local A2A acceptance evaluation](docs/archive/a2a-acceptance-evaluation.md)
- [Open Responses adapter record](docs/archive/openresponses-adapter.md)
