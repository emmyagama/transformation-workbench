# Spike evidence: agentgateway

**Status: DEFERRED BY OWNER (2026-11-18) — documentation inspected; no hands-on run.**
Inspected 2026-11-18. This is a truthful deferral and blocker record, not an evaluation result.

## Why it was considered

agentgateway is an open-source gateway for service, LLM, MCP, and A2A traffic.
It could test a narrow boundary: expose one read-only Workbench MCP tool through
a gateway and confirm the tool remains bounded.

## Official sources inspected

- Quickstart: <https://agentgateway.dev/docs/standalone/latest/documentation/quickstart>
- MCP quickstart: <https://agentgateway.dev/docs/standalone/latest/documentation/mcp>
- Repository: <https://github.com/agentgateway/agentgateway>
- The older `agentgateway-agentgateway.mintlify.app/quickstart` URL returned
  HTTP 404 during this review; it was not used.

## Environment probe

```powershell
Get-Command agentgateway, cargo, docker, podman -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -c "import importlib.util; print(importlib.util.find_spec('agentgateway'))"
```

```text
agentgateway=not_found
cargo=not_found
docker=not_found
podman=not_found
node=v24.16.0
npx=11.13.0
```

The official quickstart needs a pre-built agentgateway binary or a build from
source with Rust/Cargo; the Docker alternative needs Docker. Downloading the
install script, a release binary, a container image, or a package would be a
network write and installation, which the working agreement requires explicit
human approval for.

## What was actually done

- Read the official quickstart and MCP documentation.
- Probed for the required executable and container runtime.
- Recorded the deferral and blocker without downloading, installing, or running anything.

## Fit assessment

**Not demonstrated.** The docs suggest a plausible read-only MCP proxy trial, but
this review produced no gateway run, tool-list observation, latency result, or
security finding. Do not describe agentgateway as integrated, evaluated, or
recommended.

## What a later hands-on pass would require

With explicit approval and a disposable environment:

1. Install a pinned agentgateway binary or approved image.
2. Start only loopback listeners.
3. Point one route at the local Workbench MCP child.
4. List tools and confirm the read-only surface.
5. Test an unknown tool name and an attempted write path.
6. Record versions, commands, output, and cleanup.

## Boundary

No real data, secrets, hosted model call, external endpoint, or production
traffic was used.
