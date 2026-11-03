"""Alert arithmetic, chronology, and episode tests; no external incident claims."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from urbanflow_ai.anomaly_validation import (
    add_diagnostics, episodes, overlap, period_metrics, ranked_queue, select_window,
    window_metrics,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample():
    data = pd.read_csv(ROOT / 'data/anomaly/cta-4c1a-v1/predictions.csv', parse_dates=['date', 'fit_cutoff'])
    return add_diagnostics(data)


def alert_fixture(dates, modes=None, direction='low'):
    n = len(dates)
    return pd.DataFrame(dict(date=pd.to_datetime(dates), model=['model']*n,
        mode=modes or ['bus']*n, direction=[direction]*n, score=[-4.]*n,
        absolute_deviation=[10000.]*n))


def test_half_open_windows_and_invalid_bounds(sample):
    selected = select_window(sample, '2025-01-01', '2026-01-01')
    assert selected.date.min() == pd.Timestamp('2025-01-01')
    assert selected.date.max() == pd.Timestamp('2025-12-31')
    with pytest.raises(ValueError):
        select_window(sample, '2026-01-01', '2025-01-01')


def test_episode_gap_direction_and_cross_mode_rules():
    alerts = alert_fixture(['2020-01-01', '2020-01-02', '2020-01-04'])
    assert episodes(alerts).calendar_days.tolist() == [2, 1]
    alerts.loc[1, 'direction'] = 'high'
    assert len(episodes(alerts)) == 3
    paired = alert_fixture(['2020-01-01', '2020-01-01', '2020-01-02'], ['bus', 'rail', 'rail'])
    combined = episodes(paired, combine_modes=True)
    assert combined.calendar_days.tolist() == [2]
    assert combined.alert_observations.tolist() == [3]
    assert len(episodes(paired)) == 2
    assert episodes(alerts.iloc[:0]).empty


def test_group_globally_then_count_boundary_intersection(sample):
    sample = sample.iloc[:0].copy()
    # A deliberately boundary-crossing episode tests reporting, not CTA evidence.
    records = pd.DataFrame(dict(date=pd.to_datetime(['2021-12-31','2022-01-01']),
        model=['model']*2, mode=['bus']*2, observed=[10000.]*2, residual=[-20000.]*2,
        absolute_deviation=[20000.]*2, direction=['low']*2, score=[-4.]*2,
        **{'alert_3': [True]*2, 'alert_3.5': [True]*2, 'alert_4.5': [False]*2}))
    summary, _ = window_metrics(records, episodes(records))
    validation = summary[summary.window == 'retrospective_validation'].iloc[0]
    assert validation.scored_days == 1
    assert validation.episodes_intersecting == 1
    assert validation.boundary_crossing_episodes == 1
    assert validation.longest_run_days == 2


def test_alert_reconciliation_and_threshold_sensitivity(sample):
    assert sample['alert_3.5'].equals(sample.candidate)
    assert (sample['alert_3'] >= sample['alert_3.5']).all()
    assert (sample['alert_3.5'] >= sample['alert_4.5']).all()
    assert sample[sample.residual < 0].direction.eq('low').all()
    assert not sample.duplicated(['model','mode','date']).any()


def test_input_leakage_and_duplicate_guards(sample):
    invalid = sample.copy()
    invalid.loc[0, 'fit_cutoff'] = invalid.loc[0, 'date']
    with pytest.raises(ValueError, match='cutoff'):
        add_diagnostics(invalid)
    with pytest.raises(ValueError, match='Duplicate'):
        add_diagnostics(pd.concat([sample, sample.head(1)]))
    invalid = sample.copy()
    invalid.loc[0, 'candidate'] = not invalid.loc[0, 'candidate']
    with pytest.raises(ValueError, match='candidate flags'):
        add_diagnostics(invalid)


def test_zero_alert_months_partial_years_and_overlap(sample):
    monthly = period_metrics(sample, 'M')
    assert monthly.alerts.eq(0).any()
    annual = period_metrics(sample, 'Y')
    assert not annual[annual.period == '2026'].complete_calendar_period.any()
    assert annual[annual.period == '2025'].complete_calendar_period.all()
    paired = overlap(sample)
    assert (paired.either_mode_dates == paired.both_modes_dates + paired.bus_only_dates + paired.rail_only_dates).all()


def test_ranking_retains_unranked_observations_and_ties(sample):
    queue = ranked_queue(sample)
    assert len(queue) == sample['alert_3.5'].sum()
    assert queue.groupby(['model','month']).in_monthly_top_three.sum().le(3).all()
    assert (~queue.in_monthly_top_three).any()
    pd.testing.assert_frame_equal(queue, ranked_queue(sample.sample(frac=1, random_state=42)))


def test_past_month_diagnostics_unaffected_by_future_suffix(sample):
    before = period_metrics(select_window(sample, '2019-01-01','2022-01-01'), 'M')
    changed = sample.copy()
    changed.loc[changed.date >= '2022-01-01', 'score'] = 999
    after = period_metrics(select_window(changed, '2019-01-01','2022-01-01'), 'M')
    pd.testing.assert_frame_equal(before, after)


def test_threshold_and_gate_boundary_are_explicit(sample):
    row = sample.head(1).copy()
    row.loc[:, 'observed'] = 30000.
    row.loc[:, 'expected'] = 20000.
    row.loc[:, 'residual'] = 10000.
    row.loc[:, 'log_residual'] = np.log1p(30000.) - np.log1p(20000.)
    row.loc[:, 'scale'] = .1
    row.loc[:, 'score'] = 3.5
    row.loc[:, 'center'] = row.log_residual - .35
    row.loc[:, 'candidate'] = False
    result = add_diagnostics(row)
    assert result.magnitude_gate.iloc[0]
    assert not result['alert_3.5'].iloc[0]
    assert result['alert_3'].iloc[0]


def test_calibration_reconstructs_only_strictly_prior_same_type_residuals(sample):
    from urbanflow_ai.anomaly import residual_score
    for model, mode, day in [('calendar_median', 'bus', '2021-06-04'),
                             ('seasonal_trend', 'rail', '2025-03-15')]:
        target = sample[(sample.model == model) & (sample['mode'] == mode) & (sample.date == day)].iloc[0]
        prior = sample[(sample.model == model) & (sample['mode'] == mode) &
                       (sample.day_type == target.day_type) & (sample.date < target.date) &
                       (sample.date >= target.date - pd.Timedelta(days=365))]
        score, center, scale = residual_score(target.log_residual, prior.log_residual.to_list())
        np.testing.assert_allclose([score, center, scale], [target.score, target.center, target.scale])
        assert target.calibration_days == len(prior)


def test_invalid_ranking_budget(sample):
    with pytest.raises(ValueError, match='positive integer'):
        ranked_queue(sample, budget=0)
