"""Shared, parameterized PostgreSQL and DuckDB analytics; no UI dependencies."""

from dataclasses import dataclass
from datetime import date
from importlib.resources import files

import pandas as pd

QUERY_NAMES = ("summary", "daily", "weekly", "day_comparison", "extremes", "monthly")
SQL_DIRECTORY = files("urbanflow_ai").joinpath("sql")


@dataclass(frozen=True)
class AnalyticsFilter:
    """Inclusive start, exclusive end, and optional CTA service day classification."""

    start_date: date
    end_date: date
    day_type: str = "All"

    def __post_init__(self):
        if type(self.start_date) is not date or type(self.end_date) is not date:
            raise ValueError("Filters require date objects")
        if self.start_date >= self.end_date:
            raise ValueError("Start date must precede the exclusive end date")
        if (self.end_date - self.start_date).days > 36600:
            raise ValueError("Date range must not exceed 36,600 days")
        if self.day_type not in ("All", "W", "A", "U"):
            raise ValueError("Day type must be All, W, A, or U")

    @property
    def parameters(self):
        return (self.start_date, self.end_date, self.day_type)


def query_sql(name: str, dialect: str = "postgres") -> str:
    """Load allowlisted SQL and adapt only driver placeholders, never values."""
    if name not in QUERY_NAMES or dialect not in ("postgres", "duckdb"):
        raise ValueError("Unknown analytics query or SQL dialect")
    sql = SQL_DIRECTORY.joinpath("base.sql").read_text() + "\n" + SQL_DIRECTORY.joinpath(f"{name}.sql").read_text()
    return sql.replace("%s", "?") if dialect == "duckdb" else sql


def run_analytics(connection, filters: AnalyticsFilter, *, dialect="postgres") -> dict[str, pd.DataFrame]:
    """Execute all metrics on a caller-owned connection and transaction.

    Driver errors propagate to the data access boundary. Callers must provide a
    consistent read transaction when concurrent writes are possible.
    """
    result = {}
    for name in QUERY_NAMES:
        cursor = connection.execute(query_sql(name, dialect), filters.parameters)
        result[name] = pd.DataFrame(cursor.fetchall(), columns=[column[0] for column in cursor.description])
    return result
