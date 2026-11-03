"""Pure selection/evidence/export models; never fit or recalibrate a detector."""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from io import BytesIO
import json
from zipfile import ZipFile, ZIP_DEFLATED

import pandas as pd

from .anomaly_research_data import MODELS, ResearchBundle


@dataclass(frozen=True)
class ResearchFilter:
    model: str
    mode: str
    start_date: date
    end_date_exclusive: date
    direction: str = "all"
    urgent_only: bool = False
    cross_mode_only: bool = False
    health_warning_only: bool = False
    query: str = ""

    def __post_init__(self):
        if (
            self.model not in MODELS
            or self.mode not in ("bus", "rail")
            or self.direction not in ("all", "high", "low")
        ):
            raise ValueError(
                "Choose a supported model, transit mode and deviation direction"
            )
        if (
            type(self.start_date) is not date
            or type(self.end_date_exclusive) is not date
            or self.start_date >= self.end_date_exclusive
        ):
            raise ValueError("Choose a valid start and inclusive end date")
        if any(
            type(value) is not bool
            for value in (
                self.urgent_only,
                self.cross_mode_only,
                self.health_warning_only,
            )
        ):
            raise ValueError("Candidate filter flags must be boolean")
        if not isinstance(self.query, str) or len(self.query) > 200:
            raise ValueError("Case search must be at most 200 characters")


@dataclass(frozen=True)
class ResearchView:
    observations: pd.DataFrame
    candidates: pd.DataFrame
    health: pd.DataFrame
    episode_context: pd.DataFrame
    counts: dict
    selection_context: dict


@dataclass(frozen=True)
class CaseEvidence:
    case: dict
    daily: dict
    prior_context: pd.DataFrame
    episode: dict


def build_research_view(bundle: ResearchBundle, filters: ResearchFilter):
    first, last = pd.Timestamp(bundle.provenance["first_date"]), pd.Timestamp(
        bundle.provenance["last_date"]
    )
    start, end = pd.Timestamp(filters.start_date), pd.Timestamp(
        filters.end_date_exclusive
    )
    if start < first or end > last + pd.Timedelta(days=1):
        raise ValueError("Date range is outside frozen research coverage")

    def primary(frame):
        return frame[
            (frame.model == filters.model)
            & (frame["mode"] == filters.mode)
            & (frame.date >= start)
            & (frame.date < end)
        ].copy()

    observations = primary(bundle.daily).sort_values("date")
    # An explicit calendar grid prevents Plotly connecting across missing dates.
    observations = (
        observations.set_index("date")
        .reindex(pd.date_range(start, end - pd.Timedelta(days=1), freq="D"))
        .rename_axis("date")
        .reset_index()
    )
    health = primary(bundle.health).sort_values("date").reset_index(drop=True)
    candidates = primary(bundle.cases)
    total = len(candidates)
    if filters.direction != "all":
        candidates = candidates[candidates.actual_direction == filters.direction]
    for enabled, column in [
        (filters.urgent_only, "urgent"),
        (filters.cross_mode_only, "cross_mode_alert"),
        (filters.health_warning_only, "model_health_warning"),
    ]:
        if enabled:
            candidates = candidates[candidates[column].eq(True).fillna(False)]
    query = filters.query.strip()
    if query and not candidates.empty:
        text = (
            candidates[["case_id", "date", "day_type", "actual_direction"]]
            .astype(str)
            .agg(" ".join, axis=1)
        )
        candidates = candidates[text.str.contains(query, case=False, regex=False)]
    candidates = candidates.sort_values(["date", "case_id"]).reset_index(drop=True)
    episodes = bundle.episodes[
        bundle.episodes.episode_id.isin(candidates.episode_id)
    ].copy()
    counts = dict(
        observed_dates=int(observations.observed.notna().sum()),
        context_candidates=total,
        visible_candidates=len(candidates),
        health_warning_dates=int(health.health_warning.sum()),
        unknown_health_dates=int(
            (~health.health_status.isin(["clear", "warning"])).sum()
        ),
    )
    context = dict(
        filters={
            key: str(value) if isinstance(value, date) else value
            for key, value in asdict(filters).items()
        },
        **bundle.provenance,
        counts=counts,
        scopes={
            "observations": "Full model/mode/date context; candidate filters do not remove observations",
            "candidates": "Exact direction/options/search subset",
            "model_health": "Full selected period, independent of candidate filters",
            "episode_context": "Full retrospective registry records; may extend beyond selected dates",
        },
        selected_case_id=None,
    )
    return ResearchView(observations, candidates, health, episodes, counts, context)


def select_case(bundle, view, case_id):
    chosen = view.candidates[view.candidates.case_id == case_id]
    if chosen.empty:
        return None
    case = chosen.iloc[0]
    daily = bundle.daily[
        (bundle.daily.model == case.model)
        & (bundle.daily["mode"] == case["mode"])
        & (bundle.daily.date == case.date)
    ].iloc[0]
    episode = view.episode_context[
        view.episode_context.episode_id == case.episode_id
    ].iloc[0]
    return CaseEvidence(
        case.to_dict(),
        daily.to_dict(),
        pd.DataFrame(json.loads(case.prior_comparable_observations)),
        episode.to_dict(),
    )


def export_research_view(view, selected_case_id=None):
    stream = BytesIO()
    context = {
        **view.selection_context,
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_case_id": (
            selected_case_id
            if selected_case_id in set(view.candidates.case_id)
            else None
        ),
    }
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        for name, frame in [
            ("observations", view.observations),
            ("candidates", view.candidates),
            ("model_health", view.health),
            ("episode_context", view.episode_context),
        ]:
            archive.writestr(name + ".csv", frame.to_csv(index=False))
        archive.writestr("selection.json", json.dumps(context, indent=2))
        archive.writestr(
            "context.txt",
            "Experimental Research — Not a Production Alerting System\nOperational Readiness: NO-GO\nCandidates are not confirmed incidents. All cases are unreviewed; causes unknown.\nAll periods are retrospective and previously inspected. No prospective validation occurred.\nEpisode registry includes retrospective full duration; case fields are as-of.\n"
            + json.dumps(context["scopes"], indent=2),
        )
    return stream.getvalue()
