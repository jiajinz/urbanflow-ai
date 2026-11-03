"""Presentation contracts: scoped styling and unchanged plotted evidence."""

import json

import plotly.graph_objects as go

from urbanflow_ai.explorer_components import refine_explorer_figure
from urbanflow_ai.ui_design import page_styles


def test_shared_style_is_page_scoped_and_preserves_native_focus():
    css = page_styles('research_methodology', 'methodology')
    assert '.st-key-research_methodology' in css
    assert 'executive_overview' not in css
    assert ':focus-visible' in css
    assert 'st-emotion' not in css


def test_explorer_refinement_preserves_data_and_colors():
    figure = go.Figure(go.Scatter(x=[2024, 2025], y=[70.9, None], line={'color': '#0072B2'}))
    figure.add_annotation(text='Service=Weekday (W)', x=1, y=0.5, textangle=90)
    before = json.dumps(figure.to_plotly_json()['data'], sort_keys=True)
    refined = refine_explorer_figure(figure, 'Recovery')
    assert json.dumps(refined.to_plotly_json()['data'], sort_keys=True) == before
    assert refined.layout.annotations[0].text == 'Weekday (W)'
    assert refined.layout.annotations[0].textangle == 0
    assert refined.layout.annotations[-1].text == 'Baseline = 100'
