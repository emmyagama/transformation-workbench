from decimal import Decimal

from tests.helpers import csv_text, row
from transformation_workbench.data import load_cases_from_csv
from transformation_workbench.metrics import MetricStatus, compute_metrics


def test_expected_rollups(fixture_csv: str) -> None:
    metrics = compute_metrics(load_cases_from_csv(fixture_csv))
    presentation = metrics.to_presentation()

    assert metrics.input_rows == 15
    assert metrics.measurable_closed == 9
    assert metrics.cycle_time_sum_hours == Decimal("261.50")
    assert presentation["mean_cycle_time_hours"] == "29.06"
    assert presentation["median_cycle_time_hours"] == "9.00"
    assert metrics.sla_met_count == 6
    assert presentation["sla_met"] == "6/9"
    assert presentation["sla_met_percent"] == "66.7"
    assert metrics.rework_cases == 2
    assert presentation["rework_rate_percent"] == "22.2"
    assert metrics.rework_volume == 3
    assert metrics.backlog_cases == 2
    assert metrics.backlog_overdue == 1
    assert metrics.excluded_count == 4
    assert {issue.case_id: issue.reason for issue in metrics.exclusions} == {
        "C-006": "INCOMPLETE_MISSING_CLOSED_AT",
        "C-010": "INVALID_DATE",
        "C-011": "OUT_OF_ORDER",
        "C-014": "DUPLICATE_OF:C-007",
    }
    assert (
        metrics.measurable_closed + metrics.excluded_count + metrics.backlog_cases
        == 15
    )


def test_fixture_exact_sla_boundary_case_is_met(fixture_csv: str) -> None:
    metrics = compute_metrics(load_cases_from_csv(fixture_csv))
    c009 = next(case for case in metrics.measurable if case.case_id == "C-009")

    assert c009.cycle_time_hours == Decimal("24")
    assert c009.sla_met is True


def test_exact_sla_boundary_is_inclusive() -> None:
    metrics = compute_metrics(
        load_cases_from_csv(
            csv_text(
                row(case_id="C-200", closed_at="2026-03-02T00:00:00Z"),
                row(case_id="C-201", closed_at="2026-03-02T00:00:01Z"),
            )
        )
    )

    by_id = {case.case_id: case for case in metrics.measurable}
    assert by_id["C-200"].cycle_time_hours == Decimal("24")
    assert by_id["C-200"].sla_met is True
    assert by_id["C-201"].sla_met is False
    assert metrics.sla_met_count == 1


def test_median_for_even_sized_measurable_set() -> None:
    metrics = compute_metrics(
        load_cases_from_csv(
            csv_text(
                row(case_id="C-200", closed_at="2026-03-01T01:00:00Z"),
                row(case_id="C-201", closed_at="2026-03-01T03:00:00Z"),
            )
        )
    )

    assert [case.cycle_time_hours for case in metrics.measurable] == [
        Decimal("1"),
        Decimal("3"),
    ]
    assert metrics.median_cycle_time_hours == Decimal("2")
    assert metrics.mean_cycle_time_hours == Decimal("2")


def test_backlog_overdue_is_strictly_greater_than_target() -> None:
    metrics = compute_metrics(
        load_cases_from_csv(
            csv_text(
                row(
                    case_id="C-300",
                    status="open",
                    closed_at="",
                    priority="P1",
                    received_at="2026-03-13T09:00:00Z",
                    acknowledged_at="2026-03-13T09:00:00Z",
                ),
                row(
                    case_id="C-301",
                    status="open",
                    closed_at="",
                    priority="P1",
                    received_at="2026-03-13T08:59:59Z",
                    acknowledged_at="2026-03-13T08:59:59Z",
                ),
            )
        )
    )
    backlog = {case.case_id: case for case in metrics.backlog}

    assert backlog["C-300"].age_hours == Decimal("8")
    assert backlog["C-300"].overdue is False
    assert backlog["C-301"].age_hours > Decimal("8")
    assert backlog["C-301"].overdue is True
    assert metrics.backlog_overdue == 1


def test_future_timestamp_is_excluded_from_metrics() -> None:
    metrics = compute_metrics(
        load_cases_from_csv(
            csv_text(
                row(
                    case_id="C-350",
                    closed_at="2026-03-14T00:00:00Z",
                )
            )
        )
    )

    assert metrics.status is MetricStatus.NO_MEASURABLE_CASES
    assert metrics.measurable_closed == 0
    assert metrics.excluded_count == 1
    assert metrics.exclusions[0].case_id == "C-350"
    assert metrics.exclusions[0].reason == "FUTURE_OF_SNAPSHOT"


def test_invalid_date_is_excluded_not_an_sla_miss(fixture_csv: str) -> None:
    metrics = compute_metrics(load_cases_from_csv(fixture_csv))

    issue = next(issue for issue in metrics.exclusions if issue.case_id == "C-010")
    assert issue.reason == "INVALID_DATE"
    assert all(case.case_id != "C-010" for case in metrics.measurable)
    assert metrics.measurable_closed == 9


def test_out_of_order_is_excluded_and_not_counted(fixture_csv: str) -> None:
    metrics = compute_metrics(load_cases_from_csv(fixture_csv))

    issue = next(issue for issue in metrics.exclusions if issue.case_id == "C-011")
    assert issue.reason == "OUT_OF_ORDER"
    assert all(case.case_id != "C-011" for case in metrics.measurable)
    assert metrics.measurable_closed == 9
    assert metrics.cycle_time_sum_hours == Decimal("261.50")


def test_missing_close_is_excluded_not_an_sla_miss(fixture_csv: str) -> None:
    metrics = compute_metrics(load_cases_from_csv(fixture_csv))

    issue = next(issue for issue in metrics.exclusions if issue.case_id == "C-006")
    assert issue.reason == "INCOMPLETE_MISSING_CLOSED_AT"
    assert all(case.case_id != "C-006" for case in metrics.measurable)
    assert metrics.measurable_closed == 9


def test_duplicate_is_excluded_from_denominators(fixture_csv: str) -> None:
    metrics = compute_metrics(load_cases_from_csv(fixture_csv))

    issue = next(issue for issue in metrics.exclusions if issue.case_id == "C-014")
    assert issue.reason == "DUPLICATE_OF:C-007"
    assert all(case.case_id != "C-014" for case in metrics.measurable)
    assert metrics.measurable_closed == 9
    assert metrics.rework_cases == 2


def test_backlog_counts_and_overdue_boundary(fixture_csv: str) -> None:
    metrics = compute_metrics(load_cases_from_csv(fixture_csv))
    backlog = {case.case_id: case for case in metrics.backlog}

    assert set(backlog) == {"C-012", "C-013"}
    assert backlog["C-012"].age_hours == Decimal("32")
    assert backlog["C-012"].sla_target_hours == Decimal("8")
    assert backlog["C-012"].overdue is True
    assert backlog["C-013"].age_hours == Decimal("55")
    assert backlog["C-013"].sla_target_hours == Decimal("72")
    assert backlog["C-013"].overdue is False
    assert metrics.backlog_overdue == 1


def test_completely_empty_input_returns_no_measurable_cases() -> None:
    metrics = compute_metrics(load_cases_from_csv(""))

    assert metrics.input_rows == 0
    assert metrics.status is MetricStatus.NO_MEASURABLE_CASES
    assert metrics.sla_met_percent is None


def test_empty_input_returns_no_measurable_cases() -> None:
    metrics = compute_metrics(load_cases_from_csv(csv_text()))
    presentation = metrics.to_presentation()

    assert metrics.input_rows == 0
    assert metrics.status is MetricStatus.NO_MEASURABLE_CASES
    assert metrics.measurable_closed == 0
    assert metrics.mean_cycle_time_hours is None
    assert metrics.median_cycle_time_hours is None
    assert metrics.sla_met_percent is None
    assert metrics.rework_rate_percent is None
    assert presentation["status"] == "no measurable cases"
    assert presentation["sla_met_percent"] is None


def test_only_excluded_rows_do_not_fake_attainment() -> None:
    metrics = compute_metrics(
        load_cases_from_csv(
            csv_text(
                row(case_id="C-300", closed_at=""),
                row(case_id="C-301", received_at="not-a-date"),
            )
        )
    )

    assert metrics.status is MetricStatus.NO_MEASURABLE_CASES
    assert metrics.measurable_closed == 0
    assert metrics.sla_met_percent is None
    assert metrics.excluded_count == 2


def test_backlog_only_input_returns_no_measurable_cases() -> None:
    metrics = compute_metrics(
        load_cases_from_csv(csv_text(row(case_id="C-400", status="open", closed_at="")))
    )

    assert metrics.status is MetricStatus.NO_MEASURABLE_CASES
    assert metrics.measurable_closed == 0
    assert metrics.backlog_cases == 1
    assert metrics.sla_met_percent is None
