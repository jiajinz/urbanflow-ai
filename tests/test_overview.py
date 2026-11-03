"""Executive Overview evidence and presentation contracts against approved 4A data."""

from dataclasses import replace

import pandas as pd
import pytest

from urbanflow_ai.dashboard_data import load_bundle
from urbanflow_ai.overview import overview_model
from urbanflow_ai.dashboard_charts import weekday_mode_trend


@pytest.fixture(scope='module')
def data():
    return load_bundle()


@pytest.mark.parametrize('baseline,expected', [
    ('2019', (70.896085, 88.097900, 89.294850, 22.275277)),
    ('2017-2019', (69.175301, 84.952783, 85.931711, 21.674523)),
])
def test_overview_reuses_verified_evidence(data, baseline, expected):
    model = overview_model(data, baseline)
    assert model['year'] == 2025
    assert list(model['metrics'].values()) == pytest.approx(expected, abs=1e-5)
    assert all(set(note) == {'title', 'evidence', 'interpretation', 'planning', 'limitation', 'source'} for note in model['insights'])
    assert '51.88%' in model['insights'][2]['evidence']
    assert '58.98%' in model['insights'][2]['evidence']
    assert 'calendar months 1,2,3,4,5,6,7,8, 2026' in model['insights'][2]['evidence']


def test_chart_window_does_not_redefine_annual_kpis(data):
    complete = overview_model(data)
    partial = overview_model(data, chart_years=(2026, 2026))
    assert partial['metrics'] == complete['metrics']
    assert partial['insights'] == complete['insights']
    assert partial['chart_period'] == 'Jan 2026–Aug 2026'
    assert set(partial['chart_trend'].year) == {2026}
    assert len(partial['mode_trend']) == 8


def test_missing_month_is_not_connected_or_imputed(data):
    recovery = data.recovery.loc[data.recovery.month != pd.Timestamp('2024-06-01')].copy()
    model = overview_model(replace(data, recovery=recovery), chart_years=(2024, 2024))
    absent = model['chart_trend'][model['chart_trend'].month == pd.Timestamp('2024-06-01')]
    assert len(absent) == 3
    assert absent[['bus_index', 'rail_index', 'total_index']].isna().all().all()
    figure = weekday_mode_trend(model['mode_trend'])
    assert all(trace.connectgaps is False for trace in figure.data)
    assert all(pd.isna(trace.y[5]) for trace in figure.data)


def test_mode_plot_receives_exact_analytical_values(data):
    model = overview_model(data, chart_years=(2025, 2025))
    figure = weekday_mode_trend(model['mode_trend'])
    assert list(figure.data[0].y) == list(model['mode_trend'].bus_index)
    assert list(figure.data[1].y) == list(model['mode_trend'].rail_index)
    assert figure.layout.shapes[0].y0 == 100


@pytest.mark.parametrize('window', [(2026, 2025), (2019, 2025), (2025, 2027)])
def test_invalid_chart_window(data, window):
    with pytest.raises(ValueError, match='ordered chart window'):
        overview_model(data, chart_years=window)


def test_insufficient_annual_evidence_has_no_overview(data):
    assert overview_model(replace(data, annual=data.annual.iloc[:0])) is None
