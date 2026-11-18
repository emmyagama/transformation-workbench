# AAIF evidence card: OpenSandbox

**Status: DEFERRED BY OWNER (2026-11-18) — documentation inspected; no hands-on run.**

## Problem addressed

A future write-capable tool would need process, filesystem, network, and
credential isolation rather than running with the host user's full access.

## Official source and version

- Repository: <https://github.com/opensandbox-group/OpenSandbox>
- Inspected example:
  <https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/examples/aks-kata.md>
- Inspected: 2026-11-18.

## What was actually run or built

Nothing. The example requires an AKS cluster with Kata isolation, Helm,
`kubectl`, Python packages, container images, and an LLM endpoint. The probe
found no `opensandbox` package, Docker, or Podman. No cloud resource, package
install, or hosted call was authorized.

## One observed limitation

No isolation boundary was observed. There is no result for process, filesystem,
network, or credential behavior.

## Fit to Transformation Workbench

**Future-fit only.** The current demo is read-only and has no code-execution
tool to isolate. OpenSandbox becomes relevant only if a write or arbitrary
execution path is proposed; that path is currently prohibited.

## Evidence links

- Detailed deferral and blocker card: [`../spikes/opensandbox.md`](../spikes/opensandbox.md)
- `docs/product/threat-model.md`
