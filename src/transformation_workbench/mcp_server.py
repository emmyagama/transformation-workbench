"""Read-only Week 1 MCP server over the deterministic analysis core."""

import logging
import sys
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from importlib.resources import files
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from .data import (
    SNAPSHOT_AT,
    CaseRecord,
    CaseStatus,
    LoadResult,
    RowIssue,
    load_cases_from_csv,
)
from .metrics import MetricsResult, compute_metrics

logger = logging.getLogger(__name__)

FIXTURE_PACKAGE = "transformation_workbench"
FIXTURE_RESOURCE = "data/synthetic_cases.csv"
FIXTURE_DESCRIPTION = "transformation_workbench/data/synthetic_cases.csv"

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    read_only_hint=True,
    open_world_hint=False,
)

PROCESS_CONTEXT = """# Transformation Workbench - Week 1 process context

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
"""

DIAGNOSTIC_PROMPT = """Review the Week 1 baseline for the synthetic Transformation Workbench.

1. Call `calculate_baseline_metrics` with no arguments.
2. Call `list_case_exceptions` with no arguments.
3. Use `get_case_details` with a unique case ID or with `row_number` when an
   exception row has a duplicate or blank ID.
4. Report the exact rollups, excluded rows, and backlog.
5. Distinguish data-quality exclusions from SLA misses, and do not invent
   real-world savings or deployment claims.
"""


class BaselineMetrics(BaseModel):
    status: Literal["ok", "no measurable cases"] = Field(
        description="Either 'ok' or 'no measurable cases'."
    )
    snapshot_at: str = Field(description="UTC snapshot used for backlog aging.")
    input_rows: int
    measurable_closed: int
    cycle_time_sum_hours: float
    mean_cycle_time_hours: float | None
    median_cycle_time_hours: float | None
    sla_met_count: int
    sla_met_percent: float | None
    rework_cases: int
    rework_rate_percent: float | None
    rework_volume: int
    backlog_cases: int
    backlog_overdue: int
    excluded_count: int


class CaseException(BaseModel):
    case_id: str | None
    reason: str
    row_number: int


class CaseExceptionList(BaseModel):
    input_rows: int
    count: int
    exceptions: list[CaseException]


class CaseDetails(BaseModel):
    case_id: str | None
    row_number: int
    classification: Literal["measurable", "backlog", "duplicate", "invalid"]
    status: str | None
    priority: str | None
    received_at: str | None
    acknowledged_at: str | None
    closed_at: str | None
    rework_count: int | None
    duplicate_of: str | None
    exclusion_reason: str | None
    cycle_time_hours: float | None
    sla_target_hours: float | None
    sla_met: bool | None
    backlog_age_hours: float | None
    backlog_overdue: bool | None


mcp = MCPServer(
    name="Transformation Workbench",
    version="0.1.0",
    instructions=(
        "Read-only Week 1 baseline metrics over a fixed synthetic fixture. "
        "No caller-supplied paths, writes, network calls, or external actions."
    ),
)


@mcp.tool(structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
def calculate_baseline_metrics() -> BaselineMetrics:
    """Calculate deterministic Week 1 baseline metrics from the fixed fixture."""
    logger.info("tool=calculate_baseline_metrics")
    metrics = compute_metrics(_load_dataset())
    presentation = metrics.to_presentation()
    snapshot_at = _format_utc(SNAPSHOT_AT)
    if snapshot_at is None:  # pragma: no cover - SNAPSHOT_AT is always set
        raise ValueError("snapshot is missing")
    return BaselineMetrics(
        status=metrics.status.value,
        snapshot_at=snapshot_at,
        input_rows=metrics.input_rows,
        measurable_closed=metrics.measurable_closed,
        cycle_time_sum_hours=_as_float(presentation["cycle_time_sum_hours"]),
        mean_cycle_time_hours=_as_optional_float(
            presentation["mean_cycle_time_hours"]
        ),
        median_cycle_time_hours=_as_optional_float(
            presentation["median_cycle_time_hours"]
        ),
        sla_met_count=metrics.sla_met_count,
        sla_met_percent=_as_optional_float(presentation["sla_met_percent"]),
        rework_cases=metrics.rework_cases,
        rework_rate_percent=_as_optional_float(
            presentation["rework_rate_percent"]
        ),
        rework_volume=metrics.rework_volume,
        backlog_cases=metrics.backlog_cases,
        backlog_overdue=metrics.backlog_overdue,
        excluded_count=metrics.excluded_count,
    )


@mcp.tool(structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
def list_case_exceptions() -> CaseExceptionList:
    """List rows excluded from Week 1 metrics with explicit reasons."""
    logger.info("tool=list_case_exceptions")
    metrics = compute_metrics(_load_dataset())
    exceptions = [
        CaseException(
            case_id=issue.case_id,
            reason=issue.reason,
            row_number=issue.row_number,
        )
        for issue in metrics.exclusions
    ]
    return CaseExceptionList(
        input_rows=metrics.input_rows,
        count=len(exceptions),
        exceptions=exceptions,
    )


@mcp.tool(structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
def get_case_details(
    case_id: Annotated[
        str | None,
        Field(
            description=(
                "Case identifier such as C-009. "
                "Provide exactly one of case_id or row_number."
            )
        ),
    ] = None,
    row_number: Annotated[
        int | None,
        Field(
            description=(
                "CSV record number starting at 2; the header is row 1. "
                "Provide exactly one of case_id or row_number."
            ),
            ge=2,
        ),
    ] = None,
) -> CaseDetails:
    """Return one synthetic row and its Week 1 classification."""
    logger.info(
        "tool=get_case_details case_id=%r row_number=%r",
        case_id,
        row_number,
    )
    dataset = _load_dataset()
    metrics = compute_metrics(dataset)
    return _select_case_details(
        dataset,
        metrics,
        case_id=case_id,
        row_number=row_number,
    )


@mcp.resource(
    "workbench://process-context",
    name="process_context",
    title="Week 1 process context",
    description="Synthetic process, snapshot, SLA targets, and data policy.",
    mime_type="text/markdown",
)
def process_context() -> str:
    """Synthetic process, snapshot, SLA targets, and data policy for Week 1."""
    return PROCESS_CONTEXT


@mcp.prompt(
    name="week1_diagnostic",
    title="Week 1 baseline diagnostic",
)
def week1_diagnostic() -> str:
    """Guide a read-only review of Week 1 metrics, exceptions, and backlog."""
    return DIAGNOSTIC_PROMPT


def _load_dataset() -> LoadResult:
    logger.debug("Reading package fixture %s", FIXTURE_DESCRIPTION)
    fixture = files(FIXTURE_PACKAGE).joinpath(*FIXTURE_RESOURCE.split("/"))
    return load_cases_from_csv(fixture.read_text(encoding="utf-8"))


def _known_case_ids(dataset: LoadResult) -> set[str]:
    ids = {case.case_id for case in dataset.cases}
    ids.update(
        issue.case_id
        for issue in dataset.invalid_rows
        if issue.case_id is not None
    )
    return ids


def _select_case_details(
    dataset: LoadResult,
    metrics: MetricsResult,
    *,
    case_id: str | None,
    row_number: int | None,
) -> CaseDetails:
    if (case_id is None) == (row_number is None):
        raise ToolError("Provide exactly one of case_id or row_number.")

    if row_number is not None:
        case, issue = _row_by_number(dataset, row_number)
    else:
        if case_id is None:  # pragma: no cover - guarded above
            raise ToolError("Provide exactly one of case_id or row_number.")
        case, issue = _row_by_case_id(dataset, case_id)

    if issue is not None:
        return _invalid_case_details(issue)
    if case is None:  # pragma: no cover - selectors always find one row
        raise ToolError("No row matched the requested selector.")
    return _valid_case_details(case, metrics)


def _row_by_number(
    dataset: LoadResult, row_number: int
) -> tuple[CaseRecord | None, RowIssue | None]:
    if row_number < 2:
        raise ToolError("row_number must be 2 or greater; the header is row 1.")

    case = next(
        (item for item in dataset.cases if item.row_number == row_number),
        None,
    )
    issue = next(
        (item for item in dataset.invalid_rows if item.row_number == row_number),
        None,
    )
    if case is None and issue is None:
        known_rows = sorted(
            [item.row_number for item in dataset.cases]
            + [item.row_number for item in dataset.invalid_rows]
        )
        raise ToolError(
            f"Unknown row_number {row_number}. "
            f"Known rows: {', '.join(str(row) for row in known_rows)}."
        )
    return case, issue


def _row_by_case_id(
    dataset: LoadResult, case_id: str
) -> tuple[CaseRecord | None, RowIssue | None]:
    normalized = case_id.strip()
    if not normalized:
        raise ToolError(
            "case_id must not be blank. Use row_number to inspect blank-ID rows."
        )

    matches: list[tuple[int, CaseRecord | None, RowIssue | None]] = [
        (case.row_number, case, None)
        for case in dataset.cases
        if case.case_id == normalized
    ]
    matches.extend(
        (issue.row_number, None, issue)
        for issue in dataset.invalid_rows
        if issue.case_id == normalized
    )

    if not matches:
        allowed_ids = _known_case_ids(dataset)
        raise ToolError(
            f"Unknown case_id {case_id!r}. "
            f"Allowed IDs: {', '.join(sorted(allowed_ids))}."
        )
    if len(matches) > 1:
        rows = ", ".join(
            str(row_number)
            for row_number, _, _ in sorted(matches, key=lambda match: match[0])
        )
        raise ToolError(
            f"Ambiguous case_id {case_id!r}: matches rows {rows}. "
            "Use row_number to select one row."
        )

    _, case, issue = matches[0]
    return case, issue


def _valid_case_details(case: CaseRecord, metrics: MetricsResult) -> CaseDetails:
    if case.status is CaseStatus.DUPLICATE:
        issue = next(
            (
                item
                for item in metrics.exclusions
                if item.row_number == case.row_number
            ),
            None,
        )
        if issue is None:  # pragma: no cover - duplicate rows are excluded
            raise ToolError(f"Duplicate case {case.case_id} has no exclusion reason.")
        return _case_details(
            case,
            classification="duplicate",
            exclusion_reason=issue.reason,
        )

    if case.status is CaseStatus.CLOSED:
        measured = next(
            (
                item
                for item in metrics.measurable
                if item.case_id == case.case_id
            ),
            None,
        )
        if measured is None:  # pragma: no cover - closed rows are measurable
            raise ToolError(f"Closed case {case.case_id} has no measurable result.")
        return _case_details(
            case,
            classification="measurable",
            cycle_time_hours=_hours_2dp(measured.cycle_time_hours),
            sla_target_hours=_hours_2dp(measured.sla_target_hours),
            sla_met=measured.sla_met,
        )

    backlog = next(
        (item for item in metrics.backlog if item.case_id == case.case_id),
        None,
    )
    if backlog is None:  # pragma: no cover - open rows are backlog
        raise ToolError(f"Open case {case.case_id} has no backlog result.")
    return _case_details(
        case,
        classification="backlog",
        sla_target_hours=_hours_2dp(backlog.sla_target_hours),
        backlog_age_hours=_hours_2dp(backlog.age_hours),
        backlog_overdue=backlog.overdue,
    )


def _case_details(
    case: CaseRecord,
    *,
    classification: Literal["measurable", "backlog", "duplicate"],
    exclusion_reason: str | None = None,
    cycle_time_hours: float | None = None,
    sla_target_hours: float | None = None,
    sla_met: bool | None = None,
    backlog_age_hours: float | None = None,
    backlog_overdue: bool | None = None,
) -> CaseDetails:
    return CaseDetails(
        case_id=case.case_id,
        row_number=case.row_number,
        classification=classification,
        status=case.status.value,
        priority=case.priority.value,
        received_at=_format_utc(case.received_at),
        acknowledged_at=_format_utc(case.acknowledged_at),
        closed_at=_format_utc(case.closed_at),
        rework_count=case.rework_count,
        duplicate_of=case.duplicate_of,
        exclusion_reason=exclusion_reason,
        cycle_time_hours=cycle_time_hours,
        sla_target_hours=sla_target_hours,
        sla_met=sla_met,
        backlog_age_hours=backlog_age_hours,
        backlog_overdue=backlog_overdue,
    )


def _invalid_case_details(issue: RowIssue) -> CaseDetails:
    return CaseDetails(
        case_id=issue.case_id,
        row_number=issue.row_number,
        classification="invalid",
        status=None,
        priority=None,
        received_at=None,
        acknowledged_at=None,
        closed_at=None,
        rework_count=None,
        duplicate_of=None,
        exclusion_reason=issue.reason,
        cycle_time_hours=None,
        sla_target_hours=None,
        sla_met=None,
        backlog_age_hours=None,
        backlog_overdue=None,
    )


def _format_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hours_2dp(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _as_float(value: object) -> float:
    return float(str(value))


def _as_optional_float(value: object) -> float | None:
    return None if value is None else float(str(value))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )
    logger.info("Starting Transformation Workbench MCP server over stdio")
    logger.info("Using package fixture %s", FIXTURE_DESCRIPTION)
    mcp.run()


if __name__ == "__main__":
    main()
