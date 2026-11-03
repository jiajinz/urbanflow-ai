"""Offline contracts for complete-history pagination, retries, and audits."""

import json
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from unittest.mock import MagicMock

import pandas as pd
import pytest

from urbanflow_ai import history
from urbanflow_ai.ingestion import IngestionError


def response(value):
    context = MagicMock()
    context.__enter__.return_value.read.return_value = json.dumps(value).encode()
    return context


def test_retry_transient_status_honors_bounded_retry_after(monkeypatch):
    request = MagicMock(side_effect=[HTTPError('https://example.test', 429, 'busy', {'Retry-After': '999'}, None), response([])])
    pause = MagicMock()
    monkeypatch.setattr(history, 'urlopen', request)
    monkeypatch.setattr(history.time, 'sleep', pause)
    assert history.request_page('https://example.test') == []
    assert request.call_count == 2
    pause.assert_called_once_with(30)


@pytest.mark.parametrize('status', [400, 401, 403, 404])
def test_permanent_http_error_is_not_retried(monkeypatch, status):
    request = MagicMock(side_effect=HTTPError('https://example.test', status, 'failure', {}, None))
    monkeypatch.setattr(history, 'urlopen', request)
    with pytest.raises(IngestionError, match=f'HTTP {status}'):
        history.request_page('https://example.test')
    assert request.call_count == 1


def test_network_retries_are_bounded(monkeypatch):
    request = MagicMock(side_effect=URLError('offline'))
    pause = MagicMock()
    monkeypatch.setattr(history, 'urlopen', request)
    monkeypatch.setattr(history.time, 'sleep', pause)
    with pytest.raises(IngestionError):
        history.request_page('https://example.test', retries=2)
    assert request.call_count == 3
    assert [call.args[0] for call in pause.call_args_list] == [1, 2]


def test_invalid_json_is_not_retried(monkeypatch):
    context = response([])
    context.__enter__.return_value.read.return_value = b'broken'
    request = MagicMock(return_value=context)
    monkeypatch.setattr(history, 'urlopen', request)
    with pytest.raises(IngestionError, match='invalid JSON'):
        history.request_page('https://example.test')
    assert request.call_count == 1


def test_history_exact_pages_and_stable_order(monkeypatch):
    coverage = dict(first_date='2024-01-01', last_date='2024-01-02', row_count=2)
    monkeypatch.setattr(history, 'source_coverage', lambda *args: coverage)
    requests = []
    pages = iter([[{'a': 1}], [{'a': 2}], []])
    def page(url):
        requests.append(parse_qs(urlsplit(url).query))
        return next(pages)
    monkeypatch.setattr(history, 'request_page', page)
    rows, actual = history.fetch_history(page_size=1)
    assert len(rows) == 2 and actual == coverage
    assert [query['$offset'] for query in requests] == [['0'], ['1'], ['2']]
    assert requests[0]['$order'] == ['service_date ASC, :id ASC']


def test_source_changes_abort_pagination(monkeypatch):
    coverage = dict(first_date='2024-01-01', last_date='2024-01-02', row_count=2)
    monkeypatch.setattr(history, 'source_coverage', MagicMock(side_effect=[coverage, {**coverage, 'row_count': 3}]))
    monkeypatch.setattr(history, 'request_page', lambda *args: [{}, {}])
    with pytest.raises(IngestionError, match='changed'):
        history.fetch_history()


def test_later_page_failure_never_reaches_upsert(monkeypatch, tmp_path):
    coverage = dict(first_date='2024-01-01', last_date='2024-01-02', row_count=1001)
    monkeypatch.setattr(history, 'source_coverage', lambda *args: coverage)
    monkeypatch.setattr(history, 'request_page', MagicMock(side_effect=[[{}] * 1000, IngestionError('failed')]))
    persist = MagicMock()
    monkeypatch.setattr(history, 'persist_records', persist)
    with pytest.raises(IngestionError):
        history.backfill(tmp_path / 'new')
    persist.assert_not_called()


def test_duplicates_reject_entire_backfill_before_write(monkeypatch, tmp_path):
    row = dict(service_date='2024-01-01', day_type='U', bus=1, rail_boardings=1, total_rides=2)
    monkeypatch.setattr(history, 'fetch_history', lambda **kwargs: ([row, row], {}))
    persist = MagicMock()
    monkeypatch.setattr(history, 'persist_records', persist)
    with pytest.raises(IngestionError, match='rejected 1'):
        history.backfill(tmp_path / 'new')
    persist.assert_not_called()


def test_coverage_missing_dates_and_incomplete_boundary_periods():
    frame = pd.DataFrame({'service_date': [date(2024, 1, 30), date(2024, 2, 1)]})
    result = history.coverage_details(frame)
    assert result['missing_dates'] == ['2024-01-31']
    assert not any(row['complete'] for row in result['monthly'])
    assert result['annual'][0]['expected_days'] == 366


@pytest.mark.parametrize('size', [0, -1, 5001, True])
def test_invalid_page_size_never_requests(monkeypatch, size):
    request = MagicMock()
    monkeypatch.setattr(history, 'source_coverage', request)
    with pytest.raises(ValueError):
        history.fetch_history(page_size=size)
    request.assert_not_called()
