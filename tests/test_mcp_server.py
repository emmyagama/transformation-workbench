import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.mcpserver.exceptions import ToolError

from tests.helpers import csv_text, row
from transformation_workbench import mcp_server as server
from transformation_workbench.data import load_cases_from_csv
from transformation_workbench.mcp_server import mcp
from transformation_workbench.metrics import compute_metrics

REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_OUTPUT_TYPES = {
    "calculate_baseline_metrics": {
        "status": {"string"},
        "snapshot_at": {"string"},
        "input_rows": {"integer"},
        "measurable_closed": {"integer"},
        "cycle_time_sum_hours": {"number"},
        "mean_cycle_time_hours": {"number", "null"},
        "median_cycle_time_hours": {"number", "null"},
        "sla_met_count": {"integer"},
        "sla_met_percent": {"number", "null"},
        "rework_cases": {"integer"},
        "rework_rate_percent": {"number", "null"},
        "rework_volume": {"integer"},
        "backlog_cases": {"integer"},
        "backlog_overdue": {"integer"},
        "excluded_count": {"integer"},
    },
    "list_case_exceptions": {
        "input_rows": {"integer"},
        "count": {"integer"},
        "exceptions": {"array"},
    },
    "get_case_details": {
        "case_id": {"string", "null"},
        "row_number": {"integer"},
        "classification": {"string"},
        "status": {"string", "null"},
        "priority": {"string", "null"},
        "received_at": {"string", "null"},
        "acknowledged_at": {"string", "null"},
        "closed_at": {"string", "null"},
        "rework_count": {"integer", "null"},
        "duplicate_of": {"string", "null"},
        "exclusion_reason": {"string", "null"},
        "cycle_time_hours": {"number", "null"},
        "sla_target_hours": {"number", "null"},
        "sla_met": {"boolean", "null"},
        "backlog_age_hours": {"number", "null"},
        "backlog_overdue": {"boolean", "null"},
    },
}


@pytest.fixture
async def client():
    async with Client(mcp, raise_exceptions=True) as connected:
        yield connected


def _schema_types(schema: dict[str, object]) -> set[str]:
    if "type" in schema:
        return {str(schema["type"])}
    types: set[str] = set()
    for option in schema.get("anyOf", []):  # type: ignore[union-attr]
        if isinstance(option, dict) and "type" in option:
            types.add(str(option["type"]))
    return types


@pytest.mark.anyio
async def test_tools_expose_only_read_only_inputs(client: Client) -> None:
    result = await client.list_tools()
    tools = {tool.name: tool for tool in result.tools}

    assert set(tools) == {
        "calculate_baseline_metrics",
        "list_case_exceptions",
        "get_case_details",
    }
    assert tools["calculate_baseline_metrics"].input_schema["properties"] == {}
    assert tools["list_case_exceptions"].input_schema["properties"] == {}
    details_schema = tools["get_case_details"].input_schema
    assert set(details_schema["properties"]) == {"case_id", "row_number"}
    assert not details_schema.get("required")
    assert _schema_types(details_schema["properties"]["case_id"]) == {
        "string",
        "null",
    }
    assert _schema_types(details_schema["properties"]["row_number"]) == {
        "integer",
        "null",
    }

    for tool in tools.values():
        assert not any(
            word in name.lower()
            for name in tool.input_schema.get("properties", {})
            for word in ("path", "file", "write", "action")
        )


@pytest.mark.anyio
async def test_tools_declare_read_only_non_open_world_annotations(
    client: Client,
) -> None:
    result = await client.list_tools()

    for tool in result.tools:
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.open_world_hint is False


@pytest.mark.anyio
async def test_output_schemas_have_required_keys_and_types(client: Client) -> None:
    result = await client.list_tools()
    tools = {tool.name: tool for tool in result.tools}

    for tool_name, expected_types in EXPECTED_OUTPUT_TYPES.items():
        schema = tools[tool_name].output_schema
        assert schema is not None
        assert set(schema["required"]) == set(expected_types)
        for property_name, expected in expected_types.items():
            assert _schema_types(schema["properties"][property_name]) == expected

    status_schema = tools["calculate_baseline_metrics"].output_schema["properties"][
        "status"
    ]
    assert status_schema["type"] == "string"
    assert set(status_schema["enum"]) == {"ok", "no measurable cases"}


@pytest.mark.anyio
async def test_structured_content_matches_declared_output_schemas(
    client: Client,
) -> None:
    listed = await client.list_tools()
    tools = {tool.name: tool for tool in listed.tools}
    calls = {
        "calculate_baseline_metrics": {},
        "list_case_exceptions": {},
        "get_case_details": {"case_id": "C-009"},
    }

    for tool_name, arguments in calls.items():
        result = await client.call_tool(tool_name, arguments)
        assert result.is_error is False
        assert result.structured_content is not None
        Draft202012Validator(tools[tool_name].output_schema).validate(
            result.structured_content
        )


@pytest.mark.anyio
async def test_calculate_baseline_metrics(client: Client) -> None:
    result = await client.call_tool("calculate_baseline_metrics", {})

    assert result.is_error is False
    data = result.structured_content
    assert data is not None
    assert data["status"] == "ok"
    assert data["snapshot_at"] == "2026-03-13T17:00:00Z"
    assert data["input_rows"] == 15
    assert data["measurable_closed"] == 9
    assert data["cycle_time_sum_hours"] == pytest.approx(261.50)
    assert data["mean_cycle_time_hours"] == pytest.approx(29.06)
    assert data["median_cycle_time_hours"] == pytest.approx(9.00)
    assert data["sla_met_count"] == 6
    assert data["sla_met_percent"] == pytest.approx(66.7)
    assert data["rework_cases"] == 2
    assert data["rework_rate_percent"] == pytest.approx(22.2)
    assert data["rework_volume"] == 3
    assert data["backlog_cases"] == 2
    assert data["backlog_overdue"] == 1
    assert data["excluded_count"] == 4


@pytest.mark.anyio
async def test_list_case_exceptions(client: Client) -> None:
    result = await client.call_tool("list_case_exceptions", {})

    assert result.is_error is False
    data = result.structured_content
    assert data is not None
    assert data["input_rows"] == 15
    assert data["count"] == 4
    assert {item["case_id"]: item["reason"] for item in data["exceptions"]} == {
        "C-006": "INCOMPLETE_MISSING_CLOSED_AT",
        "C-010": "INVALID_DATE",
        "C-011": "OUT_OF_ORDER",
        "C-014": "DUPLICATE_OF:C-007",
    }
    assert {item["row_number"] for item in data["exceptions"]} == {7, 11, 12, 15}


@pytest.mark.anyio
async def test_get_measurable_case_details(client: Client) -> None:
    result = await client.call_tool("get_case_details", {"case_id": "C-009"})

    assert result.is_error is False
    data = result.structured_content
    assert data is not None
    assert data["classification"] == "measurable"
    assert data["status"] == "closed"
    assert data["priority"] == "P2"
    assert data["received_at"] == "2026-03-09T09:00:00Z"
    assert data["cycle_time_hours"] == pytest.approx(24.0)
    assert data["sla_target_hours"] == pytest.approx(24.0)
    assert data["sla_met"] is True


@pytest.mark.anyio
async def test_get_backlog_case_details(client: Client) -> None:
    result = await client.call_tool("get_case_details", {"case_id": "C-012"})

    assert result.is_error is False
    data = result.structured_content
    assert data is not None
    assert data["classification"] == "backlog"
    assert data["status"] == "open"
    assert data["backlog_age_hours"] == pytest.approx(32.0)
    assert data["sla_target_hours"] == pytest.approx(8.0)
    assert data["backlog_overdue"] is True


@pytest.mark.anyio
async def test_get_duplicate_case_details(client: Client) -> None:
    result = await client.call_tool("get_case_details", {"case_id": "C-014"})

    assert result.is_error is False
    data = result.structured_content
    assert data is not None
    assert data["classification"] == "duplicate"
    assert data["duplicate_of"] == "C-007"
    assert data["exclusion_reason"] == "DUPLICATE_OF:C-007"


@pytest.mark.anyio
async def test_get_case_details_by_row_number(client: Client) -> None:
    result = await client.call_tool("get_case_details", {"row_number": 15})

    assert result.is_error is False
    data = result.structured_content
    assert data is not None
    assert data["case_id"] == "C-014"
    assert data["row_number"] == 15
    assert data["classification"] == "duplicate"
    assert data["exclusion_reason"] == "DUPLICATE_OF:C-007"


@pytest.mark.anyio
async def test_get_invalid_case_details(client: Client) -> None:
    result = await client.call_tool("get_case_details", {"case_id": "C-010"})

    assert result.is_error is False
    data = result.structured_content
    assert data is not None
    assert data["classification"] == "invalid"
    assert data["exclusion_reason"] == "INVALID_DATE"
    assert data["received_at"] is None


def test_row_lookup_disambiguates_duplicate_corrected_and_blank_ids() -> None:
    dataset = load_cases_from_csv(
        csv_text(
            row(case_id=""),
            row(case_id="C-700", rework_count="invalid"),
            row(case_id="C-700"),
            row(case_id="C-700"),
        )
    )
    metrics = compute_metrics(dataset)

    blank = server._select_case_details(
        dataset,
        metrics,
        case_id=None,
        row_number=2,
    )
    assert (blank.row_number, blank.case_id, blank.classification) == (
        2,
        None,
        "invalid",
    )
    assert blank.exclusion_reason == "MISSING_CASE_ID"

    corrected_invalid = server._select_case_details(
        dataset,
        metrics,
        case_id=None,
        row_number=3,
    )
    assert corrected_invalid.case_id == "C-700"
    assert corrected_invalid.exclusion_reason == "INVALID_REWORK_COUNT:invalid"

    corrected_valid = server._select_case_details(
        dataset,
        metrics,
        case_id=None,
        row_number=4,
    )
    assert corrected_valid.case_id == "C-700"
    assert corrected_valid.classification == "measurable"

    duplicate = server._select_case_details(
        dataset,
        metrics,
        case_id=None,
        row_number=5,
    )
    assert duplicate.case_id == "C-700"
    assert duplicate.classification == "invalid"
    assert duplicate.exclusion_reason == "DUPLICATE_CASE_ID:C-700"

    with pytest.raises(ToolError, match=r"Ambiguous case_id 'C-700'"):
        server._select_case_details(
            dataset,
            metrics,
            case_id="C-700",
            row_number=None,
        )


def test_case_lookup_requires_exactly_one_selector() -> None:
    dataset = load_cases_from_csv(csv_text(row(case_id="C-701")))
    metrics = compute_metrics(dataset)

    with pytest.raises(ToolError, match="exactly one"):
        server._select_case_details(
            dataset,
            metrics,
            case_id="C-701",
            row_number=2,
        )
    with pytest.raises(ToolError, match="exactly one"):
        server._select_case_details(
            dataset,
            metrics,
            case_id=None,
            row_number=None,
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "bad_case_id",
    [
        "C-999",
        "../src/transformation_workbench/data/synthetic_cases.csv",
        "synthetic_cases.csv",
    ],
)
async def test_unknown_or_path_like_case_id_is_rejected(
    client: Client, bad_case_id: str
) -> None:
    result = await client.call_tool("get_case_details", {"case_id": bad_case_id})

    assert result.is_error is True
    assert result.structured_content is None
    text = "".join(
        block.text for block in result.content if getattr(block, "text", None)
    )
    assert "Unknown case_id" in text


@pytest.mark.anyio
async def test_unknown_row_number_is_rejected(client: Client) -> None:
    result = await client.call_tool("get_case_details", {"row_number": 999})

    assert result.is_error is True
    assert result.structured_content is None
    text = "".join(
        block.text for block in result.content if getattr(block, "text", None)
    )
    assert "Unknown row_number 999" in text


@pytest.mark.anyio
async def test_process_context_resource(client: Client) -> None:
    listed = await client.list_resources()
    assert "workbench://process-context" in {
        resource.uri for resource in listed.resources
    }

    result = await client.read_resource("workbench://process-context")
    content = result.contents[0]
    assert content.mime_type == "text/markdown"
    assert "2026-03-13T17:00:00Z" in content.text
    assert "P1 = 8 h" in content.text
    assert "synthetic" in content.text.lower()


@pytest.mark.anyio
async def test_diagnostic_prompt(client: Client) -> None:
    listed = await client.list_prompts()
    assert "week1_diagnostic" in {prompt.name for prompt in listed.prompts}

    result = await client.get_prompt("week1_diagnostic")
    message = result.messages[0]
    assert message.role == "user"
    assert "calculate_baseline_metrics" in message.content.text
    assert "list_case_exceptions" in message.content.text
    assert "row_number" in message.content.text


@pytest.mark.anyio
async def test_stdio_subprocess_smoke(tmp_path: Path) -> None:
    stderr_path = tmp_path / "server-stderr.log"
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "transformation_workbench.mcp_server"],
        cwd=REPO_ROOT,
    )

    with stderr_path.open("w", encoding="utf-8") as errlog:
        async with Client(
            stdio_client(parameters, errlog=errlog),
            raise_exceptions=True,
        ) as connected:
            tools = await connected.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "calculate_baseline_metrics",
                "list_case_exceptions",
                "get_case_details",
            }
            result = await connected.call_tool("calculate_baseline_metrics", {})

    assert result.is_error is False
    data = result.structured_content
    assert data is not None
    assert data["input_rows"] == 15
    assert data["measurable_closed"] == 9
    assert data["sla_met_percent"] == pytest.approx(66.7)

    diagnostics = stderr_path.read_text(encoding="utf-8")
    assert "Starting Transformation Workbench MCP server over stdio" in diagnostics
    assert "Using package fixture" in diagnostics
