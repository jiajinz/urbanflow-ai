# Research Execution and Debugging Notes

This document covers Chicago Transit Authority (CTA) ridership data and analysis.

## Extraction entry point

`python -m urbanflow_ai.history --output NEW_DIRECTORY --quarantine-rejections`
calls `history.main()`, which parses the output directory and opt-in quarantine
policy, then calls `backfill()`.

`fetch_history()` discovers the source's bounds and row count using
`source_coverage()`. It requests each page through `request_page()` with a stable
`service_date ASC, :id ASC` order. On the archived run, ten data pages covered 9,374
source rows; the last page was shorter than the 1,000-row limit. A count-bound loop
prevents endless page requests. Bounds/count changes or page failures abort before
validation or database writes. The latest-100 and explicit-date-range ingestion
interfaces retain their prior behavior and tests.

`request_page()` returns a decoded JSON list. Transient HTTP/transport failures
receive at most three retries. Permanent HTTP errors or malformed JSON raise
`IngestionError`. `with urlopen(...)` closes the response even if reading fails.
Retry delays are bounded, so a large server Retry-After cannot suspend the process
indefinitely. Timeouts apply per attempt, not to the entire backfill.

## Validation and persistence

`backfill()` passes the unmodified list to `processing.process_records()`. That
function returns immutable accepted/rejected records, reserving dates only for
accepted rows. No historical relaxation was added to the parser. July 2012's actual
07:00 timestamps therefore enter quarantine. Date-prefix conversion in the raw
calendar audit is diagnostic only; it does not make those records valid.

Without the quarantine flag, any rejection stops writes. With it, only accepted
records reach `database.persist_records()`. Duplicate dates always require review.
The existing transaction and `ON CONFLICT ... DO UPDATE ... WHERE ... IS DISTINCT
FROM` preserve idempotence. A second actual run changed zero records. A bounded
readback checks that database values equal the validated source, then new files
are staged and renamed into an immutable output directory.

If database writing succeeds but readback or file publication fails, the database
transaction has already committed. No artifact success should be inferred. Rerun
idempotently with a new output directory after diagnosing the failure; there is no
distributed transaction spanning PostgreSQL and the filesystem.

## SQL aggregation

`research.monthly_aggregates(frame)` accepts validated daily rows and returns a
DataFrame with one row per observed month/CTA day type. It executes
`sql/research_monthly.sql` in DuckDB. Four placeholders receive the same half-open
date bounds twice: once for coverage and once for records. PostgreSQL uses `%s`;
DuckDB receives `?`. Data values are bound, not concatenated into SQL.

The `month_coverage` CTE groups dates before any W/A/U split. It compares calendar
row count against the month's actual number of days, including leap February.
The next query groups by month and `day_type`, returning sums, day counts, and
means. For example, `AVG(r.bus)` is the average bus boardings across that cell's
observed dates. A complete target month means every calendar date is validated;
this does not prove CTA's measurement accuracy.

The SQL returns no row for a wholly missing month. Matching and annual coverage
checks prevent such a gap from being treated as a valid adjacent comparison.
`verify_postgres_monthly()` executes the same SQL against a read-only repeatable
read transaction and compares all result cells, including dates and completeness.

## Python transformations

`recovery_indices(monthly)` accepts the SQL result and returns matched complete
post-2019 month/day-type rows for both baselines. It groups baseline cells by
month number and day type, requires every baseline year, merges with
`validate="many_to_one"`, and computes:

```python
joined[f"{mode}_index"] = joined[f"{mode}_daily"].div(joined[f"{mode}_baseline"].replace(0, np.nan)) * 100
```

The f-string selects each mode's column. `.replace(0, np.nan)` makes a zero
baseline unavailable rather than allowing infinity. `merge`'s validation catches
a duplicate denominator that would multiply rows. The 2025 W means of monthly
indices are bus 81.63 and rail 59.36; their difference is 22.28 percentage points.
This is not a 22.28 percent increase in actual bus boardings.

`standardized_periods()` equally averages monthly indices and records the number
of months. Twelve-month 2025 and eight-month 2026 summaries have different seasonal
windows; use `matched_composition()` for matched-period comparisons. That function
multiplies each monthly/day-type daily mean by the same 2019 day count. Its weighted
values are accounting estimates, not actual observed boardings.

`monthly_changes()` joins complete same-type monthly means to the immediately
prior month and prior-year month by shifted dates. It cannot bridge missing months.
`annual_summary()` preserves observed totals but suppresses YoY when either year
is incomplete or the years are not adjacent.

`moving_block_interval(values)` takes an ordered, finite monthly contrast vector
and returns two percentile endpoints. Seeded NumPy draws select consecutive
circular blocks; the calculation averages the resulting sampled months. The
three/six-month lengths are sensitivity choices. `persistence_analysis()` and
`day_type_contrasts()` suppress intervals across missing months rather than
pretending those observations are adjacent. These intervals do not establish
causality or account for reporting error and nonstationarity.

`unusual_observations()` returns review candidates with same-cell medians, MAD,
and modified z scores. The actual March 15, 2025 Saturday count of 1,038,464 is
47.98% above its cell median, but no event attribution is made. Small cells can
make MAD unstable, so candidates are retained in all primary metrics.

## Artifact and plotting boundaries

`run_research()` verifies the input Parquet checksum, validates rows again,
computes tables, and writes CSVs plus a provenance manifest to a new directory.
It requires no network by default. `research_plots.build_figures()` reads those
CSVs and returns five Plotly figures; its CLI writes HTML and JSON specifications.
It does not fetch data, write to PostgreSQL, or change the analytical method.

## What verification proves

- Unit tests exercise pagination, retry limits, quarantine policy, date coverage,
  matching, baseline weights, incomplete periods, zero denominators, reproducible
  intervals, and unsupported hypotheses with synthetic fixtures.
- Real PostgreSQL integration tests isolate temporary schemas/tables. They verify
  driver/SQL behavior, constraints, rollback, and engine parity. They are opt-in
  through a separate `TEST_DATABASE_URL`.
- Live extraction is an observed source audit, not a deterministic test. It proves
  what the endpoint returned during this extraction, not future availability.
- HTML visual review checks rendering and labels, not analytical correctness.

## Hands-on exercise

1. Copy the archived Parquet into memory and remove one date from February 2024.
2. Run `monthly_aggregates()` and inspect February's `complete_month` flags.
3. Run `recovery_indices()`: February 2024 should be excluded for all day types.
4. Run `annual_summary()` with a fresh `coverage_details()` audit: 2024 YoY and
   2025 YoY should both be unavailable because one side is incomplete.
5. Restore the date and reproduce the original CSVs in a new temporary directory.

Do not overwrite the versioned archive or change production data for this exercise.
