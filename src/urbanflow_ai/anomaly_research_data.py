"""Portable, read-only loading of pinned anomaly research; no model execution."""

from dataclasses import dataclass
from io import BytesIO
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data_access import DataAccessError, validate_frame
from .history import coverage_details

ROOT = Path(__file__).resolve().parents[2]
VERSION = "cta-4c1c-v1"
A = "data/anomaly/cta-4c1a-v1"
B = "data/anomaly/cta-4c1b-v1"
C = "data/anomaly/cta-4c1c-v1"
HISTORY = "data/history/cta-2026-11-01-v1"
PINNED_MANIFEST = "1baafeffd3a700e9b74364f90d8b6ce9a790426daf8c6bc39a2914a4b3858e1c"
MODELS = ("calendar_median", "seasonal_trend")
HEALTH_STATES = (
    "clear",
    "warning",
    "insufficient_history",
    "unknown_drift_or_error",
    "scored_data_gap",
)
EXPERIMENTAL = "Experimental Research — Not a Production Alerting System"
NO_GO = "Operational Readiness: NO-GO"


@dataclass(frozen=True)
class ResearchBundle:
    daily: pd.DataFrame
    cases: pd.DataFrame
    health: pd.DataFrame
    episodes: pd.DataFrame
    provenance: dict


def digest(value):
    return hashlib.sha256(value).hexdigest()


def _read(root, relative):
    base = Path(root).resolve()
    file = (base / relative).resolve()
    if not file.is_relative_to(base):
        raise DataAccessError(
            "Research artifact path escapes the configured repository root"
        )
    return file.read_bytes()


def _logical_key(key):
    # These are legacy labels, never filesystem access instructions.
    if key.startswith("/Users/jiajinzhou/urbanflow-ai/"):
        return key.removeprefix("/Users/jiajinzhou/urbanflow-ai/")
    return key


def verified_payloads(root=ROOT, version_id=VERSION):
    """Check actual bytes on EVERY call, including before cached parsing."""
    try:
        if version_id != VERSION:
            raise DataAccessError("Unsupported frozen anomaly research version")
        payloads = {}

        def read(relative, expected=None):
            if relative not in payloads:
                payloads[relative] = _read(root, relative)
            if expected and digest(payloads[relative]) != expected:
                raise DataAccessError(
                    "Research artifact checksum mismatch: " + relative
                )
            return payloads[relative]

        c = json.loads(read(C + "/manifest.json", PINNED_MANIFEST))
        allowed_inputs = {
            B + "/manifest.json",
            B + "/daily.csv",
            A + "/predictions.csv",
            A + "/manifest.json",
            HISTORY + "/manifest.json",
            "docs/anomaly_readiness_config.json",
            "docs/anomaly_prospective_protocol.md",
            "docs/anomaly_validation_protocol.md",
            "src/urbanflow_ai/anomaly.py",
            "src/urbanflow_ai/anomaly_validation.py",
            "src/urbanflow_ai/anomaly_readiness.py",
        }

        def inputs(manifest):
            for key, expected in manifest["inputs_sha256"].items():
                logical = _logical_key(key)
                if logical not in allowed_inputs:
                    raise DataAccessError("Unsupported research lineage path")
                read(logical, expected)

        inputs(c)
        b = json.loads(read(B + "/manifest.json"))
        inputs(b)
        for directory, manifest in ((B, b), (C, c)):
            for name, expected in manifest["outputs_sha256"].items():
                if name not in OUTPUT_NAMES[directory]:
                    raise DataAccessError("Unexpected research artifact name")
                read(directory + "/" + name + ".csv", expected)
            if set(manifest["outputs_sha256"]) != set(OUTPUT_NAMES[directory]):
                raise DataAccessError("Research manifest lacks required output hashes")
        a = json.loads(read(A + "/manifest.json"))
        history = json.loads(read(HISTORY + "/manifest.json"))
        read(HISTORY + "/daily_ridership.parquet", history["parquet_sha256"])
        config = json.loads(read("docs/anomaly_readiness_config.json"))
        if not (
            c["prospective_validation_executed"] is False
            and c["integration_decision"].startswith("NO-GO:")
            and config["prospective_validation_executed"] is False
            and config["primary_score_threshold"] == 3.5
            and config["magnitude_min_boardings"] == 10000
            and config["magnitude_expected_fraction"] == 0.2
        ):
            raise DataAccessError(
                "Research readiness or frozen threshold metadata is incompatible"
            )
        if (
            a["source"]["input_parquet_sha256"] != history["parquet_sha256"]
            or c["source_parquet_sha256"] != history["parquet_sha256"]
        ):
            raise DataAccessError(
                "Anomaly source lineage differs from the validated archive"
            )
        if config["detector_sha256"] != digest(
            read("src/urbanflow_ai/anomaly.py")
        ) or config["frozen_prediction_sha256"] != digest(read(A + "/predictions.csv")):
            raise DataAccessError("Frozen detector/prediction metadata is inconsistent")
        return payloads
    except DataAccessError:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        raise DataAccessError(
            "Frozen anomaly research is missing or incompatible; restore the pinned artifacts"
        ) from None


def _table(payload, name):
    frame = pd.read_csv(BytesIO(payload), dtype=str, keep_default_na=False)
    if list(frame.columns) != SCHEMAS[name]:
        raise DataAccessError("Invalid research schema: " + name)
    for column in frame:
        if column in DATE_COLUMNS:
            if not frame[column].str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
                raise DataAccessError("Invalid research date field: " + column)
            frame[column] = pd.to_datetime(frame[column], errors="raise")
        elif column in BOOLEAN_COLUMNS:
            nullable = column in ("cross_mode_alert", "model_health_warning")
            accepted = ["True", "False", ""] if nullable else ["True", "False"]
            if not frame[column].isin(accepted).all():
                raise DataAccessError("Invalid research boolean: " + column)
            frame[column] = (
                frame[column]
                .map({"True": True, "False": False, "": None})
                .astype("boolean" if nullable else bool)
            )
        elif column not in TEXT_COLUMNS:
            frame[column] = pd.to_numeric(
                frame[column].replace("", np.nan), errors="raise"
            )
            nullable = column in NULLABLE_NUMERIC or column.endswith(
                ("_center_shift", "_scale_ratio")
            )
            values = frame[column].dropna() if nullable else frame[column]
            if not np.isfinite(values).all():
                raise DataAccessError(
                    "Nonfinite required research numeric field: " + column
                )
    return frame


def parse_bundle(payloads):
    """Parse previously verified bytes and enforce relational evidence contracts."""
    try:
        daily = _table(payloads[B + "/daily.csv"], "daily")
        cases = _table(payloads[C + "/cases.csv"], "cases")
        health = _table(payloads[C + "/model_health.csv"], "health")
        episodes = _table(payloads[C + "/episode_registry.csv"], "episodes")
        raw = validate_frame(
            pd.read_parquet(BytesIO(payloads[HISTORY + "/daily_ridership.parquet"]))
        )
        a = json.loads(payloads[A + "/manifest.json"])
        config = json.loads(payloads["docs/anomaly_readiness_config.json"])
        if coverage_details(raw) != a["source"]["coverage"]:
            raise DataAccessError("Research source coverage mismatch")
        keys = ["model", "mode", "date"]
        for frame in (daily, cases, health):
            if (
                frame.duplicated(keys).any()
                or not frame.model.isin(MODELS).all()
                or not frame["mode"].isin(["bus", "rail"]).all()
            ):
                raise DataAccessError("Duplicate or invalid research model/mode keys")
        if (
            not daily.day_type.isin(["W", "A", "U"]).all()
            or not cases.day_type.isin(["W", "A", "U"]).all()
        ):
            raise DataAccessError("Invalid CTA research day type")
        if (
            len(daily) != 11200
            or len(cases) != 763
            or len(health) != 11200
            or len(episodes) != 200
        ):
            raise DataAccessError(
                "Pinned research coverage/counts differ from approved version"
            )
        if daily.date.min() != pd.Timestamp(
            "2019-01-01"
        ) or daily.date.max() != pd.Timestamp("2026-08-31"):
            raise DataAccessError("Pinned evaluation date coverage mismatch")
        expected_grid = pd.MultiIndex.from_product(
            [MODELS, ["bus", "rail"], pd.date_range("2019-01-01", "2026-08-31")],
            names=keys,
        )
        for frame in (daily, health):
            if set(frame.set_index(keys).index) != set(expected_grid):
                raise DataAccessError(
                    "Research observation or health calendar coverage is incomplete"
                )
        if (
            not health.health_status.isin(HEALTH_STATES).all()
            or (health.health_status.eq("clear") & ~health.health_evaluable).any()
        ):
            raise DataAccessError("Invalid or misleading model-health state")
        if (
            not (daily.fit_cutoff < daily.date).all()
            or (daily.scale <= 0).any()
            or (daily.expected < 0).any()
        ):
            raise DataAccessError("Invalid research fitting bounds/scale/expectation")
        source = raw.assign(date=pd.to_datetime(raw.service_date)).set_index("date")
        for mode, column in [("bus", "bus"), ("rail", "rail_boardings")]:
            g = daily[daily["mode"] == mode]
            if not np.array_equal(
                g.observed.to_numpy(), source.loc[g.date, column].to_numpy()
            ) or not np.array_equal(
                g.day_type.to_numpy(), source.loc[g.date, "day_type"].to_numpy()
            ):
                raise DataAccessError(
                    "Observed research counts/day types differ from source"
                )
        if not np.allclose(
            daily.observed - daily.expected, daily.residual
        ) or not np.allclose(
            (daily.log_residual - daily.center) / daily.scale, daily.score
        ):
            raise DataAccessError(
                "Stored research residual/score arithmetic is inconsistent"
            )
        rule = daily.score.abs().gt(3.5) & daily.residual.abs().ge(
            np.maximum(10000, 0.2 * daily.expected)
        )
        if not rule.equals(daily.candidate):
            raise DataAccessError("Stored candidate flags disagree with frozen rules")
        expected_ids = daily[daily.candidate].apply(
            lambda r: f"{r.model}|{r['mode']}|{r.date.date()}", axis=1
        )
        if cases.case_id.duplicated().any() or set(cases.case_id) != set(expected_ids):
            raise DataAccessError("Research candidate preservation mismatch")
        evidence = daily.set_index(keys).loc[cases.set_index(keys).index].reset_index()
        for case_column, daily_column in [
            ("observed", "observed"),
            ("expected", "expected"),
            ("signed_deviation", "residual"),
            ("centered_score", "score"),
        ]:
            if not np.allclose(cases[case_column], evidence[daily_column]):
                raise DataAccessError("Case values differ from frozen daily evidence")
        direction = np.where(cases.signed_deviation > 0, "high", "low")
        signs = np.where(cases.centered_score > 0, "positive", "negative")
        if not np.array_equal(cases.actual_direction, direction) or not np.array_equal(
            cases.centered_score_sign, signs
        ):
            raise DataAccessError(
                "Case deviation direction or centered sign is inconsistent"
            )
        if (
            not cases.review_status.eq("unreviewed").all()
            or not cases.cause.eq("unknown").all()
        ):
            raise DataAccessError("Unverified research review/causal status changed")
        if (
            episodes.episode_id.duplicated().any()
            or not cases.episode_id.isin(episodes.episode_id).all()
        ):
            raise DataAccessError("Invalid episode associations")
        joined = episodes.set_index("episode_id").loc[cases.episode_id].reset_index()
        if not (
            (joined.start <= cases.date)
            & (joined.end >= cases.date)
            & joined.model.eq(cases.model)
            & joined["mode"].eq(cases["mode"])
            & joined.direction.eq(cases.actual_direction)
        ).all():
            raise DataAccessError("Case does not belong to its referenced episode")
        if not np.array_equal(
            cases.episode_days_asof, (cases.date - joined.start).dt.days + 1
        ):
            raise DataAccessError("Case as-of episode age is invalid")
        if not np.allclose(
            cases.absolute_deviation, cases.signed_deviation.abs()
        ) or not np.allclose(
            cases.relative_deviation_pct,
            100 * cases.signed_deviation / cases.expected.replace(0, np.nan),
            equal_nan=True,
        ):
            raise DataAccessError(
                "Case deviation magnitude or percentage is inconsistent"
            )
        if not cases.data_quality_status.eq("validated_matches_archive").all():
            raise DataAccessError("Unverified case source-quality state")
        other_keys = cases[keys].copy()
        other_keys["mode"] = other_keys["mode"].map({"bus": "rail", "rail": "bus"})
        other = (
            daily.set_index(keys).loc[other_keys.set_index(keys).index].reset_index()
        )
        if (
            not cases.cross_mode_available.all()
            or not np.allclose(cases.cross_mode_observed, other.observed)
            or not np.allclose(cases.cross_mode_expected, other.expected)
            or not np.array_equal(cases.cross_mode_alert, other.candidate)
            or not np.array_equal(cases.cross_mode_direction, other.direction)
        ):
            raise DataAccessError("Case cross-mode evidence is inconsistent")
        for row in cases.itertuples():
            context = json.loads(row.prior_comparable_observations)
            if (
                not isinstance(context, list)
                or len(context) != row.prior_same_type_count
            ):
                raise DataAccessError("Invalid comparable case context count")
            context_dates = []
            for point in context:
                day = pd.Timestamp(point["date"])
                if (
                    day >= row.date
                    or day < row.date - pd.Timedelta(days=28)
                    or day not in source.index
                ):
                    raise DataAccessError("Invalid or future comparable case context")
                actual = source.loc[day]
                field = "bus" if row.mode == "bus" else "rail_boardings"
                if (
                    point["observed"] != actual[field]
                    or actual.day_type != row.day_type
                ):
                    raise DataAccessError("Comparable case context differs from source")
                context_dates.append(day)
            if len(set(context_dates)) != len(context_dates):
                raise DataAccessError("Duplicate comparable observations")
        for episode_id, group in cases.groupby("episode_id"):
            episode = episodes.set_index("episode_id").loc[episode_id]
            if (
                group.date.min() != episode.start
                or group.date.max() != episode.end
                or len(group) != episode.alert_observations
                or group.date.nunique() != episode.calendar_days
            ):
                raise DataAccessError(
                    "Episode registry membership count/bounds differ from candidates"
                )
        stored_health = health.set_index(keys).loc[cases.set_index(keys).index]
        if not np.array_equal(
            cases.model_health_status, stored_health.health_status
        ) or not np.array_equal(
            cases.model_health_warning, stored_health.health_warning
        ):
            raise DataAccessError("Case health differs from full health context")
        provenance = dict(
            version=VERSION,
            experimental_label=EXPERIMENTAL,
            operational_readiness=NO_GO,
            prospective_validation_executed=False,
            first_date="2019-01-01",
            last_date="2026-08-31",
            source_url=a["source"]["source_url"],
            source_retrieved_at_utc=a["source"]["source_retrieved_at_utc"],
            research_generation_time="Not recorded",
            agency_publication_time="Not recorded",
            prospective_freeze_utc=config["prospective_freeze_utc"],
            score_threshold=3.5,
            magnitude_gate="abs deviation >= max(10000 boardings, 20% expected)",
            source_sha256={
                name: digest(value) for name, value in sorted(payloads.items())
            },
        )
        return ResearchBundle(daily, cases, health, episodes, provenance)
    except DataAccessError:
        raise
    except (ValueError, KeyError, TypeError, IndexError, OSError):
        raise DataAccessError(
            "Frozen anomaly research tables are incompatible or inconsistent"
        ) from None


def load_research_bundle(root=ROOT, version_id=VERSION):
    return parse_bundle(verified_payloads(root, version_id))


SCHEMAS = {
    "daily": [
        "date",
        "day_type",
        "mode",
        "model",
        "observed",
        "expected",
        "residual",
        "log_residual",
        "score",
        "center",
        "scale",
        "training_days",
        "calibration_days",
        "fit_cutoff",
        "candidate",
        "year",
        "direction",
        "absolute_deviation",
        "relative_deviation_pct",
        "magnitude_gate",
        "alert_3",
        "alert_3.5",
        "alert_4.5",
        "zero_center_score",
        "zero_center_alert",
        "magnitude_without_alert",
        "center_suppressed",
        "center_created",
    ],
    "cases": [
        "case_id",
        "date",
        "model",
        "mode",
        "day_type",
        "observed",
        "expected",
        "signed_deviation",
        "absolute_deviation",
        "relative_deviation_pct",
        "centered_score",
        "actual_direction",
        "centered_score_sign",
        "prior_calendar_days",
        "prior_expected_days",
        "prior_coverage_complete",
        "prior_same_type_count",
        "prior_same_type_median",
        "prior_comparable_observations",
        "cross_mode_available",
        "cross_mode_alert",
        "cross_mode_observed",
        "cross_mode_expected",
        "cross_mode_direction",
        "episode_id",
        "episode_days_asof",
        "data_quality_status",
        "model_health_status",
        "model_health_warning",
        "magnitude_points",
        "unusualness_points",
        "cross_mode_points",
        "persistence_points",
        "priority_points",
        "review_lane",
        "urgent",
        "review_status",
        "uncertainty",
        "cause",
        "reviewer",
        "reviewed_at_utc",
        "review_evidence",
        "evidence_limitations",
        "daily_review_rank",
    ],
    "health": [
        "date",
        "scored_days",
        "window_days",
        "target_scored",
        "history_window_mature",
        "wape_pct",
        "median_relative_residual",
        "median_log_residual",
        "median_center",
        "median_scale",
        "alert_rate_pct",
        "high_residual_fraction",
        "low_residual_fraction",
        "bias_warning",
        "sustained_underprediction",
        "sustained_overprediction",
        "error_warning",
        "alert_frequency_warning",
        "W_center_shift",
        "W_scale_ratio",
        "A_center_shift",
        "A_scale_ratio",
        "U_center_shift",
        "U_scale_ratio",
        "drift_types_evaluable",
        "drift_warning",
        "scored_evidence_missing_days",
        "health_evaluable",
        "health_warning",
        "health_status",
        "model",
        "mode",
    ],
    "episodes": [
        "model",
        "mode",
        "direction",
        "start",
        "end",
        "alert_observations",
        "calendar_days",
        "modes",
        "max_absolute_score",
        "max_absolute_deviation",
        "episode_id",
    ],
}
DATE_COLUMNS = ["date", "fit_cutoff", "start", "end"]
BOOLEAN_COLUMNS = [
    "candidate",
    "magnitude_gate",
    "alert_3",
    "alert_3.5",
    "alert_4.5",
    "zero_center_alert",
    "magnitude_without_alert",
    "center_suppressed",
    "center_created",
    "prior_coverage_complete",
    "cross_mode_available",
    "cross_mode_alert",
    "model_health_warning",
    "urgent",
    "target_scored",
    "history_window_mature",
    "bias_warning",
    "sustained_underprediction",
    "sustained_overprediction",
    "error_warning",
    "alert_frequency_warning",
    "drift_warning",
    "health_evaluable",
    "health_warning",
]
TEXT_COLUMNS = [
    "model",
    "mode",
    "day_type",
    "direction",
    "case_id",
    "actual_direction",
    "centered_score_sign",
    "prior_comparable_observations",
    "cross_mode_direction",
    "episode_id",
    "data_quality_status",
    "model_health_status",
    "review_lane",
    "review_status",
    "uncertainty",
    "cause",
    "reviewer",
    "reviewed_at_utc",
    "review_evidence",
    "evidence_limitations",
    "health_status",
    "modes",
]
NULLABLE_NUMERIC = [
    "relative_deviation_pct",
    "prior_same_type_median",
    "cross_mode_observed",
    "cross_mode_expected",
    "wape_pct",
    "median_relative_residual",
    "median_log_residual",
    "median_center",
    "median_scale",
    "alert_rate_pct",
    "high_residual_fraction",
    "low_residual_fraction",
]
OUTPUT_NAMES = {
    "data/anomaly/cta-4c1b-v1": [
        "windows",
        "ranked_queue",
        "threshold_episodes",
        "cross_mode_episodes",
        "investigations",
        "episodes",
        "daily",
        "scores",
        "annual",
        "overlap",
        "monthly",
    ],
    "data/anomaly/cta-4c1c-v1": [
        "weekly_load",
        "cases",
        "model_health",
        "episode_registry",
    ],
}
