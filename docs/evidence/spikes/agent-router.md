# Spike evidence: Agent Router

**Status: DEFERRED BY OWNER (2026-11-18) — documentation inspected; no hands-on run.**
Inspected 2026-11-18. This is a truthful deferral and blocker record, not an evaluation result.

## Correct project identity

Agent Router is `theagentrouter/agent-router`, formerly **Envoy AI Gateway**,
and an Agentic AI Foundation project. It is not the separate product
“AgentRoute”. The repository, CLI (`aigw`), CRDs, and API group remain stable
through the rename.

Official sources:

- Repository: <https://github.com/theagentrouter/agent-router>
- Documentation: <https://theagentrouter.ai/docs/>
- Rename announcement:
  <https://aaif.io/blog/agent-router-joins-aaif>

## Why it was considered

Agent Router could test a platform boundary for model/tool routing: one
OpenAI-compatible entry point and MCP routing with credentials, quotas, and
failover outside application code. For this demo, the useful question is narrow:
can a router expose only the read-only Workbench tool surface?

## Environment probe

```powershell
Get-Command agent-router, agentrouter, aigw, docker, podman -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -c "import importlib.util; print(importlib.util.find_spec('agent_router'))"
```

```text
agent-router=not_found
agentrouter=not_found
aigw=not_found
docker=not_found
podman=not_found
go=go1.26.4 windows/amd64
node=v24.16.0
```

The standalone quickstart is:

```text
OPENAI_API_KEY=sk-... aigw run
```

That requires the `aigw` binary and a hosted provider key. A local build or
container path would require source/network access, Go build tooling, Docker, or
an installation. None was authorized for this review.

## What was actually done

- Checked the official repository and docs, including the rename notice.
- Confirmed the current project identity and CLI name.
- Probed for `aigw` and container runtimes.
- Did not install, build, or run the product.

## Fit assessment

**Not demonstrated.** Agent Router is relevant to platform-level routing and
credential separation, but this review has no run, no MCP route, no tool-list
observation, and no policy test. Do not claim an integration or a security
result.

## What a later hands-on pass would require

With explicit approval and a disposable environment:

1. Install a pinned `aigw` release or approved image.
2. Run a loopback-only standalone instance with a non-production provider or a
   local fake.
3. Route one MCP server and list its tools.
4. Verify that only the intended read-only tool appears.
5. Test an unknown tool and a denied action.
6. Record the configuration, versions, output, and cleanup.

## Boundary

No hosted model call, API key, real data, external endpoint, or production
traffic was used.
