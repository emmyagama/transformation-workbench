# Build a read-only MCP business-process baseline

This tutorial uses the actual Transformation Workbench repository to show how a
local MCP server exposes deterministic baseline metrics from synthetic service
requests. It is a local portfolio demonstration, not a deployment guide and not
a claim about real savings, productivity, or business outcomes.

The completed path is:

1. Create a Python 3.11 virtual environment and install the package.
2. Run the automated tests.
3. Read the packaged synthetic CSV through `importlib.resources`.
4. Connect OpenCode, as the MCP host, to this repository's local MCP server.
5. Call the three read-only tools and inspect the resource and prompt.

## What is in the repository

The single fixture is:

```text
src/transformation_workbench/data/synthetic_cases.csv
```

It contains 15 synthetic email-based service-request rows, a header row, and an
intentional mix of valid and invalid data. The snapshot is
`2026-03-13T17:00:00Z`; SLA targets are P1 = 8 h, P2 = 24 h, and P3 = 72 h.

The server is in `src/transformation_workbench/mcp_server.py`. It exposes:

- tools: `calculate_baseline_metrics`, `list_case_exceptions`,
  `get_case_details`
- resource: `workbench://process-context`
- prompt: `baseline_diagnostic`

The fixture is package data, configured in `pyproject.toml`:

```toml
[tool.setuptools.package-data]
transformation_workbench = ["data/*.csv"]
```

The server reads it with `importlib.resources`, not by constructing a filesystem
path from `__file__`. That keeps the same resource lookup working in an editable
checkout and in an installed wheel.

## Synthetic-data boundary

All records are fictional and synthetic. The metrics in this tutorial are
fixture results only. Do not present them as production performance, savings,
ROI, or proof of enterprise readiness.

The MCP server is intentionally narrow:

- no caller-supplied filesystem paths
- no write tools
- no network calls or external actions
- no real business, customer, employee, or personal data
- read-only tool annotations

The data includes invalid rows on purpose so exclusion handling is visible. For
this fixture, 12 rows validate and 3 are reported as row-level issues; one
duplicate-status case is excluded separately during metric computation. That is
why the reconciliation is 15 input rows = 9 measurable + 4 excluded + 2 backlog.

## MCP host, MCP server, and stdio

An MCP host is the application that manages the user experience, model, and tool
approvals. In this tutorial, OpenCode is the host application. Its built-in MCP
client component reads the project configuration, starts the server, and
exchanges protocol messages with it. The MCP client is part of the host, not a
separate host and not the component that owns the business logic. The MCP server
is the local Python process that advertises tools, resources, and prompts.

```text
OpenCode host
  |
  |  starts the configured command
  v
.venv/Scripts/python.exe -m transformation_workbench.mcp_server
  |
  |  MCP messages over stdin/stdout
  v
Transformation Workbench MCP server
```

stdio is the transport. The host starts the server process and exchanges MCP
protocol messages over the process's standard input and output. Application
diagnostics are written to standard error, so they do not corrupt the protocol
messages on standard output. There is no listening port and no web deployment.

The test suite includes a real subprocess smoke test using the MCP SDK client:
it launches the current virtualenv's Python, discovers the tools, calls
`calculate_baseline_metrics`, and confirms that diagnostics were written to
stderr.

## Set up the environment

### Windows PowerShell

Run these commands from the repository root. The tested interpreter was Python
3.11.9.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

Observed output from the clean-copy verification on Windows:

```text
87 passed in 28.51s
```

The duration varies by machine. The important part is that all tests pass.

Check the installed dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Observed output:

```text
No broken requirements found.
```

### macOS/Linux

Use the POSIX virtualenv layout and a Python 3.11 executable from `PATH`:

```bash
python3.11 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
./.venv/bin/python -m pytest -q
./.venv/bin/python -m pip check
```

These commands are documented for portability but were not executed in this
Windows audit. No absolute interpreter paths are required on either platform.

## Verify the packaged fixture resource

This prints a Boolean and a few counts rather than a machine-specific path:

```powershell
.\.venv\Scripts\python.exe -c "from importlib.resources import files; from transformation_workbench.data import load_cases_from_csv; resource = files('transformation_workbench').joinpath('data', 'synthetic_cases.csv'); result = load_cases_from_csv(resource.read_text(encoding='utf-8')); print(f'resource_present={resource.is_file()}'); print(f'input_rows={result.input_rows} valid={len(result.cases)} invalid={len(result.invalid_rows)}')"
```

Observed output:

```text
resource_present=True
input_rows=15 valid=12 invalid=3
```

The 12 valid rows plus 3 loader-level invalid rows account for all 15 input
records at this stage. The duplicate-status row is valid at load time and is
excluded later from metric calculations, giving the four reported exceptions and
the final reconciliation described in `docs/data-contract.md`.

## Connect OpenCode with a project-scoped config

Create `opencode.json` in the repository root, next to `pyproject.toml`. The
active local file uses the Windows interpreter path:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "transformation-workbench": {
        "type": "local",
        "command": [
          ".venv/Scripts/python.exe",
          "-m",
          "transformation_workbench.mcp_server"
        ],
        "cwd": ".",
        "codemode": false
      }
    }
  }
}
```

The rest of the config is the same on macOS/Linux; only the interpreter path
changes:

| Platform | Interpreter command |
| --- | --- |
| Windows | `.venv/Scripts/python.exe` |
| macOS/Linux | `.venv/bin/python` |

For example, replace the `command` array on macOS/Linux with:

```json
"command": [
  ".venv/bin/python",
  "-m",
  "transformation_workbench.mcp_server"
]
```

Keep `cwd: "."` and start OpenCode from the repository root so it resolves to
this project.

The local config is intentionally not committed because interpreter paths can
vary by platform. Exclude it in `.git/info/exclude`, which is local to your
checkout and does not modify tracked `.gitignore` rules:

```text
# Local-only OpenCode config
/opencode.json
```

Confirm the exclusion before staging:

```powershell
git check-ignore -v opencode.json
```

Do not add this server to an unrelated global OpenCode config. The `.venv`
directory is local and ignored by Git; each checkout recreates it with the
setup commands above.

Start OpenCode from the repository root, then check the connection:

```powershell
opencode mcp list
```

Observed output, with terminal table borders omitted:

```text
•  ✓ transformation-workbench connected
      .venv/Scripts/python.exe -m transformation_workbench.mcp_server
—  1 server(s)
```

OpenCode namespaces the tools with the server name. A call to the third tool was
observed as `transformation-workbench_get_case_details` with
`{"row_number": 15}`.

If the server does not start, first confirm that the virtual environment exists
and that the command works from the repository root:

```powershell
Test-Path .\.venv\Scripts\python.exe
.\.venv\Scripts\python.exe -m transformation_workbench.mcp_server
```

On macOS/Linux, the equivalent checks are:

```bash
test -x .venv/bin/python
./.venv/bin/python -m transformation_workbench.mcp_server
```

The server command is an MCP stdio server; it will wait for protocol input rather
than printing a normal shell prompt. That blocking behavior is expected. Stop it
with `Ctrl+C` when testing manually.

## Tool 1: calculate_baseline_metrics

This tool takes no arguments and computes the baseline from the packaged fixture.
Its structured result is:

```json
{
  "status": "ok",
  "snapshot_at": "2026-03-13T17:00:00Z",
  "input_rows": 15,
  "measurable_closed": 9,
  "cycle_time_sum_hours": 261.5,
  "mean_cycle_time_hours": 29.06,
  "median_cycle_time_hours": 9.0,
  "sla_met_count": 6,
  "sla_met_percent": 66.7,
  "rework_cases": 2,
  "rework_rate_percent": 22.2,
  "rework_volume": 3,
  "backlog_cases": 2,
  "backlog_overdue": 1,
  "excluded_count": 4
}
```

For this synthetic fixture, 9 closed cases are measurable, 6 meet SLA, 2 had
rework, and 2 cases are backlog at the snapshot. The exact 24-hour C-009 case is
an inclusive SLA boundary and is counted as met. These are fixture calculations,
not a business claim.

## Tool 2: list_case_exceptions

This tool takes no arguments and returns the rows excluded from metric
denominators, with explicit reasons and row numbers.

```json
{
  "input_rows": 15,
  "count": 4,
  "exceptions": [
    {
      "case_id": "C-006",
      "reason": "INCOMPLETE_MISSING_CLOSED_AT",
      "row_number": 7
    },
    {
      "case_id": "C-010",
      "reason": "INVALID_DATE",
      "row_number": 11
    },
    {
      "case_id": "C-011",
      "reason": "OUT_OF_ORDER",
      "row_number": 12
    },
    {
      "case_id": "C-014",
      "reason": "DUPLICATE_OF:C-007",
      "row_number": 15
    }
  ]
}
```

Excluded rows are not silently dropped and are not counted as SLA misses.

## Tool 3: get_case_details

The tool accepts exactly one selector:

- `case_id` for a unique case identifier such as `C-009`
- `row_number` for one CSV record; the header is row 1, so data starts at row 2

Row lookup is useful when a case ID is duplicated across an invalid and corrected
row, when an earlier row is invalid and a later row reuses the ID, or when a row
has no case ID at all. Case-ID lookup returns a clear ambiguity error if more
than one row matches:

```text
Ambiguous case_id 'C-700': matches rows 3, 4, 5. Use row_number to select one row.
```

The `C-700` ambiguity is an illustrative test case from the automated tests, not
a row in the shipped fixture. For the shipped fixture, row 15 is the
duplicate-status case:

```json
{
  "case_id": "C-014",
  "row_number": 15,
  "classification": "duplicate",
  "status": "duplicate",
  "priority": "P2",
  "received_at": "2026-03-05T11:04:00Z",
  "acknowledged_at": "2026-03-05T11:15:00Z",
  "closed_at": "2026-03-05T20:00:00Z",
  "rework_count": 0,
  "duplicate_of": "C-007",
  "exclusion_reason": "DUPLICATE_OF:C-007",
  "cycle_time_hours": null,
  "sla_target_hours": null,
  "sla_met": null,
  "backlog_age_hours": null,
  "backlog_overdue": null
}
```

A blank-ID row is also an illustrative test case from the automated tests, not a
row in the shipped fixture. It can be inspected by row number and returns
`case_id` as `null`. The output type permits that explicitly, rather than
representing a missing ID as an empty string.

## Resource: workbench://process-context

The resource is read-only context for the host. Its MIME type is
`text/markdown`. The actual content is:

```markdown
# Transformation Workbench process context

This is a fictional, synthetic email-based service-request process. It supports
deterministic baseline metrics only and makes no claims about real savings,
productivity, or enterprise deployment.

- Fixture: package resource `transformation_workbench/data/synthetic_cases.csv`
  (15 synthetic rows)
- Snapshot: 2026-03-13T17:00:00Z
- SLA targets: P1 = 8 h, P2 = 24 h, P3 = 72 h
- Cycle time: `closed_at - received_at`, wall clock, no pause deductions
- Measurable: closed, valid timestamps, ordered timestamps, valid priority,
  not future-dated, and not a duplicate
- Backlog: open and `awaiting_info` cases at the snapshot
- A case with any event timestamp after the snapshot is excluded as
  `FUTURE_OF_SNAPSHOT`
- `get_case_details` accepts one of `case_id` or `row_number`; row numbers
  start at 2 because the CSV header is row 1
- Data policy: synthetic data only; read-only; no caller-supplied paths
```

Resources supply context; they do not perform writes or calculations. The host
can read this resource before or during a diagnostic conversation.

## Prompt: baseline_diagnostic

The prompt supplies a repeatable workflow for a host:

```text
Review the baseline for the synthetic Transformation Workbench.

1. Call `calculate_baseline_metrics` with no arguments.
2. Call `list_case_exceptions` with no arguments.
3. Use `get_case_details` with a unique case ID or with `row_number` when an
   exception row has a duplicate or blank ID.
4. Report the exact rollups, excluded rows, and backlog.
5. Distinguish data-quality exclusions from SLA misses, and do not invent
   real-world savings or deployment claims.
```

Prompts guide the host; they do not bypass the tool schemas or the read-only
boundary.

## Structured results and annotations

Each tool returns a Pydantic model, not arbitrary prose. The server publishes an
output schema for each tool, and the host receives a JSON structured result. The
`BaselineMetrics.status` field is restricted to exactly:

```text
ok
no measurable cases
```

The tests validate the required output-schema keys and JSON types, and validate
the returned `structured_content` against the declared schemas with
`jsonschema`.

All three tools declare:

```text
read_only_hint = true
open_world_hint = false
```

That tells the host these operations are read-only and do not reach arbitrary
external systems. It is an annotation, not a substitute for the server's actual
implementation boundary. The OpenCode configuration selects and launches the
server but does not enforce read-only behavior; the server implementation and
tests define that boundary.

## Clean-copy verification

The Windows PowerShell setup commands in this tutorial were rerun in a temporary
copy that excluded `.venv`, `.git`, and the local `opencode.json`. The copy
recreated a Python 3.11 virtual environment from scratch and installed `.[dev]`.
The macOS/Linux commands are documented for portability but were not executed in
this Windows audit.

Recorded results:

```text
Python 3.11.9
87 passed in 28.51s
No broken requirements found.
resource_present=True
input_rows=15 valid=12 invalid=3
```

The MCP test suite also launches the server as a real stdio subprocess using the
virtualenv's interpreter and the SDK client, so this is not an in-process-only
smoke test.

## Scope and limitations

This tutorial demonstrates a local, synthetic, read-only MCP baseline. It does
not demonstrate:

- production deployment
- authentication or authorization for a hosted service
- real business data handling
- write actions, approvals, or external side effects
- financial savings or productivity outcomes

Before adding consequential actions, the human approval gate described in
`AGENTS.md` would need to be implemented and enforced. The current server has no
write or action tools.
