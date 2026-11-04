"""Run an offline, read-only release smoke check from an installed checkout.

This validates local execution, not Linux/cloud compatibility or data-use rights.
Run after installing requirements.txt and the existing test extra.
"""

from datetime import date
from importlib import metadata, resources
import json
from pathlib import Path
import platform
import time
from unittest.mock import patch

from packaging.requirements import Requirement
from streamlit.testing.v1 import AppTest
import urbanflow_ai
from urbanflow_ai.anomaly_research_data import load_research_bundle, verified_payloads
from urbanflow_ai.dashboard_data import load_bundle

ROOT = Path(__file__).resolve().parents[1]


def validate_runtime_constraints(path, version_lookup=metadata.version):
    """Check installed versions against constraints and platform markers."""
    checked = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        requirement = Requirement(line)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            installed = version_lookup(requirement.name)
        except metadata.PackageNotFoundError:
            raise RuntimeError(f"Missing release dependency: {requirement.name}") from None
        if installed not in requirement.specifier:
            raise RuntimeError(f"Release dependency differs from constraints: {requirement.name}")
        checked[requirement.name] = installed
    return checked


def forbidden(*args, **kwargs):
    raise AssertionError("Public-mode smoke checks must not access a database/API or fit models")


def run():
    if not Path(urbanflow_ai.__file__).resolve().is_relative_to(ROOT):
        raise RuntimeError("Install this checkout through requirements.txt before running preflight")
    sql = sorted(p.name for p in resources.files("urbanflow_ai").joinpath("sql").iterdir())
    assert len(sql) == 8 and all(name.endswith(".sql") for name in sql)
    runtime = {name: metadata.version(name) for name in [
        "streamlit", "plotly", "pandas", "numpy", "pyarrow", "duckdb", "psycopg"
    ]}
    result = {"python": platform.python_version(), "platform": platform.system(),
              "architecture": platform.machine(), "runtime": runtime, "sql_files": sql}
    result["validated_runtime_pins"] = validate_runtime_constraints(ROOT / "constraints.txt")
    guards = ["psycopg.connect", "urllib.request.urlopen", "urbanflow_ai.ingestion.urlopen",
              "urbanflow_ai.anomaly.detect", "urbanflow_ai.anomaly_readiness.model_health",
              "urbanflow_ai.anomaly_readiness.build_cases"]
    from contextlib import ExitStack
    with ExitStack() as stack:
        for target in guards:
            stack.enter_context(patch(target, forbidden))
        started = time.perf_counter()
        data = load_bundle(ROOT / "data/dashboard/cta-2026-11-01-v2")
        result["snapshot_load_seconds"] = time.perf_counter() - started
        started = time.perf_counter()
        research = load_research_bundle(ROOT)
        result["research_load_seconds"] = time.perf_counter() - started
        result["artifact_paths"] = sorted(verified_payloads(ROOT))
        result["counts"] = {"validated_dates": len(data.daily), "research_daily": len(research.daily),
                            "candidates": len(research.cases), "health": len(research.health)}
        assert result["counts"] == {"validated_dates": 9343, "research_daily": 11200,
                                     "candidates": 763, "health": 11200}
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
        assert not app.exception and not app.error
        assert [m.value for m in app.metric] == ["70.90", "88.10", "89.29", "22.28 pp"]
        app.button_group(key="overview_baseline").set_value("2017-2019").run()
        assert [m.value for m in app.metric] == ["69.18", "84.95", "85.93", "21.67 pp"]
        app.switch_page("app_pages/explorer.py").run()
        for question in ["Trend", "Year-over-year", "Seasonal", "Recovery"]:
            app.button_group(key="explorer_question").set_value(question).run()
            assert not app.exception and not app.error
        app.button_group(key="explorer_modes").set_value([]).run()
        assert any("No observed records" in item.value for item in app.info)
        app.switch_page("app_pages/methodology.py").run()
        assert len(app.header) == 5 and not app.exception
        assert any("07:00" in item.value for item in app.markdown)
        app.switch_page("app_pages/anomaly_research.py").run()
        assert not app.exception and not app.error
        assert any("Operational Readiness: NO-GO" in item.value for item in app.markdown)
        for model in ["calendar_median", "seasonal_trend"]:
            app.button_group(key="research_model").set_value(model).run()
            assert not app.exception and not app.error
        app.button_group(key="research_model").set_value("calendar_median").run()
        app.button_group(key="research_mode").set_value("rail").run()
        app.date_input(key="research_dates").set_value((date(2021, 6, 4), date(2021, 6, 4))).run()
        app.button_group(key="research_direction").set_value("low").run()
        app.selectbox(key="research_selected").set_value("calendar_median|rail|2021-06-04").run()
        assert any("-65.94%" in item.value for item in app.markdown)
        assert any("+3.94 (positive)" in item.value for item in app.markdown)
        app.text_input(key="research_query").set_value("no-candidate").run()
        assert not app.exception and len(app.get("plotly_chart")) == 2
        assert len(app.dataframe[0].value) == 1
        result["offline_four_page_smoke"] = "PASS"
        result["operational_readiness"] = "NO-GO"
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
