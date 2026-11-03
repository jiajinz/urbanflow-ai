# Milestone 4C.1D.1 — Anomaly Research Explorer Design & Integration Review

Chicago Transit Authority (CTA) historical anomaly research, designed for first-time
readers and technical reviewers. **Design only: no fourth page or runtime loader
has been implemented.** All interfaces and file changes below are proposed for
4C.1D.2 and require explicit approval.

## 1. Decision and scientific boundary

Page name: **Anomaly Research Explorer**. Proposed route: `/anomaly-research`.
Persistent, exact label: **Experimental Research — Not a Production Alerting System**.

Preserve 4C.1C's **operational NO-GO** and `prospective_validation_executed=false`.
Authorization to explore historical research is separate from production-readiness
approval. No live alerts, model fitting, threshold adjustment, incident confirmation,
review-status editing, forecasting, or prospective validation runs belong here.
A locally clear health window does not overturn the global NO-GO. Public hosting
of a read-only research page would require separate deployment authorization and
would not constitute operational approval.

## 2. Inspected evidence and reusable boundaries

Read AGENTS.md; 4C.1A detector, report and tests; 4C.1B protocol, report, validation
module and tests; 4C.1C case/health exporter, report, config, manifests and tests;
current navigation, data loader, page shell and shared design system.

Read-only inventory verified for this design:

| Artifact | Current evidence | Intended use |
| --- | --- | --- |
| `data/anomaly/cta-4c1a-v1/predictions.csv` | 11,200 rows, 16 columns; 2 models × 2 modes × 2,800 dates | Original prediction lineage, not a second competing runtime series |
| `data/anomaly/cta-4c1b-v1/daily.csv` | 11,200 rows, 28 columns | Actual/expected lines, stored scores, flags and calibration evidence |
| `data/anomaly/cta-4c1c-v1/cases.csv` | 763 rows, 44 columns; 464 calendar median, 299 seasonal trend; all unreviewed | Candidate table, as-of evidence and priority components |
| `data/anomaly/cta-4c1c-v1/model_health.csv` | 11,200 rows, 32 columns | Full historical health context, including unknown/insufficient states |
| `data/anomaly/cta-4c1c-v1/episode_registry.csv` | 200 rows | Membership and separately labeled retrospective full-episode context |

Coverage is 2019-01-01–2026-08-31, not all dates in the 2001–2026 source archive.
July 2012 quarantine is outside the selectable scored period. Link to Methodology
rather than inventing model estimates for the gap. Current health states are clear,
insufficient_history, unknown_drift_or_error, and warning; missing-date fixtures
must additionally cover scored_data_gap. No source revisions or new API data were
acquired. The four proposed runtime research CSVs total **8,052,466 bytes** before
source/protocol metadata; this is disk size, not an estimate of pandas RAM.

Reuse:

- `streamlit_app.py`: existing `st.navigation`/`st.Page`; future registration is
  one additional route, preserving existing page defaults and paths.
- `ui_design.page_styles()` / `apply_page_styles()`: public container-key scoping,
  native focus states, typography and semantic palette. New namespace only.
- `dashboard_charts.MODE_COLORS`, `MODE_LABELS`, `DAY_LABELS`: preserve existing
  bus/rail identity and plain-English CTA day-type labels.
- `DataAccessError`, `validate_frame()`, `history.coverage_details()`: safe failures,
  source validation and calendar audit at the research data boundary.
- Existing 4C.1A/B/C outputs and hash chains: evidence, not functions to rerun in UI.

Do not call `detect()`, `anomaly_validation.run()`, `model_health()`, or
`build_cases()` from Streamlit. Do not use `dashboard_data.load_archive()` for the
new runtime path: it calls `build_analytical_data()` and recomputes unrelated
analytics. Existing `dataset()` also selects PostgreSQL or the transit dashboard
bundle, so it is not the research-page loader. Existing chart helpers label
ridership recovery/YoY and are not interchangeable with anomaly charts.

## 3. Proposed page workflow and interaction contract

### Persistent research framing

Introduction: "Explore historical Chicago Transit Authority (CTA) ridership
candidates and the limits of their model-based evidence."
Show exact experimental label, "Operational readiness: NO-GO", historical date
coverage and artifact version before controls. Explain once: "A statistical
candidate is an observation for investigation, not a confirmed transit incident."
No green readiness badge or incident counter. Frozen urgency means a historical research-priority heuristic, not a live escalation. A concise source/version caption
links to the research/prospective reports; detailed provenance lives in an expander.

### 1 — Choose the historical comparison

| Control | Default / options | Effect |
| --- | --- | --- |
| Model | Seasonal Trend; Calendar Median also visible | Selects one frozen model for lines, cases and health; default is presentation convenience, not production endorsement |
| Service date range | Last 365 calendar days within scored coverage; currently 2025-09-01–2026-08-31 inclusive | Filters chart targets, table targets and displayed health dates |
| Transit mode | Bus; single Bus or Rail | Keeps one mode's evidence legible; cross-mode detail still uses stored other-mode evidence |
| Candidate direction | All; Above expected; Below expected | Filters candidate markers and cases by actual residual direction, never score sign |
| More candidate filters | Frozen urgency flag only; Other mode also a candidate; Cases with health warnings; all off | Restricts candidate subset only; never changes thresholds or hides full-period health |
| Search cases | Empty; literal case ID, ISO date, day type or direction text | Server-side candidate search; same subset drives table, markers and case export |

Avoid adjustable score thresholds, arbitrary baseline controls, day-type filters,
year/aggregation selectors, model training controls or health-hiding toggles in the
first iteration. Day type remains in hover/table detail to explain comparability.
Date endpoints are inclusive in UI and normalized once to half-open bounds in the
view-model filter. Reject invalid/reversed/out-of-coverage inputs visibly; an
unfinished date range requests completion without changing other pages.

Active-selection text explicitly distinguishes:
"Context: [model / mode / dates]. Candidate subset: [direction / options / query]."
Show visible candidate count and candidate count before optional subset filters.
Do not display an alert rate using the narrowed search results as its denominator.
Optional health-warning filtering matches explicit true only; unknown health is
not clear, remains visible in context, and has an explained count.

### 2 — Actual versus expected

One daily Plotly chart, full selected model/mode/date context. Actual uses existing
mode color; expected is a navy dashed line. Candidate overlays use distinct
up/down marker shapes keyed to actual direction. Legend: "Actual boardings",
"Frozen model expectation", "Candidate: above expected", "Candidate: below
expected". Shape and dash carry meaning independently of color.

Hover includes date, CTA day type, actual, expected, signed/percentage deviation,
centered score and actual direction. No causal text or incident labels. Missing
calendar dates are null gaps with no line bridging; no smoothing, aggregation,
zero fill or confidence band. These artifacts do not supply prediction intervals.
Candidate subset filters affect markers, not the complete actual/expected lines.
Caption this behavior explicitly so hidden markers are not mistaken for erased
observations or reclassified non-candidates.

A compact, aligned health-state strip shows every selected date, including
warnings and unknown states; it is not limited to candidate dates. An adjacent
caption points to full health evidence below. Avoid one vertical band per warning
on the main chart, which would obscure long stress periods.

### 3 — Inspect a candidate

Read-only native dataframe with configured columns: date, mode, actual, expected,
signed percentage deviation, actual direction, centered score, health state,
review state. Stable case ID is retained internally and in export. Default
chronological ordering; optional visible stored priority points may explain the
research ordering without implying event likelihood.

Use native single-row selection with an accessible case-ID selector fallback.
Resolve selections through the rendered frame's row-to-case-ID mapping, never a
stale global dataframe position. Clear selection if filters exclude that case;
never silently open a different row. Native client-side table find/sort is display
only; the explicit "Search cases" input defines exported membership. Label this
boundary; downloads do not claim to follow an unobservable client-side search.

Case evidence opens below the table:

- Counts and deviations; separate labels for "Actual deviation direction" and
  "Centered score sign". Example 2021-06-04 calendar median rail: actual 244,454,
  expected 717,811, deviation -65.94%, score +3.94. Do not label it above expected.
- "Why flagged": stored score exceeds 3.5 in absolute value AND absolute
  deviation meets max(10,000 boardings, 20% expected). Explain log residual,
  historical center and scale from the matching daily row in an expander.
- Prior same-day-type observations from the frozen case JSON, labeled
  "Prior 28-calendar-day context; target excluded". Parse JSON safely, never eval.
  Missing/empty context is unavailable, not zero demand.
- Same-date other-mode observations, expectation, candidate flag and direction.
  Unavailable context stays unavailable, not "other mode normal".
- Episode ID and elapsed days as of the case date. A separate disclosure may show
  full registry start/end/count with "Retrospective episode context, including
  dates after this case". Date/candidate filters do not recompute episode membership.
- Data-quality status, prior coverage, uncertainty, unknown cause and unreviewed
  status; fields are descriptive and cannot be edited or promoted to confirmed.

### 4 — Model health and limitations

Show selected-period stored health evidence independently of candidate filters.
Retain 28-day WAPE/bias, calibration center/scale and drift flags, alert-frequency
warning and health status in a concise summary plus detailed dataframe/expander.
Do not recompute rolling metrics on the selected date slice: first selected dates
may depend on earlier observations, already represented in the frozen values.

Unknown/insufficient/gap states have explicit text. "Clear under research guards"
is a local diagnostic state, never "production ready". Global NO-GO stays visible
regardless of model selection or local health. State that rolling windows overlap,
health warnings are not incidents, and all historical dates were previously
inspected. The health grid ends at the last scored service date, so it cannot
monitor delayed/unpublished tail observations or live pipeline freshness.

### 5 — Export the selected research evidence

Prefer one in-memory ZIP, generated only on request:

- `observations.csv`: full selected model/mode/date context used by chart lines.
- `candidates.csv`: exact candidate subset shown by direction/options/query.
- `model_health.csv`: all selected-period states, unaffected by candidate filters.
- `episode_context.csv`: full records for referenced episode IDs, clearly marked
  retrospective and potentially extending outside target dates.
- `selection.json`: normalized filters, search field policy, counts, selected case
  ID if any, immutable thresholds, version, source SHA-256 chain, source retrieval
  timestamp, protocol freeze time, export UTC, NO-GO, experimental label and
  prospective_validation_executed=false. Export time is not source freshness.
- `context.txt`: concise scientific limitations and column/scope definitions.

Do not export only candidate days under the name historical observations. Preserve
original stable IDs and numerical values; percentage fields stay in documented
percent units. No review writes, source mutations, application URL secrets, or
local absolute developer paths in public metadata. Exports must disclose that
candidate filtering does not erase source candidates. Future externally supplied
text needs CSV formula-injection protection without modifying numeric evidence.

## 4. Frozen loading and integrity design

### Initial format and source selection

Read the existing versioned CSVs; no new Parquet conversion or regenerated model
outputs are needed. Proposed trusted version catalog maps logical artifacts to
fixed repository-relative paths under a configured server-side root. Initial
catalog version joins 4C.1B daily diagnostics with 4C.1C cases/health/registry and
original 4C.1A lineage. It also maps readiness config, prospective protocol,
historical source manifest and daily source Parquet for count verification.
No user-uploaded artifacts or browser-supplied paths.

Keep the research environment independent of `URBANFLOW_DATA_BACKEND`: even when
other pages use local PostgreSQL, this page reads one explicit frozen research
version. Display that distinction; never splice current PostgreSQL observations
into historical model outputs. No fallback to live data or another artifact version.

### Verification sequence (proposed)

1. Select an allowlisted version with trusted manifest digests. Pin the root
   4C.1C manifest hash in the application version catalog so modifying both a CSV
   and its manifest is not sufficient to bypass integrity checks. Hashes assure
   approved bytes/lineage, not independent measurement accuracy or signed agency data.
2. Resolve only catalog paths within the configured root; reject traversal,
   unexpected files and symlinks escaping it. Existing manifests contain absolute
   `/Users/...` source-code keys: treat them as legacy lineage labels and map exact
   recognized logical names to packaged files. Never open arbitrary manifest paths.
   Preserve original manifests; sanitize path labels only in public display/export.
3. Verify B output hashes, C output hashes, C-to-B manifest/daily links, B-to-A
   prediction/manifest links, detector/validation/readiness source hashes, readiness
   config/protocol bytes and original source Parquet provenance. A does not have an
   output-hash map; its predictions are authenticated by B's recorded input hash
   and the readiness config. Do not invent an A output-checksum field.
4. Parse explicit date, boolean, enum and numeric schemas. Never use bool("False")
   or blanket fillna(0). Require one row per model/mode/date, unique case/episode
   IDs, valid model/mode/day types, date bounds, finite required scores/counts,
   positive scales, recognized health states and exact preserved review states.
   Nullable comparison percentages/context must remain nullable.
5. Cross-check observed counts/day types against validated source using
   `validate_frame()` and source checksums. Verify stored candidate flags, residual
   and score reconciliation with documented numeric tolerance; do not rerun models.
   Case count and exact case-ID set must match candidate-true daily rows, scores
   and directions must agree, and every case must map to one registry episode.
   Opposite score/deviation signs are valid, not a load error.
6. Require health coverage for the declared model/mode calendar grid, retaining
   explicit unknown/gap states. A missing required health table/row is an integrity
   error, not permission to hide the panel. Check as-of episode age and prior JSON
   timestamps without replacing frozen fields. Preserve full episode boundaries.
7. Check metadata says retrospective, operational NO-GO, and no prospective
   execution. A future readiness decision requires a new explicitly approved
   catalog/schema version; it must not silently remove these constraints.

Cache verified parsed frames using `st.cache_data` with bounded entries. Use an
actual content fingerprint of required manifests/artifacts as the cache identity,
not only the path or mtime. Verify current bytes against expected hashes before
using a cached version; a cache miss re-verifies bytes used for parsing. This
small fixed dataset favors robust validation over fragile freshness shortcuts.
Source retrieval time may be read from original provenance. Research generation and
agency publication times are not recorded in these research manifests; label them
unknown rather than borrowing dashboard generation time or prospective freeze time.
Do not reuse the existing dashboard header unchanged if its metadata assumptions
would imply a generation date that is absent here.
No network access, credentials, database connection, fitting or artifact rewriting
is involved. Any integrity failure stops this page with an actionable error and
no fabricated chart; other pages remain available.

## 5. Proposed pure view-model contracts

These are design signatures, not implemented classes/functions:

```text
ResearchBundle
  daily, cases, health, episodes: validated DataFrames
  provenance: normalized immutable version/hash/source/status metadata

ResearchFilter
  model: calendar_median | seasonal_trend
  mode: bus | rail
  start_date, end_date_exclusive: typed dates
  direction: all | high | low
  urgent_only, cross_mode_only, health_warning_only: booleans
  query: bounded literal string, not regex

ResearchView
  observations: full primary-filter rows and explicit chart date gaps
  candidates: secondary-filter rows, stable case IDs and stored evidence
  health: complete primary-filter calendar states
  episode_context: full registry rows referenced by candidates
  counts: context observations / unfiltered candidates / visible candidates /
          warning dates / unknown dates, with scope labels
  selection_context: filters, versions, NO-GO, export scopes and limitations

CaseEvidence
  selected case row + matching daily calibration row + stored prior context
  same-day stored cross-mode context + as-of/full-episode scope labels
```

`load_research_bundle(root, version_id) -> ResearchBundle`: all validation at the
boundary; raises safe `DataAccessError` on missing/corrupt/inconsistent artifacts.
`build_research_view(bundle, filters) -> ResearchView`: selection and plotting
reshape only; returns explicit empty subsets, raises ValueError for invalid filters.
`select_case(view, case_id) -> CaseEvidence | None`: only a currently visible ID;
stale/empty selection returns None with guidance, not a guessed row.
`export_research_view(view, provenance) -> bytes`: ZIP exactly matching view scopes.
Plotly renderers consume these frames without computing scores, thresholds, health,
priority or episode membership. No existing `AnalyticalData` schema change.

## 6. Presentation and accessibility acceptance

Reuse Deep Navy #142B49, Teal #087E83, Blue #3D76BC, Amber #C08431, Canvas #F3F6FA
and White #FFFFFF. Preserve existing mode colors. Use navy hierarchy, teal active
controls, blue evidence and amber limitations; no decorative severity gradients.
Use native containers, segmented controls, dataframe and expanders, `width="stretch"`,
semantic labels and chart `alt` descriptions. New page-key namespace only; no
changes to global CSS/theme or the three approved pages.

First screen: framing, compact primary controls, then actual/expected chart.
Candidate table, one selected case, health evidence and export follow the same
workflow. Keep statistical formulas in an expander, with visible plain-language
meaning and limitations. Empty candidate subsets retain chart/health context;
empty/unknown data must not read "no incidents" or "healthy".

Manual QA in 4C.1D.2 must inspect desktop and narrow viewports, 200% zoom, keyboard
control/row selection/fallback, visible focus, readable legends, directional marker
shapes and non-color health labels. Test downloadable/assistive data alternatives;
Plotly interactivity alone does not prove screen-reader accessibility. No browser
or accessibility QA has occurred in this design phase.

## 7. Testing and acceptance plan for 4C.1D.2

- Loader unit tests: missing files, altered hashes/manifests, pinned root digest,
  portable logical path mapping, traversal/symlink rejection, invalid booleans,
  schema/enum/date failures, duplicate keys, source mismatch, broken candidate /
  episode / health joins, nullable context and unknown health. Simulate cache reuse
  after content changes without relying on changed filenames or timestamps.
- Pure view-model tests: inclusive/exclusive boundaries, both models/modes,
  direction from raw residual, combinations of candidate-only filters, literal
  search, empty subsets, stable case selection and candidate preservation.
  Verify context curves and health are unchanged by secondary filters/search.
- Golden evidence: 763 cases (464/299), 200 episodes, 11,200 daily/health rows in
  this pinned version; 2021-06-04 calendar median rail remains below expected with
  positive centered score. Case health and episode age match C exactly.
- Leakage/scope tests: filter start must not recompute rolling health; final
  episode duration cannot enter as-of priority or case age. Prior context dates
  remain before target. Full registry disclosures/export are labeled retrospective.
- Chart/export tests: every plotted actual/expected/candidate coordinate maps to
  view rows; null gaps remain gaps; ZIP tables and selection metadata match scopes
  and include version/NO-GO/experimental labels. No threshold slider or CSV writeback.
- Streamlit AppTest: fourth-page navigation, required framing, conditional detail,
  all filters, explicit search, single-row selection and fallback, invalid/empty
  states, corrupt artifact error, full-period health despite zero selected cases,
  and no changes to the three existing pages.
- Architecture boundary test: page loading/rendering must not call detector fit,
  health recomputation, PostgreSQL/API access, or filesystem write operations.
- Run the complete available suite after implementation; distinguish pure unit,
  snapshot/AppTest, optional PostgreSQL integration and manual browser evidence.
  No live API dependency is needed for ordinary tests.

Acceptance requires the exact framing, read-only behavior, validated portability,
correct filter/export scopes, full health visibility, preserved original outputs,
regression checks and actual browser review. It does not grant production readiness
or deployment authorization. Prior phase test counts are not new D.1 test results.

## 8. File-by-file implementation plan (not executed)

| Proposed file/change | Responsibility | Boundary |
| --- | --- | --- |
| `src/urbanflow_ai/anomaly_research_data.py` (new) | Trusted version catalog, typed bundle, portable validation and normalized provenance | Read frozen artifacts; never fit/export new model outputs |
| `src/urbanflow_ai/anomaly_research_views.py` (new) | Typed filter/view, selection, case evidence and scoped ZIP export | Pure selection/reshape; no Streamlit, model or SQL changes |
| `src/urbanflow_ai/anomaly_research_charts.py` (new) | Actual/expected/candidate chart and health-state strip | Plotly presentation of supplied values only |
| `src/urbanflow_ai/anomaly_research_ui.py` (new) | Native controls, framing, cache boundary, table/detail/export rendering | Reuse shared styles without altering existing pages |
| `app_pages/anomaly_research.py` (new) | Thin page script | New route body only |
| `streamlit_app.py` (future small edit) | Register fourth st.Page | Preserve current navigation defaults/paths |
| `tests/test_anomaly_research_data.py` (new) | Integrity/path/cache cases | Deterministic fixtures, no network |
| `tests/test_anomaly_research_views.py` (new) | Filters, case selection, golden values, exports | No duplicate detector implementation |
| `tests/test_anomaly_research_ui.py` (new) | AppTest and chart-data assertions | Existing page regressions remain intact |

No edits planned to README, SQL, existing models, research definitions, readiness
criteria, frozen datasets or approved page functions. Do not execute historical
export CLIs merely to build the page. A future data-format change would require a
new artifact version and separate review; it is unnecessary for initial integration.

## 9. Deployment considerations and unresolved decisions

- Existing pandas, NumPy, Plotly, Streamlit and standard-library JSON/hash/ZIP tools
  suffice; no new dependency, database credentials, API access or model service.
- Package the pinned research tables, source-validation Parquet, manifests, exact
  referenced protocol/config and source files needed for hash lineage. Do not
  depend on a developer's absolute home path or transient `/tmp` evidence.
- Use repository-relative package resources and a server-configured root. Root
  version fingerprints must match the reviewed checkout even on Community Cloud.
  Fail closed when required historical code/protocol is absent or mismatched.
- Research dataset/version must remain separate from the transit analytics backend
  shown elsewhere. Do not claim local PostgreSQL content produced these predictions.
- CSVs are small enough to begin with, but measure cold load, parsed-frame memory,
  table responsiveness and generated ZIP memory on the chosen hosting tier. Disk
  byte counts alone do not prove resource compliance. Limit cached versions and
  concurrent export copies; no benchmark or cloud deployment was performed here.
- Do not expose source absolute paths, private reviewer data, environment values or
  credentials in downloadable provenance. All current cases are unreviewed; adding
  actual reviewer evidence would need a separate privacy/publication decision.
- Freeze public wording and cross-page environment labeling before implementation
  acceptance. Native row selection/search behavior must be verified against the
  installed Streamlit version, with an accessible stable-ID fallback.
- Historical viewing is proposed; public publication and operational alerting remain
  separately gated. Readiness NO-GO stays in the UI and exports, even when a local
  health state is clear. No design choice supersedes the prospective protocol.

## 10. Design-phase verification and next approval

This phase executed read-only CSV/schema/count inspection and SHA-256 checks of all
11 B outputs, all 4 C outputs, A-to-B prediction/manifest links, and C-to-B/config /
protocol links. Native dataframe selection availability was inspected locally.
Only this design document was created. No page, loader, view-model implementation,
new data bundle, source model change, pytest execution, browser QA or deployment
was performed. Protected source/data/dashboard/README hashes were checked after
writing the document; whitespace validation was clean.

Next requested approval: implement the scoped read-only design in 4C.1D.2, with the
above scientific boundaries and test gates. Stop at this review until explicitly
approved; do not proceed to implementation, deployment or 4C.2.
