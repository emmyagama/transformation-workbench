# AAIF evidence cards

One card per current AAIF project. Status is explicit: integrated evidence,
hands-on spike, partial, or blocked.

| Project | Depth | Status | Card |
| --- | --- | --- | --- |
| Model Context Protocol (MCP) | Integrated / deep | Evidence present | [MCP](mcp.md) |
| goose | Integrated / deep | Evidence present; hosted runs owner-reported | [goose](goose.md) |
| Agent Skills | Integrated / deep | Runtime evidence present | [Agent Skills](agent-skills.md) |
| AGENTS.md | Integrated / deep | Guidance present; compliance evidence partial | [AGENTS.md](agents-md.md) |
| Agent2Agent (A2A) | Integrated / deep | Local trace and tests present | [A2A](a2a.md) |
| Open Responses | Hands-on spike | Adapter + Console passed; bare Console 1 pass, 16 fail | [Open Responses](open-responses.md) |
| agentgateway | Documentation review / blocked | Blocked; no binary/runtime/install approval | [agentgateway](agentgateway.md) |
| Agent Router | Documentation review / blocked | Blocked; no `aigw`/runtime/install approval | [Agent Router](agent-router.md) |
| OpenSandbox | Documentation review / blocked | Blocked; no cluster/container/package | [OpenSandbox](opensandbox.md) |
| OpenEnv | Documentation review / blocked | Blocked; no package/container/Space approval | [OpenEnv](openenv.md) |

## Honest coverage statement

This is **not a claim of 10/10 hands-on coverage**. Five projects have integrated
evidence with limitations recorded. Open Responses has a completed, bounded
adapter + Console spike with a separate bare-route failure. The four remaining
spikes are **blocked**, and their cards record the exact environment probes and
the approval needed to proceed. No blocked card claims a successful run.

Detailed blocker cards for the four spikes are under [`../spikes/`](../spikes/).
