"""Small shared presentation system using public Streamlit container keys."""

import hashlib

import streamlit as st

CAPTION_CSS = """
<style>
[class*="st-key-readable_caption_"] div { opacity: 1; }
[class*="st-key-readable_caption_"] p { color: #526477; }
</style>
"""


def readable_caption(body, *, key=None):
    """Keep native caption semantics/size without translucent low-contrast text.

    Content-derived container keys are stable across reruns. Supply an explicit
    key when identical captions appear more than once on the same page.
    """
    identity = key or hashlib.sha256(str(body).encode()).hexdigest()[:16]
    with st.container(key=f"readable_caption_{identity}"):
        st.caption(body)


PAGE_CSS = """
<style>
.st-key-executive_overview {
  background: transparent; color: #142B49; padding: 0;
  border-radius: 0; gap: 0.75rem;
}
.st-key-executive_overview :is(h1, h2, h3, h4) { color: #142B49; }
.st-key-executive_overview h1 { font-size: 2rem; line-height: 1.2; }
.st-key-executive_overview h2 { font-size: 1.4rem; }
.st-key-executive_overview h3 { font-size: 1.12rem; }
.st-key-executive_overview p { color: #142B49; }
.st-key-executive_overview a { color: #087E83; }
.st-key-executive_overview :is(
  .st-key-overview_intro, .st-key-overview_controls, .st-key-overview_kpis,
  .st-key-overview_service_chart, .st-key-overview_mode_chart,
  .st-key-overview_transparency
) { background: #FFFFFF; border-radius: 10px; padding: 1rem; }
.st-key-executive_overview .st-key-overview_intro { padding: 0; gap: 0.25rem; }
.st-key-executive_overview .st-key-overview_intro h1 { padding-block: 0.3rem; }
.st-key-executive_overview .st-key-overview_controls { border-left: 4px solid #087E83; }
.st-key-executive_overview .st-key-overview_control_note p { color: #526477; }
.st-key-executive_overview .st-key-overview_baseline_control button[role="radio"] {
  background: #FFFFFF; color: #142B49; border: 1px solid #73859A;
  border-radius: 6px; padding: 0.65rem 1rem; font-weight: 600; min-height: 44px;
}
.st-key-executive_overview .st-key-overview_baseline_control button[role="radio"] p { color: inherit; }
.st-key-executive_overview .st-key-overview_baseline_control button[role="radio"]:hover {
  background: #EAF5F4; border-color: #087E83;
}
.st-key-executive_overview .st-key-overview_baseline_control button[role="radio"][aria-checked="true"] {
  background: #087E83 !important; color: #FFFFFF !important; border-color: #087E83;
}
.st-key-executive_overview .st-key-overview_baseline_control button[role="radio"][aria-checked="true"]:hover {
  background: #066C71 !important; border-color: #066C71;
}
.st-key-executive_overview :is(button, input, a, summary):focus-visible {
  outline: 3px solid #142B49; outline-offset: 3px;
}
.st-key-executive_overview .st-key-overview_summary {
  background: transparent; padding: 0.25rem 0; gap: 0.6rem;
}
.st-key-executive_overview [class*="st-key-overview_insight_card_"] {
  background: #FFFFFF; border-radius: 10px; padding: 1rem;
}
.st-key-executive_overview [class*="st-key-overview_evidence_"] {
  background: #EDF3FC; border-left: 3px solid #3D76BC;
  border-radius: 6px; padding: 0.75rem 1rem;
}
.st-key-executive_overview [class*="st-key-overview_planning_"] {
  background: #EAF5F4; border-left: 3px solid #087E83;
  border-radius: 6px; padding: 0.75rem 1rem;
}
.st-key-executive_overview [class*="st-key-overview_limitation_"] {
  background: #FFF5E5; border-left: 3px solid #C08431;
  border-radius: 6px; padding: 0.75rem 1rem;
}
.st-key-executive_overview .st-key-overview_summary h2 {
  font-size: 1.2rem; font-weight: 700; line-height: 1.4; margin: 0 0 1rem; padding: 0;
}
.st-key-executive_overview .st-key-overview_summary p { color: #526477; line-height: 1.5; margin: 0 0 1rem; }
.st-key-executive_overview [class*="st-key-overview_section_"] p {
  color: #526477; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em;
}
.st-key-executive_overview .st-key-overview_kpis { padding: 0.75rem 0; gap: 0.5rem; }
.st-key-executive_overview .st-key-overview_kpis h3 { padding-block: 0.2rem 0.5rem; }
</style>
"""


def page_styles(root_key, prefix):
    """Scope shared typography, surfaces, and focus states to one page."""
    return PAGE_CSS.replace('executive_overview', root_key).replace('overview_', prefix + '_')


def apply_page_styles(root_key, prefix):
    st.html(page_styles(root_key, prefix))
