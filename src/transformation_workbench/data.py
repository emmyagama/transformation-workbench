"""Deterministic CSV loading and row validation for the Week 1 contract."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TypeVar


class DataContractError(ValueError):
    """Raised when the CSV structure violates the data contract."""


class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class CaseStatus(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    AWAITING_INFO = "awaiting_info"
    DUPLICATE = "duplicate"


SLA_TARGET_HOURS: dict[Priority, int] = {
    Priority.P1: 8,
    Priority.P2: 24,
    Priority.P3: 72,
}

SNAPSHOT_AT = datetime(2026, 3, 13, 17, 0, 0, tzinfo=timezone.utc)

REQUIRED_COLUMNS = (
    "case_id",
    "received_at",
    "acknowledged_at",
    "closed_at",
    "priority",
    "status",
    "rework_count",
    "duplicate_of",
)

_TIMESTAMP_PATTERN = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
_CANONICAL_INTEGER_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)")

_EnumT = TypeVar("_EnumT", Priority, CaseStatus)


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    received_at: datetime
    acknowledged_at: datetime
    closed_at: datetime | None
    priority: Priority
    status: CaseStatus
    rework_count: int
    duplicate_of: str | None
    row_number: int


@dataclass(frozen=True)
class RowIssue:
    row_number: int
    case_id: str | None
    reason: str


@dataclass(frozen=True)
class LoadResult:
    input_rows: int
    cases: tuple[CaseRecord, ...]
    invalid_rows: tuple[RowIssue, ...]


class _RowError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def parse_utc_timestamp(value: str) -> datetime:
    """Parse a strict ISO 8601 UTC timestamp ending in ``Z``."""
    if not _TIMESTAMP_PATTERN.fullmatch(value):
        raise ValueError(f"invalid UTC timestamp: {value!r}")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError(f"invalid UTC timestamp: {value!r}") from exc
    return parsed.replace(tzinfo=timezone.utc)


def load_cases_from_csv(csv_text: str) -> LoadResult:
    """Parse CSV text and validate each row against the contract.

    This function accepts text only. It never reads from a filesystem path.
    """
    if not csv_text.strip():
        return LoadResult(input_rows=0, cases=(), invalid_rows=())

    reader = csv.reader(io.StringIO(csv_text))
    fieldnames = next(reader, None)
    if fieldnames is None or not any(_clean(name) for name in fieldnames):
        raise DataContractError("CSV text must include a header row")

    missing_columns = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
    if missing_columns:
        raise DataContractError(
            "CSV is missing required columns: " + ", ".join(missing_columns)
        )

    seen_case_ids: set[str] = set()
    cases: list[CaseRecord] = []
    invalid_rows: list[RowIssue] = []
    input_rows = 0

    for row_number, values in enumerate(reader, start=2):
        input_rows += 1
        if not any(_clean(value) for value in values):
            invalid_rows.append(RowIssue(row_number, None, "EMPTY_ROW"))
            continue

        row = _row_mapping(fieldnames, values)
        case_id = _clean(row.get("case_id"))
        if not case_id:
            invalid_rows.append(RowIssue(row_number, None, "MISSING_CASE_ID"))
            continue
        if case_id in seen_case_ids:
            invalid_rows.append(
                RowIssue(row_number, case_id, f"DUPLICATE_CASE_ID:{case_id}")
            )
            continue

        try:
            record = _parse_record(row, row_number, case_id)
        except _RowError as exc:
            invalid_rows.append(RowIssue(row_number, case_id, exc.reason))
        else:
            seen_case_ids.add(case_id)
            cases.append(record)

    return LoadResult(
        input_rows=input_rows,
        cases=tuple(cases),
        invalid_rows=tuple(invalid_rows),
    )


def _parse_record(
    row: dict[str, str | None], row_number: int, case_id: str
) -> CaseRecord:
    status = _parse_enum(row, "status", CaseStatus)
    priority = _parse_enum(row, "priority", Priority)

    received_at = _parse_timestamp(row, "received_at", required=True)
    acknowledged_at = _parse_timestamp(row, "acknowledged_at", required=True)
    closed_at = _parse_timestamp(row, "closed_at", required=False)

    rework_count = _parse_rework_count(row)

    duplicate_of = _clean(row.get("duplicate_of"))
    if status is CaseStatus.DUPLICATE:
        if not duplicate_of:
            raise _RowError("INCOMPLETE_MISSING_DUPLICATE_OF")
    elif duplicate_of:
        raise _RowError(f"UNEXPECTED_DUPLICATE_OF:{duplicate_of}")

    if received_at > acknowledged_at:
        raise _RowError("OUT_OF_ORDER")
    if closed_at is not None and acknowledged_at > closed_at:
        raise _RowError("OUT_OF_ORDER")

    if status is CaseStatus.CLOSED and closed_at is None:
        raise _RowError("INCOMPLETE_MISSING_CLOSED_AT")
    if (
        status in (CaseStatus.OPEN, CaseStatus.AWAITING_INFO)
        and closed_at is not None
    ):
        raise _RowError("UNEXPECTED_CLOSED_AT")

    event_timestamps = [received_at, acknowledged_at]
    if closed_at is not None:
        event_timestamps.append(closed_at)
    if any(timestamp > SNAPSHOT_AT for timestamp in event_timestamps):
        raise _RowError("FUTURE_OF_SNAPSHOT")

    return CaseRecord(
        case_id=case_id,
        received_at=received_at,
        acknowledged_at=acknowledged_at,
        closed_at=closed_at,
        priority=priority,
        status=status,
        rework_count=rework_count,
        duplicate_of=duplicate_of or None,
        row_number=row_number,
    )


def _parse_enum(
    row: dict[str, str | None], field: str, enum_type: type[_EnumT]
) -> _EnumT:
    raw = _required(row, field)
    try:
        return enum_type(raw)
    except ValueError as exc:
        raise _RowError(f"INVALID_{field.upper()}:{raw}") from exc


def _parse_rework_count(row: dict[str, str | None]) -> int:
    raw = row.get("rework_count")
    if raw is None or raw == "":
        raise _RowError("INCOMPLETE_MISSING_REWORK_COUNT")
    if not _CANONICAL_INTEGER_PATTERN.fullmatch(raw):
        raise _RowError(f"INVALID_REWORK_COUNT:{raw}")
    return int(raw)


def _parse_timestamp(
    row: dict[str, str | None], field: str, *, required: bool
) -> datetime | None:
    raw = row.get(field)
    if raw is None or raw == "":
        if required:
            raise _RowError(f"INCOMPLETE_MISSING_{field.upper()}")
        return None
    try:
        return parse_utc_timestamp(raw)
    except ValueError as exc:
        raise _RowError("INVALID_DATE") from exc


def _row_mapping(
    fieldnames: list[str], values: list[str]
) -> dict[str, str | None]:
    return {
        name: values[index] if index < len(values) else None
        for index, name in enumerate(fieldnames)
    }


def _required(row: dict[str, str | None], field: str) -> str:
    value = _clean(row.get(field))
    if not value:
        raise _RowError(f"INCOMPLETE_MISSING_{field.upper()}")
    return value


def _clean(value: str | None) -> str:
    return value.strip() if value is not None else ""
