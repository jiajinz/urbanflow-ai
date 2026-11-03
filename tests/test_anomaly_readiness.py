"""As-of cases and health tests; fixtures do not establish real incident labels."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from urbanflow_ai.anomaly_readiness import build_cases, model_health, run, weekly_load
from urbanflow_ai.anomaly_validation import add_diagnostics

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def inputs():
    config=json.loads((ROOT/'docs/anomaly_readiness_config.json').read_text())
    data=add_diagnostics(pd.read_csv(ROOT/'data/anomaly/cta-4c1b-v1/daily.csv',parse_dates=['date','fit_cutoff']))
    raw=pd.read_parquet(ROOT/'data/history/cta-2026-11-01-v1/daily_ridership.parquet')
    raw=raw.assign(date=pd.to_datetime(raw.service_date)).set_index('date')
    return data,raw,config


@pytest.fixture(scope='module')
def outputs(inputs):
    data,raw,config=inputs
    health=model_health(data,config)
    cases,registry=build_cases(data,raw,health,config)
    return cases,registry,health


def test_preservation_ids_and_unknown_review_state(inputs,outputs):
    data,_,_=inputs;cases,_,_=outputs
    assert len(cases)==int(data.candidate.sum())==763
    assert cases.case_id.is_unique
    assert cases.review_status.eq('unreviewed').all()
    assert cases.cause.eq('unknown').all()
    assert cases.data_quality_status.eq('validated_matches_archive').all()


def test_actual_direction_independent_of_centered_sign(outputs):
    cases,_,_=outputs
    row=cases[(cases.model=='calendar_median')&(cases['mode']=='rail')&(cases.date=='2021-06-04')].iloc[0]
    assert row.actual_direction=='low'
    assert row.centered_score_sign=='positive'
    assert row.centered_score>0 and row.signed_deviation<0


def test_episode_membership_and_prior_context(outputs):
    cases,registry,_=outputs
    assert registry.episode_id.is_unique
    for r in cases.itertuples():
        episode=registry[registry.episode_id==r.episode_id].iloc[0]
        assert episode.start<=r.date<=episode.end
        assert r.episode_days_asof==(r.date-episode.start).days+1
        assert all(pd.Timestamp(point['date'])<r.date for point in json.loads(r.prior_comparable_observations))


def test_future_suffix_cannot_change_cases_or_health(inputs,outputs):
    data,raw,config=inputs;full,_,full_health=outputs
    cutoff=pd.Timestamp('2021-07-01')
    prefix=data[data.date<cutoff]
    health=model_health(prefix,config)
    cases,_=build_cases(prefix,raw[raw.index<cutoff],health,config)
    pd.testing.assert_frame_equal(cases,full[full.date<cutoff].reset_index(drop=True))
    pd.testing.assert_frame_equal(health.sort_values(['model','mode','date']).reset_index(drop=True),
        full_health[full_health.date<cutoff].sort_values(['model','mode','date']).reset_index(drop=True))


def test_missing_target_and_cross_mode_context_are_explicit(inputs):
    data,raw,config=inputs
    day=pd.Timestamp('2025-03-15')
    missing=data[~((data['mode']=='bus')&(data.date==day))]
    health=model_health(missing,config)
    assert health[(health['mode']=='bus')&(health.date==day)].target_scored.eq(False).all()
    assert health[(health['mode']=='bus')&(health.date==day)].health_status.eq('scored_data_gap').all()
    cases,_=build_cases(missing,raw,health,config)
    row=cases[(cases.model=='seasonal_trend')&(cases['mode']=='rail')&(cases.date==day)].iloc[0]
    assert not row.cross_mode_available
    assert row.review_lane=='data_context_followup'
    assert pd.isna(row.cross_mode_observed)


def test_missing_prior_date_is_not_a_zero_observation(inputs):
    data,raw,config=inputs
    day=pd.Timestamp('2025-03-15')
    fewer=raw[raw.index!=pd.Timestamp('2025-03-08')]
    cases,_=build_cases(data,fewer,model_health(data,config),config)
    row=cases[(cases.model=='seasonal_trend')&(cases['mode']=='rail')&(cases.date==day)].iloc[0]
    assert row.prior_calendar_days==27 and not row.prior_coverage_complete
    assert not any(p['date']=='2025-03-08' for p in json.loads(row.prior_comparable_observations))


def test_health_is_separate_from_alerts_and_unknown_not_clear(inputs,outputs):
    data,_,_=inputs;_,_,health=outputs
    assert health[~health.history_window_mature].health_status.eq('insufficient_history').all()
    assert (health.health_status.eq('clear')<=health.health_evaluable).all()
    merged=data.merge(health[['model','mode','date','health_warning']],on=['model','mode','date'])
    assert ((~merged.candidate)&merged.health_warning).any()


def test_trailing_bias_and_disjoint_reference_math(inputs,outputs):
    data,_,_=inputs;_,_,health=outputs
    day=pd.Timestamp('2021-06-04')
    sample=data[(data.model=='calendar_median')&(data['mode']=='rail')]
    current=sample[sample.date.between(day-pd.Timedelta(days=27),day)]
    row=health[(health.model=='calendar_median')&(health['mode']=='rail')&(health.date==day)].iloc[0]
    np.testing.assert_allclose(row.median_relative_residual,(current.residual/current.expected).median())
    prior=sample[sample.date.between(day-pd.Timedelta(days=111),day-pd.Timedelta(days=28))]
    expected=current[current.day_type=='W'].center.median()-prior[prior.day_type=='W'].center.median()
    np.testing.assert_allclose(row.W_center_shift,expected)


def test_priority_components_and_budget_preserve_overflow(inputs,outputs):
    _,_,config=inputs;cases,_,_=outputs
    assert cases.priority_points.equals(cases[['magnitude_points','unusualness_points','cross_mode_points','persistence_points']].sum(axis=1))
    load=weekly_load(cases,config)
    assert load.candidate_observations.sum()==len(cases)
    assert load.arrivals_exceed_capacity.any()
    assert cases.daily_review_rank.min()==1


def test_empty_health_and_cases_keep_schema(inputs):
    data,raw,config=inputs
    health=model_health(data.iloc[:0],config)
    cases,registry=build_cases(data.iloc[:0],raw,health,config)
    assert health.empty and cases.empty and registry.empty
    assert 'case_id' in cases.columns


def test_existing_outputs_are_never_overwritten(tmp_path):
    with pytest.raises(ValueError,match='already exists'):
        run(tmp_path,tmp_path,tmp_path,tmp_path,tmp_path)
