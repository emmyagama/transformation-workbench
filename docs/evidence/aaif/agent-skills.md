# AAIF evidence card: Agent Skills

**Status: INTEGRATED / DEEP.** Two project skills were exercised in Goose
sessions; Python tests alone do not prove skill loading.

## Problem addressed

A reusable procedure keeps evidence retrieval and executive briefing consistent
without putting every instruction in the host prompt.

## Official source and version

- Format: <https://agentskills.io/>
- Project skills:
  `.agents/skills/process-diagnostic/SKILL.md` and
  `.agents/skills/executive-brief/SKILL.md`.
- Runtime evidence: Goose 1.59.0 sanitized exports from 2026-11-15.

## What was actually run or built

The `process-diagnostic` skill covers read-only metric retrieval, exception
review, case inspection, and bounded failures. The `executive-brief` skill
converts verified findings into a decision brief with explicit assumptions and
no unsupported savings claims. The owner-held sanitized exports show
`load_skill` calls for both skills where required; those exports are not checked
into this repository.

## One observed limitation

The Python test suite validates the scripts and MCP boundary, not the Goose skill
loader. Skill-loading evidence comes from the sanitized exports, and those
exports do not capture provider/model or latency.

## Fit to Transformation Workbench

**Fit.** The skills keep the diagnosis procedure reusable and separate measured
facts from recommendations. They do not add action capability.

## Evidence links

- `.agents/skills/process-diagnostic/SKILL.md`
- `.agents/skills/executive-brief/SKILL.md`
- `docs/archive/goose-session-excerpt.md`
- `docs/evidence/goose-summary-evaluation-20261115.json`
