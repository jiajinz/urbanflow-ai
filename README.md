# UrbanFlow AI

UrbanFlow AI is an urban mobility data automation portfolio project. It currently
fetches CTA daily ridership JSON and converts it into typed, validated records
with an explicit data quality summary and optional transactional PostgreSQL persistence.
The runtime driver is psycopg 3 (binary distribution for local development).

## Data Source

The [Chicago CTA Daily Boarding Totals dataset](https://data.cityofchicago.org/Transportation/CTA-Ridership-Daily-Boarding-Totals/6iiy-9s97)
provides systemwide daily bus and rail boardings. The public JSON endpoint is
`https://data.cityofchicago.org/resource/6iiy-9s97.json`; authentication is not
required. Fields are `service_date`, `day_type`, `bus`, `rail_boardings`, and
`total_rides`. Day types are W (weekday), A (Saturday), and U (Sunday/holiday).

## Architecture

- `ingestion.py`: standard-library HTTP requests, JSON decoding, and response
  validation. `fetch_daily_boardings()` returns the original dictionaries and
  preserves the existing fail-fast validation behavior by default.
- `processing.py`: pure conversion into immutable `BoardingRecord` objects;
  `process_records()` returns accepted records, indexed rejections, and counts
  through `ProcessingResult`. It does not mutate input or perform network I/O.
- `pipeline.py`: calls ingestion with `validate_records=False`, then processing,
  allowing record errors to be collected without duplicating HTTP logic. The CLI
  writes only when `--persist` is supplied; `run_pipeline()` still returns a
  `ProcessingResult` without database access.
- `database.py`: environment-based connections, schema initialization, parameterized
  upserts, atomic batch transactions, and committed persistence counts.

Requests select the latest 100 rows with `$order=service_date DESC`. Override the
endpoint using `endpoint=` or `CTA_BOARDINGS_API_URL`; other query parameters are
preserved. The default timeout is 10 seconds.

## Installation

Use Python 3.11 or newer:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

## Usage

Run the complete pipeline from the repository root:

```sh
python -m urbanflow_ai.pipeline
```

The output includes fetched, valid, rejected, and duplicate counts, plus the
accepted date range. It does not print individual records. Systemic failures
propagate and produce a nonzero exit status.

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

## Testing

```sh
python -m pytest
```

Default unit tests use deterministic fixtures and mock HTTP/driver calls; they
require no network access. Integration tests skip unless `TEST_DATABASE_URL` is set.
They cover ingestion failures, conversion, missing/null fields, invalid values,
consistency, duplicate conflicts, schema failures, and pipeline integration.

## Limitations and Future Development

Only the latest 100 records are fetched. There is no pagination, retry policy,
dashboard, AI reporting, or cloud deployment. Validation does not detect missing
calendar days or verify holiday classification. Historical backfills require
pagination. Schema initialization does not migrate existing tables. Counts must
fit PostgreSQL INTEGER (0 through 2,147,483,647); larger Python integers are rejected
by PostgreSQL and roll back the batch. Writes use one statement per accepted record.
There is no connection pool, automatic retry, or correction history. Concurrent
writers can change the table after the reported count was observed. A connection
loss during commit can leave its outcome uncertain; rerunning is idempotent.


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
and no highest-day row. These queries run in a SQL client; the Python module currently
exposes persistence and total count, not a general query API.
