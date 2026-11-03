import json
from datetime import date
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.error import URLError
from unittest.mock import MagicMock

import pytest

from urbanflow_ai import IngestionError, fetch_daily_boardings

RECORD = {
    "service_date": "2026-09-28T00:00:00.000",
    "day_type": "W",
    "bus": "600000",
    "rail_boardings": "300000",
    "total_rides": "900000",
}


def response_for(body):
    response = MagicMock()
    response.read.return_value = body
    context = MagicMock()
    context.__enter__.return_value = response
    return context


def test_fetches_latest_100_records_from_configured_endpoint(monkeypatch):
    from urbanflow_ai import ingestion

    mocked = response_for(json.dumps([RECORD]).encode())
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return mocked

    monkeypatch.setattr(ingestion, "urlopen", fake_urlopen)

    result = fetch_daily_boardings(endpoint="https://example.test/cta?region=north")

    assert result == [RECORD]
    request, timeout = calls[0]
    query = parse_qs(urlsplit(request.full_url).query)
    assert query == {"region": ["north"], "$limit": ["100"], "$order": ["service_date DESC"]}
    assert timeout == 10.0
    assert request.get_method() == "GET"
    assert mocked.__exit__.called


@pytest.mark.parametrize(
    ("body", "error"),
    [
        (b"not-json", "not valid JSON"),
        (b"{}", "JSON array"),
        (json.dumps([{**RECORD, "day_type": "X"}]).encode(), "day_type"),
        (json.dumps([{**RECORD, "bus": "bad"}]).encode(), "bus"),
    ],
)
def test_rejects_invalid_api_responses(monkeypatch, body, error):
    from urbanflow_ai import ingestion

    monkeypatch.setattr(ingestion, "urlopen", lambda *args, **kwargs: response_for(body))
    with pytest.raises(IngestionError, match=error):
        fetch_daily_boardings()


def test_reports_http_and_network_failures(monkeypatch):
    from urbanflow_ai import ingestion

    def fail(*args, **kwargs):
        raise URLError("network down")

    monkeypatch.setattr(ingestion, "urlopen", fail)
    with pytest.raises(IngestionError, match="failed or timed out"):
        fetch_daily_boardings()


def test_reports_http_error_and_timeout(monkeypatch):
    from urbanflow_ai import ingestion

    def http_error(*args, **kwargs):
        raise HTTPError("https://example.test", 503, "Unavailable", {}, None)

    monkeypatch.setattr(ingestion, "urlopen", http_error)
    with pytest.raises(IngestionError, match="HTTP 503"):
        fetch_daily_boardings()

    def timeout(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr(ingestion, "urlopen", timeout)
    with pytest.raises(IngestionError, match="failed or timed out"):
        fetch_daily_boardings()


def test_date_range_paginates_and_combines_existing_filter(monkeypatch):
    from urbanflow_ai import ingestion

    monkeypatch.setattr(ingestion, "RANGE_PAGE_SIZE", 2)
    pages = iter([[RECORD, RECORD], [RECORD]])
    queries = []

    def fake_urlopen(request, timeout):
        queries.append(parse_qs(urlsplit(request.full_url).query))
        return response_for(json.dumps(next(pages)).encode())

    monkeypatch.setattr(ingestion, "urlopen", fake_urlopen)
    result = fetch_daily_boardings(
        endpoint="https://example.test/cta?$where=bus>0&$offset=999&region=north",
        start_date=date(2026, 9, 1), end_date=date(2026, 10, 1),
    )
    assert len(result) == 3
    assert [query["$offset"] for query in queries] == [["0"], ["2"]]
    assert queries[0]["$where"] == [
        "(bus>0) AND (service_date >= '2026-09-01T00:00:00' AND service_date < '2026-10-01T00:00:00')"
    ]
    assert queries[0]["$order"] == ["service_date ASC, :id ASC"]
    assert queries[0]["$limit"] == ["2"]
    assert queries[0]["region"] == ["north"]


def test_date_range_exact_page_requires_empty_final_page(monkeypatch):
    from urbanflow_ai import ingestion

    monkeypatch.setattr(ingestion, "RANGE_PAGE_SIZE", 1)
    request = MagicMock(side_effect=[response_for(json.dumps([RECORD]).encode()), response_for(b'[]')])
    monkeypatch.setattr(ingestion, "urlopen", request)
    assert fetch_daily_boardings(start_date=date(2026, 9, 1), end_date=date(2026, 10, 1)) == [RECORD]
    assert request.call_count == 2


def test_date_range_empty_response_is_allowed(monkeypatch):
    from urbanflow_ai import ingestion

    monkeypatch.setattr(ingestion, "urlopen", lambda *args, **kwargs: response_for(b'[]'))
    assert fetch_daily_boardings(start_date=date(2026, 9, 1), end_date=date(2026, 10, 1)) == []


def test_later_page_failure_does_not_return_partial_records(monkeypatch):
    from urbanflow_ai import ingestion

    monkeypatch.setattr(ingestion, "RANGE_PAGE_SIZE", 1)
    request = MagicMock(side_effect=[response_for(json.dumps([RECORD]).encode()), URLError("offline")])
    monkeypatch.setattr(ingestion, "urlopen", request)
    with pytest.raises(IngestionError, match="failed or timed out"):
        fetch_daily_boardings(start_date=date(2026, 9, 1), end_date=date(2026, 10, 1))


@pytest.mark.parametrize("bounds", [
    {"start_date": "2026-09-01", "end_date": "2026-10-01"},
    {"start_date": date(2026, 9, 1)},
    {"end_date": date(2026, 10, 1)},
    {"start_date": date(2026, 10, 1), "end_date": date(2026, 9, 1)},
    {"start_date": date(2026, 9, 1), "end_date": date(2026, 9, 1)},
])
def test_invalid_date_bounds_fail_before_network(monkeypatch, bounds):
    from urbanflow_ai import ingestion

    request = MagicMock()
    monkeypatch.setattr(ingestion, "urlopen", request)
    with pytest.raises(ValueError):
        fetch_daily_boardings(**bounds)
    request.assert_not_called()
