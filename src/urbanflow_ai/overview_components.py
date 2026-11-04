"""Page-scoped Executive Overview presentation components; no analytics or I/O."""

import re

import streamlit as st

# Shared TOML remains unchanged because its colors apply to every page. These
# styles target only documented container key classes and native HTML states.
from .ui_design import page_styles

OVERVIEW_CSS = page_styles('executive_overview', 'overview')


def apply_overview_styles():
    """Insert static CSS that cannot affect a page without the Overview root key."""
    st.html(OVERVIEW_CSS)


def recovery_baseline():
    """Keep both approved choices visible, with one required native selection."""
    with st.container(key="overview_baseline_control"):
        return st.segmented_control(
            "Recovery baseline", ["2019", "2017-2019"],
            default="2019", required=True, key="overview_baseline", width="stretch",
            format_func=lambda option: "2019 reference" if option == "2019" else "2017–2019 average",
            help="Baseline means the historical reference period; index 100 equals its ridership level. Changes recovery indices, related findings, and both trajectory charts. Fixed-calendar composition retains its stated 2019 weights.",
        )


def emphasize_figures(text):
    """Bold existing decimal figures without changing their values or wording."""
    return re.sub(r"(?<![\w.])(\d+\.\d+%?)(?![\w.])", r"**\1**", text)


def insight_card(finding, index):
    """Render one finding with labeled evidence, meaning, next step, and caution."""
    with st.container(border=True, key=f"overview_insight_card_{index}", gap="small"):
        st.markdown(f"### {finding['title']}")
        with st.container(key=f"overview_evidence_{index}", gap="xsmall"):
            st.markdown("**Evidence**")
            st.markdown(emphasize_figures(finding['evidence']))
        st.markdown(f"**Interpretation** · {finding['interpretation']}")
        planning, limitation = st.columns(2, gap="small")
        with planning:
            with st.container(key=f"overview_planning_{index}", height="stretch", gap="xsmall"):
                st.markdown("**Planning implication**")
                st.markdown(finding['planning'])
        with limitation:
            with st.container(key=f"overview_limitation_{index}", height="stretch", gap="xsmall"):
                st.markdown("**Limitation**")
                st.markdown(finding['limitation'])


def section_label(text, key):
    """Render a compact, high-contrast section label within the Overview."""
    with st.container(key=f"overview_section_{key}"):
        st.markdown(f"**{text}**")


def executive_summary(model):
    """Separate the existing finding from its supporting evidence, without edits."""
    headline, separator, evidence = model['summary'].partition('. ')
    with st.container(key="overview_summary", gap="xsmall"):
        st.markdown(f"## {headline}{'.' if separator else ''}")
        if evidence:
            st.markdown(evidence)
