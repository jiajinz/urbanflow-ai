"""Ingestion for the Chicago CTA Daily Boarding Totals dataset."""

import json
import math
import os
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

DEFAULT_ENDPOINT = "https://data.cityofchicago.org/resource/6iiy-9s97.json"
REQUIRED_FIELDS = {"service_date", "day_type", "bus", "rail_boardings", "total_rides"}
DAY_TYPES = {"W", "A", "U"}


class IngestionError(RuntimeError):
    """A request, response decoding, or dataset validation error."""


def _validate_records(data: object) -> list[dict[str, object]]:
    if not isinstance(data, list):
        raise IngestionError("CTA API response must be a JSON array")
    for index, record in enumerate(data):
        if not isinstance(record, dict) or not REQUIRED_FIELDS.issubset(record):
            raise IngestionError(f"CTA record {index} is missing required fields")
        try:
            date.fromisoformat(str(record["service_date"])[:10])
        except ValueError:
            raise IngestionError(f"CTA record {index} has an invalid service_date") from None
        if record["day_type"] not in DAY_TYPES:
            raise IngestionError(f"CTA record {index} has an invalid day_type")
        for field in ("bus", "rail_boardings", "total_rides"):
            try:
                value = float(record[field])
            except (TypeError, ValueError):
                raise IngestionError(f"CTA record {index} has an invalid {field}") from None
            if not math.isfinite(value) or value < 0:
                raise IngestionError(f"CTA record {index} has an invalid {field}")
    return data


def fetch_daily_boardings(*, endpoint: str | None = None, timeout: float = 10.0) -> list[dict[str, object]]:
    """Fetch and validate the latest 100 CTA daily boarding records.

    ``endpoint`` overrides the default and can also be configured with
    ``CTA_BOARDINGS_API_URL``. Existing query parameters are preserved.
    """
    endpoint = endpoint or os.environ.get("CTA_BOARDINGS_API_URL", DEFAULT_ENDPOINT)
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("endpoint must be an absolute HTTP or HTTPS URL")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and greater than zero")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({"$limit": "100", "$order": "service_date DESC"})
    url = urlunsplit(parsed._replace(query=urlencode(query)))
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except HTTPError as exc:
        status = exc.code
        exc.close()
        raise IngestionError(f"CTA API returned HTTP {status}") from None
    except (URLError, OSError):
        raise IngestionError("CTA API request failed or timed out") from None
    try:
        data = json.loads(payload)
    except (ValueError, UnicodeError):
        raise IngestionError("CTA API response is not valid JSON") from None
    return _validate_records(data)
