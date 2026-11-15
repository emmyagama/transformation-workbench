"""Shared builders for small synthetic contract fixtures."""

from __future__ import annotations

HEADER = (
    "case_id,received_at,acknowledged_at,closed_at,priority,status,"
    "rework_count,duplicate_of"
)


def row(
    *,
    case_id: str = "C-100",
    received_at: str = "2026-03-01T00:00:00Z",
    acknowledged_at: str = "2026-03-01T00:00:00Z",
    closed_at: str = "2026-03-02T00:00:00Z",
    priority: str = "P2",
    status: str = "closed",
    rework_count: str = "0",
    duplicate_of: str = "",
) -> str:
    return ",".join(
        (
            case_id,
            received_at,
            acknowledged_at,
            closed_at,
            priority,
            status,
            rework_count,
            duplicate_of,
        )
    )


def csv_text(*rows: str) -> str:
    return "\n".join((HEADER, *rows)) + "\n"
