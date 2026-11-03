"""Methodology content contracts backed by archived evidence and real analytics."""

import copy
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from urbanflow_ai.dashboard_data import load_bundle, DEFAULT_BUNDLE
from urbanflow_ai.methodology import METRICS, SECTIONS, UNKNOWN, provenance_labels
from urbanflow_ai.processing import process_records
from urbanflow_ai.research import BASELINES

ROOT = Path(__file__).resolve().parents[1]


def test_provenance_uses_supplied_metadata_without_inference():
    metadata = copy.deepcopy(load_bundle(DEFAULT_BUNDLE).metadata)
    metadata['coverage']['row_count'] = 123
    metadata['source_row_count'] = None
    labels = provenance_labels(metadata)
    assert labels['records'] == '123'
    assert labels['first'] == metadata['coverage']['first_date']
    assert labels['last'] == metadata['coverage']['last_date']
    assert labels['missing'] == str(len(metadata['coverage']['missing_dates']))
    assert labels['source_rows'] == UNKNOWN
    assert labels['retrieved'] == metadata['source_retrieved_at_utc']
    assert labels['generated'] == metadata['generated_at_utc']


def test_unknown_source_metadata_is_never_zero_or_live():
    labels = provenance_labels({'backend': 'postgres'})
    assert labels['environment'] == 'Local PostgreSQL read'
    assert all(value == UNKNOWN for key, value in labels.items() if key != 'environment')


def test_quarantine_case_matches_archived_validation_evidence():
    archive = ROOT / 'data/history/cta-2026-11-01-v1'
    rejected = json.loads((archive / 'quarantine.json').read_text())
    assert len(rejected) == 31
    assert all(row['service_date'].startswith('2012-07-') and 'T07:00' in row['service_date'] for row in rejected)
    assert all(row['errors'] == ['service_date must be a valid ISO date or midnight timestamp'] for row in rejected)
    result = process_records([row['raw'] for row in rejected])
    assert len(result.rejected_records) == 31
    assert not result.valid_records
    raw = rejected[0]['raw']
    assert (int(raw['bus']), int(raw['rail_boardings']), int(raw['total_rides'])) == (474631, 350123, 824754)


def test_metric_contract_matches_supported_baselines_and_explorer_definitions():
    assert BASELINES == {'2019': (2019,), '2017-2019': (2017, 2018, 2019)}
    recovery = METRICS['Recovery index · baseline = 100'][1]
    assert 'equally averages' in recovery and 'requires all three years' in recovery
    assert 'full history' in recovery and 'equally averages monthly indices' in recovery
    trends = METRICS['Trends, seasonal views, and filters'][1]
    assert 'seven consecutive' in trends and 'all 12 complete' in trends
    assert 'exclusive next-day' in trends


def test_methodology_renders_five_sections_and_archived_case(monkeypatch):
    monkeypatch.setenv('URBANFLOW_DATA_BACKEND', 'snapshot')
    monkeypatch.delenv('URBANFLOW_SNAPSHOT_DIR', raising=False)
    app = AppTest.from_file(str(ROOT / 'streamlit_app.py'), default_timeout=30).run()
    app.switch_page('app_pages/methodology.py').run()
    assert not app.exception
    assert [heading.value for heading in app.header] == list(SECTIONS)
    assert [metric.value for metric in app.metric] == ['9,343', '2001-01-01', '2026-08-31']
    assert any('07:00' in warning.value for warning in app.warning)
    assert len(app.expander) == 11
    assert not app.get('plotly_chart')
