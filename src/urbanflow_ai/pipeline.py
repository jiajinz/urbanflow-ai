"""A small API-to-clean-records entry point."""

from datetime import date

from .ingestion import fetch_daily_boardings, validate_date_range
from .processing import ProcessingResult, process_records


def run_pipeline(
    *, endpoint: str | None = None, timeout: float = 10.0,
    start_date: date | None = None, end_date: date | None = None,
) -> ProcessingResult:
    """Fetch the selected batch and collect data quality failures independently."""
    return process_records(fetch_daily_boardings(
        endpoint=endpoint, timeout=timeout, validate_records=False,
        start_date=start_date, end_date=end_date
    ))


def format_summary(result: ProcessingResult) -> str:
    """Format counts and accepted dates without exposing source records."""
    dates = result.date_range
    date_range = f"{dates[0]} to {dates[1]}" if dates else "none"
    return (
        f"Fetched: {result.fetched_count}\n"
        f"Valid: {len(result.valid_records)}\n"
        f"Rejected: {len(result.rejected_records)}\n"
        f"Duplicates: {result.duplicate_count}\n"
        f"Accepted date range: {date_range}"
    )


def main() -> None:
    """Print a concise summary; systemic failures propagate to the caller."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch and validate CTA daily ridership")
    parser.add_argument("--persist", action="store_true", help="Write accepted records to PostgreSQL")
    parser.add_argument("--start-date", type=date.fromisoformat, help="Inclusive start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=date.fromisoformat, help="Exclusive end date (YYYY-MM-DD)")
    args = parser.parse_args()
    try:
        validate_date_range(args.start_date, args.end_date)
    except ValueError as exc:
        parser.error(str(exc))
    if args.start_date is None:
        result = run_pipeline()
    else:
        result = run_pipeline(start_date=args.start_date, end_date=args.end_date)
    summary = format_summary(result)
    if args.start_date is not None:
        expected = (args.end_date - args.start_date).days
        covered = len({
            record.service_date for record in result.valid_records
            if args.start_date <= record.service_date < args.end_date
        })
        summary += (
            f"\nRequested range: [{args.start_date}, {args.end_date})"
            f"\nExpected calendar days: {expected}"
            f"\nDays without accepted records: {expected - covered}"
        )
    if args.persist:
        from .database import persist_records

        stored = persist_records(result.valid_records)
        summary += (
            f"\nDatabase inserted or updated: {stored.inserted_or_updated_count}"
            f"\nDatabase unchanged: {stored.unchanged_count}"
            f"\nTotal stored: {stored.total_stored_count}"
        )
    print(summary)


if __name__ == "__main__":
    main()
