"""Research filtering and evidence/export equivalence over the real bundle."""

from datetime import date
from io import BytesIO
import json
from zipfile import ZipFile

import pandas as pd
import pytest

from urbanflow_ai.anomaly_research_data import load_research_bundle, ResearchBundle
from urbanflow_ai.anomaly_research_views import (
    ResearchFilter,
    build_research_view,
    select_case,
    export_research_view,
)
from urbanflow_ai.anomaly_research_charts import observation_chart


@pytest.fixture(scope="module")
def bundle():
    return load_research_bundle()


def test_below_expected_positive_centered_score(bundle):
    filters = ResearchFilter(
        "calendar_median", "rail", date(2021, 6, 4), date(2021, 6, 5), "low"
    )
    view = build_research_view(bundle, filters)
    row = view.candidates.iloc[0]
    assert row.observed == 244454 and row.expected == 717811
    assert row.actual_direction == "low" and row.centered_score > 0
    evidence = select_case(bundle, view, row.case_id)
    assert evidence.case["episode_id"] == evidence.episode["episode_id"]
    assert evidence.daily["score"] == row.centered_score
    assert select_case(bundle, view, "stale-id") is None


@pytest.mark.parametrize("model", ["calendar_median", "seasonal_trend"])
@pytest.mark.parametrize("mode", ["bus", "rail"])
def test_primary_bounds_and_independent_candidate_filters(bundle, model, mode):
    basic = ResearchFilter(model, mode, date(2025, 1, 1), date(2026, 1, 1))
    base = build_research_view(bundle, basic)
    filtered = build_research_view(
        bundle,
        ResearchFilter(
            model,
            mode,
            date(2025, 1, 1),
            date(2026, 1, 1),
            "high",
            True,
            True,
            True,
            "no-match",
        ),
    )
    assert base.observations.date.min() == pd.Timestamp("2025-01-01")
    assert base.observations.date.max() == pd.Timestamp("2025-12-31")
    pd.testing.assert_frame_equal(base.observations, filtered.observations)
    pd.testing.assert_frame_equal(base.health, filtered.health)
    assert filtered.candidates.empty


def test_literal_search_and_invalid_filters(bundle):
    view = build_research_view(
        bundle,
        ResearchFilter(
            "seasonal_trend", "rail", date(2025, 1, 1), date(2026, 1, 1), query="["
        ),
    )
    assert view.candidates.empty
    with pytest.raises(ValueError):
        ResearchFilter("unknown", "bus", date(2025, 1, 1), date(2026, 1, 1))
    with pytest.raises(ValueError):
        ResearchFilter("seasonal_trend", "bus", date(2025, 1, 1), date(2025, 1, 1))
    with pytest.raises(ValueError):
        build_research_view(
            bundle,
            ResearchFilter("seasonal_trend", "bus", date(2012, 7, 1), date(2012, 8, 1)),
        )


def test_null_date_gap_stays_null(bundle):
    daily = bundle.daily[
        ~(
            (bundle.daily.date == "2025-03-14")
            & (bundle.daily["mode"] == "rail")
            & (bundle.daily.model == "seasonal_trend")
        )
    ]
    altered = ResearchBundle(
        daily, bundle.cases, bundle.health, bundle.episodes, bundle.provenance
    )
    view = build_research_view(
        altered,
        ResearchFilter("seasonal_trend", "rail", date(2025, 3, 13), date(2025, 3, 16)),
    )
    assert (
        view.observations.loc[view.observations.date == "2025-03-14", "observed"]
        .isna()
        .all()
    )
    assert not observation_chart(view).data[0].connectgaps


def test_chart_and_zip_match_exact_visible_frames(bundle):
    view = build_research_view(
        bundle,
        ResearchFilter(
            "seasonal_trend",
            "rail",
            date(2025, 1, 1),
            date(2026, 1, 1),
            "high",
            query="2025-03-15",
        ),
    )
    figure = observation_chart(view)
    assert list(figure.data[0].y) == view.observations.observed.tolist()
    assert list(figure.data[1].y) == view.observations.expected.tolist()
    assert list(figure.data[2].y) == view.candidates.observed.tolist()
    assert not len(figure.data[3].y)
    archive = ZipFile(
        BytesIO(export_research_view(view, view.candidates.case_id.iloc[0]))
    )
    csv = pd.read_csv(archive.open("candidates.csv"))
    assert csv.case_id.tolist() == view.candidates.case_id.tolist()
    assert len(pd.read_csv(archive.open("observations.csv"))) == 365
    assert len(pd.read_csv(archive.open("model_health.csv"))) == len(view.health)
    context = json.loads(archive.read("selection.json"))
    assert context["prospective_validation_executed"] is False
    assert "NO-GO" in context["operational_readiness"]
    assert "/Users/" not in archive.read("selection.json").decode()


@pytest.mark.parametrize(
    "flag,column",
    [
        ("urgent_only", "urgent"),
        ("cross_mode_only", "cross_mode_alert"),
        ("health_warning_only", "model_health_warning"),
    ],
)
def test_each_candidate_flag_uses_stored_evidence(bundle, flag, column):
    kwargs = dict(
        model="calendar_median",
        mode="rail",
        start_date=date(2020, 1, 1),
        end_date_exclusive=date(2022, 1, 1),
    )
    base = build_research_view(bundle, ResearchFilter(**kwargs))
    filtered = build_research_view(bundle, ResearchFilter(**kwargs, **{flag: True}))
    assert (
        filtered.candidates.case_id.tolist()
        == base.candidates[base.candidates[column].eq(True)].case_id.tolist()
    )
    pd.testing.assert_frame_equal(base.observations, filtered.observations)
    pd.testing.assert_frame_equal(base.health, filtered.health)
