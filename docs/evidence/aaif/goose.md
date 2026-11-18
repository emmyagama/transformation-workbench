# AAIF evidence card: goose

**Status: INTEGRATED / DEEP.** Runtime evidence exists for local and
owner-reported hosted sessions; provenance differs.

## Problem addressed

A user needs a governed agent host that can load project instructions, reusable
skills, and only the read-only Workbench MCP extension.

## Official source and version

- Project: <https://block.github.io/goose/>
- Version exercised: Goose 1.59.0.
- Local model path: Ollama 0.40.16 with `llama3.2:3b`.

## What was actually run or built

The project agent `transformation-analyst` was loaded through Summon
`load(source: "transformation-analyst")`. The delegated sessions show
`load_skill` for `process-diagnostic` and, where requested, `executive-brief`.
Ten sanitized Markdown exports from 2026-11-15 were reviewed by the owner; they
are owner-held external evidence and are not checked into this repository.
Hosted Goose diagnostic and wording-repeat sessions are owner-reported; only
Goose inference was hosted, while the A2A specialist exchanges remained local.

## One observed limitation

The sanitized exports do not identify provider/model or latency, and no export
shows a resource read of `workbench://process-context`. The local 3B model's
free-form prose was unreliable, so the deterministic report is authoritative.

## Fit to Transformation Workbench

**Fit, with limits.** Goose provides a realistic agent-host boundary and shows
project-agent and skill loading. It is not a production control plane, and the
hosted outcomes remain owner-reported because no sanitized trace was checked in.

## Evidence links

- `docs/archive/goose-coordinator.md`
- `docs/evidence/goose-session-excerpt.md`
- `docs/evidence/goose-summary-evaluation-20261115.json`
- `.agents/agents/transformation-analyst.md`
