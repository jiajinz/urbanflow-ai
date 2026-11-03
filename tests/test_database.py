"""Offline driver contract tests and opt-in PostgreSQL integration tests."""

import os
from dataclasses import replace
from datetime import date
from unittest.mock import MagicMock

import psycopg
import pytest

from urbanflow_ai import database
from urbanflow_ai.processing import BoardingRecord

RECORD = BoardingRecord(date(2026, 8, 31), "W", 643844, 432794, 1076638)


@pytest.fixture
def connection(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    monkeypatch.setattr(database, "connect_database", lambda: connection)
    return connection


def test_persistence_binds_values_and_closes_context(connection):
    connection.execute.return_value.fetchone.side_effect = [(RECORD.service_date,), (1,)]
    assert database.persist_records([RECORD]) == database.PersistenceResult(1, 0, 1)
    assert connection.execute.call_args_list[1].args == (
        database.UPSERT_SQL,
        (RECORD.service_date, "W", 643844, 432794, 1076638),
    )
    connection.__exit__.assert_called_once_with(None, None, None)


def test_unchanged_conflict_is_not_counted_as_write(connection):
    connection.execute.return_value.fetchone.side_effect = [None, (1,)]
    assert database.persist_records([RECORD]) == database.PersistenceResult(0, 1, 1)


@pytest.mark.parametrize("error", [psycopg.OperationalError, psycopg.IntegrityError])
def test_failure_reaches_transaction_context_without_returning_counts(connection, error):
    connection.execute.side_effect = [MagicMock(), error("sensitive server detail")]
    with pytest.raises(database.DatabaseError) as caught:
        database.persist_records([RECORD])
    assert "sensitive" not in str(caught.value)
    assert connection.__exit__.call_args.args[0] is error


def test_commit_failure_is_not_reported_as_success(connection):
    connection.execute.return_value.fetchone.side_effect = [(RECORD.service_date,), (1,)]
    connection.__exit__.side_effect = psycopg.OperationalError("lost commit response")
    with pytest.raises(database.DatabaseError, match="no successful commit"):
        database.persist_records([RECORD])


def test_missing_connection_configuration(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(database.DatabaseError, match="DATABASE_URL is required"):
        database.connect_database()


def test_connection_failure_hides_credentials(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@localhost/db")
    connect = MagicMock(side_effect=psycopg.OperationalError("secret"))
    monkeypatch.setattr(database.psycopg, "connect", connect)
    with pytest.raises(database.DatabaseError, match="connection failed") as caught:
        database.connect_database()
    assert "secret" not in str(caught.value)
    assert connect.call_args.kwargs["connect_timeout"] == 10


def test_cli_persistence_is_explicit(monkeypatch, capsys):
    from urbanflow_ai import pipeline
    from urbanflow_ai.processing import ProcessingResult
    import sys

    monkeypatch.setattr(pipeline, "run_pipeline", lambda: ProcessingResult(1, (RECORD,), ()))
    persist = MagicMock(return_value=database.PersistenceResult(1, 0, 1))
    monkeypatch.setattr(database, "persist_records", persist)
    monkeypatch.setattr(sys, "argv", ["pipeline"])
    pipeline.main()
    persist.assert_not_called()
    monkeypatch.setattr(sys, "argv", ["pipeline", "--persist"])
    pipeline.main()
    persist.assert_called_once_with((RECORD,))
    assert "Database inserted or updated: 1" in capsys.readouterr().out


@pytest.fixture
def postgres(monkeypatch):
    """Isolate real tables in a temporary schema in the selected test database."""
    from uuid import uuid4
    from psycopg import sql

    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests")
    schema = "urbanflow_test_" + uuid4().hex
    original_connect = psycopg.connect
    with original_connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        def isolated_connection():
            return original_connect(url, options=f"-c search_path={schema}")
        monkeypatch.setattr(database, "connect_database", isolated_connection)
        try:
            yield isolated_connection
        finally:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.mark.integration
def test_real_persistence_repetition_and_correction(postgres):
    assert database.persist_records([RECORD]) == database.PersistenceResult(1, 0, 1)
    with postgres() as conn:
        before = conn.execute("SELECT updated_at FROM daily_ridership").fetchone()[0]
    assert database.persist_records([RECORD]) == database.PersistenceResult(0, 1, 1)
    with postgres() as conn:
        assert conn.execute("SELECT updated_at FROM daily_ridership").fetchone()[0] == before
    corrected = replace(RECORD, bus=643845, total_rides=1076639)
    assert database.persist_records([corrected]) == database.PersistenceResult(1, 0, 1)
    with postgres() as conn:
        assert conn.execute("SELECT bus, total_rides FROM daily_ridership").fetchone() == (643845, 1076639)


@pytest.mark.integration
@pytest.mark.parametrize("changes", [
    {"bus": -1}, {"rail_boardings": -1}, {"total_rides": -1},
    {"total_rides": 0}, {"day_type": "X"}, {"bus": None}, {"service_date": None},
])
def test_real_constraint_failure_rolls_back_entire_batch(postgres, changes):
    database.persist_records([RECORD])
    new = replace(RECORD, service_date=date(2026, 9, 1))
    with pytest.raises(database.DatabaseError, match="constraint violation"):
        database.persist_records([new, replace(RECORD, **changes)])
    with postgres() as conn:
        assert conn.execute("SELECT COUNT(*) FROM daily_ridership").fetchone()[0] == 1
        assert conn.execute("SELECT bus FROM daily_ridership").fetchone()[0] == RECORD.bus
