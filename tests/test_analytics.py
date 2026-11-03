"""Deterministic SQL tests execute real queries without network dependencies."""

from datetime import date, timedelta

import pandas as pd
import pytest

from urbanflow_ai.analytics import AnalyticsFilter, query_sql
from urbanflow_ai.data_access import COLUMNS, snapshot_analytics


def sample(start=date(2024, 1, 1), days=60, missing=(), zero=False):
    """Synthetic test fixture only; never exported as CTA data."""
    rows = []
    for n in range(days):
        day = start + timedelta(days=n)
        if day in missing:
            continue
        bus, rail = (0, 0) if zero else (60, 40)
        kind = "A" if day.weekday() == 5 else "U" if day.weekday() == 6 else "W"
        rows.append((day, kind, bus, rail, bus + rail))
    return pd.DataFrame(rows, columns=COLUMNS)


def report(frame=None, start=date(2024, 1, 1), end=date(2024, 3, 1), kind="All"):
    return snapshot_analytics(sample() if frame is None else frame, AnalyticsFilter(start, end, kind))


def test_totals_shares_daily_averages_and_tied_extremes():
    result = report()
    summary = result["summary"].iloc[0]
    assert summary.total_rides == 6000
    assert summary.average_daily_bus == 60
    assert summary.average_daily_rail == 40
    assert summary.bus_share == pytest.approx(.6)
    assert summary.rail_share == pytest.approx(.4)
    assert len(result["extremes"]) == 120
    assert result["day_comparison"].observed_days.sum() == 60
    assert result["daily"].rolling_average_7d.iloc[:6].isna().all()
    assert (result["daily"].rolling_average_7d.iloc[6:] == 100).all()
    assert result["monthly"].iloc[1].month_over_month_change == pytest.approx(2900 / 3100 - 1)


def test_half_open_date_filter():
    result = report(start=date(2024, 1, 2), end=date(2024, 1, 4))
    assert result["summary"].iloc[0].total_rides == 200
    assert list(result["daily"].service_date) == [date(2024, 1, 2), date(2024, 1, 3)]


def test_missing_date_is_not_zero_and_breaks_rolling_window_and_month_comparison():
    result = report(sample(missing=(date(2024, 1, 8),)))
    assert result["summary"].iloc[0].missing_days == 1
    daily = result["daily"]
    assert pd.isna(daily.iloc[7].total_rides)
    assert daily.iloc[7:14].rolling_average_7d.isna().all()
    assert daily.iloc[14].rolling_average_7d == 100
    assert result["monthly"].month_over_month_change.isna().all()
    assert not result["weekly"].iloc[1].complete_week


def test_partial_months_and_weeks_are_labeled_and_not_compared():
    result = report(start=date(2024, 1, 2), end=date(2024, 2, 15))
    assert not result["monthly"].complete_month.any()
    assert result["monthly"].month_over_month_change.isna().all()
    assert not result["weekly"].iloc[0].complete_week
    assert not result["weekly"].iloc[-1].complete_week


def test_missing_entire_month_does_not_bridge_month_over_month():
    frame = pd.concat([sample(days=31), sample(start=date(2024, 3, 1), days=31)])
    result = report(frame, end=date(2024, 4, 1))
    assert len(result["monthly"]) == 3
    assert result["monthly"].month_over_month_change.isna().all()


def test_day_filter_preserves_calendar_and_suppresses_month_change():
    result = report(kind="A")
    assert result["summary"].iloc[0].observed_days == 8
    assert result["summary"].iloc[0].missing_days == 0
    assert len(result["daily"]) == 60
    assert result["daily"].rolling_average_7d.isna().all()
    assert result["monthly"].month_over_month_change.isna().all()
    assert list(result["day_comparison"].calendar_type) == ["Weekend"]


@pytest.mark.parametrize("frame", [sample(days=0), sample(zero=True)])
def test_empty_and_zero_denominators(frame):
    result = report(frame)
    assert result["summary"].iloc[0].total_rides == 0
    assert pd.isna(result["summary"].iloc[0].bus_share)
    assert result["monthly"].month_over_month_change.isna().all()
    if frame.empty:
        assert pd.isna(result["summary"].iloc[0].average_daily_bus)
        assert result["extremes"].empty
        assert result["summary"].iloc[0].missing_days == 60


@pytest.mark.parametrize("args", [
    ("2024-01-01", date(2024, 2, 1)),
    (date(2024, 1, 1), date(2024, 1, 1)),
    (date(2024, 2, 1), date(2024, 1, 1)),
    (date(2024, 1, 1), date(2024, 2, 1), "X"),
])
def test_invalid_filters(args):
    with pytest.raises(ValueError):
        AnalyticsFilter(*args)


def test_query_allowlist_and_parameter_binding():
    assert query_sql("summary").count("%s") == 3
    assert query_sql("summary", "duckdb").count("?") == 3
    with pytest.raises(ValueError):
        query_sql("../database")


@pytest.mark.integration
def test_postgres_and_duckdb_execute_identical_sql():
    """A real PostgreSQL engine test in a private temporary table."""
    import os
    import psycopg
    from urbanflow_ai.analytics import QUERY_NAMES, run_analytics
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL for PostgreSQL analytics integration")
    frame = sample(missing=(date(2024, 1, 8),))
    filters = AnalyticsFilter(date(2024, 1, 1), date(2024, 3, 1))
    with psycopg.connect(url) as connection:
        connection.execute("CREATE TEMP TABLE daily_ridership (service_date DATE, day_type TEXT, bus INTEGER, rail_boardings INTEGER, total_rides INTEGER)")
        with connection.cursor() as cursor:
            cursor.executemany("INSERT INTO daily_ridership VALUES (%s,%s,%s,%s,%s)", list(frame.itertuples(index=False, name=None)))
        for kind in ("All", "W", "A", "U"):
            filters = AnalyticsFilter(filters.start_date, filters.end_date, kind)
            postgres = run_analytics(connection, filters)
            offline = snapshot_analytics(frame, filters)
            for name in QUERY_NAMES:
                left = postgres[name].map(lambda v: float(v) if hasattr(v, "as_tuple") else v)
                pd.testing.assert_frame_equal(left, offline[name], check_dtype=False, rtol=1e-10, atol=1e-8)
