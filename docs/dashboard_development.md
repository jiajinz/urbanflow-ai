# Dashboard Development, Debugging, and Deployment Preparation

This document covers Chicago Transit Authority (CTA) ridership data and analysis.

## Application scope

The application implements Executive Overview, Ridership Explorer, and Research &
Methodology. It runs locally from a versioned historical snapshot by default.
Public deployment and AI reporting are future work. Historical review records
capture verification at specific points; they are not current test results or
proof of comprehensive responsive or accessibility coverage.

## Run locally

Use Python 3.11 (the development environment uses 3.11.9):

```sh
python -m pip install -e '.[test]'
python -m streamlit run streamlit_app.py
```

The default snapshot includes 9,343 validated days, 2001-01-01–2026-08-31. No network
or database is needed to explore it. PostgreSQL mode is opt-in with
`URBANFLOW_DATA_BACKEND=postgres` and an exported `DATABASE_URL`. Do not expose a
local database publicly to support the demo. The public app never queries CTA.

## Function-level execution flow

1. `streamlit_app.main()` sets page configuration and registers three page files
   using `st.Page`. `st.navigation(...).run()` executes the selected page.
2. A page file calls `dashboard_ui.executive_overview()`, `ridership_explorer()`,
   or `research_methodology()`. Streamlit reruns the entrypoint/page after widget
   interactions. Widget state survives reruns through stable keys.
3. `dashboard_ui.dataset()` reads explicit backend configuration and invokes
   `cached_data(backend, directory, version)`. The manifest modification time is
   part of the snapshot cache key. Results expire after 300 seconds; refresh clears
   the data cache. `DataAccessError` produces an actionable error and stops output.
4. `dashboard_data.load_data()` chooses exactly one backend. `load_bundle()` checks
   six file hashes, analytical version hashes, schema, provenance, and coverage,
   then returns `AnalyticalData`. It never calls PostgreSQL or the API.
   `load_postgres()` reads daily records and existing monthly SQL under one read-only
   repeatable-read transaction, then applies the same 4A Python transformations.
   Connection/SQL errors are sanitized and never select another backend.
5. `dashboard_metrics.executive_model(data, baseline)` returns the latest complete
   year, four metrics, three computed findings, and supporting tables. It returns
   `None` when a complete supported comparison is unavailable. For the archive,
   2025 weekday recovery is 70.90 and the bus-minus-rail gap is 22.28 points.
6. Explorer constructs an immutable `ExplorerFilter`. Dates use Python `date`;
   the UI's inclusive end becomes `end + timedelta(days=1)` for half-open logic.
   Empty category/year tuples mean an empty selection, not "all." Invalid filters
   raise `ValueError`. Changing the date window resets available comparison years.
7. `selected_daily()` filters date, day type, year, and mode availability.
   `selected_monthly()` requires an entire selected complete calendar month.
   Recovery uses precomputed full-history baseline denominators, so restricting
   the target to 2025 does not erase its 2019 reference.
8. `explorer_series()` returns tidy plotted rows with explicit null gaps. Monthly
   and seasonal views use same-type daily means; yearly views require twelve
   complete months and return observed-day-weighted daily means. Daily averages
   reuse existing SQL windows for bus/rail/total and are suppressed unless all
   seven calendar dates are observed and selected.
9. `dashboard_charts` renders those rows with Plotly; it has no SQL or statistical
   formulas. `st.plotly_chart()` embeds the interactive figure in the page.

## Streamlit versus Plotly

Streamlit provides the Python application runtime, navigation, controls, state,
and layout. Plotly supplies figures, hover details, zoom, and legends. A Plotly
figure does not implement application navigation or data access. The separation
lets the same metric models serve tests, exports, future reports, and another UI.

For example, the actual analytics formula in `research.recovery_indices()` is:

```python
joined[f"{mode}_index"] = joined[f"{mode}_daily"].div(joined[f"{mode}_baseline"].replace(0, np.nan)) * 100
```

The f-string selects each mode's columns; the vectorized division applies to every
matched cell. Replacing a zero denominator with NaN prevents an infinite recovery
claim. This calculation belongs in research logic, not inside a Streamlit page.

## Snapshot generation

```sh
python -m urbanflow_ai.dashboard_data export \
  --archive data/history/cta-2026-11-01-v1 \
  --output /tmp/urbanflow-dashboard-review
URBANFLOW_SNAPSHOT_DIR=/tmp/urbanflow-dashboard-review \
  python -m streamlit run streamlit_app.py
```

`load_archive()` validates the original 4A hash and records its provenance;
`build_analytical_data()` reuses 4A definitions; `export_bundle()` stages six
Parquet tables and a manifest, exercises the public loader, then renames the staged
directory into a new version. Existing versions cannot be overwritten. Before export, all six tables are compared
with a fresh calculation from validated daily data; inconsistent derived values
are rejected before publication. Exporting
with `--postgres` instead reads local data; unknown source retrieval/quarantine
metadata stays unknown. Generation/read time is not source publication time.

Analytical source/SQL changes invalidate a bundle. Generate and review a fresh
version, update the explicit default path, and rerun tests before publication.
Do not edit a checksum merely to bypass a validation failure.

## PyCharm debugging

Create a Python Run/Debug configuration with module name `streamlit`, parameters
`run streamlit_app.py --server.headless true`, project root as working directory,
and the project's `.venv` interpreter. Choose Debug and open the reported local URL.
For PostgreSQL mode, configure the two environment variables locally; `.env` is
not automatically loaded and must never be committed.

Set breakpoints in `dashboard_ui.ridership_explorer()` after filter creation and
in `dashboard_metrics.selected_monthly()`. Inspect `filters`, `table.complete_month`,
month starts/ends, and the resulting mask. Use a new browser session or the sidebar
refresh button when diagnosing cached data. Pure functions can also be debugged
without Streamlit through their pytest cases.

Hands-on exercise: select January 2–31, 2025. Recovery should have no eligible
complete month, while Daily shows actual observations. Then include January 1 and
confirm the monthly comparison reappears. Select only W in Daily: the seven-day
calendar mean should be unavailable because weekends are excluded. Finally compare
2026 Yearly against Monthly: the partial year is unavailable in Yearly, but its
complete observed months are usable in Monthly.

## Tests and what they prove

```sh
python -m pytest -q
TEST_DATABASE_URL=postgresql:///urbanflow_ai_test python -m pytest -q
```

Unit tests use deterministic fixtures and checked-in snapshots. They verify
analytics, filtering, complete periods, both baselines, export integrity, error
boundaries, plotted outputs, and Streamlit page interactions. AppTest covers
application state/output; it does not prove responsive browser rendering.
Integration tests use isolated PostgreSQL tables/schemas and verify actual SQL,
transaction, and parity behavior. Live API availability is not a test dependency.
Browser review and a read-only full-table PostgreSQL/snapshot comparison provide
additional observed checks, separately from deterministic test counts.

## Screenshots

Store real screenshots in `docs/screenshots/`:

- `overview-desktop.jpg`: four 2025 recovery metrics and the recovery chart.
- `explorer-desktop.jpg`: visible filters, period, metric units, and a comparison.
- `methodology-desktop.jpg`: definitions and actual coverage.
- `overview-mobile.jpg`: narrow-layout review.

Run the app with the default bundle and 2019 baseline, open it at a desktop width
such as 1440 pixels, and capture actual rendering. Check a narrow mobile viewport
and navigation/sidebar accessibility. Do not use mockups or simulated statistics
as screenshot evidence. Re-capture after material visual or metric changes.

## Streamlit Community Cloud preparation

For a future deployment, connect the intended GitHub repository in Community Cloud, select
`streamlit_app.py` as the entrypoint, and select Python 3.11. Root `requirements.txt`
installs the project and its declared dependencies. Include `app_pages/`, packaged
SQL, and the default `data/dashboard/` bundle in the reviewed commit. No database
secrets are needed for default snapshot mode. Do not set the PostgreSQL backend
in public configuration.

Keep `.env`, `.idea/`, `AGENTS.md`, and `.streamlit/secrets.toml` ignored. Set a public
URL in README only after an actual deployment succeeds. Review Community Cloud's
current dependency/Python settings at deployment time:
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies

## Future AI reporting boundary

A future reporting layer can consume `AnalyticalData`, `executive_model()`, and
explicitly filtered explorer tables with their provenance and definitions. Keep
numerical computation in tested SQL/Python, and distinguish generated narrative
from observed evidence. The dashboard does not integrate an LLM, agent, or future forecast. Separate
retrospective anomaly research is implemented in `anomaly.py`; its candidates
are not confirmed incidents and are not displayed in the dashboard.


## Pipeline and database reference

The following operational details supplement the dashboard workflow. PostgreSQL
is optional for the default offline dashboard.

## Usage

Run the complete pipeline from the repository root:

```sh
python -m urbanflow_ai.pipeline
```

The output includes fetched, valid, rejected, and duplicate counts, plus the
accepted date range. It does not print individual records. Systemic failures
propagate and produce a nonzero exit status.

### Monthly, Quarterly, and Historical Loading

Supply both dates as `YYYY-MM-DD`. The start date is included and the end date is
excluded, so adjacent periods do not overlap. The following examples fetch October
2025, Q2 2026, and the first half of 2026:

```sh
python -m urbanflow_ai.pipeline --start-date 2025-10-01 --end-date 2025-11-01
python -m urbanflow_ai.pipeline --start-date 2026-04-01 --end-date 2026-07-01
python -m urbanflow_ai.pipeline --start-date 2026-01-01 --end-date 2026-07-01 --persist
```

Export DATABASE_URL before using `--persist` (see Local PostgreSQL Setup). Without
that flag, historical requests only fetch and validate. Repeating or overlapping
historical loads uses the same database upsert behavior as the default command.
A single month normally contains 28-31 daily rows, and a calendar quarter contains
90-92; requesting a quarter does not imply more than 100 rows.

The range summary reports expected calendar days and days without accepted records
in this request. Missing days can reflect unpublished source data, validation
rejections, or additional endpoint filters; they do not necessarily mean the API
request failed. Existing database rows are not used to calculate this coverage.
An empty source response is allowed and reports every requested day as missing.
As checked on November 1, 2026, the source's latest date was August 31, 2026;
September and October 2026 were not available. Source availability changes over time.

All pages are fetched before processing or database writes. If any page fails,
the pipeline raises and does not persist that partial fetch. Pagination ends on a
short page, including an empty final page when the count is an exact multiple of
100. Invalid or incomplete date bounds fail before any network request.

For direct Python use, supply `datetime.date` objects:

```python
from datetime import date
from urbanflow_ai.pipeline import run_pipeline

result = run_pipeline(start_date=date(2026, 4, 1), end_date=date(2026, 7, 1))
```

Use ingestion or processing independently:

```python
from urbanflow_ai import fetch_daily_boardings
from urbanflow_ai.processing import process_records

raw = fetch_daily_boardings(validate_records=False)
result = process_records(raw)
for rejection in result.rejected_records:
    print(rejection.index, rejection.service_date, rejection.errors)
```

For offline processing, pass a locally loaded JSON array to `process_records`.
To inspect an unmodified API sample locally:

```sh
curl --fail --get 'https://data.cityofchicago.org/resource/6iiy-9s97.json' \
  --data-urlencode '$limit=100' --data-urlencode '$order=service_date DESC' \
  --output cta-sample.json
python -m json.tool cta-sample.json
```

## Validation Rules

- All five source fields are required. Extra fields are ignored.
- Dates accept ISO `YYYY-MM-DD` or the observed midnight timestamp format,
  such as `2026-08-31T00:00:00.000`, and become Python `date` objects. Invalid
  dates, time zones, and non-midnight timestamps are rejected.
- Counts accept nonnegative Python integers or ASCII digit strings. Nulls,
  missing values, booleans, floats, decimal strings, and malformed values are
  rejected; no rounding or default-to-zero behavior is applied.
- `day_type` must be W, A, or U. Holiday calendars are not inferred.
- `total_rides` must equal `bus + rail_boardings`.
- The unique key is `service_date` at this dataset's systemwide daily grain.
  The first valid record wins; subsequent valid rows for the same date are
  rejected as identical or conflicting duplicates. Equal counts on different
  dates are legitimate repeated measurements. Invalid rows do not reserve keys.
- Each rejected row has a zero-based input index, a bounded source date context,
  and its first validation error. Raw records are not logged.
- Individual errors are collected while valid records continue. Network errors,
  invalid JSON, non-array responses, and nonempty batches with no object
  containing all required fields fail the pipeline. This last rule is an explicit
  schema-drift heuristic; empty input is allowed.

Duplicate count is a subset of rejected count. Duplicate classification occurs
only after field and integrity validation. Rejections reference the caller's
original array by index; retain that array when investigating or replaying rows.

If a local Python installation reports `CERTIFICATE_VERIFY_FAILED`, repair its
CA configuration (on python.org macOS installations, run the bundled
`Install Certificates.command`). Where appropriate, set `SSL_CERT_FILE` to a
trusted system CA bundle. Do not disable TLS certificate verification.

## Local PostgreSQL Setup

Use PostgreSQL 17 and Python 3.11+. Homebrew is the simplest option when already
installed; these commands work with both Intel and Apple Silicon Homebrew paths.
Check availability first with `command -v psql` and `brew list --versions postgresql@17`.
The [Homebrew formula](https://formulae.brew.sh/formula/postgresql@17) initializes
a default cluster during installation.

```sh
brew install postgresql@17
brew services start postgresql@17
export PATH="$(brew --prefix postgresql@17)/bin:$PATH"
pg_isready
createdb urbanflow_ai
cp .env.example .env
set -a
source .env
set +a
python -m urbanflow_ai.pipeline --persist
```

Run `createdb` once. The example uses a local Unix socket and the current macOS
user; it contains no password. `.env` is Git-ignored and is not loaded automatically
by Python. Export it in each terminal, or configure DATABASE_URL in your IDE run
configuration. Do not commit real connection strings. For a password-based server,
use `postgresql://USER:PASSWORD@HOST:5432/urbanflow_ai` with URL-encoded credentials.

If Homebrew is missing, install it using the instructions at [brew.sh](https://brew.sh/),
then run the commands above. Postgres.app is a GUI alternative; Docker is useful
when already configured but adds a container runtime and volume management.
Neither Docker nor a running PostgreSQL server is assumed by this project.

## Persistence and Schema

`daily_ridership` stores one systemwide record per service date, so `service_date`
is its DATE primary key. This key would need redesign for route- or station-level
data. `day_type` is non-null TEXT restricted to W/A/U. The three counts are non-null,
nonnegative INTEGERs. A CHECK enforces `total_rides = bus + rail_boardings`, matching
the existing validated data model. The check casts to BIGINT before addition to
avoid overflow in the expression. `updated_at` is a non-null TIMESTAMPTZ set by
PostgreSQL using the transaction start time.

`persist_records()` takes validated `BoardingRecord` objects and returns an immutable
`PersistenceResult`. It creates the table if absent, performs parameterized
`INSERT ... ON CONFLICT (service_date) DO UPDATE`, and reads the table count in one
transaction. On a conflicting date, EXCLUDED contains the proposed row. A distinctness
condition skips identical records and preserves their timestamp. Corrections replace
the existing values and refresh the timestamp. The summary reports a combined
inserted-or-updated count, a separate unchanged count, and total stored rows; it does
not claim to distinguish inserts from updates. Processing duplicates remain a
separate, within-batch metric.

The psycopg connection context commits on success, rolls back on exceptions, and
closes the connection. Safe `DatabaseError` messages omit server details and
credentials. No success summary is printed when persistence fails. Ingestion and
validation failures occur before opening a database connection.

## Database Tests

```sh
python -m pytest                         # All tests; integration skips without configuration
python -m pytest -m 'not integration'    # Offline unit tests only
createdb urbanflow_ai_test               # One-time setup
export TEST_DATABASE_URL=postgresql:///urbanflow_ai_test
python -m pytest -m integration          # Real PostgreSQL only
```

Use a separate disposable test database and a role allowed to create schemas.
Each integration case creates a unique schema and drops it in a finally block;
it does not truncate application tables. A configured but unavailable server fails
tests rather than silently skipping. Tests verify real upserts, unchanged timestamps,
corrections, constraints, and rollback of an earlier successful write in a failed
batch. Offline mocks verify driver calls, context handling, failure messages, commit
failure handling, and explicit CLI persistence; they do not prove PostgreSQL behavior.
No test makes a live CTA API request.

## SQL Inspection

Open `psql "$DATABASE_URL"` after exporting the environment, or configure a PostgreSQL
data source in a SQL client. In PyCharm editions with Database Tools, add a PostgreSQL
data source with the same database/user/host settings, download its driver if prompted,
test the connection, and open a query console. For the example Unix socket setup,
`psql` is simplest; a JDBC client may require localhost and explicit role credentials.

```sql
-- Count all stored service dates.
SELECT COUNT(*) FROM daily_ridership;

-- Inspect the most recent ten dates.
SELECT * FROM daily_ridership ORDER BY service_date DESC LIMIT 10;

-- Average daily bus and rail boardings over the stored dates.
SELECT AVG(bus) AS average_daily_bus FROM daily_ridership;
SELECT AVG(rail_boardings) AS average_daily_rail FROM daily_ridership;

-- Select one highest-ridership day; resolve ties by the latest date.
SELECT * FROM daily_ridership
ORDER BY total_rides DESC, service_date DESC LIMIT 1;
```

Averages cover stored dates only, not missing days. Empty tables return NULL averages
and no highest-day row. These inspection examples run in a SQL client. Dedicated Python analytics and
research modules now expose reusable parameterized analytical queries.


### Ingestion and persistence contracts

Without date bounds, ingestion selects the latest 100 rows ordered by
`service_date DESC`. Supplying both bounds selects a half-open range with
100-row pages ordered by `service_date ASC, :id ASC`. Range mode owns `$limit`,
`$offset`, and `$order`; it combines existing `$where` predicates with the date
filter and preserves other query parameters. Use the raw resource schema rather
than aggregate/projection queries. The default per-request timeout is 10 seconds.
Override the endpoint with `endpoint=` or `CTA_BOARDINGS_API_URL`.

The original latest/range ingestion does not retry. The dedicated history loader
allows four attempts for explicitly allowed transient transport errors and HTTP
408/429/5xx responses, with exponential delays and a 30-second cap on numeric
Retry-After. Permanent HTTP errors and malformed responses are not retried.
All pages are fetched before processing or writes, so a later-page failure does
not persist a partial fetch. Bounds/count checks cannot detect every in-place
source revision; offset pagination is not a source transaction.

All fetched rows remain in memory and persistence uses one transaction and one
statement per accepted record. There is no connection pool, correction history,
or automatic database retry. Very large backfills may require batching and
resumability. Schema initialization creates missing tables but does not migrate
existing schemas. Counts must fit PostgreSQL INTEGER; larger Python integers
cause persistence failure and rollback. Concurrent writers can change the table
after a reported count. Connection loss during commit can leave the outcome
uncertain; rerunning the same validated records is idempotent.

PostgreSQL mode uses read-only consistent analytical queries. It does not infer
source publication/retrieval times or quarantine counts from database rows.
Unset `URBANFLOW_DATA_BACKEND` or set it to `snapshot` to restore offline mode;
restart after changing environment configuration. Cached data expires after five
minutes. The sidebar refresh reloads the selected backend without calling CTA.
