# Milestone 4B.2B — Interactive Ridership Explorer

This document covers Chicago Transit Authority (CTA) ridership data and analysis.

## Scope and status

The Explorer is implemented for owner review. Executive Overview calculations,
visuals, presentation components, navigation, and approved snapshot are unchanged.
Research & Methodology remains a preserved draft. No AI reporting, forecast,
deployment, dependency addition, commit, or push is included. Stop here until
explicit approval for 4B.2C.

## Review decisions

The existing draft already provided validated date/day-type filters, full-month
selection, recovery indices, complete-year daily means, and seven-calendar-day SQL
windows. Those analytical functions were retained. Problems were an always-visible
baseline unrelated to some views, overlapping date/year filters, no YoY view,
unclear period exclusions, and no explicit export of comparison denominators.

The workbench now presents one question and one chart at a time:

- **Trend:** monthly or complete-year average daily boardings, or observed daily
  boardings. Only this question displays the aggregation control.
- **Recovery:** same-month/day-type recovery against 2019 or 2017–2019. Only this
  question displays baseline selection. References remain in full history.
- **Year-over-year:** 4A same-month/day-type daily-average percentage change. Both
  target/reference months must be complete. The reference can be outside the
  selected target window and is exported explicitly. There is no undefined zero
  denominator percentage or partial-year total comparison.
- **Seasonal:** monthly daily means by selected comparison years. Only this question
  exposes a year selector. Mode color remains consistent; line style identifies year.

Date bounds, mode, and W/A/U affect every question. Default recovery shows weekday
bus and rail over the last three reporting years, avoiding multiple initial charts.
Other day types and total can be added deliberately. Empty categories mean empty
results. No cause or service recommendation is inferred automatically.

## Period and export semantics

The UI end date is inclusive; ExplorerFilter uses the following date as an exclusive
upper bound. Daily views permit partial periods and preserve unselected/missing
calendar dates as nulls. Seven-day means require seven consecutive selected,
observed calendar dates; unavailable rolling controls are hidden with an explanation.

Monthly metrics require a fully selected complete calendar month. Annual values
are sum of observed boardings divided by observed days within each CTA day type,
not an equal-weight average of monthly means and not annual totals. Twelve complete,
fully selected months are required; 2026's published January–August window is not
an eligible annual comparison. Seasonal curves retain gaps for unpublished months.

Coverage is audited before day-type filtering because a missing date has no known
CTA classification. July 2012's quarantined dates remain absent. The coverage table
separates partial selections from missing validated dates. The annual eligibility
table explains which years cannot contribute.

Exports include the exact plotted series (with null gaps and availability flags),
calendar coverage, and JSON selection/metric definitions. YoY rows additionally
contain current/reference daily means, both service-day counts, reference month,
and comparability status. A valid target with an unavailable or zero reference
remains undefined rather than becoming zero percent. A valid target with no prior-year
reference receives a specific empty-state explanation; for example, July 2013
cannot use quarantined July 2012 as a YoY denominator.

## Actual execution flow

1. `streamlit_app.main()` routes to existing `app_pages/explorer.py`, which calls
   `dashboard_ui.ridership_explorer()`. Existing cached `dataset()` access explicitly
   chooses PostgreSQL or the approved Parquet bundle; failures do not switch backend.
2. Native segmented controls select question, aggregation, or recovery baseline;
   pills select modes/day types; date_input selects target dates. Only Seasonal
   needs a comparison-year multiselect. The page constructs an immutable ExplorerFilter.
3. `explorer.explorer_model()` passes ordinary views to existing
   `dashboard_metrics.explorer_series()`, retaining 4A recovery definitions and
   complete-period behavior. Most interactive filters operate on validated SQL
   aggregate DataFrames; they do not run new PostgreSQL queries on every click.
4. Daily series reuse `snapshot_analytics()` and the existing parameterized SQL
   calendar/window queries on the loaded data. The seven-day window is calendar
   based, not the last seven selected weekday rows.
5. `yoy_series()` calls `research.monthly_changes(data.monthly)` before target
   filtering. This preserves the previous-year reference outside the target window,
   then matches the complete selected month/day-type cells. It reindexes absent
   target months to nulls so a line cannot bridge missing observations.
6. `period_coverage()` counts calendar observations independently of service type.
   The model returns chart data, definition, units, limitations, and diagnostic
   coverage together, making the page's interpretation and exports consistent.
7. `explorer_components.explorer_plot()` renders the same model DataFrame using
   Plotly. Existing explorer_chart renders ordinary views; YoY has a zero reference
   line and denominator details in hover. The table and CSV use that same DataFrame.

Example from the approved archive: for August 2026 weekday bus, target daily mean
is 632,429.714286 and August 2025 reference mean is 635,369.666667; the 4A YoY result
is −0.462715%. Weekday rail means are 470,991.714286 and 463,930.857143, producing
+1.521963%. These are observed daily-average changes, not evidence of a cause.

## Reproduce independently

```python
from datetime import date
from urbanflow_ai.dashboard_data import load_bundle
from urbanflow_ai.dashboard_metrics import ExplorerFilter
from urbanflow_ai.explorer import explorer_model

data = load_bundle()
filters = ExplorerFilter(
    date(2026, 8, 1), date(2026, 9, 1),
    day_types=("W",), modes=("bus", "rail"), years=(2026,),
)
model = explorer_model(data, filters, "Year-over-year")
print(model["series"][["mode", "current_daily", "previous_daily", "value"]])
```

This needs no live API or local PostgreSQL. In PyCharm, break after model creation
and inspect filters, series, and coverage. Try January 2–31, 2025: monthly metrics
are unavailable, but Daily can show actual observations. Then test July 2013 YoY:
its July 2012 reference is absent, so no percentage should be invented.

## Visual reuse and limitations

Explorer scopes the approved Overview CSS tokens to a separate root/container
namespace. It imports the existing style constant without editing Overview. Navy
structures the page, teal identifies active primary selections, blue describes
metric evidence, and amber distinguishes methodological limits. Original bus/rail
chart colors are retained; year comparison uses line styles instead of extra mode
colors. Native widget labels and an explicit chart alternative description remain.

Desktop browser review covered default Recovery controls and the switch to YoY,
including removal of irrelevant baseline controls, percentage axis, zero line,
and limitations. Tests are not proof of accessibility. Mobile, screen-reader,
comprehensive keyboard, and cross-browser verification remain incomplete. Large
ranges or many year/day-type selections can make charts dense; no automatic
statistical explanation or outlier correction is added.

## Actual verification

```sh
.venv/bin/python -m pytest tests/test_explorer.py tests/test_dashboard.py -q
.venv/bin/python -m pytest -q
TEST_DATABASE_URL=postgresql:///urbanflow_ai_test .venv/bin/python -m pytest -q
```

Results: **22 passed** for targeted tests; **190 passed, 11 integration tests
skipped** without a test database; **201 passed** with the isolated PostgreSQL
test database configured. Ordinary tests require no CTA access.

Coverage includes filter/date boundaries, both baselines, full-history references,
day-weighted annual means, incomplete/missing periods, zero/missing denominators,
empty selections, seasonal years, rolling eligibility, archived 4A YoY parity,
page interactions, and chart/export table equality with analytical outputs.

Source comparisons confirmed all non-Explorer UI functions, all non-Explorer chart
functions, Overview components, 4A definitions, data access, global theme, and
routing are unchanged. `git diff --check` passed. The workspace already contains
uncommitted earlier milestones; aggregate Git statistics do not isolate this phase.

## Files changed

- `src/urbanflow_ai/explorer.py`: new pure view models and period diagnostics.
- `src/urbanflow_ai/explorer_components.py`: scoped presentation and YoY renderer.
- `src/urbanflow_ai/dashboard_ui.py`: Ridership Explorer function only.
- `src/urbanflow_ai/dashboard_charts.py`: seasonal Explorer uses mode color/year dash.
- `tests/test_explorer.py`: new analytical contracts.
- `tests/test_dashboard.py`: Explorer interactions and chart/export consistency;
  existing Overview/Methodology behavior remains tested.
- This review and phase-status notes in the specification/README.

## Local launch and owner review

From the repository root, stop an existing process on the chosen port before starting:

```sh
.venv/bin/python -m streamlit run streamlit_app.py --server.port 8511
```

Open http://localhost:8511/explorer. Review these scenarios:

1. Recovery: compare both baselines, then add A/U and total. Verify visible day-type
   facets and the baseline=100 reference.
2. YoY: select August 2026; inspect exported reference means and August 2025 dates.
3. Trend → Annual: confirm partial 2026 is excluded. Trend → Daily: include all day
   types to enable seven-day means; filter to W and confirm their unavailability.
4. Seasonal: select 2024 and 2026; check consistent bus/rail colors and gaps after
   August 2026, without implying a complete-year comparison.
5. Select July 2012 or no modes/day types: inspect the empty state and coverage
   explanation. Open exports and verify their definitions match active selections.

Stop after 4B.2B. Research & Methodology development requires new approval.
