# Milestone 4C.1C — Investigation Workflow & Model Readiness

Chicago Transit Authority (CTA) retrospective evidence; current integration decision: **NO-GO**. This phase exports auditable cases and separate health indicators. No production detector, review service, incident confirmation, prospective execution, or Dashboard integration is implemented.

## Audit and reuse

4C.1A already implements separate bus/rail calendar-median and seasonal-trend estimators with past-only log-residual calibration. 4C.1B already implements threshold sensitivity, raw-direction diagnostics, chronological partitions, overlap, and episode grouping. This phase reuses `add_diagnostics()`, `episodes()`, `load_archive()`, frozen predictions, and validated archives. Existing model source, SQL, research definitions, historical snapshots, README, and Dashboard files were not changed.

All dates through 2026-08-31 were already inspected. No previously inspected period becomes an independent holdout. No API acquisition or external event research occurred; new data availability has not been checked. The source retains 31 quarantined July 2012 timestamps; that period is outside the current scoring window and is not imputed.

## Auditable investigation records

`cases.csv` contains **763** model/mode/date candidates: calendar_median 464, seasonal_trend 299. All are preserved, with stable case IDs and exactly one of 200 traceable same-mode/direction episodes. Every review is initially unreviewed; cause unknown; uncertainty high. No human investigation usefulness is inferred from the export.

Fields include actual/expected boardings; signed, absolute and percentage deviation; actual direction; centered score and sign; dated prior same-type observations; same-date cross-mode counts/expectations/alert/direction; stable episode ID and elapsed days; source checks and coverage; model-health state; transparent priority components; review status, reviewer/time/evidence placeholders and limitations. Relative deviation is unavailable for zero expected counts, not infinite or zero.

**32 cases** have score sign opposite to actual deviation direction. Actual direction always follows observed minus expected. A score is relative to historical residual bias, not necessarily relative to expected counts.

Prior comparable observations use only the preceding 28 calendar days, same CTA day type, excluding the target. No future neighbors enter cases. Same-date cross-mode evidence is explicitly unavailable if missing. Source counts, day types and bus + rail reconciliation are checked. Validated matches do not independently establish agency measurement accuracy. Partial context is marked and routed to data/context follow-up; severe cases are not deleted.

Full episode end/duration in `episode_registry.csv` are retrospective context. Case age, ID, priority and daily rank use only the episode start and current date; no final duration enters as-of ranking. The same case can be revisited in an append-only review ledger; that operational ledger and state-transition enforcement are specified, not implemented.

## Separate model-health diagnostics

Health metrics are trailing 28-calendar-day statistics as of the reported date, including its observed count. They are not inputs available before observing that date. Minimum 21 scored observations permits partial-window calculations; a clear/evaluable classification requires all 28 dates, mature context, defined error/bias, and evaluable same-type drift for W/A/U. Missing dates, insufficient history and unknown drift never become clear. No count is zero-filled.

Fixed guards: absolute median daily relative residual >20%; WAPE >20%; same-sign residual fraction >=80% with bias >20% for sustained under/overprediction; raw candidate rate >20%. For each day type compare current 28-day calibration medians with preceding disjoint 84 days: center shift >0.15 log units or scale ratio outside [0.5,2] warns, requiring >=3 current and >=9 reference observations. These are proposed engineering gates, not significance levels. Day-type drift prevents simple calendar-composition changes from being the sole comparison; individual holiday mix remains uncontrolled.

Health warning rates below use fully evaluable dates only. Rolling windows overlap and are not independent events. Unknown and partial dates are reported separately; warning run lengths do not identify causal regime changes.

- calendar_median, bus: 2,712 evaluable / 2,800 calendar dates; warnings 1,591 (58.67%); longest warning run 720 days; sustained under/overprediction 746/568; drift-warning dates 366. Previously inspected 2025–August 2026: 147/608 warnings (24.18%).
- calendar_median, rail: 2,712 evaluable / 2,800 calendar dates; warnings 1,389 (51.22%); longest warning run 898 days; sustained under/overprediction 577/499; drift-warning dates 501. Previously inspected 2025–August 2026: 7/608 warnings (1.15%).
- seasonal_trend, bus: 2,712 evaluable / 2,800 calendar dates; warnings 433 (15.97%); longest warning run 179 days; sustained under/overprediction 215/146; drift-warning dates 46. Previously inspected 2025–August 2026: 3/608 warnings (0.49%).
- seasonal_trend, rail: 2,712 evaluable / 2,800 calendar dates; warnings 659 (24.30%); longest warning run 283 days; sustained under/overprediction 283/202; drift-warning dates 247. Previously inspected 2025–August 2026: 29/608 warnings (4.77%).

551 candidate records coincide with a model-health warning; this does not invalidate or confirm their ridership deviation. Route model-health review separately and retain their original alert status. All retrospective initial unknown/insufficient classifications remain visible.

## Representative case studies

Examples are selected for interpretation, not sampled accuracy. Full prior observations and source checks are in the case table. What all examples support: model-relative deviations in validated systemwide counts. What remains unknown: service interruptions, weather, event attribution, individual holiday effects, causes, and measurement error. No external incident evidence was collected.

- **2021-06-04, calendar_median, rail:** observed 244,454, expected 717,811.0; signed deviation -473,357.0, absolute 473,357.0, relative -65.94%; actual direction low, centered score +3.94 (positive). Prior same-type median 208,470, n=19; preceding calendar coverage 28/28. Other mode available/alert=True/False, direction=low. Episode calendar_median|rail|low|2021-06-04, elapsed 1 days. Health=warning; source status=validated_matches_archive; review=unreviewed; uncertainty=high; model-relative evidence only.
- **2025-03-15, seasonal_trend, rail:** observed 578,528, expected 270,475.0; signed deviation +308,053.0, absolute 308,053.0, relative +113.89%; actual direction high, centered score +12.38 (positive). Prior same-type median 243,450, n=4; preceding calendar coverage 28/28. Other mode available/alert=True/False, direction=high. Episode seasonal_trend|rail|high|2025-03-15, elapsed 1 days. Health=clear; source status=validated_matches_archive; review=unreviewed; uncertainty=high; model-relative evidence only.
- **2026-01-23, seasonal_trend, bus:** observed 241,720, expected 538,240.3; signed deviation -296,520.3, absolute 296,520.3, relative -55.09%; actual direction low, centered score -13.24 (negative). Prior same-type median 586,434, n=19; preceding calendar coverage 28/28. Other mode available/alert=True/True, direction=low. Episode seasonal_trend|bus|low|2026-01-23, elapsed 1 days. Health=clear; source status=validated_matches_archive; review=unreviewed; uncertainty=high; model-relative evidence only.
- **2026-01-23, seasonal_trend, rail:** observed 145,668, expected 328,607.4; signed deviation -182,939.4, absolute 182,939.4, relative -55.67%; actual direction low, centered score -12.66 (negative). Prior same-type median 375,119, n=19; preceding calendar coverage 28/28. Other mode available/alert=True/True, direction=low. Episode seasonal_trend|rail|low|2026-01-23, elapsed 1 days. Health=warning; source status=validated_matches_archive; review=unreviewed; uncertainty=high; model-relative evidence only.
- **2020-04-01, seasonal_trend, rail:** observed 100,042, expected 381,389.3; signed deviation -281,347.3, absolute 281,347.3, relative -73.77%; actual direction low, centered score -19.17 (negative). Prior same-type median 198,305, n=20; preceding calendar coverage 28/28. Other mode available/alert=True/True, direction=low. Episode seasonal_trend|rail|low|2020-03-13, elapsed 20 days. Health=warning; source status=validated_matches_archive; review=unreviewed; uncertainty=high; model-relative evidence only.

The 2021 baseline example is low relative to expected counts despite a positive centered score, demonstrating bias absorption. The March 2025 rail example is an isolated high-deviation investigation. January 2026 provides same-day bus/rail evidence, not independent causal corroboration. The April 2020 example sits inside a long alert episode and a model-health stress context; it cannot automatically become a separate disruption or an identified change point.

## Review ordering and capacity policy

Priority sums visible components: magnitude (1 at >=20% absolute relative deviation, 2 at >=50%), unusualness (1 at |score|>=5, 2 at >=10), other-mode same-day alert (+1), episode age >=3 days (+1). Same-date rank uses priority, incomplete context first, then stable case ID. Missing percentage contributes no magnitude points and stays explicit. Data completeness selects a follow-up lane without dropping severity. Model-health warnings remain a separate escalation. Ranking is a workload heuristic, not incident likelihood.

Proposed capacity is 10 new case reviews/week across both models/modes plus 2 non-alert audits. Actual human throughput/backlog is not simulated. Of 102 weeks with candidate arrivals, 27 exceed new-case capacity; maximum arrivals 28. 549/763 records meet proposed urgency (|score|>=10, |relative deviation|>=50%, or episode age>=7); urgent arrivals alone exceed capacity in 21 weeks. Raw candidate records across models can describe the same real-world date and do not represent unique incidents.

This stress result makes the proposed budget/urgency policy unproven, especially during sustained failures. Do not silently relax thresholds or discard overflow. Maintain all cases; acknowledge urgent records within two business days and others within five; escalate staffing when urgent arrivals exceed capacity, pending records exceed 20, or an SLA is breached. Episode-member updates may share an investigation with every member ID preserved. Queue age and achieved SLA require real append-only reviewer records and were not measured retrospectively.

Human workflow: validate source and prior coverage -> inspect actual direction versus centered score -> inspect cross-mode/episode/health context -> record evidence, uncertainty and a justified disposition -> escalate model/data issues separately. Cause remains unknown unless independently source-supported. Proposed review states and correction policy are in the prospective protocol; every exported record remains unreviewed.

## Prospective validation and go/no-go

The [frozen prospective protocol](anomaly_prospective_protocol.md) and `anomaly_readiness_config.json` freeze detector hash, 3.5 primary threshold and magnitude gate, health rules, review rubric, metrics, budget assumptions and signoff criteria. Freeze UTC is recorded in configuration; both files are hashed in the output manifest. No future newly published observations were acquired or evaluated; prospective evidence is absent and availability unknown.

- Eligibility: service dates after 2026-08-31, unseen, acquired after freeze, with post-freeze publication evidence. Unknown publication time cannot support an independent newly-published-data claim. Source vintages and revisions must be logged; later-published prior records must not leak into earlier evaluations.
- Duration: at least 90 eligible consecutive service dates; extend to at most 180 if fewer than 30 cases complete review. Fewer observations/reviews is inconclusive.
- Integrity: zero chronology/hash/reconciliation violations, 100% candidate preservation, >=99% scored calendar coverage per mode.
- Health: <=10% warning dates; no unresolved seven-day warning run; no unknown health states at signoff. These guards are proposed, not an established operating envelope.
- Human evidence: >=30 cases from a predeclared stratified random sample (seed 42); >=80% reviewer-justified investigation usefulness. Review every urgent case separately; report its selection bias. At least 20% of sampled cases double-reviewed, >=80% disposition agreement and adjudicated disagreements.
- Operations: >=95% overall acknowledgment within five business days, 100% urgent within two, no overdue overflow at signoff, and an owned escalation/revision policy. Define the actual business calendar before measuring SLA.
- Claims: no unsupported incident/causal statements; every reviewed decision needs reviewer, UTC time, uncertainty and evidence. Non-alert audits do not establish incident recall. Any threshold/rubric change requires a new version and fresh prospective assessment.

**Current decision: NO-GO for dashboard integration.** Artifact integrity and case traceability are demonstrated, but no prospective period, human usefulness assessment, reviewer agreement, actual SLA or capacity evidence exists. Historical health failures and overload reinforce that absence. Recent historical warning rates below a proposed bound do not pass an untouched prospective gate. Readiness is not an automatically issued certificate.

## Unresolved risks and next step

Rolling bias absorption, scale inflation, correlated health windows, mixed holidays, absent service supply, source publication/revision uncertainty, ambiguous incident labels, duplicate cross-model workload, and urgent-volume overload remain. A validated data record is not a verified real-world measurement. Full episode endings are retrospective and not known live. The retrospective calendar spine stops at the last scored service date; detecting delayed or absent tail publications requires a separate feed-freshness monitor, which is not implemented. No new model family, forecasting, change-point algorithm, agent, LLM, or UI was added.

Next step requires explicit approval: assign a human reviewer and agree on capacity/SLA/calendar, freeze prospective acquisition eligibility, acquire unseen publication-vintaged observations, and run a time-ordered shadow review with the unchanged detector. Do not start public Dashboard integration or 4C.2 from this report.

## Reproduction and verification

```bash
python -m urbanflow_ai.anomaly_readiness --source data/anomaly/cta-4c1b-v1 --archive data/history/cta-2026-11-01-v1 --output data/anomaly/cta-4c1c-v1
python -m urbanflow_ai.anomaly_readiness_report --results data/anomaly/cta-4c1c-v1 --report docs/anomaly_readiness_report.md --chart docs/figures/08_anomaly_readiness.html
python -m pytest tests/test_anomaly_readiness.py -q
TEST_DATABASE_URL=postgresql:///urbanflow_ai_test python -m pytest -q
```

Use new output paths; existing research is never overwritten. Manifests hash source diagnostics, detector, configuration, protocol and outputs. The verification record reports tests actually executed, prior-artifact hash preservation, independent rerun equality and future-suffix invariance. No browser or accessibility audit is claimed.

[Retrospective health-warning evidence](figures/08_anomaly_readiness.html) plots monthly fractions of fully evaluable as-of dates with warnings. Months without evaluable dates are omitted, not zero-filled; overlapping rolling windows are not independent incidents.
