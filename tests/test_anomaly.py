"""Deterministic anomaly tests; synthetic fixtures are not CTA event evidence."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from urbanflow_ai.anomaly import detect, features, residual_score, run, summarize
from urbanflow_ai.data_access import COLUMNS, DataAccessError


@pytest.fixture(scope='module')
def history():
    dates = pd.date_range('2014-01-01', '2019-02-01')
    kinds = np.where(dates.dayofweek < 5, 'W', np.where(dates.dayofweek == 5, 'A', 'U'))
    bus = (100000 + 5000 * np.sin(np.arange(len(dates)) / 30)).astype(int)
    return pd.DataFrame(dict(service_date=dates.date, day_type=kinds, bus=bus,
                            rail_boardings=bus // 2, total_rides=bus + bus // 2))[COLUMNS]


def test_no_future_or_current_target_leakage(history):
    target = date(2019, 1, 15)
    original = detect(history)
    changed = history.copy()
    mask = changed.service_date >= target
    changed.loc[mask, 'bus'] *= 4
    changed.loc[mask, 'total_rides'] = changed.loc[mask, 'bus'] + changed.loc[mask, 'rail_boardings']
    updated = detect(changed)
    pd.testing.assert_frame_equal(original[original.date < str(target)], updated[updated.date < str(target)])
    current = original[original.date == str(target)]
    altered = updated[updated.date == str(target)]
    np.testing.assert_allclose(current.expected, altered.expected)
    np.testing.assert_allclose(current.scale, altered.scale)
    assert (original.fit_cutoff < original.date).all()


def test_calendar_median_matches_strictly_prior_cell(history):
    result = detect(history)
    row = result[(result.date == '2019-01-15') & (result.model == 'calendar_median') & (result['mode'] == 'bus')].iloc[0]
    dates = pd.to_datetime(history.service_date)
    mask = (dates < row.date) & (dates >= row.date - pd.Timedelta(days=1096)) & (dates.dt.month == 1) & history.day_type.eq('W')
    assert row.expected == history.loc[mask, 'bus'].median()
    assert row.training_days == mask.sum()


def test_empty_and_invalid_inputs(history):
    assert detect(history.iloc[:0]).empty
    evaluation, metrics = summarize(detect(history.iloc[:0]))
    assert evaluation.empty and metrics.empty
    invalid = history.copy()
    invalid.loc[0, 'total_rides'] = 1
    with pytest.raises(DataAccessError):
        detect(invalid)


def test_missing_dates_are_not_imputed(history):
    missing = date(2018, 7, 1)
    result = detect(history[history.service_date != missing])
    assert not (result.date == str(missing)).any()
    assert not result.duplicated(['date', 'mode', 'model']).any()


def test_robust_score_warmup_zero_scale_and_injection():
    assert np.isnan(residual_score(1, [0] * 29)[0])
    assert residual_score(0, [0] * 30) == (0, 0, .05)
    assert residual_score(np.log(1.5), [0] * 30)[0] > 3.5
    assert residual_score(np.log(.5), [0] * 30)[0] < -3.5


def test_features_finite_and_evaluation_bounds(history):
    assert np.isfinite(features(pd.date_range('2016-02-28', periods=3), pd.Timestamp('2016-02-01'))).all()
    evaluation, metrics = summarize(detect(history))
    assert evaluation.date.min() == pd.Timestamp('2019-01-01')
    assert (metrics['alerts_3'] >= metrics.alerts).all()
    assert (metrics.alerts >= metrics['alerts_4.5']).all()


def test_output_cannot_overwrite_archive(tmp_path):
    with pytest.raises(ValueError, match='already exists'):
        run(tmp_path / 'unused', tmp_path)
