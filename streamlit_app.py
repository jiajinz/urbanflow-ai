"""UrbanFlow AI decision-support application entrypoint."""

import streamlit as st

from urbanflow_ai.ui_design import CAPTION_CSS, readable_caption



def main():
    st.set_page_config(page_title="UrbanFlow AI | Transit Decision Intelligence", layout="wide")
    st.html(CAPTION_CSS)
    with st.sidebar:
        st.markdown("### UrbanFlow AI")
        readable_caption("TRANSIT DECISION INTELLIGENCE")
        readable_caption(
            "Data provided by Chicago Transit Authority (CTA). Independent project; no agency affiliation or endorsement."
        )
    page = st.navigation([
        st.Page("app_pages/overview.py", title="Executive Overview", default=True),
        st.Page("app_pages/explorer.py", title="Ridership Explorer", url_path="explorer"),
        st.Page("app_pages/methodology.py", title="Research & Methodology", url_path="methodology"),
        st.Page("app_pages/anomaly_research.py", title="Anomaly Research Explorer", url_path="anomaly-research"),
    ])
    page.run()


if __name__ == "__main__":
    main()
