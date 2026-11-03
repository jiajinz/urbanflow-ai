# UrbanFlow AI — Milestone 4A Insight Report

This document covers Chicago Transit Authority (CTA) ridership data and analysis.

Historical CTA demand patterns and mode recovery. Prepared November 1, 2026.
This is exploratory observational research, not a forecast or causal evaluation.
No Streamlit interface or AI-generated analysis is part of this milestone.

## Executive findings

- Demand recovery differs materially by service day type. In 2025, the mean of
  twelve same-month total ridership indices was **70.90 for weekdays (W), 88.10 for Saturdays (A), and
  89.29 for Sundays/holidays (U)**, with each comparable 2019 month/day type set to 100.
- Bus and rail followed different recovery trajectories. In 2025, weekday bus
  recovery averaged **81.63**, versus **59.36** for rail. Bus exceeded rail in
  all **56** weekday monthly comparisons from January 2022 through August 2026.
- These directions survive a 2017–2019 baseline and fixed-calendar weighting.
  Claims that all service types or both modes have fully recovered are unsupported.
- January–August 2026 is the latest complete matched-month window, not a complete
  year. Its fixed-2019-calendar bus and rail recovery indices are **86.83** and
  **65.13**, respectively.

## Data provenance and completeness

Source: [Chicago CTA Daily Boarding Totals, resource 6iiy-9s97](https://data.cityofchicago.org/Transportation/CTA-Ridership-Daily-Boarding-Totals/6iiy-9s97).
See the archived [manifest](../data/history/cta-2026-11-01-v1/manifest.json),
[source calendar audit](../data/history/cta-2026-11-01-v1/source_calendar_coverage.json),
[validated coverage](../data/history/cta-2026-11-01-v1/coverage.json), and
[quarantine](../data/history/cta-2026-11-01-v1/quarantine.json).

The API was read in stable `service_date ASC, :id ASC` order with 1,000-row pages.
Bounds and count were queried before and after fetching. The source contained
**9,374 rows**, from **2001-01-01 through 2026-08-31**, one for every calendar date,
with **zero duplicate dates and zero missing source calendar dates**. This is the
latest observed service period at extraction; it is not a promise about future
source availability. September–December 2026 is not represented.

Existing validation rejected **31 rows**, all of July 2012, because their timestamp
is `07:00:00` rather than the accepted midnight representation. For example,
`2012-07-01T07:00:00.000` has bus 474,631, rail 350,123, and total 824,754; its
counts reconcile, but its timestamp violates the existing parser contract.
The original values are retained without silently changing this contract.

The validated PostgreSQL and Parquet data therefore contain **9,343 rows**, no
accepted duplicate dates, and **31 missing validated dates**. July 2012 is excluded
from complete-month comparisons. The 2012 annual total is partial and receives no
YoY percentage; neither does 2013 receive a YoY percentage against partial 2012.
All other years through 2025 are complete. The last year contains eight complete
months and 243 observed dates. The 2017–2019 baseline is complete.

The first upsert changed 8,825 rows and left 518 existing rows unchanged. An actual
repeat from the same archive changed **zero** rows and left all **9,343 unchanged**:
[idempotence evidence](../data/history/cta-2026-11-01-v1/idempotence_check.json).
All **921** month/day-type SQL cells were compared successfully between PostgreSQL
and DuckDB: [SQL verification](../data/research/cta-2026-11-01-v1/sql_verification.json).
These checks prove extraction consistency and pipeline behavior, not independent
accuracy of CTA's original counts. Count/bound checks cannot detect every in-place
source revision during pagination; raw archived bytes define the research version.

## Definitions and methods

- **Boardings** measure recorded rides, not unique people. No route, station,
  time-of-day, service-hours, weather, or rider-purpose data are available here.
- **W / A / U** mean weekday / Saturday / Sunday-or-holiday service classification.
  U is not synonymous with calendar Sunday, and W is not evidence of commuting.
  See the [official data catalog definition](https://catalog.data.gov/dataset/cta-ridership-daily-boarding-totals).
- **Complete month** requires one validated row for every calendar date. Missing
  dates are never zero-filled. Annual percentage changes require two adjacent,
  complete years. Same-type monthly MoM and YoY require both complete months;
  MoM remains seasonal and is not an estimate of underlying recovery.
- **Monthly daily mean** is the sum of a mode's boardings divided by observed
  dates in the same calendar month and CTA day type. Splitting by day type avoids
  attributing a larger number of Saturdays to higher typical Saturday demand.
- **Recovery index** is `100 × target monthly daily mean / baseline monthly daily
  mean`, matched on month number and day type. A zero or missing denominator
  produces an unavailable comparison.
- **2019 baseline** is the last full pre-pandemic calendar year. **2017–2019
  baseline** equally averages the three individual years' monthly daily means.
  It does not pool their day counts. Equal-month period summaries average monthly
  indices, so they are not ratios of annual totals or weighted daily means.
- **Calendar standardization** separately applies fixed 2019 day-type counts for
  January–August to each year's same-cell daily means, then sums the weighted
  values. This holds month/day-type composition fixed while retaining 2019's
  seasonal weights. These weighted boardings are counterfactual accounting
  quantities, not actual recorded annual rides or a causal counterfactual.
- **Persistence analysis** pairs monthly bus and rail indices within day type,
  or A/U and W total indices within month, for January 2022–August 2026. A circular
  moving-block bootstrap resamples contiguous blocks of three or six months,
  with 5,000 repetitions and seed 42. Percentile 2.5/97.5 intervals describe
  sensitivity of period means to resampled months, conditional on this record.
  The persistence window starts in 2022 to separate these multi-year contrasts
  from 2020–2021 transition/early-recovery observations; it is not a universal
  definition of pandemic timing.
  Counts are a census-like administrative series: these are not measurement-error
  confidence intervals, causal intervals, or independent-month significance tests.
  See the [time-series bootstrap reference](https://bashtage.github.io/arch/bootstrap/timeseries-bootstraps.html)
  for the distinction between circular and non-wrapping blocks. This implementation
  uses circular blocks, without requiring the arch package.
  Trend/nonstationarity, long-range dependence, the circular end-to-start join,
  and baseline uncertainty limit their inferential interpretation. Direction
  counts, annual summaries, and baseline sensitivity are the primary evidence.

## Finding 1 — Saturday and Sunday/holiday demand recovered further than weekday demand

**Research question.** How did W, A, and U demand change relative to pre-pandemic levels?

**Methodology.** Compare complete target months to the same month/day type in 2019,
then equally average the twelve monthly total indices for each complete year.
Repeat with the 2017–2019 baseline. Pair A-minus-W and U-minus-W monthly indices.

**Actual quantitative result.** With 2019 = 100:

- 2022: W **51.72**, A **59.98**, U **60.13**.
- 2023: W **59.22**, A **70.68**, U **71.03**.
- 2024: W **64.84**, A **79.76**, U **80.22**.
- 2025: W **70.90**, A **88.10**, U **89.29**.
- January–August 2026, eight matched months: W **72.55**, A **92.12**, U **95.55**.
  This last row must not be read as a full-year change from 2025.

Across all **56** paired months since January 2022, both A and U exceeded W in
**56/56** months. The mean gaps were **13.91 percentage points** for A-minus-W and
**14.86 points** for U-minus-W. Three-month block intervals were **12.02–15.88**
and **12.45–17.32** points; six-month versions were **11.56–16.19** and
**11.94–17.75**. Both contrasts retain a positive direction under both baselines.

**Supporting data or visualization.** [Day-type recovery Plotly exhibit](figures/02_day_type_recovery.html),
[period recovery cells](../data/research/cta-2026-11-01-v1/period_recovery.csv),
and [paired day-type contrasts](../data/research/cta-2026-11-01-v1/day_type_persistence.csv).

**Interpretation — observed.** The difference is persistent across periods and is
not explained simply by counting more weekend dates. All three total indices
remain below 100 in the latest matched-month period.

**Planning implication — recommendation.** Include Saturday and Sunday/holiday
service performance in recovery monitoring and service-allocation reviews.
Do not translate these indices directly into frequency changes without examining
loads, reliability, service supplied, and route-specific access needs.

**Limitations.** U mixes Sundays with holidays. Same-month matching does not align
specific holidays, weather, school calendars, special events, or individual routes.
Average demand cannot locate crowding. The data cannot identify trip purpose.

**Suggested follow-up analysis.** Join scheduled and delivered service hours,
route ridership, load factors, and holiday calendars. Test whether high-recovery
routes face unmet demand before proposing operational changes.

## Finding 2 — Bus recovered further than rail, especially on weekdays

**Research question.** Have bus and rail followed different recovery trajectories?

**Methodology.** Compute separate mode indices using each mode's own pre-pandemic
monthly mean; compare bus-minus-rail percentage-point gaps within W/A/U.
The hypothesis that modes recovered equally is evaluated descriptively, not with
a causal treatment model.

**Actual quantitative result.** In 2025, equal-month 2019-based indices were:

- W: bus **81.63**, rail **59.36**, gap **22.28 points**.
- A: bus **94.08**, rail **81.13**, gap **12.95 points**.
- U: bus **96.70**, rail **80.76**, gap **15.94 points**.

For weekdays, the mean gap increased from **13.80** points in 2022 to **15.47**
in 2023, **19.23** in 2024, and **22.28** in 2025. Bus exceeded rail in **56/56**
weekday, **54/56** Saturday, and **53/56** Sunday/holiday months during 2022–August
2026. The mean weekday gap over those months was **18.41 points**, with a
three-month block interval **16.78–20.07** and a six-month interval **16.26–20.54**.

As an absolute-scale check, annual weighted weekday daily means were **621,159 bus
and 421,346 rail boardings in 2025**, versus **760,577 and 708,154** in 2019.
These weighted means and the equal-month indices are different summaries.

**Supporting data or visualization.** [Mode recovery Plotly exhibit](figures/03_mode_recovery.html),
[mode persistence](../data/research/cta-2026-11-01-v1/mode_persistence.csv), and
[monthly SQL aggregates](../data/research/cta-2026-11-01-v1/monthly.csv).

**Interpretation — observed.** Equal recovery is not supported. A persistent mode
gap survives within-day-type comparisons, so a shift in day-type counts alone
cannot account for it. A growing recovery gap is operationally substantial but
is not evidence that people switched from rail to bus.

**Planning implication — recommendation.** Use separate bus and rail planning
assumptions. Investigate weekday rail service availability, reliability, geographic
coverage, and demand conditions rather than relying on one systemwide recovery KPI.

**Limitations.** Different starting demand, supply changes, changing destinations,
and reporting definitions may contribute. The data cannot isolate remote work,
perceived safety, fares, modal substitution, or service cuts as causes.

**Suggested follow-up analysis.** Join rail station entries, route-level bus
ridership, delivered service, reliability, and employment geography. Compare
corridors while accounting for service supplied and network changes.

## Finding 3 — Demand composition changed beyond the calendar mix

**Research question.** Are the apparent mode and service-type shifts just calendar effects?

**Methodology.** Restrict every year to January–August, the latest eight complete
months. Apply identical 2019 month/day-type day-count weights to each year's means.
Compare standardized shares and mode recovery with actual observed shares.

**Actual quantitative result.** For January–August:

- Bus share was **51.88%** in 2019 and **58.98%** in 2026 after standardization,
  a **7.09-point** increase. The actual 2026 share was also **58.98%**.
- W's standardized share of total demand fell from **82.42%** to **78.35%**.
- A's standardized share increased from **9.87%** to **11.98%**; U increased
  from **7.72%** to **9.66%**.
- Standardized 2026 recovery was **86.83 bus / 65.13 rail / 76.39 total**.
- Relative to the same January–August 2025 window and fixed weights, 2026 bus
  increased **1.96%**, rail **3.84%**, and total **2.72%**. Rail's more recent
  growth was faster even though its recovery level remained much lower.

The complete 2025 recorded annual total was **338,041,690 boardings**, **9.33%**
above complete 2024. The latest monthly comparison is more muted: August 2026
same-type daily totals changed **+0.37% W / +0.78% A / −1.34% U** versus August
2025. This monthly result does not establish a sustained reversal.

**Supporting data or visualization.** [Monthly MoM/YoY calculations](../data/research/cta-2026-11-01-v1/monthly_changes.csv),
[annual totals](../data/research/cta-2026-11-01-v1/annual.csv), and
[Matched-calendar composition and recovery](../data/research/cta-2026-11-01-v1/matched_composition.csv).

**Interpretation — observed.** The composition shift persists with a common
calendar. The hypothesis that day counts entirely explain the shift is unsupported.
The stronger rail growth in this recent window also rejects an overly broad claim
that bus always grows faster in every period.

**Planning implication — recommendation.** Monitor recovery levels and recent
growth separately. A low recovery level can coexist with faster current growth;
resource discussions should show both measures and absolute volumes.

**Limitations.** Fixed weights remove only the selected calendar composition, not
holiday mix within U, weather, events, population change, or changes in service.
This eight-month result cannot represent September–December 2026.

**Suggested follow-up analysis.** Repeat when all twelve 2026 months are published;
add holiday-specific categories and compare alternate reference calendars.

## Finding 4 — Baseline choices affect levels, not the core ordering

**Research question.** Are the findings sensitive to the pre-pandemic reference?

**Methodology.** Repeat all monthly indices using equally weighted 2017–2019
same-month/day-type means. Inspect pre-pandemic totals for preexisting trends.

**Actual quantitative result.** Under the 2017–2019 baseline, 2025 total indices
are **69.18 W / 84.95 A / 85.93 U**, versus **70.90 / 88.10 / 89.29** using 2019.
The 2025 weekday bus/rail gap remains **21.67 points**, compared with **22.28**
using 2019. The direction is unchanged.

Pre-pandemic annual bus totals declined from **249,231,176 in 2017** to
**237,276,399 in 2019**; rail declined from **230,204,047** to **218,467,141**.
Thus 2019 is a lower comparison level than the preceding multiyear period.

For January–August 2026, U bus's equal-month index is **105.08** versus 2019
and **100.85** versus 2017–2019, whereas U total is **95.55 / 90.61**. A narrow
claim about U bus exceeding its baseline does not establish systemwide recovery.

**Supporting data or visualization.** [Baseline sensitivity Plotly exhibit](figures/04_baseline_sensitivity.html),
[full annual series](../data/research/cta-2026-11-01-v1/annual.csv), and
[all monthly recovery indices](../data/research/cta-2026-11-01-v1/recovery_indices.csv).

**Interpretation — observed.** The central day-type and mode ordering is robust to
these two practical baselines. Exact recovery percentages and how close a series
is to 100 depend on the reference.

**Planning implication — recommendation.** Publish both baselines for executive
review rather than selecting the reference that makes recovery look strongest.

**Limitations.** Neither baseline estimates the no-pandemic trend. Three years
reduce single-year noise but incorporate an earlier, higher demand regime. Both
include historical service conditions and calendar anomalies. No extrapolated
counterfactual is justified without further modeling and external covariates.

**Suggested follow-up analysis.** Examine a pre-pandemic trend-adjusted reference
as an explicitly modeled scenario, with out-of-sample validation and uncertainty;
retain these transparent empirical baselines alongside it.

## Finding 5 — Seasonality and isolated days can distort unadjusted comparisons

**Research question.** Could seasonal or unusual days invalidate the main findings?

**Methodology.** Inspect complete monthly weekday means in 2019 and 2025. Screen
daily totals against the median and median absolute deviation (MAD) of the same
year/month/day-type cell, requiring at least four observations. Flag absolute
modified z scores above 3.5; retain all validated observations in the core results.

**Actual quantitative result.** In 2019, weekday bus daily means ranged from
**661,185 in January** to **837,924 in September**; rail ranged from **616,929**
to **774,270** in the same months. In 2025, weekday bus ranged from **548,003 in
January** to **679,519 in September**; rail from **345,354** to **482,445**.
Same-month matching is therefore materially preferable to comparing arbitrary
adjacent months as recovery evidence.

The screen flagged **510** of 9,343 validated days. On **2025-03-15**, Saturday
boardings were **1,038,464**, versus its five-day March Saturday cell median
**701,778**, or **47.98% higher**. This is an observed spike, not proof of an event's
causal effect. Very small MADs in four/five-day Saturday cells can produce extreme
scores, so these are review candidates, not established errors.

**Supporting data or visualization.** [Seasonal comparison Plotly exhibit](figures/05_seasonal_comparison.html),
[unusual-day candidates](../data/research/cta-2026-11-01-v1/unusual_days.csv), and
[long historical boardings Plotly exhibit](figures/01_historical_boardings.html).

**Interpretation — observed and untested hypothesis.** Month-of-year patterns are
visible, but weather, holidays, events, service, and other factors are not separated.
Special events may explain some spikes; this is an untested hypothesis. The core
recovery differences recur across many matched months, so a single isolated day
is not an adequate explanation. A formal outlier-exclusion sensitivity analysis
has not been performed, and robustness to removing all flagged days is unproven.

**Planning implication — recommendation.** Preserve unusual days for operations
review, and use matched-month monitoring before treating a MoM change as a trend.
Do not suppress valid special-event demand automatically.

**Limitations.** Screening is exploratory, with no multiple-testing correction,
small weekend cells, possible structural changes, and no external event matching.
No flagged record is declared incorrect from this screen alone.

**Suggested follow-up analysis.** Join weather and event calendars; evaluate robust
monthly medians and event-day exclusions as explicit sensitivity analyses. Inspect
source records before any correction.

## Reproduction and analytical audit

From an installed checkout, with a local PostgreSQL database configured:

```sh
# Full source discovery, bounded retries, validation, quarantine, and upserts.
# The output directory must be new; do not overwrite the archived research version.
python -m urbanflow_ai.history --output data/history/cta-new-version --quarantine-rejections

# Offline reproduction from the checked-in validated archive.
python -m urbanflow_ai.research \
  --snapshot data/history/cta-2026-11-01-v1 \
  --output /tmp/urbanflow-research-reproduction

# Add --verify-postgres only when the database matches the archived input.
python -m urbanflow_ai.research_plots \
  --results /tmp/urbanflow-research-reproduction \
  --output /tmp/urbanflow-research-figures
```

`history.py` is the extraction/orchestration boundary. `processing.py` retains the
original validation contract. `database.py` owns transactional persistence.
[research_monthly.sql](../src/urbanflow_ai/sql/research_monthly.sql) performs bounded
SQL aggregation; [research.py](../src/urbanflow_ai/research.py) calculates matched
comparisons and sensitivity measures; [research_plots.py](../src/urbanflow_ai/research_plots.py)
only renders those analytical tables.

The research manifest records source retrieval time, input Parquet checksum, SQL
checksum, baseline definitions, and bootstrap seed. CSVs retain numerical precision
beyond rounded report values. Plotly HTML files share the adjacent `plotly.min.js`
and work without a network connection when that file is retained. GitHub does not
execute these HTML files inline; download the directory or serve it locally.

## Verification record

On November 1, 2026, the full regression suite with the separate PostgreSQL test
database configured completed with **147 passed**. Without database configuration,
the deterministic run completed with **137 passed and 10 integration tests
skipped**. Tests do not call the live CTA API. The real source audit and real
idempotent backfill are separate evidence described above.

All nine analytical CSV tables were independently regenerated from the archived
Parquet and matched byte-for-byte. PostgreSQL/DuckDB monthly SQL verification
matched all 921 cells. Plotly exhibits were generated from those tables; the
mode-recovery, day-type-recovery, and baseline-sensitivity HTML pages were inspected
in a browser. This is not a comprehensive browser or accessibility test.
