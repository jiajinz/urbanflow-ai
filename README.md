# UrbanFlow AI

UrbanFlow AI currently provides a focused ingestion client for the Chicago Transit Authority (CTA) Daily Boarding Totals dataset. It retrieves the latest 100 daily records from the Chicago Data Portal and validates the response before returning it to the caller.

The dataset reports systemwide bus and rail boardings. Its fields are `service_date`, `day_type`, `bus`, `rail_boardings`, and `total_rides`. Valid `day_type` values are `W` (weekday), `A` (Saturday), and `U` (Sunday or holiday). See the [Chicago Data Portal dataset page](https://data.cityofchicago.org/Transportation/CTA-Ridership-Daily-Boarding-Totals/6iiy-9s97) for source details.

## Architecture

The implementation lives in `src/urbanflow_ai/ingestion.py`. `fetch_daily_boardings` builds a GET request with `$limit=100` and `$order=service_date DESC`, decodes the JSON response, and validates the dataset's required fields and values. It uses Python's standard library for HTTP requests, so the application has no runtime dependencies. `IngestionError` represents HTTP, network, decoding, and dataset validation failures.

The endpoint defaults to `https://data.cityofchicago.org/resource/6iiy-9s97.json`. Callers can override it with the `endpoint` argument or the `CTA_BOARDINGS_API_URL` environment variable. Existing endpoint query parameters are retained; the required limit and ordering parameters take precedence. The default request timeout is 10 seconds.

## Requirements

- Python 3.10 or newer
- pytest for running the test suite

## Installation

Create and activate a virtual environment, then install the package with its test dependency:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

## Usage

Fetch the latest records using the default endpoint:

```sh
python -c 'from urbanflow_ai import fetch_daily_boardings; print(fetch_daily_boardings())'
```

To use a different endpoint, pass it directly:

```python
from urbanflow_ai import fetch_daily_boardings

records = fetch_daily_boardings(endpoint="https://example.com/cta.json", timeout=5)
```

Or set the environment variable:

```sh
export CTA_BOARDINGS_API_URL='https://example.com/cta.json'
python -c 'from urbanflow_ai import fetch_daily_boardings; print(fetch_daily_boardings())'
```

The current Chicago Data Portal endpoint does not require authentication. The module returns the original record dictionaries without changing their values.

## Testing

Run the pytest suite from the repository root:

```sh
python -m pytest
```

Tests mock the HTTP boundary and cover request parameters, response validation, invalid JSON, HTTP errors, network failures, and timeouts. They do not require network access.

## Future Development

Potential next steps include adding explicit pagination when the required volume grows, defining a typed domain model, and adding a persistence layer when storage requirements are established. Any schema or transformation changes should be based on the source dataset contract and covered by focused tests.
