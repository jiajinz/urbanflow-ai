# Milestone 4B Dashboard Specification

This document covers Chicago Transit Authority (CTA) ridership data and analysis.

## Scope and approval status

This specification is the 4B.1 design deliverable. Existing full page/chart drafts
were written before the scope revision and are preserved without further UI work.
4B.2 implementation acceptance and 4B.3 visual/portfolio review are deferred until
explicit approval. The contracts below describe the intended application, not
completed UI acceptance. No deployment or AI reporting is authorized here.

## Executive Overview phase update

4B.2A authorizes Executive Overview only. Its implementation and local verification
are recorded in [milestone_4b2a_review.md](milestone_4b2a_review.md). Owner acceptance
is pending. The other pages remain preserved, unapproved drafts. Overview chart-year
selection controls monthly trajectories only; four KPIs retain the latest complete
year. Fixed-calendar composition keeps its separately labeled matched-month window.
No other 4B.2 work or responsive/deployment preparation is authorized by this phase.

## Explorer phase update

4B.2B refines only Ridership Explorer; Overview is approved for progression and
unchanged. The workbench offers Trend (Daily/Monthly/Annual), Recovery, same-month
YoY, and Seasonal questions, with conditional controls and explicit period coverage.
Its implementation, actual tests, and review limits are recorded in
[milestone_4b2b_review.md](milestone_4b2b_review.md). Owner review is pending;
Methodology and subsequent phases remain deferred.

## Audience and decision

Urban planners, transit analysts, and portfolio reviewers need to distinguish
recovery levels, recent growth, and calendar composition before recommending
service investigations. The app is observational decision support, not a causal
model, forecast, or automated service-allocation system.

## Supported evidence mapped to views

### Day-type recovery (4A finding 1)

- Question: Did W, A, and U recover differently?
- Business relevance: Track weekday and weekend/holiday service needs separately.
- Metric: Same-month/day-type daily boarding recovery; equal-month period means.
- Visualization: Monthly index lines and grouped day-type/mode bars.
- Interaction: Baseline selector in Overview; date, mode, year, and day-type filters
  in Explorer. Baseline always uses full archived history, not the target window.
- Interpretation: In complete 2025, 2019-based total indices average 70.90 W,
  88.10 A, and 89.29 U. These are not annual-total ratios.
- Limitation: U includes weekday holidays; day type is not trip purpose.

### Mode recovery (4A finding 2)

- Question: Did bus and rail follow different recovery paths?
- Business relevance: Avoid applying one recovery assumption to both networks.
- Metric: Mode-specific indices and bus-minus-rail percentage-point gaps.
- Visualization: Weekday bus/rail recovery lines and mode/day-type period bars.
- Interaction: Two supported baseline definitions and exploratory target periods.
- Interpretation: Complete 2025 weekday indices are 81.63 bus and 59.36 rail;
  the 22.28-point gap is not evidence of riders switching modes.
- Limitation: No delivered-service, route, or reliability covariates.

### Composition and recent growth (4A finding 3)

- Question: Does composition change remain under fixed calendar weights?
- Business relevance: Separate the recovery level from recent matched-period growth.
- Metric: Existing 4A fixed-2019-calendar matched-month composition and indices.
- Visualization: Explicit findings and a downloadable matched-period evidence table.
- Interaction: Overview period is dataset-derived and fixed, preventing incompatible
  filter changes. Explorer findings are not copied from Overview into other windows.
- Interpretation: January–August 2026 standardized bus share is 58.98%, versus
  51.88% in 2019. Rail grows faster in this recent matched window despite lower recovery.
- Limitation: Fixed calendar weighting is not formal seasonal adjustment.

### Baseline sensitivity (4A finding 4)

- Question: Does the conclusion depend on a single baseline?
- Business relevance: Make reference choices visible in executive interpretation.
- Metric: 2019 or equal-year 2017–2019 same-month/day-type denominators.
- Visualization: Recovery figures and a baseline comparison evidence table.
- Interaction: Supported baseline selector only; no arbitrary denominator years.
- Limitation: Neither baseline estimates a no-pandemic counterfactual.

### Seasonality and unusual days (4A finding 5)

- Question: Do recurring seasonal patterns affect raw comparisons?
- Business relevance: Avoid interpreting arbitrary MoM changes as recovery.
- Metric: Same-type monthly daily means by month of year; optional daily 7-day mean.
- Visualization: Seasonal year comparison and daily/complete-month/complete-year trends.
- Interaction: Select years and day types; display gaps rather than interpolate.
- Limitation: Outlier exclusion sensitivity and event attribution remain unfinished.

## Page contract

- Executive Overview: Problem, reporting coverage, latest complete year, four
  recovery metrics (W/A/U total and W mode gap), long historical recovery,
  mode/day-type comparison, three computed findings, planning implications.
- Ridership Explorer: Inclusive UI dates become exclusive upper bounds. Default
  target is January 1 two years before the last reporting year through the last reporting date. Users select modes, W/A/U,
  years, baseline, and daily/monthly/yearly/seasonal/recovery views. Raw partial
  daily periods are allowed. Monthly/yearly comparisons require fully selected,
  fully observed calendar periods. No rolling average across missing or excluded days.
- Research & Methodology: Dataset provenance, definitions, raw/validated coverage,
  baseline formulas, normalization, bootstrap interpretation, unfinished analyses,
  local-versus-snapshot behavior, and links/downloads for traceable evidence.

## Architecture and publication

Streamlit entrypoint routes page files with st.navigation/st.Page. Presentation
lives in dashboard_ui.py and dashboard_charts.py; no SQL or statistical formulas
appear in page functions. dashboard_data.py owns explicit environment selection,
read-only PostgreSQL access, and versioned Parquet export/loading. dashboard_metrics.py
reuses research.py and existing daily analytics for deterministic view models.

Public mode defaults to a checked-in historical bundle. All table hashes, source
provenance, analytical definition hashes, coverage, and generation time are verified.
A new output directory is required for export. There is no API request or silent
backend fallback in the app. PostgreSQL mode is explicit and local-only by default.
No credentials, .env, .idea, or AGENTS.md are added to version control.

## Verification boundaries and future acceptance checks

Deterministic tests cover date/type/year filtering, complete periods, both baselines,
empty selections/data, zero denominators, seven consecutive days, bundle integrity,
backend errors, research parity, and Streamlit navigation/output consistency.
The complete suite includes opt-in PostgreSQL tests. Browser review of all three
pages and desktop/mobile layouts is a future 4B.3 acceptance requirement, not a
completed 4B.1 check. Deployment remains a documented future action;
no cloud publication, LLM integration, agent, or forecast is included.


## 4B.1 data access acceptance

The bundle contains daily, monthly, recovery, annual, periods, and composition
Parquet tables. Export recomputes the 4A definitions from validated daily rows and
compares every analytical table before publishing a new directory. Loading verifies
file checksums, analytical definition hashes, provenance fields, and daily coverage.
Checksums detect accidental changes; they are not source authentication and do not
independently establish CTA measurement accuracy. Empty data and inconsistent
analytical tables cannot be exported. PostgreSQL errors do not trigger fallback.

Raw source coverage is 9,374 dates from 2001-01-01 through 2026-08-31. Validated data
has 9,343 rows; July 2012's 31 non-midnight source timestamps remain quarantined.
Outlier-exclusion sensitivity, causal attribution, and delivered-service analyses
remain unfinished research, not dashboard findings.
