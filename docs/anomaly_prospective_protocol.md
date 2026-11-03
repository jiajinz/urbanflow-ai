# Milestone 4C.1C — Prospective Validation and Readiness Protocol

Chicago Transit Authority (CTA) anomaly investigation; proposed engineering gates,
not validated statistical cutoffs. This document and `anomaly_readiness_config.json`
are frozen by SHA-256 in the 4C.1C manifest before prospective data acquisition.
No newly published observations were acquired or assessed in this phase; whether
new agency observations are available has not been checked.

## Eligibility and frozen detector

All historical dates through 2026-08-31 were exposed in 4A/4C.1A/1B. None can be
relabeled untouched. New records must have a service date after this boundary,
first acquisition after the freeze, no prior researcher inspection, and evidence
that publication occurred after the freeze. A first-seen timestamp alone is not
proof of publication time; unknown publication timing blocks an independent
newly-published-data claim. Revisions of inspected dates are sensitivity data.
Record exact acquisition UTC, publication evidence, source version/hash, schema,
first-seen date, revisions, and eligibility decisions in an append-only log.
Future acquisition/scoring infrastructure is specified, not implemented here.

Freeze both existing model families and the SHA-256 of `anomaly.py`. Calendar
median: prior 1,096 days, same month/day type, minimum eight. Seasonal trend:
prior 730 days, separate mode/day-type log regressions, annual harmonics 1/2,
weekly sine/cosine, linear trend, monthly refits, 180-day half-life, ridge 1 on
non-intercept coefficients, minimum 90 rows, output clipping unchanged.
Calibration: prior 365 calendar days, same model/mode/day type, minimum 30 errors,
median centering, MAD/0.67448975, scale floor 0.05. Candidate rule remains
|centered score| > 3.5 AND absolute deviation >= max(10,000, 20% expected).
Past-only online updates are allowed exactly as implemented; parameter tuning is
not. Only earlier available source vintages may enter a target's historical fit
or calibration. Batch arrival must not let later service dates affect earlier
ones. Record unavailable predictions; never impute a score or alter day types.

## Model-health criteria (separate from ridership alerts)

After each observed service date, use that date and the preceding 27 calendar
days. Minimum 21 scored dates; a full 28-calendar-day context is still required
for a healthy classification. Missing target dates and history gaps are explicit
coverage warnings. Never zero-fill missing counts. Before window maturity label
insufficient history, not healthy. Data availability, health, and anomaly status
are separate fields.

- WAPE > 20%: prediction-error warning; undefined denominators are unavailable.
- Absolute median daily relative residual > 20%: bias warning. Positive residual
  means underprediction; negative means overprediction.
- Bias warning AND >=80% of observed residuals have the same sign: sustained
  under/overprediction warning, not detected structural change.
- Raw candidate rate >20% of scored mode-days: alert-frequency warning.
- Drift: compare current 28-day and preceding disjoint 84-day calibration medians
  within each CTA day type; require >=3 current and >=9 reference observations.
  Absolute center shift >0.15 log units or scale ratio outside [0.5,2] warns.
  Require all three day types to be evaluable; otherwise drift is unknown.

These deliberately simple operational guards were frozen before the new health
analysis, not optimized for retrospective WAPE. Holiday composition and correlated
rolling windows limit interpretation. Flag model failure for human assessment;
do not suppress, relabel, or change ridership alerts. Inspect long warning runs
as diagnostic episodes, not change points or identified causes.

## Investigation rubric and budget

Keep every model/mode/date candidate with stable case ID and source hashes.
Record actual/expected counts, signed/absolute/percentage deviation, raw deviation
direction, centered score and its sign, prior same-type observations, same-date
cross-mode context, stable episode ID, elapsed episode days, coverage, model-health
warnings, evidence limitations, review state, uncertainty, and reviewer evidence.
No later comparable dates or final episode duration enter as-of priority.

Transparent priority components: absolute relative deviation (>=20%:1, >=50%:2),
absolute centered score (>=5:1, >=10:2), same-day other-mode alert (+1), and episode
age >=3 days (+1). Missing percentage deviation contributes no magnitude points
and is explicitly unavailable. Missing context is a data-review lane, never a
reason to delete a severe case. Sort by priority, then incomplete context first,
then stable ID within service date. This is an ordering heuristic, not a probability
of incident. Urgent if |score|>=10, |relative deviation|>=50%, or episode age>=7.
Evaluate ranking without claiming human usefulness from severity alone.

Proposed capacity: 10 new case reviews per calendar week across both models/modes,
plus two deterministic sampled non-alert audits for prospective human assessment.
This is a staffing hypothesis, not a top-N deletion rule. Preserve all overflow,
acknowledge every urgent case within two business days and others within five;
escalate capacity if urgent weekly arrivals exceed 10, pending cases exceed 20,
or any case passes its SLA. Repeated episode members can update one review with
all IDs retained; do not claim distinct models are independent corroboration.
No actual reviewer capacity or historical backlog is simulated as achieved here.

Initial status is unreviewed; uncertainty high; cause unknown. Proposed transitions:
unreviewed -> in_review -> needs_context / reviewed_investigation / model_health_followup /
data_quality_followup / not_actionable. Corrections append reviewer/time/evidence
and link superseded decisions; never overwrite generated evidence. A separate
append-only review ledger is required for operation, not implemented in this
research exporter. External incident confirmation requires independent cited
sources and human signoff; no score-based transition confirms an incident.

## Frozen metrics and go/no-go gates

Assess each model/mode independently on >=90 eligible consecutive service dates;
extend to at most 180 if fewer than 30 distinct cases have completed reviews.
Insufficient cases/context is inconclusive, never a pass. Log all gaps and the
same period's calendar baseline. Report WAPE/MAE, signed error, alert rates and
quantiles, overlap, episode burden, health warning frequency/runs, review age/SLA,
backlog, and human investigation usefulness. Do not select a model solely on WAPE.

Dashboard integration requires every gate below and a new explicit owner approval:

1. Zero chronology/hash/reconciliation breaches, 100% candidate preservation,
   and >=99% scored calendar coverage per mode. Missing outputs must be visible.
2. Health warnings on <=10% of mature evaluable dates; no unresolved warning run
   of seven calendar days; no unknown health classifications at signoff.
3. >=30 reviewed cases under a predeclared stratified random sampling plan across
   direction, mode, priority, and health state. Review all urgent cases additionally;
   report these separately from the sample. Fix seed 42 before sampling. If strata
   lack examples, record absence; do not fabricate balance. >=80% of sampled cases
   must have reviewer-justified investigation usefulness; this is not event precision.
4. >=20% of sampled cases independently double-reviewed; >=80% disposition
   agreement, all disagreements adjudicated and evidence-linked. Unavailable staff
   means pending, not assumed agreement. Non-alert audits cannot establish recall
   without independent incident labels.
5. >=95% overall acknowledgment within five business days and 100% urgent within
   two; all overflow retained and none overdue at signoff. Actual holidays and
   reviewer schedules must be defined before SLA measurement.
6. Zero unsupported causal/incident claims; every reviewed record has reviewer,
   UTC decision time, uncertainty and evidence. An owned escalation and revision
   policy plus independent reproducibility signoff must be documented.

Any breach means no-go or inconclusive pending resolution. A changed threshold,
health rule, sampling rubric, or model creates a new version and new prospective
assessment; do not retroactively apply it and claim an untouched pass. This phase
implements retrospective indicators and case export only. It does not execute
prospective sampling, reviewer workflow, automatic readiness certification, or
Dashboard integration. Current status: NO-GO / required prospective evidence absent.
