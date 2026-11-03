"""Export immutable, SQL-verified historical snapshots from local PostgreSQL."""

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from .analytics import AnalyticsFilter, QUERY_NAMES, query_sql, run_analytics
from .data_access import COLUMNS, snapshot_analytics, validate_frame
from .database import connect_database
from .ingestion import DEFAULT_ENDPOINT

EXPORT_SQL = """SELECT service_date, day_type, bus, rail_boardings, total_rides
FROM daily_ridership WHERE service_date >= %s AND service_date < %s ORDER BY service_date"""


def export_snapshot(directory: Path, filters: AnalyticsFilter) -> dict:
    """Read a stable database view, validate it, and prove SQL engine parity.

    A new output directory is required. Date bounds define the exported period;
    day-type subsets are prohibited. No API or database access occurs in the UI.
    """
    if filters.day_type != "All":
        raise ValueError("Snapshot export requires all day types")
    if directory.exists():
        raise ValueError("Snapshot directory already exists; choose a new version")
    with connect_database() as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        rows = connection.execute(EXPORT_SQL, filters.parameters[:2]).fetchall()
        frame = validate_frame(pd.DataFrame(rows, columns=COLUMNS))
        if frame.empty:
            raise ValueError("Cannot publish an empty snapshot")
        report = run_analytics(connection, filters)
    offline = snapshot_analytics(frame, filters)
    for name in QUERY_NAMES:
        left = report[name].map(lambda value: float(value) if hasattr(value, "as_tuple") else value)
        pd.testing.assert_frame_equal(left, offline[name], check_dtype=False, rtol=1e-10, atol=1e-8)
    directory.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=directory.parent) as temporary:
        staging = Path(temporary) / "snapshot"
        staging.mkdir()
        payload = staging / "daily_ridership.parquet"
        frame.to_parquet(payload, index=False)
        metadata = {
            "schema_version": 1,
            "source_url": DEFAULT_ENDPOINT,
            "source_name": "Chicago CTA Daily Boarding Totals (6iiy-9s97)",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "requested_start": filters.start_date.isoformat(),
            "requested_end_exclusive": filters.end_date.isoformat(),
            "min_date": str(frame.service_date.min()), "max_date": str(frame.service_date.max()),
            "row_count": len(frame),
            "missing_calendar_days": int(report["summary"].iloc[0].missing_days),
            "sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
            "sql_sha256": hashlib.sha256("".join(query_sql(n) for n in QUERY_NAMES).encode()).hexdigest(),
            "verification": "PostgreSQL and DuckDB results matched for all six analytics queries",
        }
        (staging / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
        # Save SQL results alongside the data for review and reproducible auditing.
        audit = {name: json.loads(table.to_json(orient="records", date_format="iso")) for name, table in offline.items()}
        (staging / "analytics.json").write_text(json.dumps(audit, indent=2) + "\n")
        staging.rename(directory)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    metadata = export_snapshot(args.output, AnalyticsFilter(args.start_date, args.end_date))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
