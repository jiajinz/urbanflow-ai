"""Deterministic validation tests with no live API dependency."""

from copy import deepcopy
from datetime import date

import pytest

from urbanflow_ai.processing import (
    ProcessingError,
    parse_count,
    parse_service_date,
    process_records,
)

RECORD = {
    "service_date": "2026-08-31T00:00:00.000",
    "day_type": "W",
    "bus": "643844",
    "rail_boardings": "432794",
    "total_rides": "1076638",
}


def test_valid_record_conversion_preserves_input():
    source = [deepcopy(RECORD)]
    before = deepcopy(source)
    result = process_records(source)
    assert source == before
    assert result.fetched_count == 1
    clean = result.valid_records[0]
    assert clean.service_date == date(2026, 8, 31)
    assert clean.bus == 643844
    assert clean.total_rides == clean.bus + clean.rail_boardings
    assert result.date_range == (date(2026, 8, 31), date(2026, 8, 31))
    assert result.rejected_records == ()


@pytest.mark.parametrize("value", ["2026-08-31", "2026-08-31T00:00:00.000"])
def test_valid_dates(value):
    assert parse_service_date(value) == date(2026, 8, 31)


@pytest.mark.parametrize("value", [None, "", "2026-02-30", "bad", 123,
                                        "2026-08-31garbage", "2026-08-31T12:00:00"])
def test_invalid_dates(value):
    with pytest.raises(ValueError, match="service_date"):
        parse_service_date(value)


@pytest.mark.parametrize(
    "value, expected", [("0", 0), ("123", 123), (0, 0), (123, 123)]
)
def test_valid_counts(value, expected):
    assert parse_count(value, "bus") == expected


@pytest.mark.parametrize("value", [None, "", "bad", "-1", -1, "1.5", "1.0",
                                        1.0, True, "1e3", "NaN", " 12", [], {}])
def test_invalid_counts(value):
    with pytest.raises(ValueError, match="bus"):
        parse_count(value, "bus")


@pytest.mark.parametrize("field", sorted(RECORD))
def test_missing_fields_are_reported(field):
    invalid = {key: value for key, value in RECORD.items() if key != field}
    result = process_records([RECORD, invalid])
    assert len(result.valid_records) == 1
    rejection = result.rejected_records[0]
    assert rejection.index == 1
    assert field in rejection.errors[0]


@pytest.mark.parametrize("field", sorted(RECORD))
def test_null_fields_are_reported(field):
    result = process_records([{**RECORD, field: None}])
    assert not result.valid_records
    assert field in result.rejected_records[0].errors[0]


@pytest.mark.parametrize("value", ["X", [], {}])
def test_invalid_day_type(value):
    result = process_records([{**RECORD, "day_type": value}])
    assert "day_type" in result.rejected_records[0].errors[0]


def test_total_consistency():
    result = process_records([{**RECORD, "total_rides": "1"}])
    assert "must equal" in result.rejected_records[0].errors[0]


def test_duplicates_and_legitimate_repeated_measurements():
    result = process_records([
        RECORD, RECORD,
        {**RECORD, "bus": "643845", "total_rides": "1076639"},
        {**RECORD, "service_date": "2026-08-30"},
    ])
    assert len(result.valid_records) == 2
    assert result.duplicate_count == 2
    assert "identical" in result.rejected_records[0].errors[0]
    assert "conflicting" in result.rejected_records[1].errors[0]


def test_invalid_record_does_not_reserve_date():
    result = process_records([{**RECORD, "bus": "bad"}, RECORD])
    assert len(result.valid_records) == 1
    assert result.duplicate_count == 0


def test_empty_input():
    result = process_records([])
    assert result.fetched_count == 0
    assert result.date_range is None
    assert result.valid_records == result.rejected_records == ()


def test_mixed_records():
    result = process_records([RECORD, None, {**RECORD, "bus": "-1"}])
    assert result.fetched_count == 3
    assert len(result.valid_records) == 1
    assert [record.index for record in result.rejected_records] == [1, 2]


@pytest.mark.parametrize(
    "records", [{}, None, "bad", [{}], [None], [{"new_schema": 1}]]
)
def test_systemic_structure_or_schema_failure(records):
    with pytest.raises(ProcessingError):
        process_records(records)


def test_pipeline_uses_raw_ingestion_and_formats_summary(monkeypatch):
    from urbanflow_ai import ingestion, pipeline
    import json
    from unittest.mock import MagicMock

    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps([
        RECORD, {**RECORD, "bus": "bad"}, RECORD
    ]).encode()
    monkeypatch.setattr(ingestion, "urlopen", lambda *args, **kwargs: response)
    result = pipeline.run_pipeline()
    assert pipeline.format_summary(result) == (
        "Fetched: 3\nValid: 1\nRejected: 2\nDuplicates: 1\n"
        "Accepted date range: 2026-08-31 to 2026-08-31"
    )


def test_raw_ingestion_still_rejects_non_array(monkeypatch):
    from urbanflow_ai import ingestion
    from unittest.mock import MagicMock

    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{}'
    monkeypatch.setattr(ingestion, "urlopen", lambda *args, **kwargs: response)
    with pytest.raises(ingestion.IngestionError, match="JSON array"):
        ingestion.fetch_daily_boardings(validate_records=False)


def test_pipeline_forwards_range_and_reports_missing_days(monkeypatch, capsys):
    from urbanflow_ai import pipeline
    from unittest.mock import MagicMock
    import sys

    fetch = MagicMock(return_value=[RECORD])
    monkeypatch.setattr(pipeline, "fetch_daily_boardings", fetch)
    monkeypatch.setattr(sys, "argv", ["pipeline", "--start-date", "2026-08-01", "--end-date", "2026-09-01"])
    pipeline.main()
    fetch.assert_called_once_with(
        endpoint=None, timeout=10.0, validate_records=False,
        start_date=date(2026, 8, 1), end_date=date(2026, 9, 1),
    )
    output = capsys.readouterr().out
    assert "Expected calendar days: 31" in output
    assert "Days without accepted records: 30" in output


def test_cli_requires_both_date_bounds_before_fetching(monkeypatch):
    from urbanflow_ai import pipeline
    from unittest.mock import MagicMock
    import sys

    fetch = MagicMock()
    monkeypatch.setattr(pipeline, "fetch_daily_boardings", fetch)
    monkeypatch.setattr(sys, "argv", ["pipeline", "--start-date", "2026-08-01"])
    with pytest.raises(SystemExit) as caught:
        pipeline.main()
    assert caught.value.code == 2
    fetch.assert_not_called()
