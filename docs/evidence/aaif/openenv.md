# AAIF evidence card: OpenEnv

**Status: DEFERRED BY OWNER (2026-11-18) — documentation inspected; no hands-on run.**

## Problem addressed

A repeatable environment abstraction could make agent tasks explicit through
`reset()`/`step()` observations and rewards. The question is whether it improves
this workflow.

## Official source and version

- Repository: <https://github.com/openenv/OpenEnv>
- Docs: <https://huggingface.co/docs/openenv>
- Inspected: 2026-11-18.

## What was actually run or built

Nothing. The official quickstart requires `pip install openenv` plus an
environment client, then a local Docker-backed environment or a remote Space.
The probe found no `openenv` package, Docker, or Podman. No install, container
run, remote Space call, or model call was authorized.

## One observed limitation

No `reset()`/`step()` interaction was observed. There is no evidence about the
environment/task abstraction, isolation, or fit.

## Fit to Transformation Workbench

**Out of scope for the current demo.** The Workbench is a deterministic
read-only diagnosis, not a training or action environment. OpenEnv would become
relevant if the project added an explicit, testable action loop; it currently
does not.

## Evidence links

- Detailed deferral and blocker card: [`../spikes/openenv.md`](../spikes/openenv.md)
- `docs/product/architecture.md`
