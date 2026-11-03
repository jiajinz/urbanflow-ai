"""AppTest verifies experimental framing, interactions and preserved UI boundaries."""

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def start(monkeypatch):
    monkeypatch.setenv("URBANFLOW_DATA_BACKEND", "snapshot")
    monkeypatch.delenv("URBANFLOW_RESEARCH_ROOT", raising=False)
    return (
        AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
        .run()
        .switch_page("app_pages/anomaly_research.py")
        .run()
    )


def test_research_default_framing_and_complete_health(monkeypatch):
    app = start(monkeypatch)
    assert not app.exception
    assert app.title[0].value == "Anomaly Research Explorer"
    assert any(
        "Experimental Research — Not a Production Alerting System" in item.value
        for item in app.warning
    )
    assert any("Operational Readiness: NO-GO" in item.value for item in app.markdown)
    assert len(app.get("plotly_chart")) == 2
    app.text_input(key="research_query").set_value("no-candidate").run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 2
    assert any("context remain visible" in item.value for item in app.info)


def test_below_expected_selection_and_export_preparation(monkeypatch):
    app = start(monkeypatch)
    app.button_group(key="research_model").set_value("calendar_median").run()
    app.button_group(key="research_mode").set_value("rail").run()
    app.date_input(key="research_dates").set_value(
        (date(2021, 6, 4), date(2021, 6, 4))
    ).run()
    app.button_group(key="research_direction").set_value("low").run()
    assert not app.exception
    options = app.selectbox(key="research_selected").options
    assert options == ["calendar_median|rail|2021-06-04"]
    app.selectbox(key="research_selected").set_value(options[0]).run()
    assert not app.exception
    assert any("65.94" in item.value for item in app.markdown)
    assert any(
        "positive" in item.value and "low" in item.value for item in app.markdown
    )
    app.button(key="research_prepare").click().run()
    assert not app.exception
    assert app.get("download_button")
    app.button_group(key="research_direction").set_value("high").run()
    assert not app.exception
    assert not app.selectbox


def test_corrupt_or_missing_root_blocks_only_research(monkeypatch, tmp_path):
    monkeypatch.setenv("URBANFLOW_RESEARCH_ROOT", str(tmp_path))
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    assert not app.exception
    app.switch_page("app_pages/anomaly_research.py").run()
    assert not app.exception
    assert app.error and not app.get("plotly_chart")
    app.switch_page("app_pages/methodology.py").run()
    assert not app.exception


def test_page_never_calls_training_recalibration_or_database(monkeypatch):
    import urbanflow_ai.anomaly as detector
    import urbanflow_ai.anomaly_readiness as readiness
    import urbanflow_ai.dashboard_data as access

    def forbidden(*args, **kwargs):
        raise AssertionError("Training/recalibration/database access is forbidden")

    # First reach the existing root page normally, then forbid research-time calls.
    monkeypatch.setenv("URBANFLOW_DATA_BACKEND", "snapshot")
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    for owner, name in [
        (detector, "detect"),
        (readiness, "model_health"),
        (readiness, "build_cases"),
        (access, "load_postgres"),
        (access, "load_archive"),
    ]:
        monkeypatch.setattr(owner, name, forbidden)
    from urbanflow_ai.anomaly_research_ui import cached_research

    cached_research.clear()
    app.switch_page("app_pages/anomaly_research.py").run()
    assert not app.exception and len(app.get("plotly_chart")) == 2
