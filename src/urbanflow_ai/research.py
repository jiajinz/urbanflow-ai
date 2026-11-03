"""Reproducible historical research calculations, separate from extraction and plots."""

import argparse
import hashlib
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from .analytics import SQL_DIRECTORY
from .data_access import validate_frame
from .history import coverage_details

MODES = ("bus", "rail", "total")
BASELINES = {"2019": (2019,), "2017-2019": (2017, 2018, 2019)}


def monthly_aggregates(frame: pd.DataFrame) -> pd.DataFrame:
    """Execute versioned SQL on validated daily data; emit month/day-type means."""
    clean = validate_frame(frame)
    if clean.empty:
        raise ValueError("Historical research requires nonempty validated data")
    first, last = clean.service_date.min(), clean.service_date.max()
    from datetime import timedelta
    bounds = (first, last + timedelta(days=1)) * 2
    sql = SQL_DIRECTORY.joinpath("research_monthly.sql").read_text().replace("%s", "?")
    with duckdb.connect(":memory:") as connection:
        connection.register("clean", clean)
        connection.execute("CREATE TABLE daily_ridership AS SELECT * REPLACE(CAST(service_date AS DATE) AS service_date) FROM clean")
        monthly = connection.execute(sql, bounds).fetchdf()
    monthly["month"] = pd.to_datetime(monthly["month"])
    monthly["year"] = monthly.month.dt.year
    monthly["month_number"] = monthly.month.dt.month
    return monthly


def recovery_indices(monthly: pd.DataFrame, baselines=None) -> pd.DataFrame:
    """Compare same calendar month/day type to complete pre-pandemic years.

    Multiyear denominators equally weight baseline years' daily averages. A
    missing baseline cell yields no comparison; it is never treated as zero.
    """
    definitions = BASELINES if baselines is None else baselines
    complete = monthly.loc[monthly.complete_month].copy()
    outputs = []
    for label, years in definitions.items():
        if not years or any(year >= 2020 for year in years):
            raise ValueError("Baseline years must be nonempty and pre-pandemic")
        base = complete[complete.year.isin(years)]
        means = base.groupby(["month_number", "day_type"]).agg(
            **{f"{mode}_baseline": (f"{mode}_daily", "mean") for mode in MODES},
            baseline_years=("year", "nunique"),
        ).reset_index()
        means = means[means.baseline_years == len(set(years))]
        joined = complete.merge(means, on=["month_number", "day_type"], how="inner", validate="many_to_one")
        joined = joined[joined.year >= 2020].copy()
        joined["baseline"] = label
        for mode in MODES:
            joined[f"{mode}_index"] = joined[f"{mode}_daily"].div(joined[f"{mode}_baseline"].replace(0, np.nan)) * 100
        joined["bus_minus_rail_pp"] = joined.bus_index - joined.rail_index
        outputs.append(joined)
    return pd.concat(outputs, ignore_index=True) if outputs else pd.DataFrame()


def annual_summary(monthly: pd.DataFrame, coverage: dict) -> pd.DataFrame:
    """Annual observed totals; YoY exists only for adjacent complete years."""
    totals = monthly.groupby("year")[[f"{mode}_total" for mode in MODES]].sum().reset_index()
    complete = {entry["year"]: entry["complete"] for entry in coverage["annual"]}
    totals["complete_year"] = totals.year.map(complete)
    for mode in MODES:
        prior = totals[f"{mode}_total"].shift()
        valid = totals.complete_year & totals.complete_year.shift(fill_value=False) & totals.year.diff().eq(1)
        totals[f"{mode}_yoy_pct"] = ((totals[f"{mode}_total"] / prior.replace(0, np.nan) - 1) * 100).where(valid)
    return totals


def monthly_changes(monthly: pd.DataFrame) -> pd.DataFrame:
    """Same-type daily-average changes, only across complete calendar months."""
    current = monthly[monthly.complete_month].copy()
    for label, offset in (("mom", 1), ("yoy", 12)):
        prior = current[["month", "day_type"] + [f"{mode}_daily" for mode in MODES]].copy()
        prior["month"] = prior.month + pd.DateOffset(months=offset)
        prior = prior.rename(columns={f"{mode}_daily": f"{mode}_prior_{label}" for mode in MODES})
        current = current.merge(prior, on=["month", "day_type"], how="left", validate="one_to_one")
        for mode in MODES:
            current[f"{mode}_daily_{label}_pct"] = (current[f"{mode}_daily"] / current[f"{mode}_prior_{label}"].replace(0, np.nan) - 1) * 100
    return current


def standardized_periods(indices: pd.DataFrame) -> pd.DataFrame:
    """Equal-month recovery means within each year and day type.

    Report month count explicitly. YTD comparisons must use matched months;
    these rows are descriptive annual summaries, not annual totals.
    """
    return indices.groupby(["baseline", "year", "day_type"]).agg(
        months=("month_number", "nunique"),
        **{f"{mode}_index": (f"{mode}_index", "mean") for mode in MODES},
        bus_minus_rail_pp=("bus_minus_rail_pp", "mean"),
    ).reset_index()


def moving_block_interval(values, *, seed=42, repetitions=5000, block_length=3):
    """Circular moving-block bootstrap interval for a monthly mean contrast.

    Resample consecutive months to retain short-range dependence. This is a
    descriptive sensitivity interval conditional on these periods, not a causal
    interval or a population sampling model for census boarding counts.
    """
    values = np.asarray(values, dtype=float)
    if len(values) < 2 * block_length or not np.isfinite(values).all():
        raise ValueError("At least two complete finite blocks are required")
    rng = np.random.default_rng(seed)
    count = int(np.ceil(len(values) / block_length))
    starts = rng.integers(0, len(values), size=(repetitions, count))
    positions = (starts[:, :, None] + np.arange(block_length)) % len(values)
    sampled = values[positions.reshape(repetitions, -1)[:, :len(values)]].mean(axis=1)
    low, high = np.quantile(sampled, [.025, .975])
    return float(low), float(high)


def persistence_analysis(indices: pd.DataFrame) -> pd.DataFrame:
    """Within-day-type bus-minus-rail paired monthly contrasts since 2022."""
    results = []
    for (baseline, kind), subset in indices[indices.year >= 2022].groupby(["baseline", "day_type"]):
        subset = subset.sort_values("month")
        # Bootstrap only a continuous run; gaps would create false adjacency.
        periods = subset.month.dt.to_period("M")
        continuous = len(periods) == len(pd.period_range(periods.min(), periods.max(), freq="M"))
        values = subset.bus_minus_rail_pp.to_numpy()
        for block in (3, 6):
            low, high = moving_block_interval(values, block_length=block) if continuous and len(values) >= 2 * block else (np.nan, np.nan)
            results.append(dict(baseline=baseline, day_type=kind, first_month=str(periods.min()), last_month=str(periods.max()),
                                months=len(values), positive_months=int((values > 0).sum()),
                                mean_gap_pp=float(values.mean()), median_gap_pp=float(np.median(values)),
                                block_months=block, interval_low_pp=low, interval_high_pp=high))
    return pd.DataFrame(results)


def day_type_contrasts(indices: pd.DataFrame) -> pd.DataFrame:
    """Paired monthly weekend-service minus weekday-service recovery gaps."""
    outputs = []
    for baseline, subset in indices[indices.year >= 2022].groupby("baseline"):
        wide = subset.pivot(index="month", columns="day_type", values="total_index").dropna()
        continuous = len(wide) == len(pd.period_range(wide.index.min(), wide.index.max(), freq="M")) if len(wide) else False
        for kind in ("A", "U"):
            if kind not in wide or "W" not in wide:
                continue
            values = (wide[kind] - wide.W).to_numpy()
            for block in (3, 6):
                low, high = moving_block_interval(values, block_length=block) if continuous and len(values) >= 2 * block else (np.nan, np.nan)
                outputs.append(dict(baseline=baseline, contrast=f"{kind} minus W", months=len(values),
                                    positive_months=int((values > 0).sum()), mean_gap_pp=float(values.mean()),
                                    block_months=block, interval_low_pp=low, interval_high_pp=high))
    return pd.DataFrame(outputs)


def matched_composition(monthly: pd.DataFrame, latest_year: int) -> pd.DataFrame:
    """Standardize all periods to 2019 day-type counts in the latest observed months.

    Calendar composition is held fixed within month/day type. Missing cells
    suppress the year; observed total shares are retained for comparison.
    """
    complete = monthly[monthly.complete_month]
    months = sorted(complete.loc[complete.year == latest_year, "month_number"].unique())
    weights = complete[(complete.year == 2019) & complete.month_number.isin(months)][["month_number", "day_type", "service_days"]].rename(columns={"service_days": "weight_days"})
    results = []
    for year in sorted(complete.year.unique()):
        selected = complete[(complete.year == year) & complete.month_number.isin(months)]
        matched = selected.merge(weights, on=["month_number", "day_type"], validate="one_to_one")
        if len(matched) != len(months) * 3 or len(weights) != len(months) * 3:
            continue
        weighted = {mode: float((matched[f"{mode}_daily"] * matched.weight_days).sum()) for mode in MODES}
        observed_total = matched.total_total.sum()
        row = dict(year=int(year), months=len(months), matched_months=",".join(map(str, months)),
                   observed_bus_share_pct=float(matched.bus_total.sum() / observed_total * 100) if observed_total else np.nan,
                   standardized_bus_share_pct=weighted["bus"] / weighted["total"] * 100 if weighted["total"] else np.nan,
                   **{f"{mode}_standardized": weighted[mode] for mode in MODES})
        for kind in ("W", "A", "U"):
            typed = matched[matched.day_type == kind]
            row[f"{kind}_share_standardized_pct"] = float((typed.total_daily * typed.weight_days).sum() / weighted["total"] * 100) if weighted["total"] else np.nan
        results.append(row)
    result = pd.DataFrame(results)
    if result.empty:
        return result
    baseline = result[result.year == 2019]
    if not baseline.empty:
        for mode in MODES:
            denominator = baseline.iloc[0][f"{mode}_standardized"]
            result[f"{mode}_recovery_index"] = result[f"{mode}_standardized"] / denominator * 100 if denominator else np.nan
    return result


def unusual_observations(frame: pd.DataFrame) -> pd.DataFrame:
    """Flag descriptive within-year/month/day-type median deviations.

    A minimum of four same-cell days is required. Modified z scores are
    exploratory screening values, not multiple-testing-adjusted significance.
    """
    daily = frame.copy()
    dates = pd.to_datetime(daily.service_date)
    daily["year"], daily["month_number"] = dates.dt.year, dates.dt.month
    grouped = daily.groupby(["year", "month_number", "day_type"]).total_rides
    daily["cell_median"] = grouped.transform("median")
    daily["absolute_deviation"] = (daily.total_rides - daily.cell_median).abs()
    daily["mad"] = daily.groupby(["year", "month_number", "day_type"]).absolute_deviation.transform("median")
    daily["modified_z"] = .67448975 * (daily.total_rides - daily.cell_median) / daily.mad.replace(0, np.nan)
    daily["cell_days"] = grouped.transform("size")
    return daily[(daily.cell_days >= 4) & (daily.modified_z.abs() > 3.5)].sort_values("modified_z", key=abs, ascending=False)


def verify_postgres_monthly(frame: pd.DataFrame, expected: pd.DataFrame) -> dict:
    """Prove that PostgreSQL and offline SQL produce identical monthly cells."""
    from datetime import timedelta
    from .database import connect_database
    first, last = frame.service_date.min(), frame.service_date.max()
    with connect_database() as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        cursor = connection.execute(SQL_DIRECTORY.joinpath("research_monthly.sql").read_text(), (first, last + timedelta(days=1)) * 2)
        actual = pd.DataFrame(cursor.fetchall(), columns=[column[0] for column in cursor.description])
    actual = actual.map(lambda value: float(value) if hasattr(value, "as_tuple") else value)
    actual["month"] = pd.to_datetime(actual.month)
    actual["year"], actual["month_number"] = actual.month.dt.year, actual.month.dt.month
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False, rtol=1e-10, atol=1e-6)
    return {"monthly_cells": len(actual), "engines": ["PostgreSQL", "DuckDB"], "matched": True}


def run_research(snapshot: Path, output: Path, *, verify_postgres=False):
    """Verify archived extraction and materialize reproducible analytical tables."""
    if output.exists():
        raise ValueError("Research output exists; choose a new version")
    metadata = json.loads((snapshot / "manifest.json").read_text())
    payload = snapshot / "daily_ridership.parquet"
    if hashlib.sha256(payload.read_bytes()).hexdigest() != metadata["parquet_sha256"]:
        raise ValueError("Historical snapshot checksum mismatch")
    frame = validate_frame(pd.read_parquet(payload))
    coverage = coverage_details(frame)
    monthly = monthly_aggregates(frame)
    verification = verify_postgres_monthly(frame, monthly) if verify_postgres else None
    indices = recovery_indices(monthly)
    annual = annual_summary(monthly, coverage)
    tables = {"monthly": monthly, "recovery_indices": indices, "annual": annual,
              "monthly_changes": monthly_changes(monthly), "period_recovery": standardized_periods(indices), "mode_persistence": persistence_analysis(indices),
              "day_type_persistence": day_type_contrasts(indices),
              "matched_composition": matched_composition(monthly, int(monthly.year.max())),
              "unusual_days": unusual_observations(frame)}
    output.mkdir(parents=True)
    if verification:
        (output / "sql_verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    for name, table in tables.items():
        table.to_csv(output / f"{name}.csv", index=False)
    (output / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
    from importlib.metadata import version
    import platform
    manifest = {"python_version": platform.python_version(),
                "runtime_versions": {package: version(package) for package in ("pandas", "numpy", "duckdb", "pyarrow", "psycopg", "plotly")},
                "analysis_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "input_parquet_sha256": metadata["parquet_sha256"], "source_retrieved_at_utc": metadata["retrieved_at_utc"],
                "monthly_sql_sha256": hashlib.sha256(SQL_DIRECTORY.joinpath("research_monthly.sql").read_bytes()).hexdigest(),
                "baselines": BASELINES, "bootstrap_seed": 42, "bootstrap_repetitions": 5000,
                "tables": {name: len(table) for name, table in tables.items()}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-postgres", action="store_true", help="Compare monthly SQL against local PostgreSQL")
    args = parser.parse_args()
    tables = run_research(args.snapshot, args.output, verify_postgres=args.verify_postgres)
    print(json.dumps({name: len(table) for name, table in tables.items()}, indent=2))


if __name__ == "__main__":
    main()
