# Milestone 4B.2A — Executive Overview Review

This document covers Chicago Transit Authority (CTA) ridership data and analysis.

## Scope and status

Executive Overview implementation is complete for owner review. Only this page,
its presentation model, its new trajectory renderer, and targeted tests changed.
Ridership Explorer, Methodology, routing, shared data loading, SQL, approved
snapshot files, and analytical definitions remain unchanged. No new dependency,
responsive polishing, deployment, AI reporting, commit, or push was introduced.

## Review findings and changes

The previous draft already had a valid data boundary, four recovery metrics,
baseline selection, a day-type trend, and a complete-year mode comparison. Those
components were retained. Gaps were an absent bus/rail trajectory, no historical
chart-window control, unstructured findings, insufficient quarantine context, and
clipped desktop KPI titles.

`overview.overview_model()` now wraps the existing `executive_model()` without
recalculating any research metric. It returns a computed executive summary, three
structured evidence records, and monthly chart tables. Each evidence record names
an observation, interpretation, planning implication, limitation, and 4A calculation
source. The original all-day-type mode bar chart remains in an expander.

The new chart-year control affects only the two monthly trajectories. The four
cards always refer to the latest complete supported year, currently 2025. A
2026-only chart window ends in August and is never presented as a full year.
Missing chart months are reindexed to explicit nulls; the mode renderer does not
connect gaps. Selecting a baseline updates recovery evidence and both figures;
fixed-2019-calendar composition remains a separate, explicitly labeled measure.

## Verified evidence

Values are retrieved from the approved analytical bundle, not hardcoded in UI:

- 2025 mean monthly total indices, 2019 = 100: W 70.90, A 88.10, U 89.29.
- 2025 weekday bus/rail indices: 81.63 / 59.36; gap 22.28 percentage points.
- 2017–2019 baseline: W 69.18, A 84.95, U 85.93; weekday mode gap 21.67 points.
- Matched January–August fixed-calendar bus share: 51.88% in 2019, 58.98% in 2026.

The bundle has 9,343 validated dates from 2001-01-01 through 2026-08-31. The 4A
source audit quarantines July 2012's 31 07:00 timestamps under the original
midnight-only rule. This affects historical July/annual 2012 comparisons, not the
2017–2019 denominators or post-2019 recovery trajectories. The page distinguishes
this archived source audit from metadata actually known in PostgreSQL mode.

These observations do not establish causal effects, trip purpose, or rail-to-bus
substitution. Service changes require further route loads, delivered-service, and
reliability analysis. Equal-month indices are not annual-total ratios or formal
seasonal adjustment.

## Actual verification

Commands executed:

```sh
.venv/bin/python -m pytest tests/test_overview.py tests/test_dashboard.py -q
.venv/bin/python -m pytest -q
TEST_DATABASE_URL=postgresql:///urbanflow_ai_test .venv/bin/python -m pytest -q
```

Results: 16 targeted tests passed; the ordinary full suite had 175 passed and 11
PostgreSQL integration skips; the database-configured full suite had 186 passed.
No ordinary test calls the CTA API.

Tests verify both baseline outputs, matched-calendar evidence, chart-window/KPI
independence, exact mode trace values, null chart gaps, invalid windows, insufficient
annual evidence, approved-bundle loading, missing/corrupt bundle errors, and existing
page regressions. An AST source comparison against the start-of-phase copy confirmed
all non-Overview UI functions unchanged. Existing metric definitions and routing
were also compared byte-for-byte and remained unchanged.

A local browser was opened on the default approved bundle. The default KPI values,
shortened desktop card labels, day-type chart, and baseline switching were observed.
Switching to 2017–2019 showed 69.18 / 84.95 / 85.93 / 21.67 pp and updated the summary.
The initial preview retained an older imported module; a fresh server process
showed the final code. Restart the process if a source edit does not appear.

A later supplementary browser check timed out in automatic authorization review.
This was not a safety rejection. Full visual inspection of the bus/rail chart is
therefore left for the owner. Passing tests is not complete visual QA. Mobile,
accessibility, and comprehensive cross-browser review were not performed.

## Files changed in this phase

- `src/urbanflow_ai/overview.py`: new presentation model over approved analytics.
- `src/urbanflow_ai/dashboard_ui.py`: Executive Overview function only.
- `src/urbanflow_ai/dashboard_charts.py`: added weekday mode trajectory renderer.
- `tests/test_overview.py`: new evidence/window/chart contracts.
- `tests/test_dashboard.py`: added two Overview interaction/error cases; prior
  other-page regression cases retained unchanged.
- `docs/dashboard_spec.md`, `README.md`: current phase status only.
- This review record.

The repository already contained extensive uncommitted ingestion, database,
research, and other dashboard drafts. Aggregate `git diff --stat` does not isolate
this phase, and it omits new untracked files. Do not treat the aggregate count as
an Executive Overview-only diff.

## Launch and owner review

From the repository root, stop any existing server on the chosen port, then run:

```sh
.venv/bin/python -m streamlit run streamlit_app.py --server.port 8505
```

Open http://localhost:8505. In PyCharm, use the project interpreter, module
`streamlit`, parameters `run streamlit_app.py --server.port 8505`, and project root
as working directory. Debug breakpoints in `executive_overview()` and
`overview_model()` show widget values and the returned analytical tables.

Inspect the four card titles, units, help text, period, and baseline. Switch both
baselines. Select 2026–2026 for chart years: charts must show January–August 2026,
while cards remain complete 2025. Check the bus/rail chart axes, hover details,
legend, 100 reference line, and missing-data behavior. Confirm that composition
remains labeled as the fixed-2019-calendar matched-month comparison. Review the
planning limitations and July 2012 explanation.

## Execution flow and interview concepts

`streamlit_app.main()` routes to `app_pages/overview.py`, which invokes
`dashboard_ui.executive_overview()`. Its existing `dataset()` function uses cached
`load_data()` access. Missing/invalid data shows a safe error and stops metrics;
there is no backend fallback. `overview_model()` receives the validated object and
selected baseline, and delegates research calculations:

```python
model = executive_model(data, baseline)
```

Streamlit reruns the page after baseline/window changes, preserving widget state.
Data caching avoids repeated disk/database reads. The baseline selects already
validated research results; the chart window selects observations without changing
the complete-year KPI definition. Plotly receives the supplied table directly:

```python
x=table.month, y=table[column], name=mode,
```

That real line in `weekday_mode_trend()` maps dates and mode indices to trace
coordinates; it does not calculate recovery. This is the distinction between a
visualization library and an application runtime, and between presentation models
and metric definitions.

Hands-on exercise: stop at a breakpoint after `overview_model()` returns, select
2026–2026, and inspect `model['year']`, `model['chart_period']`, and
`model['mode_trend']`. Expect 2025, Jan 2026–Aug 2026, and eight monthly weekday
rows. Explain why the period difference is intentional rather than a bug.

## Stop condition

Stop at 4B.2A and wait for explicit owner approval. Do not begin Explorer,
Methodology, responsive polishing, deployment, AI reporting, or another milestone.
