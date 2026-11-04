"""Streamlit multipage tests using the real versioned analytical snapshot."""

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'streamlit_app.py'


def start(monkeypatch):
    monkeypatch.setenv('URBANFLOW_DATA_BACKEND', 'snapshot')
    monkeypatch.delenv('URBANFLOW_SNAPSHOT_DIR', raising=False)
    return AppTest.from_file(str(APP), default_timeout=30).run()


def test_overview_metrics_match_research_and_baseline_switch(monkeypatch):
    app = start(monkeypatch)
    assert not app.exception
    assert [metric.value for metric in app.metric] == ['70.90', '88.10', '89.29', '22.28 pp']
    app.button_group(key='overview_baseline').set_value('2017-2019').run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ['69.18', '84.95', '85.93', '21.67 pp']


def test_explorer_navigation_filters_and_views(monkeypatch):
    app = start(monkeypatch).switch_page('app_pages/explorer.py').run()
    assert not app.exception
    assert app.title[0].value == 'Ask a comparable question.'
    for question in ['Trend', 'Year-over-year', 'Seasonal', 'Recovery']:
        app.button_group(key='explorer_question').set_value(question).run()
        assert not app.exception
    app.button_group(key='explorer_question').set_value('Trend').run()
    for aggregation in ['Monthly', 'Annual', 'Daily']:
        app.button_group(key='explorer_aggregation').set_value(aggregation).run()
        assert not app.exception
    app.button_group(key='explorer_modes').set_value([]).run()
    assert not app.exception
    assert 'No observed records' in app.info[0].value


def test_explorer_missing_dates_and_partial_year(monkeypatch):
    app = start(monkeypatch).switch_page('app_pages/explorer.py').run()
    app.date_input(key='explorer_dates').set_value((date(2012, 7, 1), date(2012, 7, 31))).run()
    assert not app.exception
    assert 'No observed records' in app.info[0].value
    assert any('31 selected calendar dates' in warning.value for warning in app.warning)
    app.date_input(key='explorer_dates').set_value((date(2026, 1, 1), date(2026, 8, 31))).run()
    app.button_group(key='explorer_question').set_value('Trend').run()
    app.button_group(key='explorer_aggregation').set_value('Annual').run()
    assert not app.exception
    assert any('Insufficient complete' in item.value for item in app.info)


def test_methodology_navigation_and_provenance(monkeypatch):
    app = start(monkeypatch).switch_page('app_pages/methodology.py').run()
    assert not app.exception
    assert app.title[0].value == 'Know what the numbers can support.'
    assert any('9,343' in paragraph.value for paragraph in app.markdown)
    assert any('not implemented' in paragraph.value for paragraph in app.markdown)


def test_missing_snapshot_is_actionable_without_fabricated_output(monkeypatch, tmp_path):
    monkeypatch.setenv('URBANFLOW_DATA_BACKEND', 'snapshot')
    monkeypatch.setenv('URBANFLOW_SNAPSHOT_DIR', str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert app.error
    assert not app.metric


def test_overview_chart_period_is_independent_of_cards(monkeypatch):
    app = start(monkeypatch)
    before = [metric.value for metric in app.metric]
    app.select_slider(key='overview_chart_years').set_value((2026, 2026)).run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == before
    assert any('Jan 2026–Aug 2026' in caption.value for caption in app.caption)
    assert any('July 2012' in item.value for item in app.markdown)
    assert any('Planning implication' in item.value for item in app.markdown)


def test_overview_corrupt_snapshot_has_error_and_no_metrics(monkeypatch, tmp_path):
    import shutil
    from urbanflow_ai.dashboard_data import DEFAULT_BUNDLE
    directory = tmp_path / 'corrupt'
    shutil.copytree(DEFAULT_BUNDLE, directory)
    (directory / 'recovery.parquet').write_bytes(b'invalid')
    monkeypatch.setenv('URBANFLOW_DATA_BACKEND', 'snapshot')
    monkeypatch.setenv('URBANFLOW_SNAPSHOT_DIR', str(directory))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert 'checksum' in app.error[0].value
    assert not app.metric


def test_overview_semantic_cards_preserve_findings_and_plot_data(monkeypatch):
    import json
    from urbanflow_ai.dashboard_data import load_bundle
    from urbanflow_ai.overview import overview_model
    from urbanflow_ai.dashboard_charts import recovery_trend, weekday_mode_trend, mode_comparison
    app = start(monkeypatch)
    assert app.button_group(key='overview_baseline').label == 'Recovery baseline'
    assert app.button_group(key='overview_baseline').value == '2019'
    model = overview_model(load_bundle())
    rendered = '\n'.join(item.value.replace('**', '') for item in app.markdown)
    for finding in model['insights']:
        for field in ('evidence', 'interpretation', 'planning', 'limitation'):
            assert finding[field] in rendered
    expected = [recovery_trend(model['chart_trend']), weekday_mode_trend(model['mode_trend']), mode_comparison(model['period'])]
    for actual, figure in zip(app.get('plotly_chart'), expected, strict=True):
        assert json.loads(actual.proto.spec)['data'] == json.loads(figure.to_json())['data']
    app.switch_page('app_pages/explorer.py').run()
    assert not app.exception
    assert not any(block.key == 'executive_overview' for block in app.get('vertical'))
    assert not any(widget.key == 'overview_baseline' for widget in app.button_group)


def test_explorer_only_exposes_relevant_controls(monkeypatch):
    app = start(monkeypatch).switch_page('app_pages/explorer.py').run()
    assert app.button_group(key='explorer_baseline').value == '2019'
    app.button_group(key='explorer_baseline').set_value('2017-2019').run()
    assert not app.exception
    assert any('2017-2019' in item.value for item in app.caption)
    app.button_group(key='explorer_question').set_value('Year-over-year').run()
    keys = {widget.key for widget in app.button_group}
    assert 'explorer_baseline' not in keys and 'explorer_aggregation' not in keys
    assert not any(widget.key == 'explorer_years' for widget in app.multiselect)
    app.button_group(key='explorer_question').set_value('Seasonal').run()
    assert app.multiselect(key='explorer_years')
    assert not app.exception


def test_explorer_yoy_chart_and_export_table_match_analytics(monkeypatch):
    import base64
    import json
    import numpy as np
    import pandas as pd
    from urbanflow_ai.dashboard_data import load_bundle
    from urbanflow_ai.dashboard_metrics import ExplorerFilter
    from urbanflow_ai.explorer import explorer_model
    app = start(monkeypatch).switch_page('app_pages/explorer.py').run()
    app.button_group(key='explorer_question').set_value('Year-over-year').run()
    app.date_input(key='explorer_dates').set_value((date(2026, 8, 1), date(2026, 8, 31))).run()
    assert not app.exception
    filters = ExplorerFilter(date(2026, 8, 1), date(2026, 9, 1), ('W',), ('bus', 'rail'), (2026,))
    expected = explorer_model(load_bundle(), filters, 'Year-over-year')['series']
    pd.testing.assert_frame_equal(app.dataframe[0].value, expected, check_dtype=False)
    assert len(app.get('plotly_chart')) == 1
    chart = json.loads(app.get('plotly_chart')[0].proto.spec)
    for trace in chart['data']:
        encoded = trace['y']
        values = np.frombuffer(base64.b64decode(encoded['bdata']), dtype=encoded['dtype']) if isinstance(encoded, dict) else encoded
        mode = trace['name'].lower()
        np.testing.assert_allclose(values, expected[expected['mode'] == mode].value, equal_nan=True)


def test_explorer_explains_valid_target_without_historical_reference(monkeypatch):
    app = start(monkeypatch).switch_page('app_pages/explorer.py').run()
    app.button_group(key='explorer_question').set_value('Year-over-year').run()
    app.date_input(key='explorer_dates').set_value((date(2013, 7, 1), date(2013, 7, 31))).run()
    assert not app.exception
    assert any('previous same-month/day-type means are missing or zero' in item.value for item in app.info)
    assert app.dataframe[0].value.value.isna().all()
    assert set(app.dataframe[0].value.comparison_status) == {'Reference unavailable'}


def test_all_four_pages_render_offline_without_database_or_api(monkeypatch):
    import urllib.request
    import psycopg
    import urbanflow_ai.ingestion as ingestion
    from urbanflow_ai.dashboard_ui import cached_data
    from urbanflow_ai.anomaly_research_ui import cached_research

    def forbidden(*args, **kwargs):
        raise AssertionError('Offline snapshot pages must not contact an API or database')

    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    monkeypatch.setattr(ingestion, 'urlopen', forbidden)
    monkeypatch.setattr(psycopg, 'connect', forbidden)
    monkeypatch.delenv('URBANFLOW_RESEARCH_ROOT', raising=False)
    cached_data.clear()
    cached_research.clear()
    app = start(monkeypatch)
    for path in ['app_pages/overview.py', 'app_pages/explorer.py', 'app_pages/methodology.py', 'app_pages/anomaly_research.py']:
        app.switch_page(path).run()
        assert not app.exception and not app.error
        assert app.title
