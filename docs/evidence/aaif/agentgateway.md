# AAIF evidence card: agentgateway

**Status: BLOCKED — documentation inspected, no hands-on run.**

## Problem addressed

A gateway could govern MCP and agent traffic with one policy boundary. The
question is whether the Workbench needs that boundary now.

## Official source and version

- Docs: <https://agentgateway.dev/docs/standalone/latest/documentation/quickstart>
- Repository: <https://github.com/agentgateway/agentgateway>
- Inspected: 2026-11-18.

## What was actually run or built

Nothing. The environment probe found no `agentgateway` binary, `cargo`, Docker,
or Podman. The official quickstart needs a pre-built binary, a Rust build, or
Docker. Downloading or installing any of those requires explicit approval.

## One observed limitation

The intended MCP proxy trial could not start. There is no observed tool-list,
policy result, traffic result, or security finding.

## Fit to Transformation Workbench

**Hypothesis only.** A gateway may be useful when the demo crosses a real
network, identity, or multi-team boundary. The current local, single-user demo
does not demonstrate that need.

## Evidence links

- Detailed blocker card: [`../spikes/agentgateway.md`](../spikes/agentgateway.md)
- `docs/product/architecture.md`
