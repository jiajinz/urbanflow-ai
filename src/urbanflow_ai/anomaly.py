"""Past-only daily anomaly research; no dashboard integration or future outputs."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data_access import validate_frame
from .dashboard_data import load_archive

MODE_COLUMNS = {'bus': 'bus', 'rail': 'rail_boardings'}
MODELS = ('calendar_median', 'seasonal_trend')


def features(dates, origin):
    """Fixed calendar features, with trend relative to the past-only fit origin."""
    dates = pd.DatetimeIndex(dates)
    trend = (dates - origin).days.to_numpy() / 365.25
    phase = 2 * np.pi * (dates.dayofyear.to_numpy() - 1) / 365.25
    week = 2 * np.pi * dates.dayofweek.to_numpy() / 7
    return np.column_stack([np.ones(len(dates)), trend, np.sin(phase), np.cos(phase),
                            np.sin(2 * phase), np.cos(2 * phase), np.sin(week), np.cos(week)])


def residual_score(residual, history):
    """Median-centered robust log residual score; unavailable until 30 prior errors."""
    if len(history) < 30:
        return np.nan, np.nan, np.nan
    center = float(np.median(history))
    scale = max(float(np.median(np.abs(np.asarray(history) - center))) / .67448975, .05)
    return (residual - center) / scale, center, scale


def detect(frame, *, warm_start='2017-01-01'):
    """Walk forward over observed dates, predicting before reading each target count.

    Fits refresh monthly using strictly earlier observations. Calibration uses
    the preceding 365 calendar days' out-of-sample residuals of the same model,
    mode, and CTA day type. Missing dates have no prediction or imputed count.
    """
    clean = validate_frame(frame).sort_values('service_date').reset_index(drop=True)
    columns = ['date', 'day_type', 'mode', 'model', 'observed', 'expected', 'residual',
               'log_residual', 'score', 'center', 'scale', 'training_days', 'calibration_days',
               'fit_cutoff', 'candidate']
    if clean.empty:
        return pd.DataFrame(columns=columns)
    dates = pd.DatetimeIndex(clean.service_date)
    kinds = clean.day_type.to_numpy()
    months = dates.month.to_numpy()
    outputs = []
    for mode, column in MODE_COLUMNS.items():
        counts = clean[column].to_numpy(dtype=float)
        cache = {}
        errors = {(model, kind): [] for model in MODELS for kind in ('W', 'A', 'U')}
        for i in np.flatnonzero(dates >= pd.Timestamp(warm_start)):
            target, kind = dates[i], kinds[i]
            previous = (dates < target) & (dates >= target - pd.Timedelta(days=1096)) & (kinds == kind) & (months == target.month)
            for model in MODELS:
                if model == 'calendar_median':
                    ntrain = int(previous.sum())
                    if ntrain < 8:
                        continue
                    expected = float(np.median(counts[previous]))
                    cutoff = dates[previous].max()
                else:
                    origin = target.to_period('M').start_time
                    key = (origin, kind)
                    if key not in cache:
                        train = (dates < origin) & (dates >= origin - pd.Timedelta(days=730)) & (kinds == kind)
                        if train.sum() < 90:
                            cache[key] = None
                        else:
                            x = features(dates[train], origin)
                            weight = np.exp2((dates[train] - origin).days.to_numpy() / 180)
                            penalty = np.eye(x.shape[1]); penalty[0, 0] = 0
                            beta = np.linalg.solve(x.T @ (weight[:, None] * x) + penalty,
                                                   x.T @ (weight * np.log1p(counts[train])))
                            cache[key] = (beta, int(train.sum()), dates[train].max())
                    if cache[key] is None:
                        continue
                    beta, ntrain, cutoff = cache[key]
                    expected = float(max(0, np.expm1(np.clip((features([target], origin) @ beta)[0], 0, 20))))
                residual = float(np.log1p(counts[i]) - np.log1p(expected))
                history = errors[model, kind]
                history[:] = [(day, value) for day, value in history if day >= target - pd.Timedelta(days=365)]
                score, center, scale = residual_score(residual, [value for _, value in history])
                difference = counts[i] - expected
                candidate = bool(np.isfinite(score) and abs(score) > 3.5 and abs(difference) >= max(10000, .2 * expected))
                outputs.append(dict(date=target, day_type=kind, mode=mode, model=model,
                    observed=counts[i], expected=expected, residual=difference, log_residual=residual,
                    score=score, center=center, scale=scale, training_days=ntrain,
                    calibration_days=len(history), fit_cutoff=cutoff, candidate=candidate))
                # Update only after scoring the current observation.
                history.append((target, residual))
    return pd.DataFrame(outputs, columns=columns).sort_values(['date', 'mode', 'model']).reset_index(drop=True)


def summarize(predictions, start='2019-01-01'):
    """Chronological descriptive evaluation; no incident labels or precision claims."""
    evaluation = predictions[(predictions.date >= pd.Timestamp(start)) & predictions.score.notna()].copy()
    if evaluation.empty:
        return evaluation, pd.DataFrame(columns=['model', 'mode', 'year', 'day_type', 'days', 'mae', 'wape_pct', 'median_abs_log_error', 'bias', 'alerts', 'alerts_3', 'alerts_3.5', 'alerts_4.5'])
    evaluation['year'] = evaluation.date.dt.year
    results = []
    for keys, group in evaluation.groupby(['model', 'mode', 'year', 'day_type']):
        gate = group.residual.abs() >= np.maximum(10000, .2 * group.expected)
        row = dict(zip(['model', 'mode', 'year', 'day_type'], keys))
        row.update(days=len(group), mae=float(group.residual.abs().mean()),
                   wape_pct=float(100 * group.residual.abs().sum() / group.observed.sum()) if group.observed.sum() else None,
                   median_abs_log_error=float(group.log_residual.abs().median()),
                   bias=float(group.residual.mean()), alerts=int(group.candidate.sum()))
        for threshold in (3, 3.5, 4.5):
            row[f'alerts_{threshold}'] = int(((group.score.abs() > threshold) & gate).sum())
        results.append(row)
    return evaluation, pd.DataFrame(results)


def run(archive, output):
    """Write a new research directory from the checksummed validated 4A archive."""
    if output.exists():
        raise ValueError('Output directory already exists; choose a new research version')
    data = load_archive(archive)
    predictions = detect(data.daily)
    evaluation, metrics = summarize(predictions)
    output.mkdir(parents=True)
    evaluation.to_csv(output / 'predictions.csv', index=False)
    metrics.to_csv(output / 'evaluation.csv', index=False)
    candidates = evaluation[evaluation.candidate].copy()
    candidates['absolute_score'] = candidates.score.abs()
    candidates.sort_values('absolute_score', ascending=False).to_csv(output / 'candidates.csv', index=False)
    manifest = dict(source=data.metadata, evaluation_start='2019-01-01', warm_start='2017-01-01',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        models=list(MODELS), score_threshold=3.5, operational_gate='abs residual >= max(10000 boardings, 20% expected)',
        dependencies={'numpy': np.__version__, 'pandas': pd.__version__},
        scope='Retrospective daily investigation candidates; not confirmed incidents or future forecasts')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(run(args.archive, args.output).to_string(index=False))


if __name__ == '__main__':
    main()
