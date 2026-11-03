"""Render frozen anomaly validation diagnostics into a reproducible research report."""

import argparse
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render(directory, report, chart):
    tables = {name: pd.read_csv(directory / f'{name}.csv') for name in (
        'windows', 'overlap', 'threshold_episodes', 'monthly', 'annual', 'episodes',
        'ranked_queue', 'investigations', 'scores', 'cross_mode_episodes')}
    lines = ['# Milestone 4C.1B — Anomaly Validation & Investigation', '',
        'Chicago Transit Authority (CTA) daily bus and rail research. An alert is a model-relative observation; an episode is a queue-grouping heuristic; neither is a confirmed external incident.', '',
        '## Evaluation design and audit', '',
        'Read the [frozen protocol](anomaly_validation_protocol.md). No untouched historical final holdout remains in the 4C.1A 2019-01-01–2026-08-31 window. Temporal partitions are development diagnostics (2019–2021), retrospective validation (2022–2024), and retrospective last-period assessment (2025–August 2026). All were previously exposed to model inspection. The last period is not independent evidence and 2026 is partial. No threshold was selected from last-period outcomes.', '',
        'Existing calendar-median and seasonal-trend models, log-residual calibration, half-open chronological fitting bounds, and the magnitude gate are unchanged. Fixed main threshold: |score| > 3.5 and absolute count deviation >= max(10,000, 20% expected). Sensitivity: 3 and 4.5 with that same gate. These settings are research heuristics, not event probabilities or validated operational thresholds.', '',
        'Source audit found no current/future-target value leakage in fitting or calibration: target counts are read only after estimating expectations, and residuals enter history after scoring. Existing deterministic tests perturb current/future observations. Monthly coefficient refresh uses only dates before month start; the median baseline uses strictly prior same-month/day-type rows. Residual history is prior 365 calendar days, same mode/model/day type, at least 30 errors. Prediction replay and CSV provenance checks are recorded separately in verification.json.', '',
        'Important limitations: previously inspected temporal holdouts are contaminated for model-selection claims; archived source corrections and publication latency are not reconstructed. 4C.1A sample selection favored large scores and was not random. High errors or low alert counts are not incident recall or precision. The 31 July 2012 invalid non-midnight timestamps remain quarantined outside these model windows. Validated source has 9,343 dates; each model/mode has 2,800 scored dates in the evaluation window. No missing date is imputed. Model-date completeness does not imply measurement accuracy.', '',
        '## Alert burden and temporal comparisons', '',
        'Denominators below are scored mode-days, not incidents. High/low uses observed minus expected, which can differ from the sign of the centered score. WAPE = sum absolute error / sum observed boardings × 100. Episode counts intersecting temporal windows may count one boundary-crossing episode in both windows; global totals are not sums of these intersecting counts.', '']
    for _, r in tables['windows'].iterrows():
        lines.append(f"- {r.window}, {r.model}, {r['mode']}: {r.scored_days:,} days; WAPE {r.wape_pct:.2f}%; {r['alerts_3.5']} alerts ({r['rate_3.5_pct']:.2f}%); high/low {r.high_alerts}/{r.low_alerts}; {r.episodes_intersecting} episodes, longest {r.longest_run_days} days; boundary-crossing episodes {r.boundary_crossing_episodes}.")
    lines += ['', '### Cross-mode overlap and score distributions', '']
    for _, r in tables['overlap'].iterrows():
        lines.append(f'- {r.model}: {r.paired_scored_dates:,} paired scored dates; either mode {r.either_mode_dates}; both modes {r.both_modes_dates}; bus-only {r.bus_only_dates}; rail-only {r.rail_only_dates}; same-direction both {r.same_direction_both}; alert-date intersection/union {r.intersection_over_union:.3f}.')
    for _, r in tables['scores'][tables['scores'].window == 'all'].iterrows():
        lines.append(f"- {r.model}, {r['mode']}: signed score p01/p05/median/p95/p99 = {r['score_q0.01']:.2f}/{r['score_q0.05']:.2f}/{r['score_q0.5']:.2f}/{r['score_q0.95']:.2f}/{r['score_q0.99']:.2f}; max |score| {r.max_absolute_score:.2f}.")
    lines += ['', 'All monthly and annual counts, including observed zero-alert periods, are in `monthly.csv` and `annual.csv`. Complete-calendar flags prevent partial 2026 from being presented as a complete year. The five highest-rate months per model/mode are listed below; this is descriptive ranking, not statistical significance.', '']
    for (model, mode), g in tables['monthly'].groupby(['model','mode']):
        top = g.sort_values(['alert_rate_pct','period'], ascending=[False,True]).head(5)
        lines.append(f"- {model}, {mode}: " + '; '.join(f'{r.period}: {r.alerts}/{r.scored_days} ({r.alert_rate_pct:.1f}%)' for r in top.itertuples()) + '.')
    lines += ['', '## Residual bias and large-shift failure analysis', '',
        'The 2020–2021 sequence is a stress window identified from the existing research, not a newly detected change point. Compare 2019 before, 2020 during, and 2021 after; this temporal language does not identify a cause. Annual error, residual center, and scale follow. Annual medians pool observed day types for diagnostics; the detector itself calibrates each day type separately.', '']
    for _, r in tables['annual'][tables['annual'].period.isin([2019,2020,2021,2023])].iterrows():
        lines.append(f"- {r.period}, {r.model}, {r['mode']}: WAPE {r.wape_pct:.2f}%; alerts {r.alerts}/{r.scored_days}; median raw log residual {r.median_log_residual:.3f}, center {r.median_center:.3f}, scale {r.median_scale:.3f}; magnitude-gate days without alert {r.magnitude_without_alert}; zero-center alerts suppressed by centering {r.center_suppressed}; alerts created by centering {r.center_created}.")
    lines += ['',
        '**Mechanism:** score = (raw log residual − historical residual median) / historical robust scale. A sustained signed error shifts the center, and unstable history enlarges the scale. Thus repeated large count errors can become ordinary relative to model-error history. `center_suppressed` holds the observed scale fixed and removes only the center: it isolates that arithmetic effect, not missed external incidents. Scale inflation and magnitude-gate failures are separate mechanisms. Positive center can hide sustained underestimation; negative center can hide sustained overestimation. Centering can also create alerts when a residual differs from historical bias without being large around zero.', '',
        '**Interpretation:** fewer calendar-baseline alerts in later windows accompany substantially worse WAPE. Conversely, seasonal-trend error is lower but its recent alert count is higher. Neither ranking establishes real-event detection quality. Long 2020 runs indicate sustained model-context mismatch and investigation burden; adaptive calibration does not prove genuine structural adaptation.', '',
        '## Threshold, ranking, and episode strategy', '',
        'Episodes join consecutive calendar dates with the same model, mode, and raw direction. A non-alert day or missing date breaks the run; CTA day type may change. Cross-mode episodes instead join same-direction consecutive alert dates across bus/rail and retain all observation membership in `daily.csv`/`ranked_queue.csv`. Opposite directions remain separate. Runs may end only because the archive ends; this right-censoring is not a confirmed event resolution. No change-point model or incident deduplication is implemented.', '']
    for _, r in tables['threshold_episodes'].iterrows():
        lines.append(f'- Threshold {r.threshold:g}, {r.model}: {r.raw_alert_observations} mode-observations, {r.distinct_alert_dates} dates, {r.mode_direction_episodes} mode/direction episodes, {r.cross_mode_direction_episodes} cross-mode/direction episodes.')
    lines += ['', 'Longest same-mode runs (global grouping):', '']
    for r in tables['episodes'].sort_values(['calendar_days','max_absolute_score'], ascending=False).head(6).itertuples():
        lines.append(f'- {r.model}, {r.mode}, {r.direction}: {r.start[:10]}–{r.end[:10]}, {r.calendar_days} days, {r.alert_observations} observations, max |score| {r.max_absolute_score:.2f}.')
    lines += ['', 'Raising a threshold reduces observation volume but can omit important deviations or split runs; grouping is not guaranteed to decrease monotonically as a threshold rises. Fixed top-three monthly ranking is evaluated only as a retrospective workload illustration. It uses the full month and is not an online selection rule. Unselected observations remain exported, including their severity. A rank cap can hide large deviations during high-volume months.', '']
    for model, g in tables['ranked_queue'].groupby('model'):
        omitted = g[~g.in_monthly_top_three]
        lines.append(f'- {model}: top-three monthly retains {g.in_monthly_top_three.sum()} of {len(g)} raw alerts; {len(omitted)} remain outside the queue, with maximum |score| {omitted.absolute_score.max():.2f}. No production cap is recommended from this alone.')
    lines += ['', '## Representative investigations', '',
        'Selection is deterministic and intentionally diverse, not random: strongest raw-positive/raw-negative candidates, isolated deviations (no adjacent same-mode alert of either direction), starts of the longest sustained episodes, and large same-day bus/rail pairs. Categories may select the same record. Nearby context includes ±14 calendar days of the same CTA day type, excluding the target; future neighbors are explicitly retrospective context, never a modeling input. All exact dated neighbors are retained in `investigations.csv`.', '']
    for _, r in tables['investigations'].iterrows():
        lines.append(f"- **{r.date[:10]}, {r.model}, {r['mode']}, {r.day_type}** ({r.selection_reason}): observed {r.observed:,.0f}; expected {r.expected:,.1f}; absolute deviation {r.absolute_deviation:,.1f}; signed relative deviation {r.relative_deviation_pct:+.1f}%; score {r.score:.2f}; center/scale {r.center:.3f}/{r.scale:.3f}; calibration n={r.calibration_days}. Nearby same-type median {r.neighboring_median:,.0f}, n={r.neighboring_same_type_days}. Source count/day-type match={r.source_count_matches}/{r.source_day_type_matches}; bus + rail = total check={r.totals_reconcile}.")
    lines += ['',
        'A particularly important interpretation check is the isolated calendar-baseline rail case on 2021-06-04: its raw residual is negative while its centered score is positive. It is higher than a strongly negative historical error center, not higher than the raw expected boarding count. Candidate direction must therefore use observed minus expected; a positive score alone must never be labeled high ridership.', '',
        'For every case, supported: a validated systemwide count differs from a particular past-only expectation and calibrated error history. Unknown: weather, events, service interruptions, individual holiday effects, data-measurement error, and causal mechanisms. No external event research or incident confirmation was performed. Day-type metadata is preserved even when a date may merit calendar-specific investigation; it is not silently reclassified.', '',
        '## Recommendation and unresolved risks', '',
        'Continue the seasonal-trend method as a research candidate with the calendar baseline visible as a comparator. Do not promote either detector or optimize a new final threshold from this contaminated historical assessment. Keep raw observations, grouped episodes, bias/scale diagnostics, provenance, and human review decisions as separate concepts in any eventual service contract. Episode grouping can reduce queue items but must display duration, member alerts, mode overlap, and maximum severity so persistent shifts remain visible.', '',
        'Before a dashboard-ready anomaly service: freeze a prospective protocol and review rubric; obtain genuinely new reporting dates; define alert budget and reviewer escalation criteria; inspect consecutive bias and calibration-scale trajectories; evaluate parameter stability without reusing the prospective assessment; then assess usefulness with independent incident/context evidence. No labeled incident detection accuracy is claimed here.', '',
        'Risks remain: publication revisions and latency, no service-supply or route-level context, heterogeneous U holidays, fixed floors and gates, rolling bias masking, observation/day/episode denominators, non-random examples, retrospective top-K selection, and non-causal episode grouping. Source/hash and arithmetic validation cannot independently guarantee CTA measurement accuracy. No deployment, dashboard change, new model family, forecast, or change-point detection is part of this phase.', '',
        '## Reproduction and verification', '',
        '```bash',
        'python -m urbanflow_ai.anomaly_validation --source data/anomaly/cta-4c1a-v1 --archive data/history/cta-2026-11-01-v1 --output data/anomaly/cta-4c1b-v1',
        'python -m urbanflow_ai.anomaly_validation_report --results data/anomaly/cta-4c1b-v1 --report docs/anomaly_validation_report.md --chart docs/figures/07_anomaly_validation.html',
        'python -m pytest tests/test_anomaly_validation.py tests/test_anomaly.py -q',
        'TEST_DATABASE_URL=postgresql:///urbanflow_ai_test python -m pytest -q', '```', '',
        'Use a new output directory; neither 4C.1A files nor an existing diagnostics directory are overwritten. The manifest hashes protocol, detector source, validation source, frozen predictions, source manifest, and output CSVs. Existing data access validates the original Parquet source. `verification.json` records replay and independent-run checks; the full-suite execution result is recorded in the phase test record.', '',
        '[Interactive monthly residual/calibration evidence](figures/07_anomaly_validation.html): each column is one transit mode; rows show median raw log residual, median residual center, and median scale. Monthly rates/counts and all score quantiles are in the accompanying CSVs. This is retrospective diagnostics, not formal regime detection.', '']
    report.write_text('\n'.join(lines))
    figure = make_subplots(rows=3, cols=2, subplot_titles=[f'{metric} · {mode}' for metric in ('Raw log residual', 'Calibration center', 'Calibration scale') for mode in ('bus','rail')], vertical_spacing=.1)
    for col, mode in enumerate(('bus','rail'), start=1):
        for row, column in enumerate(('median_log_residual','median_center','median_scale'), start=1):
            for model, g in tables['monthly'][tables['monthly']['mode'] == mode].groupby('model'):
                figure.add_trace(go.Scatter(x=g.period, y=g[column], name=model, legendgroup=model,
                    showlegend=(row==1 and col==1), mode='lines',
                    line=dict(color='#0072B2' if model == 'calendar_median' else '#D55E00')), row=row,col=col)
            figure.update_xaxes(title_text='Service month', row=row,col=col)
            figure.update_yaxes(title_text='Log-boardings units', row=row,col=col)
    figure.update_layout(template='plotly_white',height=1100,title='CTA anomaly diagnostics · January 2019–August 2026 · monthly medians')
    figure.write_html(chart, include_plotlyjs=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--chart', type=Path, required=True)
    args = parser.parse_args()
    render(args.results, args.report, args.chart)


if __name__ == '__main__':
    main()
