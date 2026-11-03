"""First-use terminology contracts for independently accessible dashboard pages."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('page', ['overview', 'explorer', 'methodology'])
def test_each_page_defines_agency_before_other_main_content_references(monkeypatch, page):
    monkeypatch.setenv('URBANFLOW_DATA_BACKEND', 'snapshot')
    monkeypatch.delenv('URBANFLOW_SNAPSHOT_DIR', raising=False)
    app = AppTest.from_file(str(ROOT / 'streamlit_app.py'), default_timeout=30).run()
    if page != 'overview':
        app.switch_page(f'app_pages/{page}.py').run()
    assert not app.exception
    paragraphs = [item.value for item in app.main.markdown if 'CTA' in item.value]
    assert 'Chicago Transit Authority (CTA)' in paragraphs[0]
    assert sum('Chicago Transit Authority (CTA)' in text for text in paragraphs) == 1
    if page == 'explorer':
        assert any('Active selection:' in item.value and 'Weekday (W)' in item.value for item in app.caption)


def test_standalone_markdown_documents_define_agency():
    for path in [ROOT / 'README.md', *ROOT.joinpath('docs').glob('*.md')]:
        text = path.read_text()
        if 'CTA' in text:
            first_use = text.index('CTA')
            assert text[max(0, first_use - 27):first_use].endswith('Chicago Transit Authority ('), path
