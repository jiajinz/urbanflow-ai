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


def test_line_styles_preserve_values_colors_and_missing_observations():
    from urbanflow_ai.dashboard_charts import style

    figure = go.Figure([
        go.Scatter(x=[2024, 2025], y=[70.9, None], name='Bus', line={'color': '#0072B2'}, connectgaps=False),
        go.Scatter(x=[2024, 2025], y=[59.4, None], name='Rail', line={'color': '#D55E00'}, connectgaps=False),
    ])
    before = [(tuple(trace.x), tuple(trace.y), trace.line.color, trace.connectgaps) for trace in figure.data]
    style(figure, y_title='Recovery index', x_title='Year')
    assert [(tuple(trace.x), tuple(trace.y), trace.line.color, trace.connectgaps) for trace in figure.data] == before
    assert figure.data[0].line.dash != figure.data[1].line.dash


def test_overview_charts_have_names_and_exact_table_alternatives(monkeypatch):
    import pandas as pd
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from urbanflow_ai.dashboard_data import load_bundle
    from urbanflow_ai.overview import overview_model

    monkeypatch.setenv('URBANFLOW_DATA_BACKEND', 'snapshot')
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'streamlit_app.py'), default_timeout=30).run()
    assert not app.exception
    assert all(item.proto.alt for item in app.get('plotly_chart'))
    assert any('Recovery trajectories' == item.value for item in app.header)
    for baseline in ['2019', '2017-2019']:
        app.button_group(key='overview_baseline').set_value(baseline).run()
        model = overview_model(load_bundle(), baseline)
        pd.testing.assert_frame_equal(app.dataframe[1].value, model['chart_trend'], check_dtype=False)
        pd.testing.assert_frame_equal(app.dataframe[2].value, model['mode_trend'], check_dtype=False)
