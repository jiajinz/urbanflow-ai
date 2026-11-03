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


RANGE_PAGE_SIZE = 100


def validate_date_range(start_date: date | None, end_date: date | None) -> None:
    """Require either no bounds or two dates defining a nonempty half-open range."""
    if start_date is None and end_date is None:
        return
    if type(start_date) is not date or type(end_date) is not date:
        raise ValueError("start_date and end_date must both be date objects")
    if start_date >= end_date:
        raise ValueError("start_date must be earlier than end_date (exclusive)")


def fetch_daily_boardings(
    *, endpoint: str | None = None, timeout: float = 10.0,
    validate_records: bool = True,
    start_date: date | None = None, end_date: date | None = None,
) -> list[dict[str, object]]:
    """Fetch the latest 100 rows, or all pages in [start_date, end_date).

    Both date bounds are required for historical loading. Date values are typed
    before interpolation into SoQL. Existing endpoint filters are combined with
    the date predicate. Range mode owns limit, offset, and ordering. Failed pages
    raise rather than returning a partial batch. Timeout applies to each request.
    Set validate_records=False to defer row validation to processing.
    """
    validate_date_range(start_date, end_date)
    endpoint = endpoint or os.environ.get("CTA_BOARDINGS_API_URL", DEFAULT_ENDPOINT)
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("endpoint must be an absolute HTTP or HTTPS URL")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and greater than zero")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if start_date is None:
        query.update({"$limit": "100", "$order": "service_date DESC"})
        data = _fetch_page(urlunsplit(parsed._replace(query=urlencode(query))), timeout)
    else:
        predicate = (
            f"service_date >= '{start_date.isoformat()}T00:00:00' AND "
            f"service_date < '{end_date.isoformat()}T00:00:00'"
        )
        existing_filter = query.get("$where")
        query["$where"] = f"({existing_filter}) AND ({predicate})" if existing_filter else predicate
        query.update({"$limit": str(RANGE_PAGE_SIZE), "$order": "service_date ASC, :id ASC"})
        data = []
        offset = 0
        while True:
            query["$offset"] = str(offset)
            page = _fetch_page(urlunsplit(parsed._replace(query=urlencode(query))), timeout)
            data.extend(page)
            if len(page) < RANGE_PAGE_SIZE:
                break
            offset += len(page)
    return _validate_records(data) if validate_records else data


def _fetch_page(url: str, timeout: float) -> list[dict[str, object]]:
    """Request one JSON array, preserving the existing safe ingestion errors."""
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
    if not isinstance(data, list):
        raise IngestionError("CTA API response must be a JSON array")
    return data
