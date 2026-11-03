"""Transactional PostgreSQL persistence for validated daily boardings."""

import os
from dataclasses import dataclass
from collections.abc import Iterable

import psycopg

from .processing import BoardingRecord

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS daily_ridership (
    service_date DATE PRIMARY KEY,
    day_type TEXT NOT NULL CHECK (day_type IN ('W', 'A', 'U')),
    bus INTEGER NOT NULL CHECK (bus >= 0),
    rail_boardings INTEGER NOT NULL CHECK (rail_boardings >= 0),
    total_rides INTEGER NOT NULL CHECK (total_rides >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (total_rides::BIGINT = bus::BIGINT + rail_boardings::BIGINT)
)
"""

UPSERT_SQL = """
INSERT INTO daily_ridership AS existing
    (service_date, day_type, bus, rail_boardings, total_rides)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (service_date) DO UPDATE SET
    day_type = EXCLUDED.day_type,
    bus = EXCLUDED.bus,
    rail_boardings = EXCLUDED.rail_boardings,
    total_rides = EXCLUDED.total_rides,
    updated_at = CURRENT_TIMESTAMP
WHERE (existing.day_type, existing.bus, existing.rail_boardings, existing.total_rides)
    IS DISTINCT FROM
    (EXCLUDED.day_type, EXCLUDED.bus, EXCLUDED.rail_boardings, EXCLUDED.total_rides)
RETURNING service_date
"""


class DatabaseError(RuntimeError):
    """A safe persistence error that does not expose connection credentials."""


@dataclass(frozen=True)
class PersistenceResult:
    """Committed changes and the table count observed in the transaction."""

    inserted_or_updated_count: int
    unchanged_count: int
    total_stored_count: int


def connect_database() -> psycopg.Connection:
    """Connect using DATABASE_URL with a bounded connection timeout."""
    url = os.environ.get("DATABASE_URL")
    if not url or not url.strip():
        raise DatabaseError("DATABASE_URL is required for persistence")
    try:
        return psycopg.connect(url, connect_timeout=10)
    except (psycopg.Error, ValueError):
        raise DatabaseError(
            "Database connection failed; check DATABASE_URL and PostgreSQL availability"
        ) from None


def initialize_schema(connection: psycopg.Connection) -> None:
    """Create the table inside the caller's transaction; do not migrate it."""
    connection.execute(SCHEMA_SQL)


def persist_records(records: Iterable[BoardingRecord]) -> PersistenceResult:
    """Initialize and upsert an entire batch atomically, then close the connection.

    Unchanged conflicts do not modify updated_at. A failed statement or commit
    raises DatabaseError; no success counts are returned before commit completes.
    """
    changed = unchanged = 0
    try:
        with connect_database() as connection:
            initialize_schema(connection)
            for record in records:
                row = connection.execute(UPSERT_SQL, (
                    record.service_date, record.day_type, record.bus,
                    record.rail_boardings, record.total_rides,
                )).fetchone()
                if row is None:
                    unchanged += 1
                else:
                    changed += 1
            total = connection.execute("SELECT COUNT(*) FROM daily_ridership").fetchone()[0]
        return PersistenceResult(changed, unchanged, total)
    except psycopg.IntegrityError:
        raise DatabaseError(
            "Database constraint violation; the entire batch was rolled back"
        ) from None
    except psycopg.Error:
        raise DatabaseError(
            "Database operation failed; no successful commit was confirmed"
        ) from None
