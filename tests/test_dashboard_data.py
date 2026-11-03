"""Snapshot publication, integrity, and explicit backend behavior."""

import json
from unittest.mock import MagicMock

import pandas as pd
import psycopg
import pytest

from urbanflow_ai import dashboard_data as access
from urbanflow_ai.data_access import DataAccessError


def test_export_roundtrip(tmp_path):
    original = access.load_bundle()
    directory = tmp_path / 'new'
    access.export_bundle(original, directory)
    loaded = access.load_bundle(directory)
    for name, expected in original.tables.items():
        pd.testing.assert_frame_equal(loaded.tables[name], expected)
    with pytest.raises(ValueError, match='exists'):
        access.export_bundle(original, directory)


def test_tampered_table_and_missing_bundle(tmp_path):
    with pytest.raises(DataAccessError, match='missing or invalid'):
        access.load_bundle(tmp_path)
    access.export_bundle(access.load_bundle(), tmp_path / 'new')
    (tmp_path / 'new/monthly.parquet').write_bytes(b'broken')
    with pytest.raises(DataAccessError, match='checksum'):
        access.load_bundle(tmp_path / 'new')


def test_definition_changes_block_stale_bundle(tmp_path):
    access.export_bundle(access.load_bundle(), tmp_path / 'new')
    path = tmp_path / 'new/manifest.json'
    metadata = json.loads(path.read_text())
    metadata['definition_hashes'] = {}
    path.write_text(json.dumps(metadata))
    with pytest.raises(DataAccessError, match='definitions changed'):
        access.load_bundle(tmp_path / 'new')


def test_postgres_failure_has_no_fallback(monkeypatch):
    monkeypatch.setattr(access, 'connect_database', MagicMock(side_effect=psycopg.OperationalError('private secret')))
    fallback = MagicMock()
    monkeypatch.setattr(access, 'load_bundle', fallback)
    with pytest.raises(DataAccessError, match='No fallback') as caught:
        access.load_data('postgres')
    assert 'secret' not in str(caught.value)
    fallback.assert_not_called()


def test_invalid_backend():
    with pytest.raises(DataAccessError, match='URBANFLOW_DATA_BACKEND'):
        access.load_data('unknown')


def test_inconsistent_analytical_table_is_not_published(tmp_path):
    data = access.load_bundle()
    data.monthly.loc[0, 'bus_daily'] += 1
    output = tmp_path / 'invalid'
    with pytest.raises(DataAccessError, match='do not match validated daily data'):
        access.export_bundle(data, output)
    assert not output.exists()


def test_archive_rebuild_matches_all_snapshot_tables():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    archived = access.load_archive(root / 'data/history/cta-2026-11-01-v1')
    snapshot = access.load_bundle()
    for name, expected in snapshot.tables.items():
        pd.testing.assert_frame_equal(archived.tables[name], expected)


def test_empty_postgres_data_is_not_replaced(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchall.return_value = []
    monkeypatch.setattr(access, 'connect_database', lambda: connection)
    with pytest.raises(DataAccessError, match='No validated records'):
        access.load_postgres()
    connection.__exit__.assert_called_once()


@pytest.mark.integration
def test_postgres_data_access_matches_rebuilt_analytics(monkeypatch):
    """Exercise the actual data adapter using an isolated PostgreSQL temp table."""
    import os
    from urbanflow_ai.dashboard_metrics import build_analytical_data
    url = os.environ.get('TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set TEST_DATABASE_URL for PostgreSQL data access integration')
    daily = access.load_bundle().daily
    years = pd.to_datetime(daily.service_date).dt.year
    daily = daily[years.isin([2017, 2018, 2019, 2025, 2026])].reset_index(drop=True)
    expected = build_analytical_data(daily)
    connection = psycopg.connect(url)
    try:
        connection.execute('CREATE TEMP TABLE daily_ridership (service_date DATE, day_type TEXT, bus INTEGER, rail_boardings INTEGER, total_rides INTEGER)')
        with connection.cursor() as cursor:
            cursor.executemany('INSERT INTO daily_ridership VALUES (%s,%s,%s,%s,%s)', list(daily.itertuples(index=False, name=None)))
        connection.commit()
        monkeypatch.setattr(access, 'connect_database', lambda: connection)
        actual = access.load_postgres()
        for name, table in expected.tables.items():
            pd.testing.assert_frame_equal(actual.tables[name], table, check_dtype=False,
                                          check_exact=False, rtol=1e-10, atol=1e-6)
        assert actual.metadata['source_retrieved_at_utc'] is None
        assert actual.metadata['quarantined_rows'] is None
    finally:
        connection.close()
