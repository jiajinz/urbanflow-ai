# Milestone 4C.1D.2 — Experimental Research Explorer Implementation Review

Chicago Transit Authority (CTA) historical anomaly research. The fourth page is
implemented as a read-only research interface. **Operational Readiness: NO-GO**
remains unchanged; no operational alerting, training, recalibration, prospective
assessment, reviewer writes, deployment, or new model family was introduced.

## Execution and boundaries

`streamlit_app.py` registers `app_pages/anomaly_research.py`, which calls the new
research UI. `verified_payloads()` checks actual artifact bytes before every cache
lookup. `cached_research()` caches parsing only. A pinned C manifest anchors B/A
lineage, protocol/config and source hashes; legacy absolute keys map to approved
repository-relative names and are never opened as arbitrary paths. Symlink escapes,
missing/corrupt artifacts, incompatible schemas and inconsistent joins fail closed.

`ResearchBundle` holds frozen evidence. `ResearchFilter` validates typed boundaries;
`build_research_view()` first selects the complete model/mode/date context and then
separately filters cases by actual direction, literal search and optional flags.
Candidate filters leave observation curves and health unchanged. `select_case()`
resolves a visible stable ID into the exact case, calibration row, prior observations
and full episode registry. Missing prior/comparison context is not zero demand.
`export_research_view()` builds an in-memory ZIP with separately named observation,
candidate, health and retrospective episode tables, selection metadata and hashes.

UI provides native row selection plus stable-ID fallback. Case direction and
centered-score sign are separate; 2021-06-04 calendar-median rail appears under
Below expected despite its positive score. Local clear health is not production
readiness. Full episode context is explicitly retrospective; case age stays as-of.
No changes to the three existing page implementations, global styles, README,
SQL, models, original historical snapshots, or frozen research outputs.

## Tests actually executed

- Initial data/view-model suite: 24 passed.
- New UI plus existing dashboard tests: 15 passed.
- Final full suite, including local PostgreSQL integration tests:
  `TEST_DATABASE_URL=postgresql:///urbanflow_ai_test python -m pytest -q --tb=short`
  **272 passed, 0 failed, 0 skipped**, 21.69 seconds.

Tests cover portable roots, hash corruption, missing files, path escapes, strict
boolean/schema parsing, candidate/episode/health joins, current score/direction
case, all primary and candidate filters, explicit null date gaps, view/chart/ZIP
membership, cached-frame invalidation after same-mtime content changes, empty
states, corrupted research roots and existing page regression. Boundary tests
forbid detector, health recomputation, archive analytics rebuild and PostgreSQL
calls while the research page renders. Tests are not proof of accessibility.

## Browser evidence actually checked

The local application was started on 127.0.0.1:8514. Browser checks confirmed
research framing, model/mode/direction/search changes, 2021-06-04 below-expected
case selection and positive centered score, persistent health context, and the
export control. The actual browser-downloaded ZIP was opened and verified:
19 default candidates, 365 observations, 365 health rows, and NO-GO metadata.
Direct-route checks rendered Executive Overview (including 70.90 KPI), Ridership
Explorer and Research & Methodology. A native sidebar-click attempt did not
navigate in the current collapsed-sidebar state; direct-route checks succeeded.

`docs/figures/anomaly_research_browser.png` records the in-app browser view. The
browser session was interrupted during final screenshot repositioning. No full
keyboard, screen-reader, dedicated desktop/mobile or 200% zoom audit is claimed.
Those checks and any further visual refinement remain review work, not a claim
that the model is ready for operations.

## Performance actually measured

Local measurements with the actual pinned bundle, five warm repetitions:

- Initial verified/cached load: approximately 0.54 seconds in the first benchmark.
- Warm verified load median: approximately 0.018 seconds.
- Pure view preparation plus two chart builds: approximately 0.018 seconds median.
- ZIP generation: approximately 0.009 seconds; default ZIP approximately 56 KB.
- Four parsed frames: 10,022,258 bytes using pandas deep-memory accounting.
- Separate tracemalloc load run: 41,585,216-byte Python allocation peak.
- Process high-water RSS: approximately 395 MiB, including imports, cache, chart
  objects and prior allocations; not a standalone bundle-memory measurement.

These are local observations, not cloud guarantees. Tracemalloc excludes untraced
native allocations. Cache argument hashing and validation still read approved
bytes on every interaction. Full-history table/plot density, concurrent sessions,
long expanded provenance and exports need deployment-tier review before hosting.
No cloud benchmark or deployment occurred.

## Local launch and acceptance checklist

```sh
python -m streamlit run streamlit_app.py --server.port 8514
```

Open `/anomaly-research`. Optionally configure server-side `URBANFLOW_RESEARCH_ROOT`
to an installed checkout with the same pinned artifacts; it is independent of
`URBANFLOW_DATA_BACKEND` and has no database/API fallback.

- Confirm exact experimental label and NO-GO on page and in ZIP metadata.
- Select Calendar Median / Rail / 2021-06-04 / Below expected; inspect low actual
  deviation and positive centered score, prior dates, episode and health evidence.
- Filter to no candidates and verify full curves and health remain available.
- Change each optional case flag and inspect its stored evidence.
- Verify table selection/fallback, search/export membership and stale-selection reset.
- Inspect warning/unknown health, legends, narrow-screen table scrolling and focus.
- Recheck original three pages; do not infer production readiness from any clear state.

## Remaining limitations and handoff

Only the reviewed immutable version is supported; a new version requires catalog,
schema and lineage review. The interface preserves the existing frozen expected
values and heuristic urgency, without claiming those heuristics are operationally
validated. Browser native table find/sort is display-only; the explicit Search
cases control determines ZIP membership. Exports are prepared on request and must
be prepared again after changing controls. No review ledger or live freshness
monitor exists. Publication timing and research-generation time remain unknown
where original metadata lacks them. Further UI/accessibility review can continue
later; do not proceed to 4C.2, deployment or operational integration automatically.

Exercise: in `anomaly_research_views.py`, inspect where `primary(bundle.daily)`
and `primary(bundle.health)` are evaluated before candidate filtering. Add a local
test proving that a new candidate-only condition cannot change either context.

Submission review preserves generated Plotly HTML byte-for-byte. `.gitattributes`
excludes bundled HTML/third-party JavaScript from whitespace-only diagnostics;
source-code whitespace checks remain enabled. Local agent configuration is not
included in the project commit.
