# Milestone 4C.1B — Anomaly Validation & Investigation

Chicago Transit Authority (CTA) daily bus and rail research. An alert is a model-relative observation; an episode is a queue-grouping heuristic; neither is a confirmed external incident.

## Evaluation design and audit

Read the [frozen protocol](anomaly_validation_protocol.md). No untouched historical final holdout remains in the 4C.1A 2019-01-01–2026-08-31 window. Temporal partitions are development diagnostics (2019–2021), retrospective validation (2022–2024), and retrospective last-period assessment (2025–August 2026). All were previously exposed to model inspection. The last period is not independent evidence and 2026 is partial. No threshold was selected from last-period outcomes.

Existing calendar-median and seasonal-trend models, log-residual calibration, half-open chronological fitting bounds, and the magnitude gate are unchanged. Fixed main threshold: |score| > 3.5 and absolute count deviation >= max(10,000, 20% expected). Sensitivity: 3 and 4.5 with that same gate. These settings are research heuristics, not event probabilities or validated operational thresholds.

Source audit found no current/future-target value leakage in fitting or calibration: target counts are read only after estimating expectations, and residuals enter history after scoring. Existing deterministic tests perturb current/future observations. Monthly coefficient refresh uses only dates before month start; the median baseline uses strictly prior same-month/day-type rows. Residual history is prior 365 calendar days, same mode/model/day type, at least 30 errors. Prediction replay and CSV provenance checks are recorded separately in verification.json.

Important limitations: previously inspected temporal holdouts are contaminated for model-selection claims; archived source corrections and publication latency are not reconstructed. 4C.1A sample selection favored large scores and was not random. High errors or low alert counts are not incident recall or precision. The 31 July 2012 invalid non-midnight timestamps remain quarantined outside these model windows. Validated source has 9,343 dates; each model/mode has 2,800 scored dates in the evaluation window. No missing date is imputed. Model-date completeness does not imply measurement accuracy.

## Alert burden and temporal comparisons

Denominators below are scored mode-days, not incidents. High/low uses observed minus expected, which can differ from the sign of the centered score. WAPE = sum absolute error / sum observed boardings × 100. Episode counts intersecting temporal windows may count one boundary-crossing episode in both windows; global totals are not sums of these intersecting counts.

- all, calendar_median, bus: 2,800 days; WAPE 27.15%; 206 alerts (7.36%); high/low 4/202; 46 episodes, longest 109 days; boundary-crossing episodes 0.
- all, calendar_median, rail: 2,800 days; WAPE 37.45%; 258 alerts (9.21%); high/low 15/243; 52 episodes, longest 163 days; boundary-crossing episodes 0.
- all, seasonal_trend, bus: 2,800 days; WAPE 10.46%; 138 alerts (4.93%); high/low 29/109; 52 episodes, longest 48 days; boundary-crossing episodes 0.
- all, seasonal_trend, rail: 2,800 days; WAPE 12.80%; 161 alerts (5.75%); high/low 28/133; 50 episodes, longest 84 days; boundary-crossing episodes 0.
- development_diagnostics, calendar_median, bus: 1,096 days; WAPE 44.92%; 177 alerts (16.15%); high/low 0/177; 28 episodes, longest 109 days; boundary-crossing episodes 0.
- development_diagnostics, calendar_median, rail: 1,096 days; WAPE 67.12%; 219 alerts (19.98%); high/low 8/211; 31 episodes, longest 163 days; boundary-crossing episodes 0.
- development_diagnostics, seasonal_trend, bus: 1,096 days; WAPE 16.61%; 96 alerts (8.76%); high/low 27/69; 26 episodes, longest 48 days; boundary-crossing episodes 0.
- development_diagnostics, seasonal_trend, rail: 1,096 days; WAPE 19.70%; 114 alerts (10.40%); high/low 16/98; 22 episodes, longest 84 days; boundary-crossing episodes 0.
- retrospective_validation, calendar_median, bus: 1,096 days; WAPE 19.19%; 16 alerts (1.46%); high/low 4/12; 11 episodes, longest 3 days; boundary-crossing episodes 0.
- retrospective_validation, calendar_median, rail: 1,096 days; WAPE 21.97%; 20 alerts (1.82%); high/low 3/17; 9 episodes, longest 5 days; boundary-crossing episodes 0.
- retrospective_validation, seasonal_trend, bus: 1,096 days; WAPE 7.35%; 20 alerts (1.82%); high/low 1/19; 11 episodes, longest 4 days; boundary-crossing episodes 0.
- retrospective_validation, seasonal_trend, rail: 1,096 days; WAPE 9.03%; 24 alerts (2.19%); high/low 5/19; 14 episodes, longest 4 days; boundary-crossing episodes 0.
- retrospective_last_assessment, calendar_median, bus: 608 days; WAPE 13.41%; 13 alerts (2.14%); high/low 0/13; 7 episodes, longest 3 days; boundary-crossing episodes 0.
- retrospective_last_assessment, calendar_median, rail: 608 days; WAPE 13.08%; 19 alerts (3.12%); high/low 4/15; 12 episodes, longest 4 days; boundary-crossing episodes 0.
- retrospective_last_assessment, seasonal_trend, bus: 608 days; WAPE 6.22%; 22 alerts (3.62%); high/low 1/21; 15 episodes, longest 4 days; boundary-crossing episodes 0.
- retrospective_last_assessment, seasonal_trend, rail: 608 days; WAPE 7.40%; 23 alerts (3.78%); high/low 7/16; 14 episodes, longest 4 days; boundary-crossing episodes 0.

### Cross-mode overlap and score distributions

- calendar_median: 2,800 paired scored dates; either mode 272; both modes 192; bus-only 14; rail-only 66; same-direction both 192; alert-date intersection/union 0.706.
- seasonal_trend: 2,800 paired scored dates; either mode 202; both modes 97; bus-only 41; rail-only 64; same-direction both 97; alert-date intersection/union 0.480.
- calendar_median, bus: signed score p01/p05/median/p95/p99 = -23.85/-6.09/0.08/2.26/6.72; max |score| 35.91.
- calendar_median, rail: signed score p01/p05/median/p95/p99 = -38.77/-9.03/0.03/2.93/12.27; max |score| 50.14.
- seasonal_trend, bus: signed score p01/p05/median/p95/p99 = -10.96/-2.92/-0.04/2.31/3.50; max |score| 28.23.
- seasonal_trend, rail: signed score p01/p05/median/p95/p99 = -19.17/-3.27/-0.01/2.46/3.49; max |score| 35.85.

All monthly and annual counts, including observed zero-alert periods, are in `monthly.csv` and `annual.csv`. Complete-calendar flags prevent partial 2026 from being presented as a complete year. The five highest-rate months per model/mode are listed below; this is descriptive ranking, not statistical significance.

- calendar_median, bus: 2020-04: 30/30 (100.0%); 2020-05: 31/31 (100.0%); 2020-06: 30/30 (100.0%); 2020-07: 29/31 (93.5%); 2020-03: 17/31 (54.8%).
- calendar_median, rail: 2020-04: 30/30 (100.0%); 2020-05: 31/31 (100.0%); 2020-06: 30/30 (100.0%); 2020-07: 31/31 (100.0%); 2020-08: 25/31 (80.6%).
- seasonal_trend, bus: 2020-04: 30/30 (100.0%); 2020-03: 18/31 (58.1%); 2021-03: 17/31 (54.8%); 2021-04: 8/30 (26.7%); 2024-12: 5/31 (16.1%).
- seasonal_trend, rail: 2020-04: 30/30 (100.0%); 2020-05: 31/31 (100.0%); 2020-03: 19/31 (61.3%); 2019-02: 6/28 (21.4%); 2025-12: 6/31 (19.4%).

## Residual bias and large-shift failure analysis

The 2020–2021 sequence is a stress window identified from the existing research, not a newly detected change point. Compare 2019 before, 2020 during, and 2021 after; this temporal language does not identify a cause. Annual error, residual center, and scale follow. Annual medians pool observed day types for diagnostics; the detector itself calibrates each day type separately.

- 2019, calendar_median, bus: WAPE 6.85%; alerts 23/365; median raw log residual -0.031, center -0.038, scale 0.050; magnitude-gate days without alert 1; zero-center alerts suppressed by centering 1; alerts created by centering 0.
- 2020, calendar_median, bus: WAPE 101.69%; alerts 149/366; median raw log residual -0.891, center -0.050, scale 0.121; magnitude-gate days without alert 146; zero-center alerts suppressed by centering 36; alerts created by centering 0.
- 2021, calendar_median, bus: WAPE 63.16%; alerts 5/365; median raw log residual -0.480, center -0.856, scale 0.156; magnitude-gate days without alert 231; zero-center alerts suppressed by centering 151; alerts created by centering 3.
- 2023, calendar_median, bus: WAPE 19.73%; alerts 6/365; median raw log residual 0.223, center 0.156, scale 0.098; magnitude-gate days without alert 231; zero-center alerts suppressed by centering 41; alerts created by centering 0.
- 2019, calendar_median, rail: WAPE 7.19%; alerts 19/365; median raw log residual -0.037, center -0.021, scale 0.050; magnitude-gate days without alert 7; zero-center alerts suppressed by centering 0; alerts created by centering 1.
- 2020, calendar_median, rail: WAPE 194.70%; alerts 168/366; median raw log residual -1.530, center -0.093, scale 0.124; magnitude-gate days without alert 128; zero-center alerts suppressed by centering 14; alerts created by centering 0.
- 2021, calendar_median, rail: WAPE 110.23%; alerts 32/365; median raw log residual -0.714, center -1.384, scale 0.205; magnitude-gate days without alert 218; zero-center alerts suppressed by centering 137; alerts created by centering 11.
- 2023, calendar_median, rail: WAPE 21.94%; alerts 4/365; median raw log residual 0.225, center 0.219, scale 0.141; magnitude-gate days without alert 222; zero-center alerts suppressed by centering 27; alerts created by centering 2.
- 2019, seasonal_trend, bus: WAPE 7.90%; alerts 15/365; median raw log residual 0.027, center 0.023, scale 0.068; magnitude-gate days without alert 11; zero-center alerts suppressed by centering 2; alerts created by centering 5.
- 2020, seasonal_trend, bus: WAPE 26.33%; alerts 55/366; median raw log residual -0.150, center -0.014, scale 0.162; magnitude-gate days without alert 87; zero-center alerts suppressed by centering 0; alerts created by centering 3.
- 2021, seasonal_trend, bus: WAPE 24.19%; alerts 26/365; median raw log residual 0.243, center 0.009, scale 0.253; magnitude-gate days without alert 197; zero-center alerts suppressed by centering 0; alerts created by centering 13.
- 2023, seasonal_trend, bus: WAPE 6.95%; alerts 5/365; median raw log residual 0.021, center -0.008, scale 0.086; magnitude-gate days without alert 20; zero-center alerts suppressed by centering 0; alerts created by centering 1.
- 2019, seasonal_trend, rail: WAPE 7.58%; alerts 20/365; median raw log residual 0.012, center 0.024, scale 0.062; magnitude-gate days without alert 12; zero-center alerts suppressed by centering 4; alerts created by centering 0.
- 2020, seasonal_trend, rail: WAPE 38.93%; alerts 88/366; median raw log residual -0.186, center -0.033, scale 0.164; magnitude-gate days without alert 101; zero-center alerts suppressed by centering 5; alerts created by centering 0.
- 2021, seasonal_trend, rail: WAPE 34.74%; alerts 6/365; median raw log residual 0.371, center 0.075, scale 0.463; magnitude-gate days without alert 279; zero-center alerts suppressed by centering 0; alerts created by centering 5.
- 2023, seasonal_trend, rail: WAPE 7.27%; alerts 8/365; median raw log residual 0.004, center -0.042, scale 0.103; magnitude-gate days without alert 22; zero-center alerts suppressed by centering 0; alerts created by centering 0.

**Mechanism:** score = (raw log residual − historical residual median) / historical robust scale. A sustained signed error shifts the center, and unstable history enlarges the scale. Thus repeated large count errors can become ordinary relative to model-error history. `center_suppressed` holds the observed scale fixed and removes only the center: it isolates that arithmetic effect, not missed external incidents. Scale inflation and magnitude-gate failures are separate mechanisms. Positive center can hide sustained underestimation; negative center can hide sustained overestimation. Centering can also create alerts when a residual differs from historical bias without being large around zero.

**Interpretation:** fewer calendar-baseline alerts in later windows accompany substantially worse WAPE. Conversely, seasonal-trend error is lower but its recent alert count is higher. Neither ranking establishes real-event detection quality. Long 2020 runs indicate sustained model-context mismatch and investigation burden; adaptive calibration does not prove genuine structural adaptation.

## Threshold, ranking, and episode strategy

Episodes join consecutive calendar dates with the same model, mode, and raw direction. A non-alert day or missing date breaks the run; CTA day type may change. Cross-mode episodes instead join same-direction consecutive alert dates across bus/rail and retain all observation membership in `daily.csv`/`ranked_queue.csv`. Opposite directions remain separate. Runs may end only because the archive ends; this right-censoring is not a confirmed event resolution. No change-point model or incident deduplication is implemented.

- Threshold 3, calendar_median: 501 mode-observations, 302 dates, 110 mode/direction episodes, 76 cross-mode/direction episodes.
- Threshold 3, seasonal_trend: 393 mode-observations, 266 dates, 137 mode/direction episodes, 92 cross-mode/direction episodes.
- Threshold 3.5, calendar_median: 464 mode-observations, 272 dates, 98 mode/direction episodes, 65 cross-mode/direction episodes.
- Threshold 3.5, seasonal_trend: 299 mode-observations, 202 dates, 102 mode/direction episodes, 69 cross-mode/direction episodes.
- Threshold 4.5, calendar_median: 403 mode-observations, 230 dates, 85 mode/direction episodes, 53 cross-mode/direction episodes.
- Threshold 4.5, seasonal_trend: 217 mode-observations, 142 dates, 70 mode/direction episodes, 48 cross-mode/direction episodes.

Longest same-mode runs (global grouping):

- calendar_median, rail, low: 2020-03-13–2020-08-22, 163 days, 163 observations, max |score| 50.14.
- calendar_median, bus, low: 2020-03-16–2020-07-02, 109 days, 109 observations, max |score| 28.13.
- seasonal_trend, rail, low: 2020-03-13–2020-06-04, 84 days, 84 observations, max |score| 29.56.
- seasonal_trend, bus, low: 2020-03-14–2020-04-30, 48 days, 48 observations, max |score| 17.86.
- calendar_median, bus, low: 2020-07-04–2020-07-25, 22 days, 22 observations, max |score| 8.88.
- seasonal_trend, bus, high: 2021-03-19–2021-03-31, 13 days, 13 observations, max |score| 4.79.

Raising a threshold reduces observation volume but can omit important deviations or split runs; grouping is not guaranteed to decrease monotonically as a threshold rises. Fixed top-three monthly ranking is evaluated only as a retrospective workload illustration. It uses the full month and is not an online selection rule. Unselected observations remain exported, including their severity. A rank cap can hide large deviations during high-volume months.

- calendar_median: top-three monthly retains 101 of 464 raw alerts; 363 remain outside the queue, with maximum |score| 41.38. No production cap is recommended from this alone.
- seasonal_trend: top-three monthly retains 97 of 299 raw alerts; 202 remain outside the queue, with maximum |score| 28.07. No production cap is recommended from this alone.

## Representative investigations

Selection is deterministic and intentionally diverse, not random: strongest raw-positive/raw-negative candidates, isolated deviations (no adjacent same-mode alert of either direction), starts of the longest sustained episodes, and large same-day bus/rail pairs. Categories may select the same record. Nearby context includes ±14 calendar days of the same CTA day type, excluding the target; future neighbors are explicitly retrospective context, never a modeling input. All exact dated neighbors are retained in `investigations.csv`.

- **2021-07-29, calendar_median, rail, W** (strong_positive): observed 362,106; expected 264,471.0; absolute deviation 97,635.0; signed relative deviation +36.9%; score 11.08; center/scale -1.495/0.163; calibration n=255. Nearby same-type median 272,796, n=20. Source count/day-type match=True/True; bus + rail = total check=True.
- **2020-06-01, calendar_median, rail, W** (strong_negative): observed 27,517; expected 755,009.0; absolute deviation 727,492.0; signed relative deviation -96.4%; score -50.14; center/scale -0.044/0.065; calibration n=254. Nearby same-type median 86,518, n=19. Source count/day-type match=True/True; bus + rail = total check=True.
- **2021-06-04, calendar_median, rail, W** (isolated_deviation): observed 244,454; expected 717,811.0; absolute deviation 473,357.0; signed relative deviation -65.9%; score 3.94; center/scale -1.533/0.116; calibration n=255. Nearby same-type median 226,276, n=19. Source count/day-type match=True/True; bus + rail = total check=True.
- **2020-03-13, calendar_median, rail, W** (sustained_episode_start): observed 496,474; expected 710,058.0; absolute deviation 213,584.0; signed relative deviation -30.1%; score -6.57; center/scale -0.029/0.050; calibration n=255. Nearby same-type median 443,263, n=20. Source count/day-type match=True/True; bus + rail = total check=True.
- **2020-06-01, calendar_median, bus, W** (same_day_cross_mode): observed 146,931; expected 783,381.0; absolute deviation 636,450.0; signed relative deviation -81.2%; score -23.89; center/scale -0.038/0.068; calibration n=254. Nearby same-type median 253,916, n=19. Source count/day-type match=True/True; bus + rail = total check=True.
- **2020-06-01, calendar_median, rail, W** (same_day_cross_mode): observed 27,517; expected 755,009.0; absolute deviation 727,492.0; signed relative deviation -96.4%; score -50.14; center/scale -0.044/0.065; calibration n=254. Nearby same-type median 86,518, n=19. Source count/day-type match=True/True; bus + rail = total check=True.
- **2025-03-15, seasonal_trend, rail, A** (strong_positive): observed 578,528; expected 270,475.0; absolute deviation 308,053.0; signed relative deviation +113.9%; score 12.38; center/scale -0.024/0.063; calibration n=52. Nearby same-type median 268,528, n=4. Source count/day-type match=True/True; bus + rail = total check=True.
- **2019-01-30, seasonal_trend, rail, W** (strong_negative): observed 97,917; expected 619,410.1; absolute deviation 521,493.1; signed relative deviation -84.2%; score -35.85; center/scale 0.026/0.052; calibration n=255. Nearby same-type median 707,984, n=20. Source count/day-type match=True/True; bus + rail = total check=True.
- **2025-03-15, seasonal_trend, rail, A** (isolated_deviation): observed 578,528; expected 270,475.0; absolute deviation 308,053.0; signed relative deviation +113.9%; score 12.38; center/scale -0.024/0.063; calibration n=52. Nearby same-type median 268,528, n=4. Source count/day-type match=True/True; bus + rail = total check=True.
- **2020-03-13, seasonal_trend, rail, W** (sustained_episode_start): observed 496,474; expected 705,051.4; absolute deviation 208,577.4; signed relative deviation -29.6%; score -5.69; center/scale 0.016/0.064; calibration n=255. Nearby same-type median 443,263, n=20. Source count/day-type match=True/True; bus + rail = total check=True.
- **2020-03-26, seasonal_trend, bus, W** (same_day_cross_mode): observed 211,746; expected 833,888.4; absolute deviation 622,142.4; signed relative deviation -74.6%; score -17.69; center/scale 0.032/0.079; calibration n=255. Nearby same-type median 225,064, n=20. Source count/day-type match=True/True; bus + rail = total check=True.
- **2020-03-26, seasonal_trend, rail, W** (same_day_cross_mode): observed 100,860; expected 752,571.9; absolute deviation 651,711.9; signed relative deviation -86.6%; score -28.81; center/scale 0.012/0.070; calibration n=255. Nearby same-type median 103,353, n=20. Source count/day-type match=True/True; bus + rail = total check=True.

A particularly important interpretation check is the isolated calendar-baseline rail case on 2021-06-04: its raw residual is negative while its centered score is positive. It is higher than a strongly negative historical error center, not higher than the raw expected boarding count. Candidate direction must therefore use observed minus expected; a positive score alone must never be labeled high ridership.

For every case, supported: a validated systemwide count differs from a particular past-only expectation and calibrated error history. Unknown: weather, events, service interruptions, individual holiday effects, data-measurement error, and causal mechanisms. No external event research or incident confirmation was performed. Day-type metadata is preserved even when a date may merit calendar-specific investigation; it is not silently reclassified.

## Recommendation and unresolved risks

Continue the seasonal-trend method as a research candidate with the calendar baseline visible as a comparator. Do not promote either detector or optimize a new final threshold from this contaminated historical assessment. Keep raw observations, grouped episodes, bias/scale diagnostics, provenance, and human review decisions as separate concepts in any eventual service contract. Episode grouping can reduce queue items but must display duration, member alerts, mode overlap, and maximum severity so persistent shifts remain visible.

Before a dashboard-ready anomaly service: freeze a prospective protocol and review rubric; obtain genuinely new reporting dates; define alert budget and reviewer escalation criteria; inspect consecutive bias and calibration-scale trajectories; evaluate parameter stability without reusing the prospective assessment; then assess usefulness with independent incident/context evidence. No labeled incident detection accuracy is claimed here.

Risks remain: publication revisions and latency, no service-supply or route-level context, heterogeneous U holidays, fixed floors and gates, rolling bias masking, observation/day/episode denominators, non-random examples, retrospective top-K selection, and non-causal episode grouping. Source/hash and arithmetic validation cannot independently guarantee CTA measurement accuracy. No deployment, dashboard change, new model family, forecast, or change-point detection is part of this phase.

## Reproduction and verification

```bash
python -m urbanflow_ai.anomaly_validation --source data/anomaly/cta-4c1a-v1 --archive data/history/cta-2026-11-01-v1 --output data/anomaly/cta-4c1b-v1
python -m urbanflow_ai.anomaly_validation_report --results data/anomaly/cta-4c1b-v1 --report docs/anomaly_validation_report.md --chart docs/figures/07_anomaly_validation.html
python -m pytest tests/test_anomaly_validation.py tests/test_anomaly.py -q
TEST_DATABASE_URL=postgresql:///urbanflow_ai_test python -m pytest -q
```

Use a new output directory; neither 4C.1A files nor an existing diagnostics directory are overwritten. The manifest hashes protocol, detector source, validation source, frozen predictions, source manifest, and output CSVs. Existing data access validates the original Parquet source. `verification.json` records replay and independent-run checks; the full-suite execution result is recorded in the phase test record.

[Interactive monthly residual/calibration evidence](figures/07_anomaly_validation.html): each column is one transit mode; rows show median raw log residual, median residual center, and median scale. Monthly rates/counts and all score quantiles are in the accompanying CSVs. This is retrospective diagnostics, not formal regime detection.
