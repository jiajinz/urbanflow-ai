"""Data boundary, integrity, and snapshot export contract tests."""

import hashlib
import json
from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import psycopg
import pytest

from urbanflow_ai import data_access, snapshot
from urbanflow_ai.analytics import AnalyticsFilter
from urbanflow_ai.ingestion import DEFAULT_ENDPOINT


@pytest.fixture
def stored(tmp_path):
    frame = pd.DataFrame([(date(2024, 1, 1), "U", 60, 40, 100)], columns=data_access.COLUMNS)
    payload = tmp_path / "daily_ridership.parquet"
    frame.to_parquet(payload, index=False)
    manifest = dict(schema_version=1, source_url=DEFAULT_ENDPOINT, sha256=hashlib.sha256(payload.read_bytes()).hexdigest(), row_count=1, min_date="2024-01-01", max_date="2024-01-01", generated_at_utc="2024-02-01T00:00:00+00:00")
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    return tmp_path, frame, manifest


def test_snapshot_roundtrip_and_source_holiday_classification(stored):
    directory, expected, _ = stored
    frame, metadata = data_access.load_snapshot(directory)
    pd.testing.assert_frame_equal(frame, expected)
    result = data_access.snapshot_analytics(frame, AnalyticsFilter(date(2024, 1, 1), date(2024, 1, 2), "U"))
    assert result["day_comparison"].iloc[0].calendar_type == "Weekday"
    assert metadata["row_count"] == 1


@pytest.mark.parametrize("field,value", [("sha256", "bad"), ("row_count", 2), ("min_date", "2023-01-01"), ("schema_version", 9), ("source_url", "invalid"), ("generated_at_utc", "yesterday")])
def test_invalid_manifest(stored, field, value):
    directory, _, metadata = stored
    metadata[field] = value
    (directory / "manifest.json").write_text(json.dumps(metadata))
    with pytest.raises(data_access.DataAccessError):
        data_access.load_snapshot(directory)


def test_missing_snapshot(tmp_path):
    with pytest.raises(data_access.DataAccessError, match="missing or invalid"):
        data_access.load_snapshot(tmp_path)


@pytest.mark.parametrize("change", ["duplicate", "negative", "total", "schema", "null"])
def test_corrupt_records_rejected(stored, change):
    _, frame, _ = stored
    if change == "duplicate":
        frame = pd.concat([frame, frame])
    elif change == "negative":
        frame.loc[0, "bus"] = -1
    elif change == "total":
        frame.loc[0, "total_rides"] = 0
    elif change == "null":
        frame.loc[0, "bus"] = None
    else:
        frame = frame.drop(columns="bus")
    with pytest.raises(data_access.DataAccessError):
        data_access.validate_frame(frame)


def test_postgres_boundary_hides_server_details(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.side_effect = psycopg.OperationalError("secret connection detail")
    monkeypatch.setattr(data_access, "connect_database", lambda: connection)
    with pytest.raises(data_access.DataAccessError) as caught:
        data_access.postgres_analytics(AnalyticsFilter(date(2024, 1, 1), date(2024, 1, 2)))
    assert "secret" not in str(caught.value)
    connection.__exit__.assert_called_once()


def test_export_refuses_overwrite_before_database_access(stored):
    with pytest.raises(ValueError, match="already exists"):
        snapshot.export_snapshot(stored[0], AnalyticsFilter(date(2024, 1, 1), date(2024, 1, 2)))


def test_export_empty_does_not_publish(tmp_path, monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchall.return_value = []
    monkeypatch.setattr(snapshot, "connect_database", lambda: connection)
    output = tmp_path / "new"
    with pytest.raises(ValueError, match="empty"):
        snapshot.export_snapshot(output, AnalyticsFilter(date(2024, 1, 1), date(2024, 1, 2)))
    assert not output.exists()


def test_export_engine_mismatch_does_not_publish(stored, monkeypatch):
    directory, frame, _ = stored
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchall.return_value = list(frame.itertuples(index=False, name=None))
    monkeypatch.setattr(snapshot, "connect_database", lambda: connection)
    monkeypatch.setattr(snapshot, "run_analytics", lambda *args: {"summary": pd.DataFrame({"wrong": [1]})})
    output = directory / "new"
    with pytest.raises(AssertionError):
        snapshot.export_snapshot(output, AnalyticsFilter(date(2024, 1, 1), date(2024, 1, 2)))
    assert not output.exists()
