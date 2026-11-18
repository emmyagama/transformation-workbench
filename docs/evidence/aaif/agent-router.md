# AAIF evidence card: Agent Router

**Status: DEFERRED BY OWNER (2026-11-18) — documentation inspected; no hands-on run.**

## Problem addressed

A platform router could centralize model and MCP access, credentials, quotas,
and failover. The question is whether the Workbench needs that platform boundary.

## Official source and version

- Repository: <https://github.com/theagentrouter/agent-router>
- Docs: <https://theagentrouter.ai/docs/>
- Project identity: formerly Envoy AI Gateway; CLI remains `aigw`.
- Inspected: 2026-11-18.

## What was actually run or built

Nothing. The probe found no `aigw`, Docker, or Podman. The official standalone
quickstart is `OPENAI_API_KEY=sk-... aigw run`, which would require a binary and
a hosted provider key. No install, build, or hosted call was authorized.

## One observed limitation

No comparison with agentgateway was possible because neither product ran. A
feature-list comparison would not satisfy the spike requirement.

## Fit to Transformation Workbench

**Hypothesis only.** Agent Router is relevant to multi-team model/tool routing
and credential separation. The local demo has no multi-tenant or provider
routing requirement to evaluate.

## Evidence links

- Detailed deferral and blocker card: [`../spikes/agent-router.md`](../spikes/agent-router.md)
- Rename announcement: <https://aaif.io/blog/agent-router-joins-aaif>
- `docs/product/architecture.md`
