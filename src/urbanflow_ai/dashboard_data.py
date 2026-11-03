"""Explicit local PostgreSQL / public Parquet analytical data boundaries."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import psycopg

from .analytics import SQL_DIRECTORY
from .dashboard_metrics import AnalyticalData, build_analytical_data
from .data_access import COLUMNS, DataAccessError, validate_frame
from .database import DatabaseError, connect_database
from .ingestion import DEFAULT_ENDPOINT

TABLE_NAMES = ("daily", "monthly", "recovery", "annual", "periods", "composition")
DEFAULT_BUNDLE = Path(__file__).resolve().parents[2] / "data/dashboard/cta-2026-11-01-v2"


def definition_hashes():
    """Invalidate exported results when SQL or analytical definitions change."""
    root = Path(__file__).parent
    sources = {"research.py": root / "research.py", "dashboard_metrics.py": root / "dashboard_metrics.py"}
    sources.update({f"sql/{file.name}": file for file in (root / "sql").glob("*.sql")})
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sorted(sources.items())}


def load_archive(directory: Path):
    """Reuse the validated 4A PostgreSQL export with its original provenance."""
    try:
        manifest = json.loads((directory / "manifest.json").read_text())
        path = directory / "daily_ridership.parquet"
        if manifest["source_url"] != DEFAULT_ENDPOINT or hashlib.sha256(path.read_bytes()).hexdigest() != manifest["parquet_sha256"]:
            raise DataAccessError("Historical archive checksum or provenance is invalid")
        frame = validate_frame(pd.read_parquet(path))
        return build_analytical_data(frame, {
            "backend": "snapshot", "source_url": DEFAULT_ENDPOINT,
            "source_retrieved_at_utc": manifest["retrieved_at_utc"],
            "source_row_count": manifest["source_coverage"]["row_count"],
            "quarantined_rows": manifest["rejected_count"],
            "input_parquet_sha256": manifest["parquet_sha256"],
        })
    except DataAccessError:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        raise DataAccessError("Historical archive is missing or invalid") from None


def load_postgres():
    """Read validated rows and existing research SQL in one stable transaction."""
    try:
        with connect_database() as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            rows = connection.execute("SELECT service_date,day_type,bus,rail_boardings,total_rides FROM daily_ridership ORDER BY service_date").fetchall()
            frame = validate_frame(pd.DataFrame(rows, columns=COLUMNS))
            if frame.empty:
                raise DataAccessError("No validated records are available in PostgreSQL")
            from datetime import timedelta
            first, last = frame.service_date.min(), frame.service_date.max()
            cursor = connection.execute(SQL_DIRECTORY.joinpath("research_monthly.sql").read_text(), (first, last + timedelta(days=1)) * 2)
            monthly = pd.DataFrame(cursor.fetchall(), columns=[column[0] for column in cursor.description])
            monthly = monthly.map(lambda value: float(value) if hasattr(value, "as_tuple") else value)
            monthly["month"] = pd.to_datetime(monthly.month)
            monthly["year"], monthly["month_number"] = monthly.month.dt.year, monthly.month.dt.month
        return build_analytical_data(frame, {
            "backend": "postgres", "source_url": DEFAULT_ENDPOINT,
            "database_read_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_retrieved_at_utc": None, "quarantined_rows": None,
        }, monthly=monthly)
    except (DatabaseError, psycopg.Error):
        raise DataAccessError("PostgreSQL access failed; verify DATABASE_URL, server availability, and schema. No fallback was used.") from None


def export_bundle(data: AnalyticalData, directory: Path):
    """Stage six Parquet tables and publish only to a new version directory."""
    if directory.exists():
        raise ValueError("Output exists; choose a new analytical snapshot version")
    if data.daily.empty:
        raise DataAccessError("Cannot export an empty analytical snapshot")
    expected = build_analytical_data(data.daily, data.metadata)
    try:
        for name, table in data.tables.items():
            pd.testing.assert_frame_equal(table, expected.tables[name], check_dtype=False,
                                          check_exact=False, rtol=1e-10, atol=1e-6)
    except AssertionError:
        raise DataAccessError("Analytical tables do not match validated daily data; rebuild them before export") from None
    directory.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=directory.parent) as temporary:
        stage = Path(temporary) / "bundle"
        stage.mkdir()
        hashes = {}
        for name, table in data.tables.items():
            path = stage / f"{name}.parquet"
            table.to_parquet(path, index=False)
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        metadata = {**data.metadata, "schema_version": 1, "kind": "urbanflow-dashboard",
                    "backend": "snapshot", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "table_sha256": hashes, "definition_hashes": definition_hashes()}
        (stage / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
        # Exercise the same loader used by the public app before publication.
        load_bundle(stage)
        stage.rename(directory)
    return metadata


def load_bundle(directory: Path = DEFAULT_BUNDLE):
    """Verify all tables and analytical version; never contact an external service."""
    try:
        metadata = json.loads((directory / "manifest.json").read_text())
        if metadata["schema_version"] != 1 or metadata["kind"] != "urbanflow-dashboard" or metadata["source_url"] != DEFAULT_ENDPOINT:
            raise DataAccessError("Unsupported analytical snapshot schema or provenance")
        if metadata["definition_hashes"] != definition_hashes():
            raise DataAccessError("Analytical definitions changed; regenerate the dashboard snapshot")
        if datetime.fromisoformat(metadata["generated_at_utc"]).utcoffset() is None:
            raise ValueError("Generation timestamp requires a time zone")
        tables = {}
        for name in TABLE_NAMES:
            path = directory / f"{name}.parquet"
            if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["table_sha256"][name]:
                raise DataAccessError("Analytical snapshot checksum mismatch; restore or regenerate the bundle")
            tables[name] = pd.read_parquet(path)
        tables["daily"] = validate_frame(tables["daily"])
        from .history import coverage_details
        if tables["daily"].empty or coverage_details(tables["daily"]) != metadata["coverage"]:
            raise DataAccessError("Analytical snapshot coverage is invalid")
        return AnalyticalData(**tables, metadata=metadata)
    except DataAccessError:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        raise DataAccessError("Dashboard snapshot is missing or invalid; run urbanflow_ai.dashboard_data export") from None


def load_data(backend="snapshot", directory=DEFAULT_BUNDLE):
    """Select one explicit environment; database errors never trigger a fallback."""
    if backend == "snapshot":
        return load_bundle(Path(directory))
    if backend == "postgres":
        return load_postgres()
    raise DataAccessError("URBANFLOW_DATA_BACKEND must be snapshot or postgres")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["export"])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", type=Path, help="Validated 4A PostgreSQL archive")
    source.add_argument("--postgres", action="store_true", help="Read current local PostgreSQL")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = load_postgres() if args.postgres else load_archive(args.archive)
    metadata = export_bundle(data, args.output)
    print(f"Exported {metadata['coverage']['row_count']:,} validated rows and six analytical tables to {args.output}")


if __name__ == "__main__":
    main()
