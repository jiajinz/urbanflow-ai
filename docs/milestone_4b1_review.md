# Milestone 4B.1 Review — Architecture and Data Access

This document covers Chicago Transit Authority (CTA) ridership data and analysis.

## Scope and current status

4B.1 is complete for owner review. Work stops at architecture, evidence mapping,
analytical data access, export/loading, and calculation consistency. Full-page
acceptance (4B.2), UI/portfolio polishing (4B.3), AI reporting, and deployment are
not included and must not proceed without new explicit authorization.

The scope revision arrived after full page/chart drafts had already been written.
Those files are preserved rather than deleted or unnecessarily rewritten:
`streamlit_app.py`, `app_pages/`, `dashboard_ui.py`, `dashboard_charts.py`, and
`tests/test_dashboard.py`. Their smoke-test results are regression evidence only,
not UI acceptance. Desktop/mobile review and current portfolio screenshots are
unfinished. The README's earlier whole-milestone completion wording and missing
screenshot reference have been corrected. No commit or push has been performed.

## Reviewed evidence and selected findings

The source archive contains 9,374 dates, 2001-01-01–2026-08-31, without source-date
gaps or duplicates. Existing strict validation quarantines July 2012's 31
07:00 timestamps, leaving 9,343 validated rows. The latest year is incomplete.
The actual local PostgreSQL table was read and confirmed to have the same 9,343
rows and bounds; a read-only comparison matched all six snapshot analytical tables.

Selected primary findings from `docs/insight_report.md`:

- Day types differ: complete 2025 equal-month 2019-based total recovery indices
  are 70.90 W, 88.10 A, and 89.29 U. Proposed monthly lines and grouped comparisons
  support separate weekday and weekend/holiday planning investigations.
- Modes differ: complete 2025 weekday bus/rail indices are 81.63 and 59.36,
  a 22.28-point gap. The 2017–2019 baseline still gives a 21.67-point gap.
  Proposed baseline controls and mode lines expose this sensitivity.
- Composition shifts persist under fixed 2019 weights: January–August 2026 bus
  share is 58.98%, versus 51.88% in 2019. Matched-period evidence should be shown
  independently of the selected recovery denominator.

Baseline sensitivity and seasonal patterns are interpretation controls, not new
causal explanations. U includes holidays. Neither calendar standardization nor
same-month matching is formal seasonal adjustment. Route/service-supply analysis,
causal attribution, event explanation, and outlier-exclusion sensitivity remain
unfinished. The complete mapping to metrics, visualizations, interactions,
limitations, and planning implications is in `dashboard_spec.md`.

## Architecture and rationale

The planned Streamlit router uses supported `st.navigation` / `st.Page` navigation.
Presentation calls pure view models rather than executing SQL. Data access owns
backend selection and integrity checks; `research.py` and existing SQL own metric
definitions. This separates numerical correctness from UI behavior and keeps
future reporting consumers independent of Streamlit.

`AnalyticalData` holds daily, monthly, recovery, annual, periods, and composition
tables plus metadata. It is an in-memory data container, not an immutable database.
Export therefore independently recomputes derived tables before accepting it.
Keeping six small tables duplicates some stored values but gives a public demo
fast, offline access to transparent, versioned results. DuckDB reuses the analytical
SQL offline; PostgreSQL parity checks mitigate dialect divergence.

## Function-level data access contract

- `load_data(backend, directory)` returns one `AnalyticalData` object. Only snapshot
  and postgres are supported. There is no implicit backend fallback.
- `load_postgres()` accepts connection configuration through existing DATABASE_URL.
  It reads validated daily records and the existing monthly SQL in one read-only
  repeatable-read transaction, then calls the shared 4A transformations. Empty
  data and driver failures produce safe `DataAccessError` messages. Unknown source
  retrieval/publication time and quarantine counts remain unknown.
- `load_archive(directory)` checks the original 4A Parquet hash/provenance, validates
  daily rows, and rebuilds analytical tables with the 4A definitions. It does not
  require a running database or network.
- `export_bundle(data, directory)` rejects existing destinations and empty data.
  It recomputes every analytical table from validated daily rows and compares all
  six tables before writing. Inconsistent values fail before publication. Six
  Parquet files and a manifest are staged, checked with the public loader, then
  renamed into a new version directory.
- `load_bundle(directory)` verifies schema, provenance fields, timestamp, file
  hashes, SQL/analytical definition hashes, and validated daily coverage. It reads
  the precomputed tables without an API/database request. Missing/corrupt/stale
  bundles raise actionable errors. A checksum detects byte changes; it does not
  authenticate a publisher or independently verify CTA measurement accuracy.

The current bundle is `data/dashboard/cta-2026-11-01-v2`. Its version name follows
the source research date; the manifest's actual generation timestamp is UTC and
can fall on a different calendar date. Keep source retrieval, export generation,
database read, and service dates distinct.

## Reproduce data access without implementing pages

```sh
python -m urbanflow_ai.dashboard_data export \
  --archive data/history/cta-2026-11-01-v1 \
  --output /tmp/urbanflow-4b1-bundle

# Optional local database export; requires exported DATABASE_URL.
python -m urbanflow_ai.dashboard_data export --postgres \
  --output /tmp/urbanflow-4b1-postgres-bundle
```

Public use selects the Parquet backend and needs no local database credentials.
Local use explicitly selects PostgreSQL. Snapshot analytical definitions changing
requires a new version, not a checksum bypass. No dependencies were added during
the revised 4B.1 scope; existing earlier dependency changes are preserved.

## Files and change attribution

Existing 4B.1 foundations retained from before the scope revision:

- `src/urbanflow_ai/dashboard_data.py`, `dashboard_metrics.py`, and shared 4A modules.
- `data/dashboard/cta-2026-11-01-v2/`: six Parquet tables and manifest.
- `tests/test_dashboard_data.py`, `tests/test_dashboard_metrics.py`.
- `docs/dashboard_spec.md` and `.env.example` backend instructions.

Changes made after the scope revision:

- `dashboard_data.py`: reject inconsistent derived tables before export.
- `test_dashboard_data.py`: inconsistent export, complete archive parity, empty
  PostgreSQL behavior, and isolated PostgreSQL adapter integration coverage.
- `test_dashboard_metrics.py`: compare all five derived tables against archived
  4A CSV results, rather than only recovery rows.
- `dashboard_spec.md`, `dashboard_development.md`, `README.md`: distinguish current
  scope, preserved drafts, and future acceptance; remove the nonexistent screenshot embed.
- This review record.

Earlier ingestion/database/research changes and untracked data artifacts already
existed before this revised instruction. They are not claimed as new 4B.1 edits.
No UI/chart/router code was changed after the scope revision.

## Actual verification

- Data access and analytical contracts without test-database configuration:
  **23 passed, 1 PostgreSQL integration test skipped**.
- Complete suite with the separate test database configured:
  **175 passed**.
- The new integration test uses a temporary table in TEST_DATABASE_URL and compares
  all six adapter outputs against shared analytical calculations. It does not
  alter application tables.
- Five derived snapshot tables match archived 4A research CSVs; rebuilding from
  the validated archive matches all six snapshot tables. Both baseline findings
  are checked numerically.
- Tests include empty data/selections, invalid filters, partial periods, missing
  dates, rolling windows, integrity/version failures, publication rejection, and
  sanitized backend failure without fallback. Ordinary tests do not call CTA.
- `git diff --check` passed. Restricted local files are not tracked. UI tests are
  preserved regression checks and do not establish visual/accessibility acceptance.

## Remaining work and stop condition

4B.2, only after explicit approval: review the preserved page drafts against this
specification, confirm navigation/filter semantics and calculation traceability,
and decide what to retain or revise. Passing existing tests alone does not accept
these drafts.

4B.3, only after later approval: complete desktop/mobile and accessibility review,
polish visual hierarchy, capture actual screenshots, and finalize portfolio docs.
Cloud deployment and AI reporting remain separate, unimplemented work.

This phase ends with the 4B.1 review. No later phase starts automatically.

## Engineering exercise

In a Python session, load the bundle, increase one monthly `bus_daily` value, and
attempt to export to a fresh temporary directory. Export must raise DataAccessError
and leave the destination unpublished. Reload the original bundle and export again:
that should succeed. This demonstrates why data validation, analytical consistency,
and file checksums are separate guarantees. Never modify the versioned source files
for the exercise.
