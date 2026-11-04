"""Streamlit pages: presentation and widgets only; analytical logic stays separate."""

import os
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from .dashboard_charts import DAY_LABELS, MODE_LABELS, explorer_chart, mode_comparison, recovery_trend
from .dashboard_data import DEFAULT_BUNDLE, load_data
from .dashboard_metrics import ExplorerFilter, executive_model, explorer_series, selected_daily
from .data_access import DataAccessError
from .ui_design import readable_caption

ROOT = Path(__file__).resolve().parents[2]


@st.cache_data(ttl=300, max_entries=4, show_spinner="Loading validated analytical data…")
def cached_data(backend, directory, version):
    """Cache only data, keyed by explicit backend and snapshot modification time."""
    return load_data(backend, directory)


def dataset():
    backend = os.environ.get("URBANFLOW_DATA_BACKEND", "snapshot")
    directory = Path(os.environ.get("URBANFLOW_SNAPSHOT_DIR", str(DEFAULT_BUNDLE)))
    manifest = directory / "manifest.json"
    version = manifest.stat().st_mtime_ns if backend == "snapshot" and manifest.exists() else 0
    try:
        data = cached_data(backend, str(directory), version)
    except DataAccessError as exc:
        st.error(str(exc))
        readable_caption("No fabricated data or automatic backend fallback is used.")
        st.stop()
    with st.sidebar:
        st.divider()
        readable_caption("DATA ENVIRONMENT")
        st.write("Historical Parquet snapshot" if backend == "snapshot" else "Local PostgreSQL · read only")
        coverage = data.metadata['coverage']
        readable_caption(f"{coverage['first_date']} → {coverage['last_date']}\n\n{coverage['row_count']:,} validated daily records")
        if st.button("Refresh analytical data", key="refresh_data", help="Reload the selected backend. This does not call the CTA API."):
            cached_data.clear()
            st.rerun()
    return data


def header(data, eyebrow, title, description):
    readable_caption(f"URBANFLOW AI / {eyebrow.upper()}")
    st.title(title)
    st.write(description)
    metadata = data.metadata
    source_time = metadata.get('source_retrieved_at_utc')
    source_label = f"Source retrieved {source_time[:10]} UTC" if source_time else "Source retrieval time not recorded"
    freshness = (f"{source_label} · Snapshot generated {metadata.get('generated_at_utc', '')[:10]} UTC"
                 if metadata.get('backend') == 'snapshot' else f"Database read {metadata.get('database_read_at_utc', '')[:19]} UTC · Source publication time is not tracked")
    readable_caption(f"Historical reporting through {metadata['coverage']['last_date']} · {freshness} · Not a live CTA feed")


def plot(figure, description):
    st.plotly_chart(figure, width="stretch", config={"displaylogo": False, "scrollZoom": False}, alt=description)


def executive_overview():
    from .overview import overview_model
    from .dashboard_charts import weekday_mode_trend
    from .overview_components import apply_overview_styles, insight_card, recovery_baseline, section_label, executive_summary

    data = dataset()
    with st.container(key="executive_overview", gap="small"):
        apply_overview_styles()
        with st.container(key="overview_intro"):
            header(data, "Executive overview", "Transit recovery is not one story.",
                   "Explore Chicago Transit Authority (CTA) bus and rail ridership compared with pre-pandemic levels.")
        with st.container(key="overview_controls", gap="small"):
            with st.container(key="overview_control_note", gap="xsmall"):
                section_label("01 · CHOOSE THE REFERENCE", "reference")
                st.markdown("Baseline means the historical reference period. Annual metrics keep their stated year; calendar-adjusted shares use fixed 2019 weights.")
            baseline = recovery_baseline()
        model = overview_model(data, baseline)
        if model is None:
            st.info("A complete post-2019 year with all three day types and supported baseline data is required for the executive comparison.")
            return
        executive_summary(model)
        with st.container(key="overview_kpis"):
            section_label("02 · REVIEW RECOVERY LEVELS", "metrics")
            st.header(f"{model['year']} · latest complete calendar year")
            columns = st.columns(4)
            labels = ["Weekday index", "Saturday index", "Sun/holiday index", "Bus–rail gap (W)"]
            keys = ["W", "A", "U", "mode_gap"]
            for column, label, key in zip(columns, labels, keys):
                unit = " pp" if key == "mode_gap" else ""
                meaning = ("Bus index minus rail index; pp means percentage points." if key == "mode_gap"
                           else "Recovery index: 100 equals the historical reference level; 70 means 30% below it. The twelve monthly comparisons receive equal weight.")
                column.metric(label, f"{model['metrics'][key]:.2f}{unit}", border=True,
                              help=f"Period: {model['year']} complete year. Baseline: {baseline}. {meaning}")
            readable_caption(f"Unit: recovery index ({baseline} = 100), except the mode gap in percentage points. Twelve monthly indices receive equal weight; this is not an annual-total ratio. Partial latest years are excluded from these cards.")

        section_label("03 · EXPLORE THE SUPPORTING EVIDENCE", "charts")
        st.header("Recovery trajectories")
        chart_years = st.select_slider("Recovery chart years", options=list(model['available_years']),
                                      value=(model['available_years'][0], model['available_years'][-1]),
                                      key="overview_chart_years",
                                      help="Changes the two monthly trajectory charts only. Annual KPIs and research findings keep their stated periods.")
        model = overview_model(data, baseline, tuple(chart_years))
        readable_caption(f"Chart window: {model['chart_period']} · {baseline} baseline = 100 · Monthly observations, including published months of partial years. Annual KPIs above remain {model['year']}.")
        with st.container(key="overview_service_chart"):
            st.subheader("How weekday and weekend/holiday demand recovered")
            plot(recovery_trend(model['chart_trend']), "Monthly total recovery by weekday, Saturday and Sunday/holiday, relative to the selected baseline of 100. Exact monthly values are in the calculation evidence table below.")
            readable_caption("Each point compares the same calendar month and CTA day type. W = weekday; A = Saturday; U = Sunday/holiday, including holidays on calendar weekdays. This normalization is not formal seasonal adjustment.")
        with st.container(key="overview_mode_chart"):
            st.subheader("Weekday bus versus rail · recovery over time")
            plot(weekday_mode_trend(model['mode_trend']), "Monthly weekday bus and rail recovery relative to the selected baseline of 100. Bus is solid and rail is dashed; exact values are available below.")
            readable_caption("Bus and rail use their own same-month weekday baseline daily means. This chart compares recovery levels, not unique riders, trip purpose, or the causes of demand changes.")
        with st.expander(f"Compare all three day types in complete {model['year']}"):
            plot(mode_comparison(model['period']), "Bus and rail mean monthly recovery for the latest complete year, grouped by CTA day type. Numeric labels and the annual KPI table provide the values.")
        section_label("04 · INTERPRET THE FINDINGS", "findings")
        st.header("Evidence and planning implications")
        for index, finding in enumerate(model['insights']):
            insight_card(finding, index)
        with st.container(key="overview_transparency"):
            st.header("Data transparency")
            coverage = data.metadata['coverage']
            st.markdown("[CTA Daily Boarding Totals · Chicago Data Portal](https://data.cityofchicago.org/Transportation/CTA-Ridership-Daily-Boarding-Totals/6iiy-9s97)")
            st.write(f"Validated historical coverage: {coverage['first_date']} to {coverage['last_date']}; {coverage['row_count']:,} daily records. The last available observation is {coverage['last_date']}. Boardings measure rides, not unique people.")
            st.write("July 2012's 31 source rows have 07:00 timestamps and are excluded from analysis and retained for review (quarantined) by the existing midnight-only validation rule. They are not zero-filled. This gap excludes July 2012 and complete-year 2012 comparisons in the 4A historical analyses; it does not affect the 2017–2019 baselines or the post-2019 recovery charts shown here.")
            readable_caption("The quarantine explanation refers to the archived 4A source audit. PostgreSQL mode does not infer original quarantine counts or CTA publication times from stored rows. Backend and retrieval/export/read timestamps are shown above and in the sidebar.")
        with st.expander("Baseline definitions and calculation evidence"):
            st.write("2019: the same month/day type in the last full pre-pandemic year. 2017–2019: equal mean of the three years' same-month/day-type daily means. Recovery = 100 × target mean / baseline mean. Missing/zero denominators are unavailable. Neither baseline models a no-pandemic counterfactual.")
            st.dataframe(model['period'], hide_index=True, width="stretch", alt="Latest complete-year recovery KPI evidence by CTA day type.")
            st.dataframe(model['chart_trend'], hide_index=True, width="stretch", alt="Exact selected monthly total recovery values by CTA day type and baseline.")
            st.dataframe(model['mode_trend'], hide_index=True, width="stretch", alt="Exact selected monthly weekday bus and rail recovery values.")
            st.dataframe(data.composition, hide_index=True, width="stretch", alt="Matched-calendar demand composition evidence using fixed 2019 weights.")
            for finding in model['insights']:
                readable_caption(finding['source'])
            st.download_button("Download annual KPI evidence", model['period'].to_csv(index=False), "urbanflow_overview_evidence.csv", "text/csv")
            st.download_button("Download selected monthly recovery evidence", model['chart_trend'].to_csv(index=False), "urbanflow_overview_monthly.csv", "text/csv")
            st.download_button("Download matched-calendar composition evidence", data.composition.to_csv(index=False), "urbanflow_composition_evidence.csv", "text/csv")
        readable_caption("Research basis: docs/insight_report.md · Observational decision support; no forecast or causal attribution.")


def ridership_explorer():
    from .explorer import explorer_model
    from .explorer_components import apply_explorer_styles, explorer_plot

    data = dataset()
    first, last = data.daily.service_date.min(), data.daily.service_date.max()
    with st.container(key="ridership_explorer", gap="small"):
        apply_explorer_styles()
        with st.container(key="explorer_intro"):
            header(data, "Ridership explorer", "Ask a comparable question.",
                   "Explore Chicago Transit Authority (CTA) ridership by date, day type, and bus or rail.")
        with st.container(key="explorer_controls", gap="small"):
            with st.container(key="explorer_question_control"):
                question = st.segmented_control("1 · Select an analytical question",
                    ['Trend', 'Recovery', 'Year-over-year', 'Seasonal'], default='Recovery', required=True,
                    key='explorer_question', width='stretch')
            readable_caption("2 · Choose relevant filters. Dates select target observations; reference periods are explained below.")
            left, right = st.columns(2)
            with left:
                dates = st.date_input("Service date range (inclusive)",
                    (max(first, date(last.year - 2, 1, 1)), last), min_value=first, max_value=last,
                    key='explorer_dates')
                with st.container(key='explorer_type_control'):
                    kinds = st.pills('CTA day types', list(DAY_LABELS), default=['W'], help='W = weekday; A = Saturday; U = Sunday/holiday, including holidays on weekdays.',
                        selection_mode='multi', format_func=DAY_LABELS.get, key='explorer_types')
            baseline, aggregation = '2019', 'Monthly'
            with right:
                with st.container(key='explorer_mode_control'):
                    modes = st.pills('Ridership modes', list(MODE_LABELS), default=['bus', 'rail'],
                        selection_mode='multi', format_func=MODE_LABELS.get, key='explorer_modes')
                if question == 'Recovery':
                    with st.container(key='explorer_baseline_control'):
                        baseline = st.segmented_control('Recovery baseline', ['2019', '2017-2019'],
                            default='2019', required=True, key='explorer_baseline', width='stretch', help='Historical reference period: 100 equals its same-month, same-day-type average. The 2017–2019 option gives each year equal weight.')
                elif question == 'Trend':
                    with st.container(key='explorer_aggregation_control'):
                        aggregation = st.segmented_control('Aggregation', ['Monthly', 'Annual', 'Daily'],
                            default='Monthly', required=True, key='explorer_aggregation', width='stretch')
            if len(dates) != 2:
                st.info('Select both a start and an end date.')
                return
            start, end = dates
            year_options = list(range(start.year, end.year + 1))
            years = year_options
            if question == 'Seasonal':
                previous = st.session_state.get('explorer_years')
                if previous is not None and any(year not in year_options for year in previous):
                    st.session_state['explorer_years'] = [year for year in previous if year in year_options] or year_options[-2:]
                years = st.multiselect('Comparison years', year_options, default=year_options[-2:], key='explorer_years')
        filters = ExplorerFilter(start, end + timedelta(days=1), tuple(kinds), tuple(modes), tuple(years), baseline)
        model = explorer_model(data, filters, question, aggregation)
        selections = f"{start}–{end} inclusive · {', '.join(MODE_LABELS[mode] for mode in modes) or 'No mode'} · {', '.join(DAY_LABELS[kind] for kind in kinds) or 'No day type'}"
        if question == 'Recovery':
            selections += f" · Baseline {baseline}"
        if question == 'Seasonal':
            selections += f" · Years {', '.join(map(str, years)) or 'None'}"
        readable_caption(f"Active selection: {selections}")
        readable_caption(f"Metric: {model['unit']} · Complete-period requirements apply.")
        if model['missing_days']:
            st.warning(f"{model['missing_days']} selected calendar dates have no validated record before day-type filtering. July 2012 contains quarantined timestamps in the 4A archive. Missing observations are not zero-filled.")
        if model['view'] != 'Daily' and model['excluded_months']:
            readable_caption(f"{model['excluded_months']} intersecting months are partial selections or have missing validated dates; they do not contribute complete-period metrics.")
        if model['view'] == 'Yearly' and not model['year_coverage'].empty:
            excluded = model['year_coverage'].loc[~model['year_coverage'].eligible, 'year'].tolist()
            if excluded:
                readable_caption(f"Annual comparison excludes {', '.join(map(str, excluded))}: twelve fully selected, complete calendar months are required.")
        if model['unavailable_references']:
            readable_caption(f"{model['unavailable_references']} mode/day-type comparisons lack a valid previous-year reference; percentages stay blank. Inspect reference means and comparison status in the export table.")
        rolling = False
        if model['view'] == 'Daily':
            if model['rolling_available']:
                rolling = st.toggle('Show trailing 7-day averages', value=True, key='show_rolling')
            else:
                readable_caption('Seven-day averages are unavailable for this selection: seven consecutive observed and selected calendar dates are required. Include all CTA day types and a sufficient date range.')
        if model['selected_dates'] == 0:
            st.info('No observed records match this selection. Choose at least one mode, day type, and year, or change the dates. Missing dates are not zero boardings.')
        elif model['valid_points'] == 0 and model['unavailable_references']:
            st.info('No comparable YoY result: previous same-month/day-type means are missing or zero. No percentage is imputed. Inspect the reference evidence below.')
        elif model['valid_points'] == 0:
            st.info('Insufficient complete, comparable data for this view. Widen the range or select Trend → Daily to inspect available observations.')
        else:
            st.header(f"3 · {question} · {model['unit']}")
            readable_caption(f"{model['selected_dates']:,} matching observed service dates · {model['valid_points']:,} available plotted points")
            with st.container(border=True, key='explorer_chart'):
                explorer_plot(model['series'], model['view'], model['unit'], show_rolling=rolling)
        with st.expander('Metric definition and comparison rules'):
            st.markdown(model['definition'])
        with st.container(key='explorer_limitation_metric', gap='xsmall'):
            st.markdown('**Interpretation and limitations**')
            st.markdown(model['limitation'])
            readable_caption('Different observed recovery or growth does not prove changes in trip purpose, modal substitution, or the effect of a specific policy.')
        with st.expander('4 · Inspect coverage and export the current selection'):
            st.dataframe(model['series'], hide_index=True, width='stretch', alt='Exact plotted metrics for the active Explorer selection, with unavailable values left blank.')
            st.dataframe(model['coverage'], hide_index=True, width='stretch', alt='Monthly calendar coverage and complete versus partial selection status.')
            if model['view'] == 'Yearly':
                st.dataframe(model['year_coverage'], hide_index=True, width='stretch', alt='Annual eligibility based on twelve selected complete months.')
            readable_caption('The CSV is the plotted series, including explicit null gaps. Coverage describes calendar dates before day-type filtering; a missing date has no inferred CTA day type.')
            st.download_button('Download plotted metrics', model['series'].to_csv(index=False),
                'urbanflow_explorer_metrics.csv', 'text/csv')
            st.download_button('Download period coverage', model['coverage'].to_csv(index=False),
                'urbanflow_explorer_coverage.csv', 'text/csv')
            context = dict(question=question, view=model['view'], metric=model['unit'], definition=model['definition'],
                           start_date=str(start), end_date_inclusive=str(end), modes=modes, day_types=kinds, years=years,
                           baseline=baseline if question == 'Recovery' else None,
                           reference_policy='Full historical same-month/day-type reference' if question in ('Recovery', 'Year-over-year') else None,
                           source_url=data.metadata.get('source_url'), backend=data.metadata.get('backend'),
                           latest_observation=data.metadata['coverage']['last_date'])
            st.download_button('Download selection definitions', json.dumps(context, indent=2),
                'urbanflow_explorer_selection.json', 'application/json')


def research_methodology():
    """Explain existing evidence without changing analytical definitions."""
    from .methodology import METRICS, REPRODUCE, SECTIONS, SOURCE_URL, provenance_labels

    data = dataset()
    metadata = data.metadata
    labels = provenance_labels(metadata)
    with st.container(key="research_methodology", gap="small"):
        from .ui_design import apply_page_styles
        apply_page_styles('research_methodology', 'methodology')
        readable_caption("URBANFLOW AI / RESEARCH & METHODOLOGY")
        st.title("Know what the numbers can support.")
        st.markdown("Understand the Chicago Transit Authority (CTA) data, comparisons, and supporting evidence.")

        st.header(SECTIONS[0])
        st.markdown(f"[CTA — Ridership — Daily Boarding Totals · 6iiy-9s97]({SOURCE_URL})")
        with st.container(horizontal=True):
            st.metric("Validated daily records", labels['records'], border=True)
            st.metric("First validated service date", labels['first'], border=True)
            st.metric("Latest validated service date", labels['last'], border=True)
        st.markdown(f"**{labels['environment']} · Not a live CTA feed.** One record describes systemwide boardings on one service date. Boardings are rides, not unique passengers.")
        readable_caption(f"Source retrieved (UTC): {labels['retrieved']} · Snapshot generated (UTC): {labels['generated']}")
        if metadata.get('backend') != 'snapshot':
            readable_caption(f"Database read (UTC): {labels['read']}. Original source retrieval and quarantine counts may be unknown.")
        readable_caption("Retrieval, snapshot generation, and database read times are not agency publication dates. Historical snapshots do not update themselves.")

        st.header(SECTIONS[1])
        st.markdown(f"**Current validated data:** {labels['records']} records; {labels['missing']} missing calendar dates within coverage; {labels['duplicates']} duplicate dates. "
                    f"Original source rows: {labels['source_rows']}; source rows excluded and retained for review (quarantined): {labels['quarantined']}.")
        with st.expander('Validation rules and field definitions'):
            st.markdown("`service_date` is the daily key; `day_type` is W/A/U; `bus`, `rail_boardings`, and `total_rides` count boardings. Required fields → strict date and nonnegative integer parsing → duplicate detection → bus + rail = total reconciliation → calendar coverage audit. Invalid or absent values are rejected, not imputed.")
        st.warning("Archived 4A case · July 2012: 31 source rows contain 07:00 timestamps. The validator accepts ISO dates or midnight timestamps only. "
                   "The source was preserved unchanged; these timestamps were not silently truncated or normalized. Their underlying cause has not been established.")
        with st.expander("Inspect the July 2012 evidence and downstream effects"):
            st.markdown("`data/history/cta-2026-11-01-v1/quarantine.json` retains the raw records and exact rejection: "
                        "`service_date must be a valid ISO date or midnight timestamp`. "
                        "Example: `2012-07-01T07:00:00.000`, bus 474,631 + rail 350,123 = total 824,754. Reconciled counts do not override an invalid date.")
            st.markdown("Rejected rows are individual validation outcomes. Quarantine preserves those raw rows for review; no additional valid dates are removed as a period-level rule. "
                        "The resulting validated archive lacks July 1–31, 2012. July is ineligible for complete-month analysis; 2012 is an incomplete year. "
                        "July 2013 monthly YoY and 2013 annual YoY lack complete prior periods. Other complete months remain usable. "
                        "This archived case is evidence about the 4A archive, not an inferred rejection count for another PostgreSQL dataset.")
        st.markdown("Complete months require every calendar date before day-type grouping. Complete years require every date in the year. Partial selections and missing observations are distinct reasons for unavailable comparisons.")
        with st.expander("Inspect current monthly coverage"):
            st.dataframe(pd.DataFrame(metadata.get('coverage', {}).get('monthly', [])), hide_index=True,
                         width="stretch", alt="Current validated monthly calendar coverage")

        st.header(SECTIONS[2])
        with st.container(key="methodology_evidence_definition"):
            st.markdown("Compare **like months and CTA day types**. Recovery index compares boardings with a historical reference (baseline = 100); year-over-year (YoY) compares with the previous year; mode share is the percentage of total boardings made by bus or rail. These metrics answer different questions.")
        for title, (definition, detail) in METRICS.items():
            with st.expander(title):
                st.markdown(definition)
                st.markdown(detail)

        st.header(SECTIONS[3])
        st.markdown("**Data limits:** systemwide boardings, without service supply or unique passengers. **Assumptions:** matched calendar comparisons, not causal attribution.")
        with st.expander('Data limitations, assumptions, and questions requiring other data'):
            st.markdown("**Confirmed data limits.** No route, station, time-of-day, unique-rider, delivered-service, capacity, weather, or trip-purpose fields. U combines Sundays and holidays. Latest reporting periods may be incomplete; source validation does not independently verify measurement accuracy.")
            st.markdown("**Methodological assumptions.** Same-month/day-type means improve comparability but do not align individual holidays or remove all seasonality. Equal-year baselines and equal-month recovery summaries are deliberate weighting choices. Neither baseline estimates a no-pandemic counterfactual.")
            st.markdown("**Questions requiring other data.** Remote work, reliability, events, and substitution are hypotheses, not established causes. Investigate route loads and delivered service before changing allocation. Event attribution, causal models, forecasting, and AI reporting are not implemented.")

        st.header(SECTIONS[4])
        st.markdown("[Project repository](https://github.com/jiajinz/urbanflow-ai) · Run from an installed checkout containing the versioned data. Output directories must be new; do not overwrite validated snapshots.")
        with st.expander("Execution flow and source files"):
            st.markdown("1. `history.backfill()` discovers and paginates the official API with bounded retries; `processing.process_records()` validates; `database.py` persists transactional idempotent upserts. Quarantine requires explicit opt-in. This online workflow requires PostgreSQL and API access.\n"
                        "2. `research.monthly_aggregates()` runs `sql/research_monthly.sql` with parameterized date bounds; `research.py` builds recovery, composition, and sensitivity tables. `research_plots.py` renders their evidence.\n"
                        "3. `dashboard_data.export_bundle()` creates six versioned Parquet tables. `load_bundle()` checks file and definition hashes and coverage without API/PostgreSQL access. Local `load_postgres()` uses a read-only repeatable-read transaction. Backend errors never trigger fallback.\n"
                        "4. `dashboard_ui.dataset()` caches the selected backend for up to five minutes. Refresh reloads that backend, not the CTA API. `explorer.explorer_model()` supplies the same analytical series to charts and exports.")
            st.markdown("Documentation: `docs/insight_report.md`, `docs/dashboard_spec.md`, and `docs/milestone_4b2c_review.md`. SQL: `src/urbanflow_ai/sql/`. Tests: `tests/test_research.py`, `tests/test_dashboard_data.py`, `tests/test_explorer.py`, `tests/test_methodology.py`.")
        with st.expander("Offline reproduction, tests, and local preview"):
            st.code(REPRODUCE, language="bash")
            readable_caption("Without TEST_DATABASE_URL, PostgreSQL integration tests are skipped. Offline reproduction requires no external API. See the phase review for commands actually verified and their results.")
        st.download_button("Download current data provenance", json.dumps(metadata, indent=2), "urbanflow_provenance.json", "application/json")
        st.download_button("Download the complete 4A insight report", (ROOT / "docs/insight_report.md").read_text(), "urbanflow_insight_report.md", "text/markdown")
