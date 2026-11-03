# Milestone 4C.1B — Frozen Retrospective Evaluation Protocol

Chicago Transit Authority (CTA) daily bus and rail anomaly investigation.

This protocol was written before implementing the 4C.1B burden analysis. All
2019-01-01–2026-08-31 observations were already evaluated and inspected in 4C.1A.
There is no untouched final historical holdout in that window. Earlier archive
rows served as historical training context, not a replacement independent test.

## Fixed windows (inclusive start, exclusive end)

- Development diagnostics: 2019-01-01 to 2022-01-01.
- Retrospective temporal validation: 2022-01-01 to 2025-01-01.
- Retrospective last-period assessment: 2025-01-01 to 2026-09-01.

The last period is not independent or a full 2026 year. Do not optimize thresholds
on it and subsequently present its results as an independent final test. Future
prospective validation requires a frozen protocol before newly available dates
are inspected, source publication/revision tracking, and human review criteria.

## Fixed comparisons

Keep both existing models and their past-only fitting/calibration unchanged.
Retain |score| > 3.5 plus absolute deviation >= max(10,000, 20% expected) as the
primary raw-alert rule. Compare 3 and 4.5 with the same magnitude gate without
selecting a winner from last-period outcomes. Exact threshold equality does not
alert; magnitude-gate equality qualifies. Direction is raw observed minus expected,
not the sign of a median-centered score.

Report scored mode-days as denominators; distinct dates as date-level burden.
Include zero-alert periods. Distinguish valid observed-date coverage from full
calendar completeness and preserve missing observations as missing.

Group raw alerts by model, mode, and raw residual direction. Only consecutive
calendar dates join; non-alert dates and missing-date gaps break a run. Day types
may change within a run. Also report cross-mode same-direction calendar runs as
an alternative queue; these do not establish shared causes. Group globally before
assigning fixed windows; window counts include episodes intersecting that window
and explicitly identify boundary-crossing episodes.

Monthly top-three raw-alert observations per model are a retrospective ranking
illustration, not a validated staffing budget or online daily policy. Preserve
unranked alerts and report their count and maximum severity. Month-complete
ranking uses later observations in the month; it must not be advertised as a
past-only online selection policy. Episodes and candidate examples are selected
for investigation, not to estimate event precision or recall.

Bias diagnostics include raw log residual, calibration center/scale, centered
score, and a zero-center score using the same observed past-only scale. This is
an explanatory counterfactual scoring diagnostic, not a third fitted model or a
proposed production threshold. Cases with high error and few alerts demonstrate
possible calibration masking, not confirmed missed incidents.

No external event research, causal attribution, new model family, change-point
algorithm, forecast, dashboard change, or threshold promotion is authorized here.
