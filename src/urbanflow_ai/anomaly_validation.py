"""Deterministic burden and episode diagnostics over frozen anomaly outputs."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .dashboard_data import load_archive

WINDOWS = (
    ('development_diagnostics', '2019-01-01', '2022-01-01'),
    ('retrospective_validation', '2022-01-01', '2025-01-01'),
    ('retrospective_last_assessment', '2025-01-01', '2026-09-01'),
)
THRESHOLDS = (3., 3.5, 4.5)


def select_window(frame, start, end):
    """Half-open boundaries; never recalculate predictions using future rows."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start >= end:
        raise ValueError('Window start must precede end')
    return frame.loc[(frame.date >= start) & (frame.date < end)].copy()


def add_diagnostics(frame):
    """Preserve predictions; derive raw-direction alerts and calibration diagnostics."""
    data = frame.copy()
    if data.duplicated(['model', 'mode', 'date']).any():
        raise ValueError('Duplicate model/mode/date predictions')
    if not (data.fit_cutoff < data.date).all():
        raise ValueError('Training cutoff must precede every target date')
    if not np.isfinite(data[['observed', 'expected', 'residual', 'score', 'center', 'scale']].to_numpy()).all() or (data.scale <= 0).any():
        raise ValueError('Validation requires finite scored observations and positive scales')
    if not np.allclose(data.observed - data.expected, data.residual):
        raise ValueError('Residuals do not reconcile with observed and expected counts')
    if not np.allclose((data.log_residual - data.center) / data.scale, data.score):
        raise ValueError('Scores do not reconcile with calibration parameters')
    data['direction'] = np.where(data.residual > 0, 'high', np.where(data.residual < 0, 'low', 'equal'))
    data['absolute_deviation'] = data.residual.abs()
    data['relative_deviation_pct'] = 100 * data.residual / data.expected.replace(0, np.nan)
    data['magnitude_gate'] = data.absolute_deviation >= np.maximum(10000, .2 * data.expected)
    for threshold in THRESHOLDS:
        data[f'alert_{threshold:g}'] = data.score.abs().gt(threshold) & data.magnitude_gate
    if not data.candidate.eq(data['alert_3.5']).all():
        raise ValueError('Frozen candidate flags differ from the documented alert rule')
    data['zero_center_score'] = data.log_residual / data.scale
    data['zero_center_alert'] = data.zero_center_score.abs().gt(3.5) & data.magnitude_gate
    data['magnitude_without_alert'] = data.magnitude_gate & ~data['alert_3.5']
    data['center_suppressed'] = data.zero_center_alert & ~data['alert_3.5']
    data['center_created'] = data['alert_3.5'] & ~data.zero_center_alert
    return data.sort_values(['model', 'mode', 'date']).reset_index(drop=True)


def episodes(alerts, *, combine_modes=False):
    """Group same-direction alerts on consecutive dates; gaps always break runs."""
    keys = ['model', 'direction'] if combine_modes else ['model', 'mode', 'direction']
    rows = []
    for values, group in alerts.groupby(keys):
        group = group.sort_values(['date', 'mode'])
        run = group.date.diff().dt.days.gt(1).cumsum()
        for _, part in group.groupby(run):
            row = dict(zip(keys, values))
            row.update(start=part.date.min(), end=part.date.max(),
                       alert_observations=len(part), calendar_days=part.date.nunique(),
                       modes=','.join(sorted(part['mode'].unique())),
                       max_absolute_score=float(part.score.abs().max()),
                       max_absolute_deviation=float(part.absolute_deviation.max()))
            rows.append(row)
    return pd.DataFrame(rows, columns=keys + ['start', 'end', 'alert_observations', 'calendar_days', 'modes', 'max_absolute_score', 'max_absolute_deviation'])


def period_metrics(data, frequency):
    """Include zero-alert periods; rates use actual scored mode-days, not imputation."""
    work = data.assign(period=data.date.dt.to_period(frequency).astype(str))
    rows = []
    for keys, group in work.groupby(['model', 'mode', 'period']):
        period = pd.Period(keys[2], freq=frequency)
        observed = group.observed.sum()
        row = dict(zip(['model', 'mode', 'period'], keys))
        row.update(scored_days=len(group), expected_calendar_days=period.days_in_month if frequency == 'M' else (366 if period.start_time.is_leap_year else 365),
            alerts=int(group['alert_3.5'].sum()), high=int((group['alert_3.5'] & group.direction.eq('high')).sum()),
            low=int((group['alert_3.5'] & group.direction.eq('low')).sum()),
            alert_rate_pct=float(group['alert_3.5'].mean()*100),
            wape_pct=float(group.absolute_deviation.sum()/observed*100) if observed else np.nan,
            mean_residual=float(group.residual.mean()), median_log_residual=float(group.log_residual.median()),
            median_center=float(group.center.median()), median_scale=float(group.scale.median()),
            magnitude_without_alert=int(group.magnitude_without_alert.sum()),
            center_suppressed=int(group.center_suppressed.sum()), center_created=int(group.center_created.sum()))
        row['complete_calendar_period'] = row['scored_days'] == row['expected_calendar_days']
        rows.append(row)
    return pd.DataFrame(rows)


def window_metrics(data, grouped):
    rows, distributions = [], []
    scopes = [('all', '2019-01-01', '2026-09-01'), *WINDOWS]
    for label, start, end in scopes:
        selected = select_window(data, start, end)
        for (model, mode), group in selected.groupby(['model', 'mode']):
            runs = grouped[(grouped.model == model) & (grouped['mode'] == mode) & (grouped.start < pd.Timestamp(end)) & (grouped.end >= pd.Timestamp(start))]
            row = dict(window=label, model=model, mode=mode, scored_days=len(group),
                wape_pct=float(group.absolute_deviation.sum()/group.observed.sum()*100) if group.observed.sum() else np.nan,
                high_alerts=int((group['alert_3.5'] & group.direction.eq('high')).sum()),
                low_alerts=int((group['alert_3.5'] & group.direction.eq('low')).sum()),
                episodes_intersecting=len(runs), singleton_episodes=int(runs.calendar_days.eq(1).sum()),
                longest_run_days=int(runs.calendar_days.max()) if len(runs) else 0,
                boundary_crossing_episodes=int(((runs.start < pd.Timestamp(start)) | (runs.end >= pd.Timestamp(end))).sum()))
            for threshold in THRESHOLDS:
                row[f'alerts_{threshold:g}'] = int(group[f'alert_{threshold:g}'].sum())
                row[f'rate_{threshold:g}_pct'] = float(group[f'alert_{threshold:g}'].mean()*100)
            rows.append(row)
            distribution = dict(window=label, model=model, mode=mode)
            for q in (.01, .05, .5, .95, .99):
                distribution[f'score_q{q}'] = float(group.score.quantile(q))
            distribution['max_absolute_score'] = float(group.score.abs().max())
            distributions.append(distribution)
    return pd.DataFrame(rows), pd.DataFrame(distributions)


def overlap(data):
    rows = []
    for model, group in data.groupby('model'):
        bus = group[group['mode'] == 'bus'].set_index('date')
        rail = group[group['mode'] == 'rail'].set_index('date')
        shared = bus.index.intersection(rail.index)
        both = bus.loc[shared, 'alert_3.5'] & rail.loc[shared, 'alert_3.5']
        either = bus.loc[shared, 'alert_3.5'] | rail.loc[shared, 'alert_3.5']
        rows.append(dict(model=model, paired_scored_dates=len(shared), either_mode_dates=int(either.sum()),
            both_modes_dates=int(both.sum()), bus_only_dates=int((bus.loc[shared, 'alert_3.5'] & ~rail.loc[shared, 'alert_3.5']).sum()),
            rail_only_dates=int((~bus.loc[shared, 'alert_3.5'] & rail.loc[shared, 'alert_3.5']).sum()),
            same_direction_both=int((both & bus.loc[shared, 'direction'].eq(rail.loc[shared, 'direction'])).sum()),
            intersection_over_union=float(both.sum()/either.sum()) if either.any() else np.nan))
    return pd.DataFrame(rows)


def ranked_queue(data, budget=3):
    """Retrospective month-end ranking, not an online selection policy."""
    if type(budget) is not int or budget < 1:
        raise ValueError('Monthly investigation budget must be a positive integer')
    alerts = data[data['alert_3.5']].copy()
    alerts['month'] = alerts.date.dt.to_period('M').astype(str)
    alerts['absolute_score'] = alerts.score.abs()
    alerts = alerts.sort_values(['absolute_score', 'date', 'mode', 'model'], ascending=[False, True, True, True])
    alerts['monthly_rank'] = alerts.groupby(['model', 'month']).cumcount() + 1
    alerts['in_monthly_top_three'] = alerts.monthly_rank <= budget
    return alerts


def investigate(data, raw, grouped):
    """Transparent diverse examples and dated adjacent same-type context."""
    cases = []
    for model, group in data[data['alert_3.5']].groupby('model'):
        positive = group[group.direction == 'high'].nlargest(1, 'score')
        negative = group[group.direction == 'low'].nsmallest(1, 'score')
        # Require no alert of either direction on either adjacent date in this mode.
        singletons = grouped[(grouped.model == model) & grouped.calendar_days.eq(1)]
        isolated = group.merge(singletons[['mode', 'direction', 'start']], left_on=['mode', 'direction', 'date'], right_on=['mode', 'direction', 'start'])
        if not isolated.empty:
            alert_dates = {mode: set(part.date) for mode, part in group.groupby('mode')}
            isolated = isolated[isolated.apply(lambda row: all(row.date + pd.Timedelta(days=offset) not in alert_dates[row['mode']] for offset in (-1, 1)), axis=1)]
        sustained = grouped[(grouped.model == model) & grouped.calendar_days.ge(3)].sort_values(['calendar_days', 'max_absolute_score'], ascending=False).head(1)
        selected = [(row, label) for label, table in [('strong_positive', positive), ('strong_negative', negative), ('isolated_deviation', isolated.nlargest(1, 'absolute_deviation'))] for _, row in table.iterrows()]
        for _, episode in sustained.iterrows():
            table = group[(group['mode'] == episode['mode']) & (group.direction == episode.direction) & group.date.between(episode.start, episode.end)]
            selected += [(row, 'sustained_episode_start') for _, row in table.head(1).iterrows()]
        paired = group.groupby('date')['mode'].nunique()
        paired_dates = paired[paired == 2].index
        if len(paired_dates):
            day = group[group.date.isin(paired_dates)].sort_values('absolute_deviation', ascending=False).iloc[0].date
            selected += [(row, 'same_day_cross_mode') for _, row in group[group.date == day].iterrows()]
        for row, reason in selected:
            mode = row['mode']
            neighbors = data[(data.model == model) & (data['mode'] == mode) & (data.day_type == row.day_type) & (data.date != row.date) & data.date.between(row.date-pd.Timedelta(days=14), row.date+pd.Timedelta(days=14))]
            source = raw.loc[row.date]
            column = 'bus' if mode == 'bus' else 'rail_boardings'
            cases.append(dict(selection_reason=reason, model=model, mode=mode, date=row.date, day_type=row.day_type,
                observed=row.observed, expected=row.expected, absolute_deviation=row.absolute_deviation,
                relative_deviation_pct=row.relative_deviation_pct, residual=row.residual, score=row.score,
                center=row.center, scale=row.scale, calibration_days=row.calibration_days,
                neighboring_same_type_days=len(neighbors), neighboring_median=float(neighbors.observed.median()),
                nearby_observations=json.dumps([{'date': str(record.date.date()), 'observed': record.observed} for record in neighbors.itertuples()]),
                source_count_matches=bool(source[column] == row.observed),
                source_day_type_matches=bool(source.day_type == row.day_type),
                totals_reconcile=bool(source.bus + source.rail_boardings == source.total_rides),
                interpretation='Observed model-relative deviation; cause and event status unknown'))
    return pd.DataFrame(cases)


def run(source, archive, output, protocol):
    """Audit frozen 4C.1A predictions and write a new reproducible diagnostics version."""
    if output.exists():
        raise ValueError('Output already exists; choose a new diagnostics directory')
    path = source / 'predictions.csv'
    manifest = json.loads((source / 'manifest.json').read_text())
    detector_path = Path(__file__).with_name('anomaly.py')
    if hashlib.sha256(detector_path.read_bytes()).hexdigest() != manifest['code_sha256']:
        raise ValueError('Detector definition changed since the frozen 4C.1A run')
    bundle = load_archive(archive)
    if bundle.metadata['input_parquet_sha256'] != manifest['source']['input_parquet_sha256']:
        raise ValueError('Validated archive differs from the frozen anomaly source')
    data = add_diagnostics(pd.read_csv(path, parse_dates=['date', 'fit_cutoff']))
    raw = bundle.daily.assign(date=pd.to_datetime(bundle.daily.service_date)).set_index('date')
    for mode, column in [('bus', 'bus'), ('rail', 'rail_boardings')]:
        group = data[data['mode'] == mode]
        if not np.array_equal(group.observed.to_numpy(), raw.loc[group.date, column].to_numpy()) or not np.array_equal(group.day_type.to_numpy(), raw.loc[group.date, 'day_type'].to_numpy()):
            raise ValueError('Frozen observations differ from validated counts/day types')
    grouped = episodes(data[data['alert_3.5']])
    windows, scores = window_metrics(data, grouped)
    tables = dict(daily=data, monthly=period_metrics(data, 'M'), annual=period_metrics(data, 'Y'),
        windows=windows, scores=scores, overlap=overlap(data), episodes=grouped,
        cross_mode_episodes=episodes(data[data['alert_3.5']], combine_modes=True),
        ranked_queue=ranked_queue(data), investigations=investigate(data, raw, grouped))
    # Threshold sensitivity includes grouping burden, not only individual observations.
    sensitivity = []
    for threshold in THRESHOLDS:
        selected = data[data[f'alert_{threshold:g}']]
        for model, group in selected.groupby('model'):
            sensitivity.append(dict(threshold=threshold, model=model, raw_alert_observations=len(group),
                distinct_alert_dates=group.date.nunique(), mode_direction_episodes=len(episodes(group)),
                cross_mode_direction_episodes=len(episodes(group, combine_modes=True))))
    tables['threshold_episodes'] = pd.DataFrame(sensitivity)
    output.mkdir(parents=True)
    for name, table in tables.items():
        table.to_csv(output / f'{name}.csv', index=False)
    files = [path, detector_path, Path(__file__), protocol, source / 'manifest.json']
    provenance = dict(protocol='Retrospective temporal validation; no untouched final holdout',
        inputs_sha256={str(file): hashlib.sha256(file.read_bytes()).hexdigest() for file in files},
        outputs_sha256={name: hashlib.sha256((output / f'{name}.csv').read_bytes()).hexdigest() for name in tables},
        pandas_version=pd.__version__, numpy_version=np.__version__)
    (output / 'manifest.json').write_text(json.dumps(provenance, indent=2))
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, default=Path('docs/anomaly_validation_protocol.md'))
    args = parser.parse_args()
    print(run(args.source, args.archive, args.output, args.protocol)['windows'].to_string(index=False))


if __name__ == '__main__':
    main()
