# Milestone 4C.1A — Daily Anomaly Research

Chicago Transit Authority (CTA) daily bus and rail boardings: reproducible, past-only investigation candidates. No incident labels, causality, precision/recall claims, future forecasts, change-point detection, or dashboard integration.

## Research question and data

Can calendar matching and a trend/seasonality model distinguish relative daily deviations from merely high or low absolute counts? Modes are modeled separately; W = weekday, A = Saturday, U = Sunday/holiday, including weekday holidays.

Input: unchanged `data/history/cta-2026-11-01-v1`, 9,343 validated dates from 2001-01-01 to 2026-08-31; 9,374 raw source rows. The 31 July 2012 non-midnight timestamps remain quarantined, not imputed or normalized. Existing validation, source hashes, reconciliation, and coverage checks are reused through `dashboard_data.load_archive()`. No observed date is synthesized. Daily models can use valid dates in partial months/years; 2026 is explicitly January–August, not a complete-year comparison.

Warm-up scoring begins 2017-01-01. Evaluation is 2019-01-01–2026-08-31: 2,800 days per model/mode, with historical model training reaching back before warm-up. Primary parameters were chosen as simple research defaults before inspecting these results; no parameter search or held-out production acceptance set was used. Results are descriptive development evidence, not an unbiased model-selection guarantee.

## Baseline and alternative

**Calendar median:** expected boardings are the median of strictly earlier observations in the preceding 1,096 calendar days with the same calendar month and CTA day type (minimum eight). This is robust to isolated counts but can lag multi-year structural changes. Training is updated each observed date; 1,096 days approximates three years and can include an unequal number of observations per year.

**Seasonal trend:** separate mode/day-type regressions of log(1 + boardings) use the previous 730 calendar days (minimum 90 observations). Features: intercept, linear trend in years, annual Fourier harmonics 1 and 2, and sine/cosine of day of week. Day-type fits represent W/A/U; weekly features capture variation within W and the mixed U category. Fits refresh at each month start, using only earlier dates; within-month observations do not update coefficients. Exponential weights have a 180-day half-life. Weighted least squares uses ridge penalty 1 on non-intercept coefficients. Expected counts = exp(linear estimate) − 1, clipped nonnegative; log estimates are capped at 20 for numerical safety. This estimates a log-scale central level, not an unbiased conditional count mean. No new dependencies.

**Score for both:** r = log(1 + observed) − log(1 + expected). From the prior 365 calendar days of genuinely out-of-sample residuals for that model/mode/day type (minimum 30), compute c = median(r), s = max(MAD / 0.67448975, 0.05), z = (r − c) / s. Current r is added only after scoring. Missing calibration produces no score, never a zero score. Floors and minimum samples are explicit heuristics, not calibrated probabilities.

**Candidate rule:** |z| > 3.5 AND |observed − expected| ≥ max(10,000 boardings, 20% of expected). Direction uses the raw residual; z is centered on historical model bias and can differ from raw residual direction. The magnitude gate expresses an initial investigation budget, not a validated service-planning threshold. Thresholds 3, 3.5, and 4.5 are compared with the same magnitude gate. These are screening scores, not significance tests or prediction intervals.

## Chronological model comparison

All errors use pre-target estimates. WAPE = 100 × sum absolute count error / sum observed boardings, not an average of daily percentages. MAE is boardings per observed day. Alert denominators count model/mode-days, not unique incidents. Recent and full windows use identical dates for both models. Lower error does not establish higher anomaly accuracy.

- Full evaluation, calendar_median, bus: n=2,800; MAE=125,573.5; WAPE=27.15%; candidates=206 (7.36%).
- Full evaluation, calendar_median, rail: n=2,800; MAE=127,649.2; WAPE=37.45%; candidates=258 (9.21%).
- Full evaluation, seasonal_trend, bus: n=2,800; MAE=48,386.5; WAPE=10.46%; candidates=138 (4.93%).
- Full evaluation, seasonal_trend, rail: n=2,800; MAE=43,636.0; WAPE=12.80%; candidates=161 (5.75%).
- 2022-01-01 onward, calendar_median, bus: n=1,704; MAE=80,826.0; WAPE=16.82%; candidates=29 (1.70%).
- 2022-01-01 onward, calendar_median, rail: n=1,704; MAE=62,776.9; WAPE=18.41%; candidates=39 (2.29%).
- 2022-01-01 onward, seasonal_trend, bus: n=1,704; MAE=33,088.9; WAPE=6.89%; candidates=42 (2.46%).
- 2022-01-01 onward, seasonal_trend, rail: n=1,704; MAE=28,573.8; WAPE=8.38%; candidates=47 (2.76%).

### Year/day-type stability and threshold sensitivity

Detailed year × mode × day-type metrics are in `evaluation.csv`; annual 2026 rows are partial-year results. Below, annual ranges describe observed rates across reporting years, not confidence intervals. Monthly rate variability is descriptive and can reflect real changes or model failures.

- calendar_median, bus: candidate counts at 3/3.5/4.5 = [223, 206, 185]; annual rate range 0.82–40.71%; monthly rate SD 20.96 percentage points; maximum monthly rate 100.00%.
- calendar_median, rail: candidate counts at 3/3.5/4.5 = [278, 258, 218]; annual rate range 0.82–45.90%; monthly rate SD 22.80 percentage points; maximum monthly rate 100.00%.
- seasonal_trend, bus: candidate counts at 3/3.5/4.5 = [179, 138, 89]; annual rate range 1.37–15.03%; monthly rate SD 13.62 percentage points; maximum monthly rate 100.00%.
- seasonal_trend, rail: candidate counts at 3/3.5/4.5 = [214, 161, 128]; annual rate range 1.10–24.04%; monthly rate SD 16.12 percentage points; maximum monthly rate 100.00%.

### Structural-change stress window (2020)

- calendar_median, bus: WAPE=101.69%; candidate rate=40.71%.
- calendar_median, rail: WAPE=194.70%; candidate rate=45.90%.
- seasonal_trend, bus: WAPE=26.33%; candidate rate=15.03%.
- seasonal_trend, rail: WAPE=38.93%; candidate rate=24.04%.

Long alert runs during a changing demand regime should be reviewed as model-context mismatch, not independent disruptions. No algorithm in this phase classifies structural versus isolated changes, detects breakpoints, or automatically suppresses alerts. Rolling training adapts gradually; median centering and larger scales can also conceal sustained misfit.

## Candidate observations and manual record review

The sample below was selected after inspecting the largest post-2021 alternative-model scores, with high/low cases and multiple day types. It is not a random sample or incident validation. Raw count reconciliation, archived day type, neighboring same-type values, and baseline agreement were checked from the validated archive by the reproduction audit. No external event attribution was attempted.

- 2026-01-23, W, bus: observed 241,720; expected 538,240.3; residual -296,520.3; z=-13.24; prior calibration n=255; baseline z=-10.86, candidate=True. Neighboring ±14-day same-type observed median=601,534 (n=20; retrospective context only, not model input).
- 2026-01-23, W, rail: observed 145,668; expected 328,607.4; residual -182,939.4; z=-12.66; prior calibration n=255; baseline z=-11.09, candidate=True. Neighboring ±14-day same-type observed median=395,172 (n=20; retrospective context only, not model input).
- 2025-03-15, A, rail: observed 578,528; expected 270,475.0; residual +308,053.0; z=12.38; prior calibration n=52; baseline z=7.27, candidate=True. Neighboring ±14-day same-type observed median=268,528 (n=4; retrospective context only, not model input).
- 2024-01-15, W, bus: observed 206,791; expected 455,236.0; residual -248,445.0; z=-11.12; prior calibration n=254; baseline z=-8.17, candidate=True. Neighboring ±14-day same-type observed median=517,198 (n=19; retrospective context only, not model input).
- 2024-01-15, W, rail: observed 127,069; expected 283,744.5; residual -156,675.5; z=-11.11; prior calibration n=254; baseline z=-6.28, candidate=True. Neighboring ±14-day same-type observed median=329,826 (n=19; retrospective context only, not model input).
- 2024-12-24, W, bus: observed 341,225; expected 531,972.9; residual -190,747.9; z=-6.91; prior calibration n=255; baseline z=-7.02, candidate=True. Neighboring ±14-day same-type observed median=512,124 (n=18; retrospective context only, not model input).
- 2024-12-24, W, rail: observed 181,487; expected 348,687.1; residual -167,200.1; z=-10.96; prior calibration n=255; baseline z=-7.77, candidate=True. Neighboring ±14-day same-type observed median=334,620 (n=18; retrospective context only, not model input).
- 2025-10-12, U, rail: observed 557,727; expected 276,116.4; residual +281,610.6; z=8.23; prior calibration n=58; baseline z=6.03, candidate=True. Neighboring ±14-day same-type observed median=257,642 (n=4; retrospective context only, not model input).

The 2025-03-15 high-rail observation also appeared in the 4A retrospective screen. Agreement between screens is not independent ground truth. W observations around calendar holidays highlight that agency day-type categories do not identify holiday eves, individual holiday effects, or service supplied. Neither count reconciliation nor a large residual establishes an operational disruption.

## Limitations and recommendation

- No labeled incidents: precision, recall, and causal attribution are unavailable. Multiple daily tests create investigation workload; no false-discovery control is claimed.
- Retrospective archive reflects one extraction, not historical publication vintages; point-in-time feature construction cannot undo source revisions or unknown reporting latency. The day type is treated as known when investigating a reported date.
- No service supply, route/station, weather, events, individual holiday calendar, or intraday context. U remains heterogeneous. Weekday effects and annual Fourier terms can be misspecified; leap-day approximation uses 365.25 days.
- Least squares on logs remains sensitive to regime shifts and influential training records. The scale floor, calibration window, refit cadence, minimum histories, and magnitude gate need prospective sensitivity review. Historical anomalies are not removed from training/calibration and may cause masking.
- More recent data are not a locked holdout; no learned hyperparameter selection or evidence of production readiness. Daily count error and alert frequency evaluate behavior, not event-detection correctness.
- Synthetic high/low log-residual tests are supplemental engineering checks only. They do not estimate real-event sensitivity or test every model failure mode.

**Recommendation:** advance the seasonal-trend approach only as a research candidate because it reduces count residuals in both windows. Retain calendar median as an interpretable comparator. Before integration, review candidate usefulness with a domain expert, audit sustained bias/alert runs, test lookback/half-life/scale-floor sensitivity using a locked later period, and agree on an investigation budget. Fewer baseline alerts despite larger recent error demonstrate why alert counts alone are insufficient. No Streamlit integration is authorized in this phase.

## Verification record

Phase execution: seven anomaly tests passed; complete suite including configured local PostgreSQL integration tests passed with 219 passed, 0 failed, 0 skipped. Tests cover future/current-target leakage, exact calendar medians, missing dates, invalid/empty data, scale floors, synthetic high/low residual checks, threshold monotonicity, and overwrite protection. No live API requests. These are software and reproducibility checks, not incident accuracy validation.

An independent detector rerun produced byte-identical predictions, candidates, and evaluation CSVs. Every exported observed count and day type matched the archive, every fit cutoff preceded its target date, and protected old data, SQL, chart/style files, and analytics hashes were unchanged. See `data/anomaly/cta-4c1a-v1/verification.json`. The approved Dashboard UI was not edited. July 2012 is outside the selected model-training/evaluation windows; it remains important provenance, not a fabricated model observation.

## Reproduction and sources

```bash
python -m urbanflow_ai.anomaly --archive data/history/cta-2026-11-01-v1 --output data/anomaly/cta-4c1a-v1
python -m urbanflow_ai.anomaly_report --results data/anomaly/cta-4c1a-v1 --report docs/anomaly_research_report.md --chart docs/figures/06_anomaly_evaluation.html
python -m pytest tests/test_anomaly.py -q
```

Use a new output directory for each detector run; existing artifacts cannot be overwritten. The manifest records code and input hashes, versions, provenance, windows, and thresholds. `predictions.csv` contains scored evaluation dates; warm-up/no-score records are omitted from that export. `candidates.csv` is the full ranked investigation list. `evaluation.csv` records year/day-type results and threshold sensitivity.

[Interactive monthly error evidence](figures/06_anomaly_evaluation.html) is self-contained Plotly, with no external script or API dependency.

[Time-ordered evaluation](https://otexts.com/fpp3/tscv.html) motivates past-only estimation. [NIST outlier guidance](https://itl.nist.gov/div898/handbook/eda/section3/eda35h.htm) supports candidate labeling rather than automatic error attribution; [NIST MAD definition](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/mad.htm) explains robust scale. The project-specific residual floor and magnitude gate are not NIST recommendations.
