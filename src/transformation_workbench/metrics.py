"""Deterministic Week 1 metrics derived from validated cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from .data import (
    SLA_TARGET_HOURS,
    SNAPSHOT_AT,
    CaseStatus,
    LoadResult,
    RowIssue,
)


class MetricStatus(str, Enum):
    OK = "ok"
    NO_MEASURABLE_CASES = "no measurable cases"


@dataclass(frozen=True)
class MeasurableCase:
    case_id: str
    cycle_time_hours: Decimal
    sla_target_hours: Decimal
    sla_met: bool
    rework_count: int


@dataclass(frozen=True)
class BacklogCase:
    case_id: str
    age_hours: Decimal
    sla_target_hours: Decimal
    overdue: bool


@dataclass(frozen=True)
class MetricsResult:
    input_rows: int
    measurable: tuple[MeasurableCase, ...]
    backlog: tuple[BacklogCase, ...]
    exclusions: tuple[RowIssue, ...]
    status: MetricStatus
    cycle_time_sum_hours: Decimal
    mean_cycle_time_hours: Decimal | None
    median_cycle_time_hours: Decimal | None
    sla_met_count: int
    sla_met_percent: Decimal | None
    rework_cases: int
    rework_rate_percent: Decimal | None
    rework_volume: int

    @property
    def measurable_closed(self) -> int:
        return len(self.measurable)

    @property
    def backlog_cases(self) -> int:
        return len(self.backlog)

    @property
    def backlog_overdue(self) -> int:
        return sum(1 for case in self.backlog if case.overdue)

    @property
    def excluded_count(self) -> int:
        return len(self.exclusions)

    def to_presentation(self) -> dict[str, object]:
        """Return contract-rounded values for display only."""
        return {
            "status": self.status.value,
            "input_rows": self.input_rows,
            "measurable_closed": self.measurable_closed,
            "cycle_time_sum_hours": _format_hours(self.cycle_time_sum_hours),
            "mean_cycle_time_hours": _format_hours(self.mean_cycle_time_hours),
            "median_cycle_time_hours": _format_hours(self.median_cycle_time_hours),
            "sla_met": (
                f"{self.sla_met_count}/{self.measurable_closed}"
                if self.measurable_closed
                else None
            ),
            "sla_met_percent": _format_percent(self.sla_met_percent),
            "rework_cases": self.rework_cases,
            "rework_rate_percent": _format_percent(self.rework_rate_percent),
            "rework_volume": self.rework_volume,
            "backlog_cases": self.backlog_cases,
            "backlog_overdue": self.backlog_overdue,
            "excluded_count": self.excluded_count,
            "exclusions": [
                {
                    "row_number": issue.row_number,
                    "case_id": issue.case_id,
                    "reason": issue.reason,
                }
                for issue in self.exclusions
            ],
        }


def compute_metrics(
    dataset: LoadResult, snapshot: datetime = SNAPSHOT_AT
) -> MetricsResult:
    """Compute Week 1 rollups from validated rows."""
    _require_utc(snapshot)

    measurable: list[MeasurableCase] = []
    backlog: list[BacklogCase] = []
    exclusions = list(dataset.invalid_rows)

    for case in dataset.cases:
        target = Decimal(SLA_TARGET_HOURS[case.priority])

        if case.status is CaseStatus.DUPLICATE:
            exclusions.append(
                RowIssue(
                    row_number=case.row_number,
                    case_id=case.case_id,
                    reason=f"DUPLICATE_OF:{case.duplicate_of}",
                )
            )
        elif case.status is CaseStatus.CLOSED:
            if case.closed_at is None:
                raise ValueError(f"closed case {case.case_id} is missing closed_at")
            cycle_time = _hours_between(case.received_at, case.closed_at)
            measurable.append(
                MeasurableCase(
                    case_id=case.case_id,
                    cycle_time_hours=cycle_time,
                    sla_target_hours=target,
                    sla_met=cycle_time <= target,
                    rework_count=case.rework_count,
                )
            )
        else:
            age = _hours_between(case.received_at, snapshot)
            backlog.append(
                BacklogCase(
                    case_id=case.case_id,
                    age_hours=age,
                    sla_target_hours=target,
                    overdue=age > target,
                )
            )

    exclusions.sort(key=lambda issue: (issue.row_number, issue.reason))

    cycle_times = [case.cycle_time_hours for case in measurable]
    cycle_time_sum = sum(cycle_times, Decimal(0))
    measurable_count = len(measurable)

    if measurable_count == 0:
        return MetricsResult(
            input_rows=dataset.input_rows,
            measurable=(),
            backlog=tuple(backlog),
            exclusions=tuple(exclusions),
            status=MetricStatus.NO_MEASURABLE_CASES,
            cycle_time_sum_hours=cycle_time_sum,
            mean_cycle_time_hours=None,
            median_cycle_time_hours=None,
            sla_met_count=0,
            sla_met_percent=None,
            rework_cases=0,
            rework_rate_percent=None,
            rework_volume=0,
        )

    sla_met_count = sum(1 for case in measurable if case.sla_met)
    rework_cases = sum(1 for case in measurable if case.rework_count >= 1)
    rework_volume = sum(case.rework_count for case in measurable)

    return MetricsResult(
        input_rows=dataset.input_rows,
        measurable=tuple(measurable),
        backlog=tuple(backlog),
        exclusions=tuple(exclusions),
        status=MetricStatus.OK,
        cycle_time_sum_hours=cycle_time_sum,
        mean_cycle_time_hours=cycle_time_sum / Decimal(measurable_count),
        median_cycle_time_hours=_median(cycle_times),
        sla_met_count=sla_met_count,
        sla_met_percent=Decimal(sla_met_count) * 100 / Decimal(measurable_count),
        rework_cases=rework_cases,
        rework_rate_percent=Decimal(rework_cases) * 100 / Decimal(measurable_count),
        rework_volume=rework_volume,
    )


def _hours_between(start: datetime, end: datetime) -> Decimal:
    delta = end - start
    microseconds = (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )
    return Decimal(microseconds) / Decimal(3_600_000_000)


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("snapshot must be timezone-aware UTC")


def _format_hours(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def _format_percent(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP):.1f}"
