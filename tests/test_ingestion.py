import json
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
