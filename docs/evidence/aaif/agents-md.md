# AAIF evidence card: AGENTS.md

**Status: GUIDANCE INTEGRATED; compliance evidence PARTIAL.** The repository
contains enforceable working rules; no separate recorded coding-agent compliance
run was found.

## Problem addressed

A repository needs a clear, tool-agnostic contract for data policy, approval,
prohibited actions, and working conventions so different agents do not invent
their own boundaries.

## Official source and version

- Format: <https://agents.md/>
- Repository guidance: `AGENTS.md`.
- Additional host instructions: `opencode.json` is local-only and not committed.

## What was actually run or built

The repository guidance defines synthetic-data-only rules, explicit human
approval for consequential actions, no arbitrary shell tools, bounded MCP
surfaces, no secrets, and no unapproved installs or commits. It also names the
local Python and test conventions. The current review followed those rules by
keeping changes local, adding tests, and using the repository review process.

## One observed limitation

No standalone transcript demonstrates a coding agent reading `AGENTS.md` and
then changing a decision because of it. Compliance in this review is inferred
from the working state, not from an independent compliance trace. Do not claim a
measured coding-agent adherence result.

## Fit to Transformation Workbench

**Fit.** The file is the operating contract for the demo and for future agent
hosts. The missing piece is a recorded compliance check, not a new integration.

## Evidence links

- `AGENTS.md`
- `README.md`
- `docs/product/threat-model.md`
- `docs/product/review-findings.md`
