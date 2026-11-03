"""Explorer analytical contracts independent of Streamlit and live API access."""

from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from urbanflow_ai.dashboard_data import load_bundle
from urbanflow_ai.dashboard_metrics import ExplorerFilter
from urbanflow_ai.explorer import explorer_model


@pytest.fixture(scope='module')
def data():
    return load_bundle()


def selection(start=date(2025, 1, 1), end=date(2026, 1, 1), **changes):
    options = dict(start_date=start, end_date=end, day_types=('W',), modes=('bus', 'rail'), years=tuple(range(start.year, (end - pd.Timedelta(days=1)).year + 1)))
    options.update(changes)
    return ExplorerFilter(**options)


def test_monthly_values_match_approved_sql_cells(data):
    model = explorer_model(data, selection(), 'Trend', 'Monthly')
    expected = data.monthly[(data.monthly.year == 2025) & (data.monthly.day_type == 'W')].sort_values('month')
    for mode in ['bus', 'rail']:
        actual = model['series'][model['series']['mode'] == mode].sort_values('date')
        assert list(actual.value) == pytest.approx(list(expected[f'{mode}_daily']))
    assert model['selected_dates'] == len(data.daily[(pd.to_datetime(data.daily.service_date).dt.year == 2025) & (data.daily.day_type == 'W')])


def test_annual_aggregation_is_day_weighted_and_excludes_partial_year(data):
    model = explorer_model(data, selection(end=date(2026, 9, 1), years=(2025, 2026)), 'Trend', 'Annual')
    bus = model['series'][model['series']['mode'] == 'bus']
    expected = data.monthly[(data.monthly.year == 2025) & (data.monthly.day_type == 'W')]
    assert bus[bus.date == 2025].iloc[0].value == pytest.approx(expected.bus_total.sum() / expected.service_days.sum())
    assert bus[bus.date == 2026].value.isna().all()
    assert not model['year_coverage'].set_index('year').loc[2026, 'eligible']


def test_partial_month_and_missing_month_are_explicit(data):
    partial = explorer_model(data, selection(start=date(2025, 1, 2), end=date(2025, 3, 1)), 'Trend')
    assert partial['excluded_months'] == 1
    assert partial['series'][partial['series'].date == pd.Timestamp('2025-01-01')].value.isna().all()
    assert partial['coverage'].iloc[0].status == 'Partial selection'
    missing = explorer_model(data, selection(start=date(2012, 7, 1), end=date(2012, 8, 1)), 'Trend')
    assert missing['missing_days'] == 31
    assert missing['valid_points'] == 0
    assert missing['coverage'].iloc[0].status == 'Missing validated dates'


def test_yoy_matches_archived_4a_and_preserves_reference_outside_target(data):
    filters = selection(start=date(2026, 8, 1), end=date(2026, 9, 1), day_types=('W', 'A', 'U'), modes=('bus', 'rail', 'total'))
    model = explorer_model(data, filters, 'Year-over-year')
    reference = pd.read_csv(Path(__file__).resolve().parents[1] / 'data/research/cta-2026-11-01-v1/monthly_changes.csv')
    reference = reference[(reference.year == 2026) & (reference.month_number == 8)].set_index('day_type')
    assert len(model['series']) == 9
    for row in model['series'].itertuples():
        assert row.value == pytest.approx(reference.loc[row.day_type, f'{row.mode}_daily_yoy_pct'])
        assert row.reference_month == pd.Timestamp('2025-08-01')
        assert row.comparison_status == 'Comparable'
        assert row.previous_service_days > 0


def test_yoy_missing_or_zero_denominator_has_no_percentage(data):
    monthly = data.monthly.copy()
    monthly.loc[(monthly.year == 2024) & (monthly.month_number == 1), 'bus_daily'] = 0
    monthly.loc[(monthly.year == 2024) & (monthly.month_number == 2), 'complete_month'] = False
    model = explorer_model(replace(data, monthly=monthly), selection(end=date(2025, 3, 1)), 'Year-over-year')
    bus = model['series'][model['series']['mode'] == 'bus'].set_index('date')
    assert pd.isna(bus.loc[pd.Timestamp('2025-01-01'), 'value'])
    assert bus.loc[pd.Timestamp('2025-01-01'), 'comparison_status'] == 'Zero reference'
    assert bus.loc[pd.Timestamp('2025-02-01'), 'comparison_status'] == 'Reference unavailable'


def test_recovery_baseline_switch_uses_full_historical_denominator(data):
    for baseline in ('2019', '2017-2019'):
        model = explorer_model(data, selection(end=date(2025, 2, 1), baseline=baseline), 'Recovery')
        expected = data.recovery[(data.recovery.baseline == baseline) & (data.recovery.month == pd.Timestamp('2025-01-01')) & (data.recovery.day_type == 'W')].iloc[0]
        assert model['series'][model['series']['mode'] == 'bus'].iloc[0].value == pytest.approx(expected.bus_index)


@pytest.mark.parametrize('change', [dict(modes=()), dict(day_types=()), dict(years=())])
def test_empty_selections_do_not_fabricate_results(data, change):
    model = explorer_model(data, selection(**change))
    assert model['series'].empty
    assert model['selected_dates'] == 0


def test_daily_boundaries_and_rolling_availability(data):
    filters = selection(start=date(2025, 1, 1), end=date(2025, 1, 11), day_types=('W', 'A', 'U'))
    model = explorer_model(data, filters, 'Trend', 'Daily')
    bus = model['series'][model['series']['mode'] == 'bus']
    assert list(bus.date)[-1] == date(2025, 1, 10)
    assert bus.rolling_average.iloc[:6].isna().all()
    assert model['rolling_available']
    assert not explorer_model(data, selection(start=date(2025, 1, 1), end=date(2025, 1, 11)), 'Trend', 'Daily')['rolling_available']


def test_seasonal_year_filter_does_not_pool_years(data):
    filters = selection(start=date(2024, 1, 1), end=date(2026, 9, 1), years=(2024, 2026))
    model = explorer_model(data, filters, 'Seasonal')
    assert set(model['series'].year) == {2024, 2026}
    assert model['series'][(model['series'].year == 2026) & (model['series'].date > 8)].value.isna().all()
