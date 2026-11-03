"""Presentation definitions and metadata labels; no analytical recalculation."""

UNKNOWN = "Not recorded"
SOURCE_URL = "https://data.cityofchicago.org/Transportation/CTA-Ridership-Daily-Boarding-Totals/6iiy-9s97"
SECTIONS = (
    "01 · Data source & coverage", "02 · Data quality & exclusions",
    "03 · Metric definitions", "04 · Assumptions & limitations", "05 · Reproducibility",
)


def provenance_labels(metadata):
    """Format validated metadata without inferring missing source history."""
    coverage = metadata.get("coverage") or {}
    def count(value):
        return f"{value:,}" if value is not None else UNKNOWN
    return {
        "records": count(coverage.get("row_count")),
        "first": coverage.get("first_date") or UNKNOWN,
        "last": coverage.get("last_date") or UNKNOWN,
        "missing": count(len(coverage["missing_dates"])) if "missing_dates" in coverage else UNKNOWN,
        "duplicates": count(coverage.get("duplicate_dates")),
        "source_rows": count(metadata.get("source_row_count")),
        "quarantined": count(metadata.get("quarantined_rows")),
        "retrieved": metadata.get("source_retrieved_at_utc") or UNKNOWN,
        "generated": metadata.get("generated_at_utc") or UNKNOWN,
        "read": metadata.get("database_read_at_utc") or UNKNOWN,
        "environment": "Historical Parquet snapshot" if metadata.get("backend") == "snapshot" else "Local PostgreSQL read",
    }


METRICS = {
    "Recovery index · baseline = 100": (
        "100 × target monthly average daily boardings / baseline same-month, same-CTA-day-type average daily boardings.",
        "`research.recovery_indices()` uses complete months. The 2019 reference uses one year; "
        "2017–2019 equally averages the three individual years' monthly daily means and requires all three years. "
        "Zero or unavailable denominators produce unavailable comparisons. Explorer target months must be fully selected, "
        "complete, and post-2019; reference data comes from full history, outside target filters. "
        "100 means equal boardings per service date, not equal unique passengers. "
        "`standardized_periods()` equally averages monthly indices; it is not a ratio of annual totals. "
        "Overview uses a complete year; shorter research windows explicitly identify matched months.",
    ),
    "Year-over-year · comparable monthly daily means": (
        "100 × (current monthly daily mean / prior-year same-month, same-day-type daily mean − 1).",
        "`research.monthly_changes()` reads full history before `explorer.yoy_series()` filters target months. "
        "Both calendar months must be complete. Missing references remain gaps; zero references have no defined percentage change. "
        "The archived annual research table is different: `annual_summary()` compares annual totals only when both adjacent years are complete.",
    ),
    "Mode share · raw and matched-calendar": (
        "Mode share is the percentage of all boardings made by bus or rail. Raw bus share (%) = 100 × bus boardings / total boardings; rail share uses the same denominator. A zero total has no defined share.",
        "Matched-calendar comparison applies the same calendar weights to each year, reducing differences caused by the number of each day type. `research.matched_composition()` compares the latest complete-month window across years using fixed 2019 "
        "month/day-type service-day counts as weights. Every required month/day-type cell must exist. "
        "Weighted bus and rail daily means determine standardized shares. Raw shares retain each year's calendar mix. "
        "These measures answer different questions; calendar weighting is independent of the recovery baseline selector and is not formal seasonal adjustment.",
    ),
    "Trends, seasonal views, and filters": (
        "Daily = observed boardings; monthly = average per service date; annual Explorer = observed-day-weighted daily average, not annual total.",
        "`dashboard_metrics.explorer_series()` requires fully selected complete months for monthly, seasonal, and recovery views, "
        "and all 12 complete selected months for annual views. Seasonal views align calendar months across years; partial years remain partial. "
        "Daily rolling means require seven consecutive observed, selected calendar dates; day-type filtering can prevent eligibility. "
        "Missing dates are never zero-filled. UI end dates are inclusive and converted to exclusive next-day bounds. "
        "Date/year/day-type/mode selections filter target observations consistently; completeness is assessed before splitting CTA day types. "
        "W = weekday, A = Saturday, U = Sunday/holiday, including holidays on weekdays. Calendar weekend SQL comparisons are a separate definition.",
    ),
    "Archived 4A sensitivity checks": (
        "Persistence and baseline sensitivity support observed differences, not causes.",
        "The January 2022–August 2026 paired analysis uses circular blocks of three/six months, 5,000 bootstrap repetitions, seed 42. "
        "Percentile ranges describe conditional resampling sensitivity, not measurement-error confidence or causal effects. "
        "Trend, dependence, circular wrapping, and baseline uncertainty limit inference. "
        "Unusual-day screening uses same-year/month/day-type median and MAD, at least four observations, "
        "and absolute modified z-score > 3.5. Flagged valid days remain in primary metrics; outlier-exclusion sensitivity is not implemented.",
    ),
}

REPRODUCE = """python -m urbanflow_ai.research \\
  --snapshot data/history/cta-2026-11-01-v1 \\
  --output /tmp/urbanflow-research-reproduction
python -m urbanflow_ai.dashboard_data export \\
  --archive data/history/cta-2026-11-01-v1 \\
  --output /tmp/urbanflow-dashboard-reproduction
python -m pytest -q
# Optional PostgreSQL integration tests (requires a dedicated local test database):
TEST_DATABASE_URL=postgresql:///urbanflow_ai_test python -m pytest -q
python -m streamlit run streamlit_app.py"""
