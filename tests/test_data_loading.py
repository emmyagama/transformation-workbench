from datetime import timedelta, timezone
from importlib.resources import files

import pytest

from tests.helpers import HEADER, csv_text, row
from transformation_workbench.data import (
    DataContractError,
    load_cases_from_csv,
    parse_utc_timestamp,
)


def test_fixture_is_readable_as_a_package_resource() -> None:
    fixture = files("transformation_workbench").joinpath(
        "data",
        "synthetic_cases.csv",
    )

    result = load_cases_from_csv(fixture.read_text(encoding="utf-8"))

    assert result.input_rows == 15


def test_fixture_loads_expected_rows_and_utc_timestamps(fixture_csv: str) -> None:
    result = load_cases_from_csv(fixture_csv)

    assert result.input_rows == 15
    assert len(result.cases) == 12
    assert {issue.case_id: issue.reason for issue in result.invalid_rows} == {
        "C-006": "INCOMPLETE_MISSING_CLOSED_AT",
        "C-010": "INVALID_DATE",
        "C-011": "OUT_OF_ORDER",
    }
    assert all(case.received_at.tzinfo is timezone.utc for case in result.cases)
    assert all(case.received_at.utcoffset() == timedelta(0) for case in result.cases)


def test_invalid_calendar_date_is_rejected_with_reason() -> None:
    result = load_cases_from_csv(
        csv_text(row(case_id="C-200", received_at="2026-02-30T09:00:00Z"))
    )

    assert len(result.cases) == 0
    assert result.invalid_rows[0].reason == "INVALID_DATE"


@pytest.mark.parametrize(
    ("bad_row", "expected_reason"),
    [
        (row(priority="P9"), "INVALID_PRIORITY:P9"),
        (row(status="pending"), "INVALID_STATUS:pending"),
        (row(rework_count="many"), "INVALID_REWORK_COUNT:many"),
        (row(rework_count="-1"), "INVALID_REWORK_COUNT:-1"),
        (row(case_id=""), "MISSING_CASE_ID"),
        (row(closed_at=""), "INCOMPLETE_MISSING_CLOSED_AT"),
        (row(status="duplicate", duplicate_of=""), "INCOMPLETE_MISSING_DUPLICATE_OF"),
        (row(duplicate_of="C-100"), "UNEXPECTED_DUPLICATE_OF:C-100"),
        (row(received_at=""), "INCOMPLETE_MISSING_RECEIVED_AT"),
        (row(acknowledged_at=""), "INCOMPLETE_MISSING_ACKNOWLEDGED_AT"),
        (row(status=""), "INCOMPLETE_MISSING_STATUS"),
        (row(priority=""), "INCOMPLETE_MISSING_PRIORITY"),
        (row(rework_count=""), "INCOMPLETE_MISSING_REWORK_COUNT"),
        (
            row(
                received_at="2026-03-02T00:00:00Z",
                acknowledged_at="2026-03-01T00:00:00Z",
            ),
            "OUT_OF_ORDER",
        ),
        (row(status="open"), "UNEXPECTED_CLOSED_AT"),
        (row(status="awaiting_info"), "UNEXPECTED_CLOSED_AT"),
    ],
)
def test_row_validation_reasons(bad_row: str, expected_reason: str) -> None:
    result = load_cases_from_csv(csv_text(bad_row))

    assert result.input_rows == 1
    assert len(result.cases) == 0
    assert result.invalid_rows[0].reason == expected_reason


@pytest.mark.parametrize(
    "value",
    ["01", "+1", " 1", "1 ", "1.0", "١", "١٢"],
)
def test_rework_count_rejects_non_canonical_integers(value: str) -> None:
    result = load_cases_from_csv(csv_text(row(rework_count=value)))

    assert len(result.cases) == 0
    assert result.invalid_rows[0].reason == f"INVALID_REWORK_COUNT:{value}"


@pytest.mark.parametrize(
    "value",
    [
        "٢٠٢٦-03-01T00:00:00Z",
        "2026-03-01T00:00:00z",
        " 2026-03-01T00:00:00Z",
        "2026-03-01T00:00:00+00:00",
    ],
)
def test_timestamp_rejects_non_ascii_or_noncanonical_values(value: str) -> None:
    result = load_cases_from_csv(csv_text(row(received_at=value)))

    assert len(result.cases) == 0
    assert result.invalid_rows[0].reason == "INVALID_DATE"


def test_duplicate_identifier_is_rejected() -> None:
    result = load_cases_from_csv(csv_text(row(), row()))

    assert len(result.cases) == 1
    assert result.invalid_rows[0].reason == "DUPLICATE_CASE_ID:C-100"


def test_invalid_row_does_not_reserve_case_id() -> None:
    result = load_cases_from_csv(
        csv_text(
            row(case_id="C-123", rework_count="invalid"),
            row(case_id="C-123"),
        )
    )

    assert result.input_rows == 2
    assert [case.case_id for case in result.cases] == ["C-123"]
    assert result.cases[0].row_number == 3
    assert result.invalid_rows[0].reason == "INVALID_REWORK_COUNT:invalid"


def test_internal_blank_record_is_reported() -> None:
    csv_input = (
        HEADER
        + "\n"
        + row(case_id="C-500")
        + "\n\n"
        + row(case_id="C-501")
        + "\n"
    )
    result = load_cases_from_csv(csv_input)

    assert result.input_rows == 3
    assert [case.case_id for case in result.cases] == ["C-500", "C-501"]
    assert len(result.invalid_rows) == 1
    issue = result.invalid_rows[0]
    assert (issue.row_number, issue.case_id, issue.reason) == (
        3,
        None,
        "EMPTY_ROW",
    )


def test_whitespace_only_record_is_reported_as_empty() -> None:
    result = load_cases_from_csv(HEADER + "\n   \n" + row(case_id="C-502") + "\n")

    assert result.input_rows == 2
    assert result.invalid_rows[0].reason == "EMPTY_ROW"
    assert [case.case_id for case in result.cases] == ["C-502"]


def test_final_newline_does_not_create_a_blank_record() -> None:
    result = load_cases_from_csv(csv_text(row(case_id="C-503")))

    assert result.input_rows == 1
    assert len(result.cases) == 1
    assert result.invalid_rows == ()


def test_header_only_input_has_no_rows_or_issues() -> None:
    result = load_cases_from_csv(csv_text())

    assert result.input_rows == 0
    assert result.cases == ()
    assert result.invalid_rows == ()


@pytest.mark.parametrize(
    ("received_at", "acknowledged_at", "closed_at"),
    [
        (
            "2026-03-14T00:00:00Z",
            "2026-03-14T00:00:00Z",
            "2026-03-15T00:00:00Z",
        ),
        (
            "2026-03-01T00:00:00Z",
            "2026-03-14T00:00:00Z",
            "2026-03-15T00:00:00Z",
        ),
        (
            "2026-03-01T00:00:00Z",
            "2026-03-02T00:00:00Z",
            "2026-03-14T00:00:00Z",
        ),
    ],
)
def test_future_event_timestamp_is_excluded(
    received_at: str, acknowledged_at: str, closed_at: str
) -> None:
    result = load_cases_from_csv(
        csv_text(
            row(
                received_at=received_at,
                acknowledged_at=acknowledged_at,
                closed_at=closed_at,
            )
        )
    )

    assert result.cases == ()
    assert result.invalid_rows[0].reason == "FUTURE_OF_SNAPSHOT"


@pytest.mark.parametrize(
    ("rows", "expected_reason"),
    [
        (
            (row(case_id="C-600"), row(case_id="C-600", status="pending")),
            "DUPLICATE_CASE_ID:C-600",
        ),
        (
            (row(status="pending", received_at="not-a-date"),),
            "INVALID_STATUS:pending",
        ),
        (
            (row(received_at="not-a-date", rework_count="invalid"),),
            "INVALID_DATE",
        ),
        (
            (
                row(
                    status="duplicate",
                    duplicate_of="",
                    rework_count="invalid",
                ),
            ),
            "INVALID_REWORK_COUNT:invalid",
        ),
        (
            (
                row(
                    status="duplicate",
                    duplicate_of="",
                    received_at="2026-03-02T00:00:00Z",
                    acknowledged_at="2026-03-01T00:00:00Z",
                ),
            ),
            "INCOMPLETE_MISSING_DUPLICATE_OF",
        ),
        (
            (
                row(
                    closed_at="",
                    received_at="2026-03-02T00:00:00Z",
                    acknowledged_at="2026-03-01T00:00:00Z",
                ),
            ),
            "OUT_OF_ORDER",
        ),
        (
            (row(status="open", closed_at="2026-03-14T00:00:00Z"),),
            "UNEXPECTED_CLOSED_AT",
        ),
    ],
)
def test_validation_reason_precedence(
    rows: tuple[str, ...], expected_reason: str
) -> None:
    result = load_cases_from_csv(csv_text(*rows))

    assert expected_reason in {issue.reason for issue in result.invalid_rows}


def test_missing_required_columns_raise_contract_error() -> None:
    with pytest.raises(DataContractError):
        load_cases_from_csv("case_id,received_at\nC-1,2026-03-01T00:00:00Z\n")


@pytest.mark.parametrize(
    "value",
    [
        "2026-02-30T09:00:00Z",
        "2026-03-01T09:00:00+00:00",
        "٢٠٢٦-03-01T09:00:00Z",
        "2026-03-01T09:00:00z",
        " 2026-03-01T09:00:00Z",
    ],
)
def test_parse_utc_timestamp_is_strict(value: str) -> None:
    with pytest.raises(ValueError):
        parse_utc_timestamp(value)
