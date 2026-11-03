"""Bounded-retry, full-history ingestion and auditable PostgreSQL backfills."""

import argparse
import hashlib
import json
import math
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import pandas as pd

from .database import connect_database, persist_records
from .ingestion import DEFAULT_ENDPOINT, IngestionError
from .processing import process_records

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


def request_page(url: str, *, timeout=30.0, retries=3) -> list:
    """Retry only transient transport/HTTP errors; cap Retry-After at 30 seconds.

    At most retries + 1 attempts are made. Malformed JSON and permanent HTTP
    errors fail immediately. Never return a partial or fabricated response.
    """
    if type(retries) is not int or not 0 <= retries <= 5:
        raise ValueError("retries must be an integer from 0 through 5")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    for attempt in range(retries + 1):
        delay = min(2 ** attempt, 30)
        try:
            request = Request(url, headers={"Accept": "application/json"})
            with urlopen(request, timeout=timeout) as response:
                payload = response.read()
        except HTTPError as exc:
            status = exc.code
            retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
            exc.close()
            if status not in RETRYABLE_STATUS or attempt == retries:
                raise IngestionError(f"Historical API returned HTTP {status}") from None
            if retry_after.isdigit():
                delay = min(int(retry_after), 30)
        except (URLError, OSError):
            if attempt == retries:
                raise IngestionError("Historical API request failed or timed out") from None
        else:
            try:
                result = json.loads(payload)
            except (ValueError, UnicodeError):
                raise IngestionError("Historical API returned invalid JSON") from None
            if not isinstance(result, list):
                raise IngestionError("Historical API response must be a JSON array")
            return result
        time.sleep(delay)


def source_coverage(endpoint=DEFAULT_ENDPOINT):
    """Discover bounds and source row count without assuming a starting year."""
    rows = request_page(endpoint + "?" + urlencode({"$query": "SELECT min(service_date) AS first_date, max(service_date) AS last_date, count(*) AS row_count"}))
    if len(rows) != 1:
        raise IngestionError("Historical source coverage is unavailable")
    try:
        return {"first_date": date.fromisoformat(rows[0]["first_date"][:10]).isoformat(),
                "last_date": date.fromisoformat(rows[0]["last_date"][:10]).isoformat(),
                "row_count": int(rows[0]["row_count"])}
    except (KeyError, TypeError, ValueError):
        raise IngestionError("Historical source coverage is invalid") from None


def fetch_history(*, endpoint=DEFAULT_ENDPOINT, page_size=1000):
    """Read all available dates in stable date/row-ID order with bounded pages.

    Bounds and count are checked again before any database write. This detects
    many source changes, not in-place corrections preserving counts and bounds.
    The retained raw response is the reproducibility boundary.
    """
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.query or parsed.fragment:
        raise ValueError("Historical endpoint must be a plain HTTPS resource URL")
    if type(page_size) is not int or not 1 <= page_size <= 5000:
        raise ValueError("page_size must be an integer from 1 through 5000")
    before = source_coverage(endpoint)
    records = []
    # The count bounds requests even if a server accidentally repeats full pages.
    for offset in range(0, before["row_count"] + page_size, page_size):
        query = {"$limit": page_size, "$offset": offset, "$order": "service_date ASC, :id ASC",
                 "$where": f"service_date < '{(date.fromisoformat(before['last_date']) + timedelta(days=1)).isoformat()}T00:00:00'"}
        page = request_page(endpoint + "?" + urlencode(query))
        if len(page) > page_size:
            raise IngestionError("Historical API exceeded the requested page size")
        records.extend(page)
        if len(page) < page_size:
            break
    if source_coverage(endpoint) != before or len(records) != before["row_count"]:
        raise IngestionError("Source coverage changed during pagination; rerun the backfill")
    return records, before


def coverage_details(frame: pd.DataFrame) -> dict:
    """Audit daily grain, duplicates, missing calendar dates, and period coverage."""
    dates = pd.to_datetime(frame.service_date)
    if dates.empty:
        return {"row_count": 0, "duplicate_dates": 0, "missing_dates": [], "monthly": [], "annual": []}
    expected = pd.date_range(dates.min(), dates.max(), freq="D")
    missing = expected.difference(dates)
    monthly = []
    for period in pd.period_range(dates.min(), dates.max(), freq="M"):
        count = int(((dates >= period.start_time) & (dates <= period.end_time)).sum())
        monthly.append({"period": str(period), "observed_days": count,
                        "expected_days": period.days_in_month, "complete": count == period.days_in_month})
    annual = []
    for year in range(dates.min().year, dates.max().year + 1):
        count = int((dates.dt.year == year).sum())
        expected_days = (date(year + 1, 1, 1) - date(year, 1, 1)).days
        annual.append({"year": year, "observed_days": count, "expected_days": expected_days, "complete": count == expected_days})
    return {"row_count": len(frame), "first_date": str(dates.min().date()), "last_date": str(dates.max().date()),
            "duplicate_dates": int(dates.duplicated().sum()), "missing_dates": [str(day.date()) for day in missing],
            "monthly": monthly, "annual": annual}


def backfill(output: Path, *, endpoint=DEFAULT_ENDPOINT, quarantine_rejections=False) -> dict:
    """Validate the entire source before writing; verify database rows afterward."""
    if output.exists():
        raise ValueError("Output exists; choose a new historical snapshot version")
    raw, source = fetch_history(endpoint=endpoint)
    result = process_records(raw)
    if result.rejected_records and not quarantine_rejections:
        raise IngestionError(f"Historical validation rejected {len(result.rejected_records)} rows; no data persisted")
    if result.duplicate_count:
        raise IngestionError("Duplicate service dates require review before persistence")
    columns = ["service_date", "day_type", "bus", "rail_boardings", "total_rides"]
    frame = pd.DataFrame([(r.service_date, r.day_type, r.bus, r.rail_boardings, r.total_rides) for r in result.valid_records], columns=columns)
    coverage = coverage_details(frame)
    if coverage.get("first_date") != source["first_date"] or coverage.get("last_date") != source["last_date"]:
        raise IngestionError("Accepted date bounds do not match source coverage")
    stored = persist_records(result.valid_records)
    with connect_database() as connection:
        rows = connection.execute("""SELECT service_date,day_type,bus,rail_boardings,total_rides
            FROM daily_ridership WHERE service_date >= %s AND service_date <= %s ORDER BY service_date""",
            (date.fromisoformat(source["first_date"]), date.fromisoformat(source["last_date"]))).fetchall()
    exported = pd.DataFrame(rows, columns=columns)
    pd.testing.assert_frame_equal(exported, frame.sort_values("service_date").reset_index(drop=True))
    from tempfile import TemporaryDirectory
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / "history"
        stage.mkdir()
        payload = json.dumps(raw, separators=(",", ":")).encode()
        (stage / "source.json").write_bytes(payload)
        from dataclasses import asdict
        (stage / "quarantine.json").write_text(json.dumps([
            {**asdict(rejected), "raw": raw[rejected.index]} for rejected in result.rejected_records
        ], indent=2) + "\n")
        raw_dates = pd.DataFrame({"service_date": [row["service_date"][:10] for row in raw]})
        (stage / "source_calendar_coverage.json").write_text(json.dumps(coverage_details(raw_dates), indent=2) + "\n")
        exported.to_parquet(stage / "daily_ridership.parquet", index=False)
        (stage / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
        manifest = {"source_url": endpoint, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                    "source_coverage": source, "rejected_count": len(result.rejected_records),
                    "duplicate_count": result.duplicate_count, "raw_sha256": hashlib.sha256(payload).hexdigest(),
                    "parquet_sha256": hashlib.sha256((stage / "daily_ridership.parquet").read_bytes()).hexdigest(),
                    "changed_rows": stored.inserted_or_updated_count, "unchanged_rows": stored.unchanged_count,
                    "database_matches_validated_source": True}
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        stage.rename(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quarantine-rejections", action="store_true", help="Retain rejected rows separately and persist accepted rows only")
    args = parser.parse_args()
    print(json.dumps(backfill(args.output, quarantine_rejections=args.quarantine_rejections), indent=2))


if __name__ == "__main__":
    main()
