# Open Responses validation runbook

## Status

Completed on 2026-11-17. No rerun is authorized. Results and operation
accounting are recorded below. Evidence:
`docs/evidence/openresponses-gate3.json`.

## Authorization limits

- Hosted-operation ceiling: **56 total**.
- Prior conservative tally: up to **31**.
- Suite allocation: at most **23**.
- Contingency reserve: **2**.
- No retries, ad hoc probes, extra model calls, staging, commit, push,
  deployment, or publication.

## Run configuration

- Model: `gpt-6.1-sol`.
- Pinned suite: `dce9ddb91921427c2ba06901c7dfaf0cc7056799`.
- The launcher accepts a base URL prefix and appends `/responses`. Do not append
  `/responses` yourself.
- Pay-as-you-go prefix: `https://opencode.ai/inference/openai/v1`.
- Go prefix: `https://opencode.ai/inference/go/openai/v1`.
- Use the prefix that matches the Console plan that owns the key.

The sanitized evidence does not record which Console plan prefix was used. It
does record `repo.dirty: true` for HEAD
`17faecf55318b7474237f9cfa939855e4d6ec16e`; Gate 3 ran from that uncommitted
working tree, not from a clean commit. Do not infer a plan or treat the dirty
tree as a committed snapshot.

## Command

Pay-as-you-go:

```powershell
Set-Location '<repo-root>'
.\scripts\Start-OpenResponses-Gate3.ps1 `
  -UpstreamUrl 'https://opencode.ai/inference/openai/v1'
```

Go:

```powershell
Set-Location '<repo-root>'
.\scripts\Start-OpenResponses-Gate3.ps1 `
  -UpstreamUrl 'https://opencode.ai/inference/go/openai/v1'
```

Optional parameters:

- `-Model` defaults to `gpt-6.1-sol`.
- `-Port` defaults to `8000`.
- `-TimeoutSeconds` defaults to `60`.
- `-AllowedUpstreamHost` defaults to the URL host and must match it.
- `-AuthHeader` defaults to `Authorization`.
- `-AuthScheme` defaults to `Bearer`.
- `-Output` defaults to `docs\evidence\openresponses-gate3.json`.

The Console key is entered only at the hidden prompt created by the launcher.
Do not paste it into chat, a prompt, a command line, or a file.

## What the launcher does

1. Validates the HTTPS upstream URL and host allowlist.
2. Confirms no conflicting hosted credential variables are set.
3. Prompts for the Console key with `Read-Host -AsSecureString`. No hosted
   request is sent before this prompt.
4. Generates a separate random 32-byte compaction key.
5. Starts the adapter with the upstream key only in
   `OPENRESPONSES_UPSTREAM_API_KEY` and the compaction key only in
   `OPENRESPONSES_COMPACTION_KEY`.
6. Clears both values from the PowerShell process immediately after the adapter
   starts. The suite runner does not inherit either value.
7. Waits for the loopback health endpoint.
8. Runs the Gate 3 suite runner with only the non-secret local token.
9. Stops the adapter in a `finally` block.
10. Writes secret-free evidence to the requested output path.

## Result

- One complete run of the 17 pinned tests.
- **17 passed, 0 failed, 0 harness errors.**
- Suite operations: **19**.
- Conservative total: `31 + 19 = 50` against the **56** ceiling.
- Remaining headroom: **6** operations; **2** are held as contingency, leaving
  **4** above the reserve.
- No retries, no accounting errors, and no budget overrun.
- The missing-model test made **0** upstream operations.
- This pass applies only to the local adapter plus Console upstream. The earlier
  direct Console route result (1 pass, 16 fail) remains a separate, unchanged
  failure.
- Evidence: `docs/evidence/openresponses-gate3.json`.

Evidence provenance note: the JSON `suite.path` value is redacted to
`<local-pinned-suite-clone>` for publication; the recorded suite commit and
results are unchanged. To run the helper scripts locally, pass `--suite
<path>` or set `OPENRESPONSES_SUITE_PATH`, and put `bun` on `PATH` or set
`OPENRESPONSES_BUN_PATH`.

| Test ID | Result | Operations | Cumulative | Duration (ms) |
| --- | --- | ---: | ---: | ---: |
| `basic-response` | Passed | 1 | 1 | 2929 |
| `assistant-phase` | Passed | 1 | 2 | 2584 |
| `response-output-phase-schema` | Passed | 0 | 2 | 0 |
| `streaming-response` | Passed | 1 | 3 | 2247 |
| `websocket-response` | Passed | 1 | 4 | 1865 |
| `websocket-sequential-responses` | Passed | 2 | 6 | 4799 |
| `websocket-continuation` | Passed | 2 | 8 | 3372 |
| `websocket-reconnect-store-false-recovery` | Passed | 2 | 10 | 4868 |
| `websocket-previous-response-not-found` | Passed | 0 | 10 | 20 |
| `websocket-failed-continuation-evicts-cache` | Passed | 2 | 12 | 2022 |
| `websocket-compact-new-chain` | Passed | 2 | 14 | 4624 |
| `system-prompt` | Passed | 1 | 15 | 1885 |
| `tool-calling` | Passed | 1 | 16 | 2513 |
| `image-input` | Passed | 1 | 17 | 1985 |
| `multi-turn` | Passed | 1 | 18 | 3091 |
| `compact-response` | Passed | 1 | 19 | 2430 |
| `compact-missing-model` | Passed | 0 | 19 | 16 |

## Review disposition

Gate 3 is complete. Stop for review. Do not rerun any test, make a repair
probe, or perform additional hosted calls. Do not stage, commit, push, deploy,
or publish.
