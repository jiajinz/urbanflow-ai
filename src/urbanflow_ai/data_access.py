"""Verified offline snapshot access and optional read-only PostgreSQL analytics."""

import hashlib
import json
from pathlib import Path

import duckdb
import pandas as pd
import psycopg

from .analytics import AnalyticsFilter, run_analytics
from .database import DatabaseError, connect_database
from .ingestion import DEFAULT_ENDPOINT
from .processing import process_records

COLUMNS = ["service_date", "day_type", "bus", "rail_boardings", "total_rides"]


class DataAccessError(RuntimeError):
    """Safe, actionable data loading failure."""


def validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate exported rows through the existing pipeline, rejecting any loss."""
    if list(frame.columns) != COLUMNS:
        raise DataAccessError("Snapshot columns do not match schema version 1")
    raw = frame.to_dict("records")
    for row in raw:
        value = row["service_date"]
        row["service_date"] = value.isoformat() if hasattr(value, "isoformat") else value
    try:
        result = process_records(raw)
    except ValueError:
        raise DataAccessError("Snapshot validation failed") from None
    if result.rejected_records:
        raise DataAccessError("Snapshot contains invalid or duplicate rows")
    return pd.DataFrame(
        [(r.service_date, r.day_type, r.bus, r.rail_boardings, r.total_rides) for r in result.valid_records],
        columns=COLUMNS,
    )


def load_snapshot(directory: Path) -> tuple[pd.DataFrame, dict]:
    """Check manifest, provenance, checksum, schema, and coverage before querying."""
    try:
        metadata = json.loads((directory / "manifest.json").read_text())
        if metadata["schema_version"] != 1 or metadata["source_url"] != DEFAULT_ENDPOINT:
            raise DataAccessError("Unsupported snapshot schema or provenance")
        payload = directory / "daily_ridership.parquet"
        if hashlib.sha256(payload.read_bytes()).hexdigest() != metadata["sha256"]:
            raise DataAccessError("Snapshot checksum mismatch; restore the versioned files")
        frame = validate_frame(pd.read_parquet(payload))
        if frame.empty or len(frame) != metadata["row_count"]:
            raise DataAccessError("Snapshot row count does not match its manifest")
        if str(frame.service_date.min()) != metadata["min_date"] or str(frame.service_date.max()) != metadata["max_date"]:
            raise DataAccessError("Snapshot coverage does not match its manifest")
        from datetime import datetime
        if datetime.fromisoformat(metadata["generated_at_utc"]).utcoffset() is None:
            raise ValueError("Timestamp requires a time zone")
        return frame, metadata
    except DataAccessError:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        raise DataAccessError("Snapshot is missing or invalid; regenerate it with urbanflow_ai.snapshot") from None


def snapshot_analytics(frame: pd.DataFrame, filters: AnalyticsFilter):
    """Query validated Parquet rows in an isolated in-memory SQL connection."""
    try:
        clean = validate_frame(frame)
        with duckdb.connect(":memory:") as connection:
            connection.register("snapshot_rows", clean)
            connection.execute("""CREATE TABLE daily_ridership AS SELECT
                CAST(service_date AS DATE) AS service_date, CAST(day_type AS TEXT) AS day_type,
                CAST(bus AS BIGINT) AS bus, CAST(rail_boardings AS BIGINT) AS rail_boardings,
                CAST(total_rides AS BIGINT) AS total_rides FROM snapshot_rows""")
            return run_analytics(connection, filters, dialect="duckdb")
    except duckdb.Error:
        raise DataAccessError("Offline analytics failed; verify the snapshot and SQL version") from None


def postgres_analytics(filters: AnalyticsFilter):
    """Read all metrics in one consistent, read-only PostgreSQL transaction."""
    try:
        with connect_database() as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            return run_analytics(connection, filters)
    except (DatabaseError, psycopg.Error):
        raise DataAccessError("PostgreSQL analytics unavailable; verify database configuration and schema") from None
