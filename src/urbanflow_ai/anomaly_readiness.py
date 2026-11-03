"""Auditable as-of investigation records and separate retrospective health guards."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .anomaly_validation import add_diagnostics, episodes
from .dashboard_data import load_archive


def model_health(data, config):
    """Trailing calendar-window diagnostics, including explicit unscored dates.

    Includes the current reported observation; never a subsequent observation.
    Drift references a disjoint earlier window within the same CTA day type.
    """
    frames = []
    n, reference = config['health_window_days'], config['drift_reference_days']
    minimum = config['minimum_scored_days']
    for (model, mode), group in data.groupby(['model', 'mode']):
        index = pd.date_range(group.date.min(), group.date.max(), freq='D', name='date')
        g = group.set_index('date').reindex(index)
        count = g.observed.rolling(n, min_periods=1).count()
        valid = count >= minimum
        actual = g.observed.rolling(n, min_periods=minimum).sum().replace(0, np.nan)
        wape = 100 * g.residual.abs().rolling(n, min_periods=minimum).sum() / actual
        relative = g.residual / g.expected.replace(0, np.nan)
        bias = relative.rolling(n, min_periods=minimum).median()
        high = g.residual.gt(0).where(g.residual.notna()).rolling(n, min_periods=minimum).sum() / count
        low = g.residual.lt(0).where(g.residual.notna()).rolling(n, min_periods=minimum).sum() / count
        rate = 100 * g.candidate.astype(float).rolling(n, min_periods=minimum).mean()
        row = pd.DataFrame(dict(scored_days=count, window_days=n, target_scored=g.observed.notna(),
            history_window_mature=index >= index.min()+pd.Timedelta(days=n-1),
            wape_pct=wape, median_relative_residual=bias,
            median_log_residual=g.log_residual.rolling(n, min_periods=minimum).median(),
            median_center=g.center.rolling(n, min_periods=minimum).median(),
            median_scale=g.scale.rolling(n, min_periods=minimum).median(),
            alert_rate_pct=rate, high_residual_fraction=high, low_residual_fraction=low), index=index)
        row['bias_warning'] = bias.abs().gt(config['bias_relative_fraction']) & valid
        row['sustained_underprediction'] = bias.gt(config['bias_relative_fraction']) & high.ge(config['sustained_direction_fraction']) & valid
        row['sustained_overprediction'] = bias.lt(-config['bias_relative_fraction']) & low.ge(config['sustained_direction_fraction']) & valid
        row['error_warning'] = wape.gt(config['error_wape_pct']) & valid
        row['alert_frequency_warning'] = rate.gt(config['alert_rate_pct']) & valid
        evaluable, flags = [], []
        for kind in ('W', 'A', 'U'):
            center = g.center.where(g.day_type == kind)
            scale = g.scale.where(g.day_type == kind)
            current = center.rolling(n, min_periods=config['drift_current_type_min']).median()
            prior = center.shift(n).rolling(reference, min_periods=config['drift_reference_type_min']).median()
            current_scale = scale.rolling(n, min_periods=config['drift_current_type_min']).median()
            prior_scale = scale.shift(n).rolling(reference, min_periods=config['drift_reference_type_min']).median()
            delta, ratio = current-prior, current_scale/prior_scale
            available = delta.notna() & ratio.notna()
            flag = available & (delta.abs().gt(config['center_drift_log_units']) |
                ratio.lt(config['scale_ratio_low']) | ratio.gt(config['scale_ratio_high']))
            evaluable.append(available); flags.append(flag)
            row[f'{kind}_center_shift'] = delta
            row[f'{kind}_scale_ratio'] = ratio
        row['drift_types_evaluable'] = pd.concat(evaluable, axis=1).sum(axis=1)
        row['drift_warning'] = pd.concat(flags, axis=1).any(axis=1)
        row['scored_evidence_missing_days'] = n-count
        row['health_evaluable'] = (count == n) & row.history_window_mature & row.drift_types_evaluable.eq(3) & wape.notna() & bias.notna()
        warning_columns = ['bias_warning', 'sustained_underprediction', 'sustained_overprediction', 'error_warning', 'alert_frequency_warning', 'drift_warning']
        row['health_warning'] = row[warning_columns].any(axis=1)
        row['health_status'] = np.select([
            ~row.history_window_mature, count.lt(n), ~row.health_evaluable, row.health_warning],
            ['insufficient_history', 'scored_data_gap', 'unknown_drift_or_error', 'warning'], default='clear')
        row['model'], row['mode'] = model, mode
        frames.append(row.reset_index())
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_cases(data, raw, health, config):
    """Preserve every candidate; enrich only with evidence available by its date."""
    alerts = data[data.candidate].copy()
    registry = episodes(alerts)
    registry['episode_id'] = registry.apply(lambda r: f"{r.model}|{r['mode']}|{r.direction}|{r.start.date()}", axis=1) if not registry.empty else pd.Series(dtype=str)
    lookup = health.set_index(['model', 'mode', 'date']) if not health.empty else None
    daily = data.set_index(['model', 'mode', 'date'])
    records = []
    for r in alerts.itertuples(index=False):
        source = raw.loc[r.date] if r.date in raw.index else None
        field = 'bus' if r.mode == 'bus' else 'rail_boardings'
        matched = source is not None and source[field] == r.observed and source.day_type == r.day_type and source.bus+source.rail_boardings == source.total_rides
        prior = raw[(raw.index < r.date) & (raw.index >= r.date-pd.Timedelta(days=28))]
        comparable = prior[prior.day_type == r.day_type]
        episode = registry[(registry.model == r.model) & (registry['mode'] == r.mode) &
            (registry.direction == r.direction) & (registry.start <= r.date) & (registry.end >= r.date)]
        if len(episode) != 1:
            raise ValueError('Candidate must have exactly one traceable episode')
        episode = episode.iloc[0]
        age = (r.date-episode.start).days+1
        other_mode = 'rail' if r.mode == 'bus' else 'bus'
        key = (r.model, other_mode, r.date)
        other = daily.loc[key] if key in daily.index else None
        relative = 100*r.residual/r.expected if r.expected else np.nan
        magnitude_points = int(abs(relative) >= 20) + int(abs(relative) >= 50) if np.isfinite(relative) else 0
        unusualness_points = int(abs(r.score) >= 5) + int(abs(r.score) >= 10)
        cross_points = int(other is not None and other.candidate)
        persistence_points = int(age >= 3)
        state = lookup.loc[(r.model, r.mode, r.date)] if lookup is not None else None
        complete = len(prior) == 28
        records.append(dict(case_id=f'{r.model}|{r.mode}|{r.date.date()}', date=r.date, model=r.model, mode=r.mode,
            day_type=r.day_type, observed=r.observed, expected=r.expected, signed_deviation=r.residual,
            absolute_deviation=abs(r.residual), relative_deviation_pct=relative, centered_score=r.score,
            actual_direction=r.direction, centered_score_sign='positive' if r.score > 0 else 'negative' if r.score < 0 else 'zero',
            prior_calendar_days=len(prior), prior_expected_days=28, prior_coverage_complete=complete,
            prior_same_type_count=len(comparable), prior_same_type_median=float(comparable[field].median()),
            prior_comparable_observations=json.dumps([{'date': str(day.date()), 'observed': int(row[field])} for day,row in comparable.iterrows()]),
            cross_mode_available=other is not None, cross_mode_alert=bool(other.candidate) if other is not None else None,
            cross_mode_observed=float(other.observed) if other is not None else np.nan,
            cross_mode_expected=float(other.expected) if other is not None else np.nan,
            cross_mode_direction=other.direction if other is not None else 'unavailable',
            episode_id=episode.episode_id, episode_days_asof=age,
            data_quality_status='validated_matches_archive' if matched else 'source_missing_or_mismatch',
            model_health_status=state.health_status if state is not None else 'unavailable',
            model_health_warning=bool(state.health_warning) if state is not None else None,
            magnitude_points=magnitude_points, unusualness_points=unusualness_points,
            cross_mode_points=cross_points, persistence_points=persistence_points,
            priority_points=magnitude_points+unusualness_points+cross_points+persistence_points,
            review_lane='investigation' if matched and complete and other is not None else 'data_context_followup',
            urgent=abs(r.score) >= config['urgent_score'] or (np.isfinite(relative) and abs(relative) >= config['urgent_relative_pct']) or age >= config['urgent_episode_days'],
            review_status='unreviewed', uncertainty='high; model-relative evidence only', cause='unknown',
            reviewer='', reviewed_at_utc='', review_evidence='',
            evidence_limitations='No incident labels, causal attribution, historical source vintages, service supply, or independent measurement verification'))
    cases = pd.DataFrame(records)
    if cases.empty:
        return pd.DataFrame(columns=['case_id','date','model','mode','review_status']), registry
    cases = cases.sort_values(['date','priority_points','prior_coverage_complete','case_id'], ascending=[True,False,True,True]).reset_index(drop=True)
    cases['daily_review_rank'] = cases.groupby('date').cumcount()+1
    if len(cases) != len(alerts) or cases.case_id.duplicated().any():
        raise ValueError('Candidate preservation invariant failed')
    return cases, registry


def weekly_load(cases, config):
    """Proposed staffing stress, not simulated completed reviews or actual backlog."""
    rows = []
    if cases.empty:
        return pd.DataFrame(columns=['week','candidate_observations','urgent_observations','episode_ids','proposed_new_case_capacity','arrivals_exceed_capacity','urgent_arrivals_exceed_capacity'])
    for week, group in cases.groupby(cases.date.dt.to_period('W-SUN')):
        rows.append(dict(week=str(week), candidate_observations=len(group), urgent_observations=int(group.urgent.sum()),
            episode_ids=group.episode_id.nunique(), proposed_new_case_capacity=config['review_new_cases_per_week'],
            arrivals_exceed_capacity=len(group)>config['review_new_cases_per_week'],
            urgent_arrivals_exceed_capacity=int(group.urgent.sum())>config['review_new_cases_per_week']))
    return pd.DataFrame(rows)


def run(source, archive, output, config_path, protocol):
    """Read frozen diagnostics; write a new investigation version with lineage."""
    if output.exists():
        raise ValueError('Output already exists; choose a new investigation version')
    config = json.loads(config_path.read_text())
    detector = Path(__file__).with_name('anomaly.py')
    if hashlib.sha256(detector.read_bytes()).hexdigest() != config['detector_sha256']:
        raise ValueError('Detector differs from the frozen readiness configuration')
    frozen_manifest = json.loads((source/'manifest.json').read_text())
    prediction_hashes = [value for name,value in frozen_manifest['inputs_sha256'].items() if Path(name).name == 'predictions.csv']
    if prediction_hashes != [config['frozen_prediction_sha256']]:
        raise ValueError('Frozen prediction lineage differs from readiness protocol')
    for name, digest in frozen_manifest['outputs_sha256'].items():
        if hashlib.sha256((source/f'{name}.csv').read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen validation output checksum mismatch')
    data = add_diagnostics(pd.read_csv(source/'daily.csv', parse_dates=['date','fit_cutoff']))
    bundle = load_archive(archive)
    raw = bundle.daily.assign(date=pd.to_datetime(bundle.daily.service_date)).set_index('date')
    health = model_health(data, config)
    cases, registry = build_cases(data, raw, health, config)
    if not cases.data_quality_status.eq('validated_matches_archive').all():
        raise ValueError('Candidate counts or day types differ from the validated archive')
    tables = dict(cases=cases, model_health=health, episode_registry=registry, weekly_load=weekly_load(cases,config))
    output.mkdir(parents=True)
    for name, table in tables.items():
        table.to_csv(output/f'{name}.csv', index=False)
    inputs = [source/'manifest.json', source/'daily.csv', config_path, protocol, detector, Path(__file__), archive/'manifest.json']
    manifest = dict(prospective_validation_executed=False, integration_decision='NO-GO: prospective and human-review evidence absent',
        inputs_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        outputs_sha256={name:hashlib.sha256((output/f'{name}.csv').read_bytes()).hexdigest() for name in tables},
        source_parquet_sha256=bundle.metadata['input_parquet_sha256'],
        notes='Case fields are as-of; full episode end/duration in registry are retrospective context, not ranking inputs',
        numpy_version=np.__version__,pandas_version=pd.__version__)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return tables


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--config',type=Path,default=Path('docs/anomaly_readiness_config.json'))
    parser.add_argument('--protocol',type=Path,default=Path('docs/anomaly_prospective_protocol.md'))
    args=parser.parse_args()
    tables=run(args.source,args.archive,args.output,args.config,args.protocol)
    print(f"Exported {len(tables['cases']):,} preserved candidate cases; prospective validation not executed.")


if __name__ == '__main__':
    main()
