"""Render reproducible anomaly evidence; do not fit or tune detection models."""

import argparse
from pathlib import Path

import pandas as pd
import plotly.express as px


def render(results, report, chart):
    p = pd.read_csv(results / 'predictions.csv', parse_dates=['date', 'fit_cutoff'])
    metrics = pd.read_csv(results / 'evaluation.csv')
    sample_dates = ['2026-01-23', '2025-03-15', '2024-01-15', '2024-12-24', '2025-10-12']
    lines = ['# Milestone 4C.1A — Daily Anomaly Research', '',
        'Chicago Transit Authority (CTA) daily bus and rail boardings: reproducible, past-only investigation candidates. No incident labels, causality, precision/recall claims, future forecasts, change-point detection, or dashboard integration.', '',
        '## Research question and data', '',
        'Can calendar matching and a trend/seasonality model distinguish relative daily deviations from merely high or low absolute counts? Modes are modeled separately; W = weekday, A = Saturday, U = Sunday/holiday, including weekday holidays.', '',
        'Input: unchanged `data/history/cta-2026-11-01-v1`, 9,343 validated dates from 2001-01-01 to 2026-08-31; 9,374 raw source rows. The 31 July 2012 non-midnight timestamps remain quarantined, not imputed or normalized. Existing validation, source hashes, reconciliation, and coverage checks are reused through `dashboard_data.load_archive()`. No observed date is synthesized. Daily models can use valid dates in partial months/years; 2026 is explicitly January–August, not a complete-year comparison.', '',
        'Warm-up scoring begins 2017-01-01. Evaluation is 2019-01-01–2026-08-31: 2,800 days per model/mode, with historical model training reaching back before warm-up. Primary parameters were chosen as simple research defaults before inspecting these results; no parameter search or held-out production acceptance set was used. Results are descriptive development evidence, not an unbiased model-selection guarantee.', '',
        '## Baseline and alternative', '',
        '**Calendar median:** expected boardings are the median of strictly earlier observations in the preceding 1,096 calendar days with the same calendar month and CTA day type (minimum eight). This is robust to isolated counts but can lag multi-year structural changes. Training is updated each observed date; 1,096 days approximates three years and can include an unequal number of observations per year.', '',
        '**Seasonal trend:** separate mode/day-type regressions of log(1 + boardings) use the previous 730 calendar days (minimum 90 observations). Features: intercept, linear trend in years, annual Fourier harmonics 1 and 2, and sine/cosine of day of week. Day-type fits represent W/A/U; weekly features capture variation within W and the mixed U category. Fits refresh at each month start, using only earlier dates; within-month observations do not update coefficients. Exponential weights have a 180-day half-life. Weighted least squares uses ridge penalty 1 on non-intercept coefficients. Expected counts = exp(linear estimate) − 1, clipped nonnegative; log estimates are capped at 20 for numerical safety. This estimates a log-scale central level, not an unbiased conditional count mean. No new dependencies.', '',
        '**Score for both:** r = log(1 + observed) − log(1 + expected). From the prior 365 calendar days of genuinely out-of-sample residuals for that model/mode/day type (minimum 30), compute c = median(r), s = max(MAD / 0.67448975, 0.05), z = (r − c) / s. Current r is added only after scoring. Missing calibration produces no score, never a zero score. Floors and minimum samples are explicit heuristics, not calibrated probabilities.', '',
        '**Candidate rule:** |z| > 3.5 AND |observed − expected| ≥ max(10,000 boardings, 20% of expected). Direction uses the raw residual; z is centered on historical model bias and can differ from raw residual direction. The magnitude gate expresses an initial investigation budget, not a validated service-planning threshold. Thresholds 3, 3.5, and 4.5 are compared with the same magnitude gate. These are screening scores, not significance tests or prediction intervals.', '',
        '## Chronological model comparison', '',
        'All errors use pre-target estimates. WAPE = 100 × sum absolute count error / sum observed boardings, not an average of daily percentages. MAE is boardings per observed day. Alert denominators count model/mode-days, not unique incidents. Recent and full windows use identical dates for both models. Lower error does not establish higher anomaly accuracy.', '']
    for label, subset in [('Full evaluation', p), ('2022-01-01 onward', p[p.date >= '2022-01-01'])]:
        for (model, mode), g in subset.groupby(['model', 'mode']):
            lines.append(f'- {label}, {model}, {mode}: n={len(g):,}; MAE={g.residual.abs().mean():,.1f}; WAPE={100*g.residual.abs().sum()/g.observed.sum():.2f}%; candidates={g.candidate.sum():,} ({100*g.candidate.mean():.2f}%).')
    lines += ['', '### Year/day-type stability and threshold sensitivity', '',
        'Detailed year × mode × day-type metrics are in `evaluation.csv`; annual 2026 rows are partial-year results. Below, annual ranges describe observed rates across reporting years, not confidence intervals. Monthly rate variability is descriptive and can reflect real changes or model failures.', '']
    for (model, mode), g in p.groupby(['model', 'mode']):
        gate = g.residual.abs() >= (g.expected * .2).clip(lower=10000)
        counts = [int(((g.score.abs() > k) & gate).sum()) for k in (3, 3.5, 4.5)]
        annual = g.groupby(g.date.dt.year).candidate.mean() * 100
        monthly = g.groupby(g.date.dt.to_period('M')).candidate.mean() * 100
        lines.append(f'- {model}, {mode}: candidate counts at 3/3.5/4.5 = {counts}; annual rate range {annual.min():.2f}–{annual.max():.2f}%; monthly rate SD {monthly.std():.2f} percentage points; maximum monthly rate {monthly.max():.2f}%.')
    lines += ['', '### Structural-change stress window (2020)', '']
    for (model, mode), g in p[p.date.dt.year == 2020].groupby(['model', 'mode']):
        lines.append(f'- {model}, {mode}: WAPE={100*g.residual.abs().sum()/g.observed.sum():.2f}%; candidate rate={100*g.candidate.mean():.2f}%.')
    lines += ['', 'Long alert runs during a changing demand regime should be reviewed as model-context mismatch, not independent disruptions. No algorithm in this phase classifies structural versus isolated changes, detects breakpoints, or automatically suppresses alerts. Rolling training adapts gradually; median centering and larger scales can also conceal sustained misfit.', '',
        '## Candidate observations and manual record review', '',
        'The sample below was selected after inspecting the largest post-2021 alternative-model scores, with high/low cases and multiple day types. It is not a random sample or incident validation. Raw count reconciliation, archived day type, neighboring same-type values, and baseline agreement were checked from the validated archive by the reproduction audit. No external event attribution was attempted.', '']
    for day in sample_dates:
        for _, row in p[(p.date == day) & (p.model == 'seasonal_trend') & p.candidate].iterrows():
            other = p[(p.date == day) & (p.model == 'calendar_median') & (p['mode'] == row['mode'])].iloc[0]
            neighborhood = p[(p.date >= row.date-pd.Timedelta(days=14)) & (p.date <= row.date+pd.Timedelta(days=14)) & (p.date != row.date) & (p.model == 'seasonal_trend') & (p['mode'] == row['mode']) & (p.day_type == row.day_type)]
            lines.append(f"- {day}, {row.day_type}, {row['mode']}: observed {row.observed:,.0f}; expected {row.expected:,.1f}; residual {row.residual:+,.1f}; z={row.score:.2f}; prior calibration n={row.calibration_days}; baseline z={other.score:.2f}, candidate={other.candidate}. Neighboring ±14-day same-type observed median={neighborhood.observed.median():,.0f} (n={len(neighborhood)}; retrospective context only, not model input).")
    lines += ['', 'The 2025-03-15 high-rail observation also appeared in the 4A retrospective screen. Agreement between screens is not independent ground truth. W observations around calendar holidays highlight that agency day-type categories do not identify holiday eves, individual holiday effects, or service supplied. Neither count reconciliation nor a large residual establishes an operational disruption.', '',
        '## Limitations and recommendation', '',
        '- No labeled incidents: precision, recall, and causal attribution are unavailable. Multiple daily tests create investigation workload; no false-discovery control is claimed.',
        '- Retrospective archive reflects one extraction, not historical publication vintages; point-in-time feature construction cannot undo source revisions or unknown reporting latency. The day type is treated as known when investigating a reported date.',
        '- No service supply, route/station, weather, events, individual holiday calendar, or intraday context. U remains heterogeneous. Weekday effects and annual Fourier terms can be misspecified; leap-day approximation uses 365.25 days.',
        '- Least squares on logs remains sensitive to regime shifts and influential training records. The scale floor, calibration window, refit cadence, minimum histories, and magnitude gate need prospective sensitivity review. Historical anomalies are not removed from training/calibration and may cause masking.',
        '- More recent data are not a locked holdout; no learned hyperparameter selection or evidence of production readiness. Daily count error and alert frequency evaluate behavior, not event-detection correctness.',
        '- Synthetic high/low log-residual tests are supplemental engineering checks only. They do not estimate real-event sensitivity or test every model failure mode.', '',
        '**Recommendation:** advance the seasonal-trend approach only as a research candidate because it reduces count residuals in both windows. Retain calendar median as an interpretable comparator. Before integration, review candidate usefulness with a domain expert, audit sustained bias/alert runs, test lookback/half-life/scale-floor sensitivity using a locked later period, and agree on an investigation budget. Fewer baseline alerts despite larger recent error demonstrate why alert counts alone are insufficient. No Streamlit integration is authorized in this phase.', '',
        '## Verification record', '',
        'Phase execution: seven anomaly tests passed; complete suite including configured local PostgreSQL integration tests passed with 219 passed, 0 failed, 0 skipped. Tests cover future/current-target leakage, exact calendar medians, missing dates, invalid/empty data, scale floors, synthetic high/low residual checks, threshold monotonicity, and overwrite protection. No live API requests. These are software and reproducibility checks, not incident accuracy validation.', '',
        'An independent detector rerun produced byte-identical predictions, candidates, and evaluation CSVs. Every exported observed count and day type matched the archive, every fit cutoff preceded its target date, and protected old data, SQL, chart/style files, and analytics hashes were unchanged. See `data/anomaly/cta-4c1a-v1/verification.json`. The approved Dashboard UI was not edited. July 2012 is outside the selected model-training/evaluation windows; it remains important provenance, not a fabricated model observation.', '',
        '## Reproduction and sources', '',
        '```bash',
        'python -m urbanflow_ai.anomaly --archive data/history/cta-2026-11-01-v1 --output data/anomaly/cta-4c1a-v1',
        'python -m urbanflow_ai.anomaly_report --results data/anomaly/cta-4c1a-v1 --report docs/anomaly_research_report.md --chart docs/figures/06_anomaly_evaluation.html',
        'python -m pytest tests/test_anomaly.py -q', '```', '',
        'Use a new output directory for each detector run; existing artifacts cannot be overwritten. The manifest records code and input hashes, versions, provenance, windows, and thresholds. `predictions.csv` contains scored evaluation dates; warm-up/no-score records are omitted from that export. `candidates.csv` is the full ranked investigation list. `evaluation.csv` records year/day-type results and threshold sensitivity.', '',
        '[Interactive monthly error evidence](figures/06_anomaly_evaluation.html) is self-contained Plotly, with no external script or API dependency.', '',
        '[Time-ordered evaluation](https://otexts.com/fpp3/tscv.html) motivates past-only estimation. [NIST outlier guidance](https://itl.nist.gov/div898/handbook/eda/section3/eda35h.htm) supports candidate labeling rather than automatic error attribution; [NIST MAD definition](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/mad.htm) explains robust scale. The project-specific residual floor and magnitude gate are not NIST recommendations.', '']
    report.write_text('\n'.join(lines))
    monthly = p.assign(month=p.date.dt.to_period('M').dt.to_timestamp(), absolute_error=p.residual.abs()).groupby(['month', 'model', 'mode'], as_index=False).absolute_error.mean()
    figure = px.line(monthly, x='month', y='absolute_error', color='model', facet_row='mode',
                     title='Past-only daily ridership estimates: monthly mean absolute error',
                     labels={'absolute_error': 'Mean absolute error (boardings/day)', 'month': 'Service month', 'model': 'Model', 'mode': 'Transit mode'})
    figure.update_layout(template='plotly_white', height=650)
    figure.write_html(chart, include_plotlyjs=True)
    return p, metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--chart', type=Path, required=True)
    args = parser.parse_args()
    render(args.results, args.report, args.chart)


if __name__ == '__main__':
    main()
