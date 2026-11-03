"""Pure dashboard view models built from the validated Milestone 4A methods."""

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from .analytics import AnalyticsFilter
from .data_access import DataAccessError, snapshot_analytics, validate_frame
from .history import coverage_details
from .research import (
    BASELINES, annual_summary, matched_composition, monthly_aggregates,
    recovery_indices, standardized_periods,
)

MODES = ("bus", "rail", "total")
DAY_TYPES = ("W", "A", "U")


@dataclass
class AnalyticalData:
    """Validated daily data, reusable research tables, and data provenance."""

    daily: pd.DataFrame
    monthly: pd.DataFrame
    recovery: pd.DataFrame
    annual: pd.DataFrame
    periods: pd.DataFrame
    composition: pd.DataFrame
    metadata: dict

    @property
    def tables(self):
        return {name: getattr(self, name) for name in ("daily", "monthly", "recovery", "annual", "periods", "composition")}


def build_analytical_data(frame, metadata=None, *, monthly=None):
    """Reuse 4A SQL/calculations; reject empty data instead of inventing metrics."""
    clean = validate_frame(frame).sort_values("service_date").reset_index(drop=True)
    if clean.empty:
        raise DataAccessError("No validated records are available for analysis")
    monthly = monthly_aggregates(clean) if monthly is None else monthly
    indices = recovery_indices(monthly)
    coverage = coverage_details(clean)
    composition = matched_composition(monthly, int(monthly.year.max()))
    return AnalyticalData(clean, monthly, indices, annual_summary(monthly, coverage),
                          standardized_periods(indices), composition,
                          {**(metadata or {}), "coverage": coverage})


@dataclass(frozen=True)
class ExplorerFilter:
    """Half-open target range. Empty category tuples are valid empty selections."""

    start_date: date
    end_date: date
    day_types: tuple[str, ...] = DAY_TYPES
    modes: tuple[str, ...] = MODES
    years: tuple[int, ...] = ()
    baseline: str = "2019"

    def __post_init__(self):
        AnalyticsFilter(self.start_date, self.end_date)
        if self.baseline not in BASELINES:
            raise ValueError("Unsupported historical baseline")
        if any(kind not in DAY_TYPES for kind in self.day_types):
            raise ValueError("Unknown CTA day type")
        if any(mode not in MODES for mode in self.modes):
            raise ValueError("Unknown ridership mode")
        if any(type(year) is not int or not 1900 <= year <= 9998 for year in self.years):
            raise ValueError("Invalid comparison year")
        if any(len(values) != len(set(values)) for values in (self.day_types, self.modes, self.years)):
            raise ValueError("Duplicate filter categories are not allowed")


def selected_daily(data, filters):
    """Filter observations; an empty category or year selection returns no rows."""
    daily = data.daily
    dates = pd.to_datetime(daily.service_date)
    mask = ((daily.service_date >= filters.start_date) & (daily.service_date < filters.end_date)
            & daily.day_type.isin(filters.day_types) & dates.dt.year.isin(filters.years))
    return daily.loc[mask].copy() if filters.modes else daily.iloc[:0].copy()


def selected_monthly(data, filters, *, recovery=False):
    """Use only fully selected, complete months; retain the full baseline history."""
    table = data.recovery if recovery else data.monthly
    ends = table.month + pd.offsets.MonthBegin(1)
    mask = (table.month.ge(pd.Timestamp(filters.start_date)) & ends.le(pd.Timestamp(filters.end_date))
            & table.day_type.isin(filters.day_types) & table.year.isin(filters.years)
            & table.complete_month)
    if recovery:
        mask &= table.baseline.eq(filters.baseline)
    return table.loc[mask].copy() if filters.modes else table.iloc[:0].copy()


def explorer_series(data, filters, view):
    """Return tidy chart data. Missing months/years remain explicit null gaps."""
    if view not in ("Daily", "Monthly", "Yearly", "Seasonal", "Recovery"):
        raise ValueError("Unknown explorer view")
    rows = []
    if not filters.day_types or not filters.modes or not filters.years:
        return pd.DataFrame(columns=["date", "year", "day_type", "mode", "value", "rolling_average"])
    if view == "Daily":
        query = snapshot_analytics(data.daily, AnalyticsFilter(filters.start_date, filters.end_date))['daily']
        dates = pd.to_datetime(query.service_date)
        included = query.day_type.isin(filters.day_types) & dates.dt.year.isin(filters.years)
        consecutive = included.astype(int).rolling(7, min_periods=7).sum().eq(7)
        columns = {"bus": "bus", "rail": "rail_boardings", "total": "total_rides"}
        rolling = {"bus": "bus_rolling_average_7d", "rail": "rail_rolling_average_7d", "total": "rolling_average_7d"}
        for mode in filters.modes:
            for index, record in query.iterrows():
                rows.append(dict(date=record.service_date, mode=mode, value=record[columns[mode]] if included.iloc[index] else None,
                                 rolling_average=record[rolling[mode]] if consecutive.iloc[index] else None))
        return pd.DataFrame(rows, columns=["date", "mode", "value", "rolling_average"])
    table = selected_monthly(data, filters, recovery=view == "Recovery")
    for (year, kind), group in table.groupby(["year", "day_type"]):
        for mode in filters.modes:
            column = f"{mode}_index" if view == "Recovery" else f"{mode}_daily"
            if view == "Yearly":
                if len(group) != 12 or filters.start_date > date(int(year), 1, 1) or filters.end_date < date(int(year) + 1, 1, 1):
                    continue
                value = group[f"{mode}_total"].sum() / group.service_days.sum()
                rows.append(dict(date=int(year), year=int(year), day_type=kind, mode=mode, value=value))
            elif view == "Seasonal":
                for record in group.itertuples():
                    rows.append(dict(date=record.month_number, year=int(year), day_type=kind, mode=mode, value=getattr(record, column)))
            else:
                for record in group.itertuples():
                    rows.append(dict(date=record.month, year=int(year), day_type=kind, mode=mode, value=getattr(record, column)))
    tidy = pd.DataFrame(rows, columns=["date", "year", "day_type", "mode", "value"])
    if view in ("Monthly", "Recovery") and not tidy.empty:
        grid = pd.date_range(pd.Timestamp(filters.start_date).replace(day=1), pd.Timestamp(filters.end_date) - pd.Timedelta(days=1), freq="MS")
        tidy = pd.concat([group.set_index("date").reindex(grid).rename_axis("date").reset_index().assign(mode=mode, day_type=kind)
                          for (mode, kind), group in tidy.groupby(["mode", "day_type"])], ignore_index=True)
    if view == "Seasonal" and not tidy.empty:
        tidy = pd.concat([group.set_index("date").reindex(range(1, 13)).rename_axis("date").reset_index().assign(mode=mode, day_type=kind, year=year)
                          for (mode, kind, year), group in tidy.groupby(["mode", "day_type", "year"])], ignore_index=True)
    if view == "Yearly" and not tidy.empty:
        tidy = pd.concat([group.set_index("date").reindex(range(min(filters.years), max(filters.years)+1)).rename_axis("date").reset_index().assign(mode=mode, day_type=kind)
                          for (mode, kind), group in tidy.groupby(["mode", "day_type"])], ignore_index=True)
    return tidy


def executive_model(data, baseline="2019"):
    """Build traceable dynamic findings for the latest fully observed year."""
    if baseline not in BASELINES:
        raise ValueError("Unsupported historical baseline")
    complete_years = data.annual.loc[data.annual.complete_year & data.annual.year.ge(2020), "year"]
    if complete_years.empty:
        return None
    year = int(complete_years.max())
    period = data.periods[(data.periods.year == year) & (data.periods.baseline == baseline) & (data.periods.months == 12)]
    if set(period.day_type) != set(DAY_TYPES) or period[["bus_index", "rail_index", "total_index"]].isna().any().any():
        return None
    typed = period.set_index("day_type")
    metrics = {kind: float(typed.loc[kind, "total_index"]) for kind in DAY_TYPES}
    metrics["mode_gap"] = float(typed.loc["W", "bus_minus_rail_pp"])
    findings = [
        f"Observed · {year}: total recovery averaged {metrics['W']:.2f} for W, {metrics['A']:.2f} for A, and {metrics['U']:.2f} for U (baseline = 100; twelve equally weighted monthly indices).",
        f"Observed · {year} weekday bus recovery was {typed.loc['W', 'bus_index']:.2f}, versus {typed.loc['W', 'rail_index']:.2f} for rail; bus minus rail = {metrics['mode_gap']:.2f} percentage points. This does not identify modal substitution.",
    ]
    composition = data.composition
    if not composition.empty and {2019, int(data.monthly.year.max())}.issubset(set(composition.year)):
        current = composition.loc[composition.year == data.monthly.year.max()].iloc[0]
        reference = composition.loc[composition.year == 2019].iloc[0]
        findings.append(f"Observed · Matched calendar months {current.matched_months}, {int(current.year)}: fixed-2019-calendar bus share is {current.standardized_bus_share_pct:.2f}% versus {reference.standardized_bus_share_pct:.2f}% in 2019. This evidence uses fixed 2019 weights, independently of the recovery baseline selector.")
    return dict(year=year, baseline=baseline, metrics=metrics, findings=findings,
                period=period, trend=data.recovery[data.recovery.baseline == baseline].copy())
