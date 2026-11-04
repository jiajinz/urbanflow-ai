# Milestone 4B.3B — Product QA Review

Verification date: November 3, 2026 (America/New_York).
Scope: four existing Streamlit pages, presentation, accessibility, reliability and
read-only deployment audit. Product QA is complete with the limitations below;
release approval and cloud validation remain separate. No deployment, push, tag,
new analytics, model fitting, prospective validation or AI integration occurred.

## Prerequisite: independent research acceptance

**4C.1D.2 Acceptance Gate: PASS**, recorded in
[the acceptance report](anomaly_research_acceptance_gate.md). Five core criteria
were checked with deterministic tests, AppTest, real browser interactions and
actual downloaded ZIP inspection. Local checkpoint: `9699ef3`.

That gate accepts an experimental historical investigation interface, not an
operational detector. **Operational Readiness: NO-GO** remains unchanged.

## Severity-ranked audit and disposition

- **Critical:** none found in the tested workflows. This is not proof that every
  possible browser, assistive technology or selection is defect-free.
- **High — Anomaly Research Explorer:** the 320-pixel direction control could hide
  All or clip Below expected in a horizontal strip. Fixed with native `wrap=True`
  on the research segmented controls. Options and filter semantics are unchanged.
- **High — all pages:** native caption containers applied 60% opacity, reducing
  contrast of reporting dates, filter context and methodological notes. Added
  `readable_caption()` with stable public container keys and narrowly scoped CSS
  that removes this opacity. Native captions, font sizes, English text and links
  remain. It does not target generated Streamlit classes or private test IDs.
- **Medium — Overview, Explorer and research:** main sections skipped from H1 to
  H3. Main sections now use H2; Overview chart/finding subsections remain H3.
  The summary retains its approved visible size through its existing scoped rule.
  Methodology keeps all five H2 sections and all substantive content.
- **Medium — Overview:** charts lacked accessible names and the complete plotted
  monthly values lacked an on-page table alternative. Added `alt` descriptions
  and exact monthly total/mode evidence tables in the existing evidence expander.
- **Medium — research:** provided a full observed/expected table alternative in
  an expander. It includes noncandidate dates and is independent of case search.
- **Medium — Overview/Explorer:** common single-mode line comparisons relied on
  color. Added redundant solid/dashed/dotted line styles, preserving all values,
  colors, gaps and reference lines. Seasonal year-dash encodings remain intact.
- **Low, retained:** full-history research curves are dense, narrow tables require
  their native internal scrolling, provenance is lengthy when expanded, and a
  hovered Plotly toolbar/tooltip can temporarily obscure part of a narrow legend.
  The textual evidence, table, export and full-screen controls remain available.
  No broad visual redesign or performance framework was justified.

## Browser and responsive checks actually performed

All four pages were actually rendered at each of:
1440 × 900, 1280 × 720, 1024 × 768, 390 × 844 and 320 × 700.
There were 20 page/viewport combinations before fixes, followed by repeated checks
after fixes, including the final caption change. Plotly SVG rendering was awaited;
Methodology has no chart. [Final DOM evidence](qa/4b3b/after_matrix.json) records
viewport sizes, headings, named figures, control bounds and sampled caption opacity.
[SVG/width evidence](qa/4b3b/render_checks.json) records plot widths at all sizes.

Final document and main scroll widths equaled viewport widths in all 20 cases.
No radio buttons or main headings extended beyond the viewport. KPI grids stacked
on mobile; long text wrapped; analytical tables remained internally scrollable.
The initial broad input-bound scan flagged a hidden slider input; this was not
classified as visible page overflow. Default Explorer seasonal comparisons selected
2025 and 2026, not all historical years.

Actual keyboard interactions exercised:

- Sidebar expansion, navigation to all four routes with Enter, and sidebar collapse.
- Model control arrow-key focus movement followed by Enter activation. Arrow keys
  alone move focus; the selected model stays unchanged until activated.
- Tab from a model control to the labeled date spinbutton.
- Native summary/expander Enter activation, search input and Enter submission.
- A visible navy 3-pixel focus outline on the focused model button.

Actual browser functional checks also covered the critical June 2021 case,
Seasonal Trend March 2025 evidence, empty candidates with full trends/health,
Overview baseline switching (2019 weekday KPI 70.90; 2017–2019 KPI 69.18), Explorer
YoY/seasonal views and no-mode empty state, and Methodology quarantine evidence
and reproducibility commands.

Actual downloads inspected:

- Three research ZIPs: all four exported tables, IDs, definitions, hashes and NO-GO.
- Explorer YoY CSV: 64 rows matched the exact active view-model series; no duplicate
  date/mode/day-type keys. One first browser event wait timed out with no file;
  a second click on the stable page succeeded. No persistent download failure was
  reproduced; automatic download reliability is not inferred from a button alone.
- Overview monthly CSV with 2017–2019 baseline: 240 rows matched the view model.
- Methodology provenance JSON: exactly matched snapshot metadata.

Local downloaded files are excluded from Git. The browser error log contained
health/reconnection messages during the deliberate local server restart; no new
application error was observed after reconnection in the tested routes.

## Accessibility findings and limits

Browser DOM inspection confirmed meaningful native widget names, page titles,
H1/H2/H3 hierarchy in the main landmark, named figures, keyboard-focusable
expanders, and native table/case selector alternatives. Native date fields expose
separate year/month/day names. Research uses distinct actual/expected line styles,
up/down candidate symbols and labeled health states. Existing mode colors remain.

Final sampled caption opacity was 1 on all four pages at all five sizes. Sampled
opaque text pairs were navy/white (14.27:1) and muted navy/white (6.09:1); the
approved teal/white pair is 4.86:1. These are contrast calculations on inspected
colors, not an exhaustive audit of all pixels, hover/disabled states or imagery.
Amber and orange are retained as graphical evidence rather than small body text.

**Not verified:** a real VoiceOver/NVDA reading session, mobile touch hardware,
complete keyboard traversal of every Plotly/data-grid action, and actual 200%
text/browser zoom. The embedded browser did not change width, device-pixel ratio
or visual-viewport scale after its native zoom shortcut. Narrow reflow tests are
not reported as zoom tests. No axe scan or WCAG conformance certification is
claimed. Streamlit's virtualized grid and Plotly SVG are not assumed to provide
complete screen-reader access; explicit names, prose, tables and CSV/ZIP exports
reduce dependence on those interfaces. No dialog flow exists in this application;
sidebar overlays and expanders were exercised, not nonexistent dialogs.

## Actual performance measurements

[Raw measurements](qa/4b3b/performance.json) were produced by
`scripts/benchmark_dashboard.py`. After benchmark imports, first in-process
entrypoint execution was 0.329 s. A separate temporary local server took 0.237 s
from CLI process creation to announcing its listening URL; this excludes first
page execution and browser rendering. Five warm repetitions per page gave:

- Overview: 60.8 ms median rerun; baseline change 60.6 ms.
- Explorer: 33.6 ms median rerun; question change 40.5 ms.
- Methodology: 6.7 ms median rerun; no analytical filter applies.
- Research: 44.1 ms median rerun; model change 44.0 ms. First research page switch
  took 0.559 s. Explicit cold verified bundle parsing took 0.532 s, warm verified
  loading 17.7 ms median. The checks still read approved bytes before cache lookup.

Warm-server browser navigation through visible content and the first Plotly SVG
(or content only for Methodology) took 464/417/519/467 ms for Overview/Explorer/
Methodology/Research at 1440 × 900. These single observations include automation
round trips and page streaming; they are not isolated Plotly paint durations,
network benchmarks or percentiles. No separate browser paint profiler was available.
The browser measurement preceded the small caption wrapper change; final SVG
rendering was rechecked at every viewport after it. The in-process measurements
above include the final change.

Four research frames used 10,022,258 bytes under pandas deep accounting. Benchmark
process high-water RSS was approximately 358 MiB, including imports, caches,
all pages and prior allocations; it is not per-session memory or a cloud quota.
No concurrency/load test occurred. A first-load research verification cost was
measurable but not large enough here to justify weakening hashes or hiding health.
The before/after timings are separate local runs, not a controlled speedup experiment.

Reproduce from the repository root:

```sh
source .venv/bin/activate
URBANFLOW_DATA_BACKEND=snapshot python scripts/benchmark_dashboard.py
python -m streamlit run streamlit_app.py --server.port 8514
TEST_DATABASE_URL=postgresql:///urbanflow_ai_test python -m pytest -q --tb=short
python -m pip check
```

The benchmark is for macOS/Linux and fails visibly on page errors. It does not
train models, fetch API data, benchmark a public service or regenerate artifacts.

## Scientific regression and tests actually executed

- Final full available regression suite, including PostgreSQL integration:
  **278 passed, 0 failed, 0 skipped in 21.88 seconds**.
- Caption/page/copy-focused suite: **30 passed in 5.96 seconds**.
- Earlier full post-refinement run before caption correction: 278 passed in 23.14 s.
- Acceptance-fix full suite: 274 passed in 20.40 s.
- `pip check`: no broken requirements. `git diff --check`: clean before staging.

New tests cover model-isolated evidence/exports, visible single-date traces with
empty candidates, exact table alternatives under both Overview baselines, complete
research tables after empty case search, unchanged line values/colors/gaps, and
all four pages rendering with API and PostgreSQL calls forbidden. Existing tests
cover SQL parity, recovery/YoY/baselines, missing periods, hashes, health joins and
NO-GO. AppTest proves Python rendering/state behavior, not browser accessibility.
PostgreSQL integration proves local database behavior; no live API test was run.

[The protected-file inventory](qa/4b3b/protected_files.json) confirms **71 files
unchanged byte-for-byte**: versioned data artifacts, SQL and analytical/model
implementations plus frozen readiness/protocol definitions. No SQL, model output,
threshold, validated data coverage, exported metric definition or NO-GO decision
was changed. Overview and Explorer export payloads matched the same analytics.

## Read-only Streamlit Community Cloud readiness audit

No deployment was attempted and no provider quotas are assumed.

- Entrypoint is `streamlit_app.py`; `requirements.txt` installs the local project
  with `-e .`; package metadata includes SQL. Default backend is the checked-in
  Parquet snapshot. Research uses checked-in frozen evidence. Neither default
  path requires the owner's PostgreSQL server, API access or runtime training.
- Paths resolve relative to the installed checkout. A legacy absolute source-root
  label remains in frozen manifests; the research loader explicitly maps that
  approved label to a relative path and rejects arbitrary/escaping paths.
  Relocated-root tests pass. Public exports normalize provenance keys.
- Tracked data total is approximately 13.2 MB. Existing generated Plotly HTML files
  are approximately 4.9 MB each; these are documentation artifacts, not retrained
  models or required browser downloads on every dashboard interaction.
- Validated runtime here: Python 3.11, Streamlit 1.66.1, Plotly 6.9.0,
  pandas 2.3.3, NumPy 2.4.6, PyArrow 23.0.1, DuckDB 1.5.6 and psycopg 3.3.6.
  No dependencies were added. The declared ranges are broader than this tested
  environment; lower-bound compatibility and fresh Linux installation were not tested.
- Tracked-file inventory and a credential-pattern scan found no real credentials
  in the reviewed matches. The two matches were a documentation password
  placeholder and a deliberate fake test URI. `.env`, Streamlit secrets, virtual
  environments and local AGENTS.md are ignored; `.agents/` remains untracked and
  excluded. This is a limited pattern review, not a comprehensive security audit.
- Experimental labeling, version identifiers, source retrieval date, unknown
  publication/generation timestamps, retrospective limits and NO-GO stay visible.
  All research candidates remain unreviewed with unknown causes.

Release prerequisites/blockers for the next authorized milestone:

1. Select and pin a tested Python/dependency environment; validate a clean Linux
   installation and the complete artifact inventory before deployment.
2. Check the chosen hosting tier's current resource limits, concurrent sessions,
   full-range plots/exports and real cold starts. Local RSS is not a hosting guarantee.
3. Finish assistive-technology and actual zoom review; address any resulting defects.
4. Review intentional publication of legacy path labels. Preserve frozen hash
   lineage; do not silently edit historical artifacts to remove metadata.
5. Deployment must reference these local commits. They have not been pushed;
   any future push and deployment require separate explicit authorization.

No proven offline startup blocker remains in the installed checkout. These release
prerequisites are not reported as a successful cloud deployment.

## Execution flow, review evidence and exercise

`streamlit_app.main()` adds the shared caption treatment and registers four
routes. Each route calls its page renderer. `readable_caption(body, key=None)`
wraps the native caption in a public-key container: a content digest gives it a
stable identity without session state; an explicit key is required for repeated
identical captions on one page. Only descendants of those owned containers have
their caption opacity corrected. No calculation or data access occurs there.

For research, `read_research()` verifies pinned bytes before `cached_research()`
parses/copies the bundle. `ResearchFilter` validates inputs; `build_research_view()`
selects full observations/health first, then candidate-only filters. Plotly and
CSV/ZIP consume those frames. Invalid filters raise a visible error; invalid
artifacts stop only that page. The new table takes the same full observations,
so search cannot erase noncandidate evidence. In the real June 2021 Rail case,
244,454 − 717,811 = −473,357, although the centered score is +3.94. Presentation
changes cannot turn this into above-expected demand or establish a cause.

Screenshots: [four-page desktop/mobile evidence](qa/4b3b/), including
[before](qa/4b3b/anomaly-320-controls-before.jpg) and
[after](qa/4b3b/anomaly-320-controls-after.jpg) narrow controls. The initial
before-capture used the older running module, prior to the server restart that
loaded the wrap correction; the final after-capture includes the caption fix.

Exercise: inspect the caption's computed color and all ancestor opacity values
in browser developer tools. Explain why assigning a darker color to a child alone
cannot undo a translucent parent. Then filter research candidates to no matches
and verify the observed-date count, health context and exported observation rows
remain unchanged. Use `test_observation_table_keeps_noncandidate_context_after_empty_search`
as the reproducible Python check.

## Changed files and checkpoint boundary

Presentation: `streamlit_app.py`, `ui_design.py`, `overview_components.py`,
`dashboard_ui.py`, `dashboard_charts.py`, `anomaly_research_ui.py`.
Tests: `test_ui_design.py`, `test_dashboard.py`, `test_anomaly_research_ui.py`.
QA deliverables: this report, `scripts/benchmark_dashboard.py`, and `docs/qa/4b3b/`.
The acceptance checkpoint separately contains its report, chart fix and view tests.

Stop after this QA checkpoint. Owner review remains required; do not proceed to
cloud release, 4C.2, forecasting or LLM development automatically.
