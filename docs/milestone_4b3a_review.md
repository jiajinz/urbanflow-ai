# Milestone 4B.3A: Cross-page UX review

## Audit and decisions

- Medium, all pages: typography and presentation rules were split across Overview,
  copied Explorer CSS, and inline Methodology CSS. Consolidate public container-key
  scoped styles in `ui_design.py`; retain native Streamlit navigation and widgets.
- Medium, Explorer: a full metric paragraph delayed the chart. Show the unit and
  active selection, then keep the full validated definition in a disclosure below
  the chart. Preserve export definitions and all filtering semantics.
- Medium, Explorer: vertical Plotly facet labels could resemble right-axis titles.
  Render horizontal day-type headings above their respective subplot domains.
  Label recovery and YoY reference lines explicitly. Preserve traces and colors.
- Medium, Explorer seasonal view: three years and two modes created unnecessary
  initial line density. Default to two recent selected years; permit all choices.
- Low, Methodology: long validation and limitation paragraphs dominated the default
  view. Preserve all text in labeled disclosures and retain five approved sections,
  visible provenance, the July 2012 warning, and direct reproduction disclosure.
- Low, all pages: align navy text, teal actions, and neutral canvas in native theme.
  Blue identifies definitions/evidence; amber identifies methodological cautions.
  Keep white analytical surfaces. No decorative charts or new analytics.
- No functional navigation or empty/error-state defect was identified during the
  source audit; retain existing actionable text and explicit no-fallback behavior.

## Scope and execution

`overview_components` and `explorer_components` obtain scoped CSS from
`ui_design.page_styles()`. Methodology calls `apply_page_styles()` within its own
keyed container. CSS uses public `st-key-*` classes, native ARIA states, and
focus-visible; no generated Streamlit classes. Overview layout and baseline
control code remain intact. The small namespace adapter retains existing public
container keys instead of introducing a component framework.

Explorer still constructs the same ExplorerFilter and calls explorer_model.
The same model series feeds charts and CSV exports. `refine_explorer_figure()`
changes layout and annotations only, after existing chart creation; it does not
modify trace coordinates, values, colors, or gap handling. Subplot headings use
actual y-axis domains to avoid placing labels over data.

## Verification

Full suite with local PostgreSQL: 208 passed, 0 failed, 0 skipped before final
annotation placement refinement; see final run below. New presentation tests check
scoping, native focus rules, horizontal facet headings, and unchanged trace data.
Existing tests cover research golden results, baselines, filtering, coverage, YoY,
and chart/export consistency. SHA-256 comparison against a pre-phase manifest
confirmed SQL, research.py, dashboard_metrics.py, explorer.py, dashboard_data.py,
and validated dashboard files remained unchanged.

No live API test, deployment, commit, push, or 4B.3B/4B.3C work was performed.

Final full suite after the annotation correction: **208 passed, 0 failed,
0 skipped** (6.17 seconds). `git diff --check` was clean. Existing uncommitted
milestone work remains; tracked diff statistics omit untracked files.

Desktop browser checks inspected all three pages and saved local screenshots:
`/tmp/urbanflow-4b3a-explorer.png`, `/tmp/urbanflow-4b3a-methodology.png`, and
`/tmp/urbanflow-4b3a-overview.png`. Explorer evidence shows horizontal weekday
heading, preserved bus/rail colors, explicit baseline reference, and the collapsed
metric-definition disclosure. Overview retained its layout, selected baseline,
and 70.90 / 88.10 / 89.29 / 22.28 pp cards. Methodology retained source metadata
and traceable July 2012 evidence with smaller shared headings.

Remaining review: narrow/mobile viewports, screen-reader and full keyboard audits,
and dense user-selected multi-year/multi-type seasonal comparisons. No complete
accessibility certification is claimed. Controls can still exceed a short desktop
viewport; they remain visible to preserve active analytical context. Explicit
user selections are never silently capped. Native navigation and warning widget
presentation remain owned by the shared Streamlit theme.

Local preview: `python -m streamlit run streamlit_app.py --server.port 8513`.
