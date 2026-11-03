"""Analytical method checks with synthetic, explicitly non-CTA fixtures."""

from datetime import date, timedelta

import pandas as pd
import pytest

from urbanflow_ai.data_access import COLUMNS
from urbanflow_ai.history import coverage_details
from urbanflow_ai.research import (
    annual_summary, day_type_contrasts, matched_composition, monthly_aggregates,
    moving_block_interval, recovery_indices, standardized_periods,
)


def fixture(years=(2017, 2018, 2019, 2024), missing=()):
    rows = []
    for year in years:
        day = date(year, 1, 1)
        while day.year == year:
            if day not in missing:
                kind = 'A' if day.weekday() == 5 else 'U' if day.weekday() == 6 else 'W'
                bus, rail = (60, 40) if year < 2020 else (48, 20)
                rows.append((day, kind, bus, rail, bus + rail))
            day += timedelta(days=1)
    return pd.DataFrame(rows, columns=COLUMNS)


def test_same_month_and_day_type_recovery_not_calendar_counts():
    result = recovery_indices(monthly_aggregates(fixture()))
    assert len(result) == 72
    assert (result.bus_index == 80).all()
    assert (result.rail_index == 50).all()
    assert (result.total_index == 68).all()
    assert (result.bus_minus_rail_pp == 30).all()
    period = standardized_periods(result)
    assert (period.months == 12).all()


def test_missing_day_excludes_entire_month_and_baseline_cell():
    months = monthly_aggregates(fixture(missing=(date(2024, 2, 1), date(2018, 3, 1))))
    indices = recovery_indices(months)
    assert not (indices.month_number == 2).any()
    assert len(indices[(indices.baseline == '2019') & (indices.month_number == 3)]) == 3
    assert indices[(indices.baseline == '2017-2019') & (indices.month_number == 3)].empty


def test_incomplete_year_not_given_yoy_change():
    frame = fixture(years=(2023, 2024), missing=(date(2024, 2, 1),))
    annual = annual_summary(monthly_aggregates(frame), coverage_details(frame))
    assert annual.total_yoy_pct.isna().all()
    assert annual.iloc[0].complete_year
    assert not annual.iloc[1].complete_year


def test_baseline_zero_is_unavailable():
    months = monthly_aggregates(fixture(years=(2019, 2024)))
    months.loc[months.year == 2019, 'rail_daily'] = 0
    result = recovery_indices(months)
    assert result.rail_index.isna().all()


def test_equal_baseline_year_weighting():
    months = monthly_aggregates(fixture())
    months.loc[months.year == 2017, 'bus_daily'] = 30
    result = recovery_indices(months)
    assert result[result.baseline == '2017-2019'].iloc[0].bus_index == pytest.approx(48 / 50 * 100)


def test_matched_composition_uses_identical_2019_calendar_weights():
    months = monthly_aggregates(fixture())
    result = matched_composition(months, 2024)
    latest = result[result.year == 2024].iloc[0]
    assert latest.bus_recovery_index == pytest.approx(80)
    assert latest.rail_recovery_index == pytest.approx(50)
    assert latest.standardized_bus_share_pct == pytest.approx(48 / 68 * 100)


def test_block_bootstrap_reproducibility_and_constant_contrast():
    assert moving_block_interval([3] * 24) == (3, 3)
    assert moving_block_interval(list(range(24))) == moving_block_interval(list(range(24)))
    with pytest.raises(ValueError):
        moving_block_interval([1, 2])


def test_day_type_paired_contrasts_report_unsupported_hypothesis():
    indices = recovery_indices(monthly_aggregates(fixture()))
    result = day_type_contrasts(indices)
    assert (result.mean_gap_pp == 0).all()
    assert (result.positive_months == 0).all()


def test_empty_research_input_is_explicit():
    with pytest.raises(ValueError, match='nonempty'):
        monthly_aggregates(pd.DataFrame(columns=COLUMNS))


def test_monthly_changes_do_not_bridge_missing_months():
    from urbanflow_ai.research import monthly_changes
    monthly = monthly_aggregates(fixture(years=(2019, 2024), missing=(date(2024, 2, 1),)))
    changes = monthly_changes(monthly)
    march = changes[(changes.year == 2024) & (changes.month_number == 3)]
    assert march.bus_daily_mom_pct.isna().all()


@pytest.mark.integration
def test_research_sql_matches_postgres(monkeypatch):
    import os
    import psycopg
    from urbanflow_ai import database
    from urbanflow_ai.research import verify_postgres_monthly
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set TEST_DATABASE_URL for historical SQL integration')
    frame = fixture(years=(2019, 2024), missing=(date(2024, 2, 1),))
    connection = psycopg.connect(url)
    try:
        connection.execute('CREATE TEMP TABLE daily_ridership (service_date DATE, day_type TEXT, bus INTEGER, rail_boardings INTEGER, total_rides INTEGER)')
        with connection.cursor() as cursor:
            cursor.executemany('INSERT INTO daily_ridership VALUES (%s,%s,%s,%s,%s)', list(frame.itertuples(index=False, name=None)))
        connection.commit()
        monkeypatch.setattr(database, 'connect_database', lambda: connection)
        result = verify_postgres_monthly(frame, monthly_aggregates(frame))
        assert result['matched']
        assert result['monthly_cells'] == 72
    finally:
        connection.close()
