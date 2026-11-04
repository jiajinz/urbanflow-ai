"""Read-only experimental historical research page; independent snapshot backend."""

from datetime import timedelta
import os
import time

import pandas as pd
import streamlit as st

from .anomaly_research_data import (
    ROOT,
    VERSION,
    EXPERIMENTAL,
    NO_GO,
    verified_payloads,
    parse_bundle,
)
from .anomaly_research_views import (
    ResearchFilter,
    build_research_view,
    select_case,
    export_research_view,
)
from .anomaly_research_charts import observation_chart, health_chart
from .data_access import DataAccessError
from .ui_design import apply_page_styles, readable_caption

MODEL_LABELS = {
    "calendar_median": "Calendar Median",
    "seasonal_trend": "Seasonal Trend",
}


@st.cache_data(max_entries=2, show_spinner=False)
def cached_research(payloads):
    """Cache parsing only; caller re-verifies content before every lookup."""
    return parse_bundle(payloads)


def read_research():
    return cached_research(
        verified_payloads(os.environ.get("URBANFLOW_RESEARCH_ROOT", str(ROOT)))
    )


def render():
    with st.container(key="anomaly_research", gap="small"):
        apply_page_styles("anomaly_research", "anomaly")
        readable_caption("URBANFLOW AI / HISTORICAL ANOMALY RESEARCH")
        st.title("Anomaly Research Explorer")
        st.markdown(
            "Explore historical Chicago Transit Authority (CTA) ridership candidates and the limits of their model-based evidence."
        )
        st.warning(EXPERIMENTAL)
        st.markdown(
            f"**{NO_GO}** · Historical candidates are unreviewed, causes unknown. A candidate is not a confirmed transit incident."
        )
        started = time.perf_counter()
        try:
            bundle = read_research()
        except DataAccessError as exc:
            st.error(str(exc))
            readable_caption(
                "Research loading stopped. No fallback, model fitting, API call or database read is used. Other pages remain available."
            )
            return
        load_seconds = time.perf_counter() - started
        first = pd.Timestamp(bundle.provenance["first_date"]).date()
        last = pd.Timestamp(bundle.provenance["last_date"]).date()
        readable_caption(
            f"Frozen research {VERSION} · {first}–{last} · independent of the other pages’ PostgreSQL/snapshot setting · not live"
        )
        with st.sidebar:
            st.divider()
            readable_caption("RESEARCH ENVIRONMENT")
            st.markdown("Frozen anomaly artifacts · read only")
            readable_caption(f"{VERSION} · NO-GO · no prospective validation")
        with st.container(key="anomaly_controls", gap="small"):
            left, right = st.columns(2)
            with left:
                model = st.segmented_control(
                    "Historical model",
                    list(MODEL_LABELS),
                    default="seasonal_trend",
                    required=True,
                    format_func=MODEL_LABELS.get,
                    key="research_model",
                    width="stretch",
                    wrap=True,
                )
                dates = st.date_input(
                    "Service date range (inclusive)",
                    (max(first, last - timedelta(days=364)), last),
                    min_value=first,
                    max_value=last,
                    key="research_dates",
                )
            with right:
                mode = st.segmented_control(
                    "Transit mode",
                    ["bus", "rail"],
                    default="bus",
                    required=True,
                    format_func=str.title,
                    key="research_mode",
                    width="stretch",
                    wrap=True,
                )
                direction = st.segmented_control(
                    "Actual deviation direction",
                    ["all", "high", "low"],
                    default="all",
                    required=True,
                    format_func={
                        "all": "All",
                        "high": "Above expected",
                        "low": "Below expected",
                    }.get,
                    key="research_direction",
                    width="stretch",
                    wrap=True,
                    help="Uses actual minus expected boardings, independently of the centered score sign.",
                )
            with st.expander("Candidate search and optional filters"):
                query = st.text_input(
                    "Search cases",
                    key="research_query",
                    max_chars=200,
                    help="Literal case ID, ISO date, CTA day-type code or high/low direction. This search also controls exports.",
                )
                urgent = st.checkbox(
                    "Frozen urgency flag only",
                    key="research_urgent",
                    help="Historical research-priority heuristic, not a live escalation.",
                )
                cross = st.checkbox("Other mode also a candidate", key="research_cross")
                warning = st.checkbox(
                    "Cases with model-health warnings",
                    key="research_warning",
                    help="Unknown health is not clear. The full-period health panel remains visible.",
                )
        if len(dates) != 2:
            st.info("Select both a start and an end date.")
            return
        try:
            filters = ResearchFilter(
                model,
                mode,
                dates[0],
                dates[1] + timedelta(days=1),
                direction,
                urgent,
                cross,
                warning,
                query,
            )
            view = build_research_view(bundle, filters)
        except ValueError as exc:
            st.error(str(exc))
            return
        readable_caption(
            f"Context: {MODEL_LABELS[model]} · {mode.title()} · {dates[0]}–{dates[1]} inclusive. Candidate subset: {direction}; urgency={urgent}, other-mode={cross}, health-warning={warning}, search={query!r}."
        )
        st.header("1 · Actual versus expected")
        readable_caption(
            f"{view.counts['observed_dates']:,} observed dates · {view.counts['visible_candidates']} visible / {view.counts['context_candidates']} context candidates. Candidate filters change markers and cases, not the curves or health context."
        )
        with st.container(border=True):
            st.plotly_chart(
                observation_chart(view),
                width="stretch",
                config={"displaylogo": False},
                alt="Historical actual and frozen expected daily boardings; up/down markers show filtered statistical candidates, not confirmed incidents.",
            )
        st.plotly_chart(
            health_chart(view),
            width="stretch",
            config={"displaylogo": False},
            alt="Full selected-period research health states, unaffected by candidate-only filtering. Unknown is not clear.",
        )
        with st.expander("Inspect actual and expected values as a table"):
            st.dataframe(
                view.observations[["date", "model", "mode", "observed", "expected"]],
                hide_index=True,
                width="stretch",
                alt="Complete selected-period actual and expected boardings, including noncandidate dates. Missing values stay blank.",
            )
        st.header("2 · Investigation cases")
        selected_id = None
        if view.candidates.empty:
            st.info(
                "No statistical candidates match these case filters. Observations and model-health context remain visible; this is not evidence of no incidents."
            )
        else:
            columns = [
                "date",
                "mode",
                "observed",
                "expected",
                "relative_deviation_pct",
                "actual_direction",
                "centered_score",
                "model_health_status",
                "review_status",
                "case_id",
            ]
            visible = view.candidates[columns]
            signature = (
                model,
                mode,
                str(dates),
                direction,
                urgent,
                cross,
                warning,
                query,
            )
            import hashlib

            table_key = (
                "research_cases_"
                + hashlib.sha256(repr(signature).encode()).hexdigest()[:12]
            )
            selection = st.dataframe(
                visible,
                hide_index=True,
                width="stretch",
                on_select="rerun",
                selection_mode="single-row",
                key=table_key,
                column_config={
                    "observed": st.column_config.NumberColumn(
                        "Actual boardings", format="localized"
                    ),
                    "expected": st.column_config.NumberColumn(
                        "Expected boardings", format="%.1f"
                    ),
                    "relative_deviation_pct": st.column_config.NumberColumn(
                        "Deviation (%)", format="%.2f"
                    ),
                    "actual_direction": "Actual direction",
                    "centered_score": "Centered score",
                    "model_health_status": "Model health",
                    "review_status": "Review status",
                },
                alt="Filtered read-only research candidates; choose a row or use the case-ID selector below.",
            )
            ids = view.candidates.case_id.tolist()
            if st.session_state.get("research_selected") not in ids:
                st.session_state["research_selected"] = None
            rows = selection.selection.rows
            previous = st.session_state.get("research_table_choice")
            choice = (table_key, tuple(rows))
            if choice != previous:
                st.session_state["research_table_choice"] = choice
                if rows and 0 <= rows[0] < len(ids):
                    st.session_state["research_selected"] = ids[rows[0]]
            selected_id = st.selectbox(
                "Case evidence (accessible case-ID selector)",
                ids,
                index=None,
                placeholder="Select a candidate to inspect its evidence",
                key="research_selected",
            )
            readable_caption(
                "Native table find/sort changes the display only. Search cases above determines exported membership."
            )
            evidence = select_case(bundle, view, selected_id)
            if evidence:
                r = evidence.case
                st.markdown(
                    f"**{pd.Timestamp(r['date']).date()} · {r['mode'].title()} · {MODEL_LABELS[r['model']]}**"
                )
                st.markdown(
                    f"Actual **{r['observed']:,.0f}**, expected **{r['expected']:,.1f}** boardings. Absolute deviation **{r['absolute_deviation']:,.1f}**; percentage deviation **{r['relative_deviation_pct']:+.2f}%**."
                )
                st.markdown(
                    f"Actual deviation direction: **{r['actual_direction']}** · Centered score: **{r['centered_score']:+.2f} ({r['centered_score_sign']})**. These signs answer different questions."
                )
                readable_caption(
                    f"Episode {r['episode_id']} · {r['episode_days_asof']} elapsed days as of this date. Review: {r['review_status']}. Cause: {r['cause']}. Uncertainty: {r['uncertainty']}."
                )
                st.markdown(
                    f"Data quality: `{r['data_quality_status']}` · Prior calendar coverage: {r['prior_calendar_days']}/{r['prior_expected_days']}. Health: `{r['model_health_status']}`."
                )
                with st.expander(
                    "Why flagged, prior observations and cross-mode evidence"
                ):
                    st.markdown(
                        "Frozen rule: absolute centered score > 3.5 AND absolute deviation ≥ max(10,000 boardings, 20% expected). A positive centered score does not necessarily mean above expected ridership."
                    )
                    st.json(
                        {
                            name: evidence.daily[name]
                            for name in [
                                "score",
                                "log_residual",
                                "center",
                                "scale",
                                "training_days",
                                "calibration_days",
                            ]
                        }
                    )
                    readable_caption(
                        "Prior 28-calendar-day same-CTA-day-type context; target excluded. No future observations are included."
                    )
                    if evidence.prior_context.empty:
                        st.info(
                            "Prior comparable observations are unavailable; no zero demand is inferred."
                        )
                    else:
                        st.dataframe(
                            evidence.prior_context,
                            hide_index=True,
                            width="stretch",
                            alt="Dated comparable observations strictly before the case date.",
                        )
                    if r["cross_mode_available"]:
                        st.markdown(
                            f"Other mode: actual {r['cross_mode_observed']:,.0f}, expected {r['cross_mode_expected']:,.1f}; candidate={r['cross_mode_alert']}, actual direction={r['cross_mode_direction']}. Cross-mode agreement does not establish a shared cause."
                        )
                    else:
                        st.info(
                            "Other-mode evidence is unavailable; normal conditions are not inferred."
                        )
                    readable_caption(r["evidence_limitations"])
                with st.expander(
                    "Full episode context — retrospective, may include later dates"
                ):
                    st.dataframe(
                        pd.DataFrame([evidence.episode]),
                        hide_index=True,
                        width="stretch",
                        alt="Full retrospective episode boundaries; not inputs to the case’s as-of priority.",
                    )
        st.header("3 · Model health and limitations")
        st.markdown(
            f"**{NO_GO}** · A locally clear state means only clear under research guards. All historical periods were previously inspected; no independent prospective evaluation occurred."
        )
        readable_caption(
            f"{view.counts['health_warning_dates']} dates with model-health warnings · {view.counts['unknown_health_dates']} dates with unknown/insufficient/gap states. Model-health warnings and ridership candidates are separate concepts."
        )
        with st.expander("Inspect complete-period health evidence and definitions"):
            st.markdown(
                "Stored trailing 28-day diagnostics include prediction error, residual bias, sustained over/underprediction, calibration drift and alert frequency. Values may use dates before your selection. They are never recomputed from the selected slice. Unknown is not healthy; missing observations are not zero-filled."
            )
            st.dataframe(
                view.health,
                hide_index=True,
                width="stretch",
                alt="All model-health evidence for the selected period, independent of candidate filters.",
            )
            readable_caption(
                "The historical grid ends at the last scored date and cannot detect unpublished tail observations or live feed delays. Scores do not identify weather, events, service disruptions or causes."
            )
        st.header("4 · Export research evidence")
        if st.button("Prepare current research export", key="research_prepare"):
            archive = export_research_view(view, selected_id)
            st.download_button(
                "Download filtered research evidence (ZIP)",
                archive,
                "urbanflow_anomaly_research.zip",
                "application/zip",
                key="research_download",
                on_click="ignore",
            )
        readable_caption(
            "ZIP: complete observations, filtered candidates, full-period health, retrospective episode context, selection definitions and provenance. Research only; no files or review decisions are written."
        )
        with st.expander("Source, model version and frozen provenance"):
            st.json(bundle.provenance)
            readable_caption(
                f"Verified research load this rerun: {load_seconds:.3f} s. Source retrieval is not agency publication; research generation time is not recorded."
            )
            for label, path in [
                ("Research methods", "docs/anomaly_research_report.md"),
                ("Validation evidence", "docs/anomaly_validation_report.md"),
                ("Readiness and NO-GO", "docs/anomaly_readiness_report.md"),
                ("Prospective protocol", "docs/anomaly_prospective_protocol.md"),
            ]:
                st.download_button(
                    "Read " + label,
                    (ROOT / path).read_text(),
                    path.split("/")[-1],
                    "text/markdown",
                    key="research_doc_" + path,
                )
