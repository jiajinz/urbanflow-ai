"""Pure validation and conversion of CTA daily boarding records."""

import re
from dataclasses import dataclass
from datetime import date, datetime

from .ingestion import DAY_TYPES, REQUIRED_FIELDS

COUNT_FIELDS = ("bus", "rail_boardings", "total_rides")


class ProcessingError(ValueError):
    """The batch does not have a recognizable CTA response structure."""


@dataclass(frozen=True)
class BoardingRecord:
    """Validated systemwide boardings for one service date."""

    service_date: date
    day_type: str
    bus: int
    rail_boardings: int
    total_rides: int


@dataclass(frozen=True)
class RejectedRecord:
    """A zero-based source position and safe, field-specific error details."""

    index: int
    service_date: str | None
    errors: tuple[str, ...]
    duplicate: bool = False


@dataclass(frozen=True)
class ProcessingResult:
    """Accepted records and explicit rejections, in source order."""

    fetched_count: int
    valid_records: tuple[BoardingRecord, ...]
    rejected_records: tuple[RejectedRecord, ...]

    @property
    def duplicate_count(self) -> int:
        return sum(record.duplicate for record in self.rejected_records)

    @property
    def date_range(self) -> tuple[date, date] | None:
        dates = [record.service_date for record in self.valid_records]
        return (min(dates), max(dates)) if dates else None


def parse_service_date(value: object) -> date:
    """Parse an ISO date or the API's midnight floating timestamp."""
    if not isinstance(value, str):
        raise ValueError("service_date must be a non-null ISO date string")
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    elif re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T00:00:00(?:\.0{1,6})?", value):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            pass
    raise ValueError("service_date must be a valid ISO date or midnight timestamp")


def parse_count(value: object, field: str) -> int:
    """Accept integers and ASCII integer strings without rounding or defaults."""
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        try:
            return int(value)
        except ValueError:
            pass
    raise ValueError(f"{field} must be a non-null, nonnegative integer")


def _convert_record(raw: dict[str, object]) -> BoardingRecord:
    missing = sorted(REQUIRED_FIELDS - raw.keys())
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    service_date = parse_service_date(raw["service_date"])
    day_type = raw["day_type"]
    if not isinstance(day_type, str) or day_type not in DAY_TYPES:
        raise ValueError("day_type must be W, A, or U")
    counts = {field: parse_count(raw[field], field) for field in COUNT_FIELDS}
    if counts["total_rides"] != counts["bus"] + counts["rail_boardings"]:
        raise ValueError("total_rides must equal bus + rail_boardings")
    return BoardingRecord(service_date, day_type, **counts)


def process_records(records: object) -> ProcessingResult:
    """Collect record errors; fail for an invalid batch or unrecognized schema.

    A nonempty batch is recognizable if at least one object contains all required
    fields. Individual partial records are rejected when that anchor exists.
    Only accepted records reserve a date; the first valid occurrence wins.
    """
    if not isinstance(records, list):
        raise ProcessingError("CTA response must be a JSON array")
    if records and not any(
        isinstance(record, dict) and REQUIRED_FIELDS.issubset(record)
        for record in records
    ):
        raise ProcessingError("No record contains the required CTA schema")
    accepted: dict[date, BoardingRecord] = {}
    rejected: list[RejectedRecord] = []
    for index, raw in enumerate(records):
        context = None
        if isinstance(raw, dict) and isinstance(raw.get("service_date"), str):
            context = raw["service_date"][:32]
        try:
            if not isinstance(raw, dict):
                raise ValueError("Record must be a JSON object")
            clean = _convert_record(raw)
        except ValueError as exc:
            rejected.append(RejectedRecord(index, context, (str(exc),)))
            continue
        if clean.service_date in accepted:
            previous = accepted[clean.service_date]
            kind = "identical" if clean == previous else "conflicting"
            rejected.append(RejectedRecord(
                index, context, (f"Duplicate service_date ({kind} record)",), True
            ))
            continue
        accepted[clean.service_date] = clean
    return ProcessingResult(len(records), tuple(accepted.values()), tuple(rejected))
