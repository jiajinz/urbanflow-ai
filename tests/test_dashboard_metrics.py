"""Deterministic 4A-to-dashboard analytical contracts."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from urbanflow_ai.dashboard_data import DEFAULT_BUNDLE, load_bundle
from urbanflow_ai.dashboard_metrics import (
    ExplorerFilter, build_analytical_data, executive_model, explorer_series,
    selected_daily, selected_monthly,
)
from urbanflow_ai.data_access import COLUMNS, DataAccessError


@pytest.fixture(scope="module")
def data():
    return load_bundle(DEFAULT_BUNDLE)


def test_overview_reproduces_report_for_both_baselines(data):
    for baseline, expected in [("2019", (70.896085, 88.097900, 89.294850, 22.275277)),
                               ("2017-2019", (69.175301, 84.952783, 85.931711, 21.674523))]:
        model = executive_model(data, baseline)
        assert model['year'] == 2025
        assert list(model['metrics'].values()) == pytest.approx(expected, abs=1e-5)
        assert len(model['findings']) == 3


def test_bundle_tables_match_4a_research(data):
    research = Path(__file__).resolve().parents[1] / 'data/research/cta-2026-11-01-v1'
    files = {'monthly': 'monthly', 'recovery': 'recovery_indices', 'annual': 'annual',
             'periods': 'period_recovery', 'composition': 'matched_composition'}
    for table, filename in files.items():
        options = {'parse_dates': ['month']} if table in ('monthly', 'recovery') else {}
        expected = pd.read_csv(research / f'{filename}.csv', **options)
        pd.testing.assert_frame_equal(data.tables[table], expected, check_dtype=False,
                                      check_exact=False, rtol=1e-10, atol=1e-6)


def test_date_type_and_year_filters(data):
    filters = ExplorerFilter(date(2025, 1, 1), date(2025, 2, 1), ('A',), ('bus',), (2025,))
    selected = selected_daily(data, filters)
    assert len(selected) == 4
    assert set(selected.day_type) == {'A'}
    assert selected.service_date.max() < filters.end_date
    monthly = selected_monthly(data, filters, recovery=True)
    assert len(monthly) == 1 and monthly.iloc[0].baseline == '2019'


def test_target_filter_does_not_remove_baseline(data):
    filters = ExplorerFilter(date(2025, 1, 1), date(2026, 1, 1), years=(2025,))
    assert len(selected_monthly(data, filters, recovery=True)) == 36


def test_partial_month_and_year_are_not_compared(data):
    filters = ExplorerFilter(date(2025, 1, 2), date(2026, 9, 1), years=(2025, 2026))
    monthly = selected_monthly(data, filters)
    assert not (monthly.month == pd.Timestamp('2025-01-01')).any()
    assert explorer_series(data, filters, 'Yearly').empty


def test_missing_entire_month_stays_a_gap(data):
    filters = ExplorerFilter(date(2012, 6, 1), date(2012, 9, 1), years=(2012,))
    series = explorer_series(data, filters, 'Monthly')
    assert series[series.date == pd.Timestamp('2012-07-01')].value.isna().all()
    assert not series[series.date == pd.Timestamp('2012-06-01')].value.isna().all()


def test_daily_rolling_uses_seven_calendar_days_for_each_mode(data):
    filters = ExplorerFilter(date(2025, 1, 1), date(2025, 1, 11), years=(2025,))
    series = explorer_series(data, filters, 'Daily')
    bus = series[series['mode'] == 'bus'].reset_index(drop=True)
    assert bus.rolling_average.iloc[:6].isna().all()
    assert bus.rolling_average.iloc[6] == pytest.approx(bus.value.iloc[:7].mean())
    restricted = explorer_series(data, ExplorerFilter(date(2025, 1, 1), date(2025, 1, 11), ('W',), years=(2025,)), 'Daily')
    assert restricted.rolling_average.isna().all()


@pytest.mark.parametrize('changes', [dict(day_types=()), dict(modes=()), dict(years=())])
def test_empty_filters_are_explicit(data, changes):
    options = dict(start_date=date(2025, 1, 1), end_date=date(2026, 1, 1), years=(2025,))
    options.update(changes)
    assert selected_daily(data, ExplorerFilter(**options)).empty


@pytest.mark.parametrize('changes', [dict(day_types=('X',)), dict(modes=('ferry',)), dict(baseline='2020'), dict(years=('2025',))])
def test_invalid_filters(changes):
    options = dict(start_date=date(2025, 1, 1), end_date=date(2026, 1, 1))
    options.update(changes)
    with pytest.raises(ValueError):
        ExplorerFilter(**options)


def test_empty_and_insufficient_history():
    with pytest.raises(DataAccessError, match='No validated'):
        build_analytical_data(pd.DataFrame(columns=COLUMNS))
    frame = pd.DataFrame([(date(2024, 1, 1), 'U', 0, 0, 0)], columns=COLUMNS)
    data = build_analytical_data(frame)
    assert executive_model(data) is None
    assert data.recovery.empty
