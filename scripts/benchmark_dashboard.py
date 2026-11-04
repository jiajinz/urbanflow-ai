"""Measure local in-process page execution, not browser or cloud performance.

Run from an installed checkout with the default offline snapshots. Timings begin
following benchmark imports. Warm medians use five reruns in one Python process.
"""

import json
from pathlib import Path
import resource
import statistics
import sys
import time

from streamlit.testing.v1 import AppTest
from urbanflow_ai.anomaly_research_ui import cached_research, read_research

ROOT = Path(__file__).resolve().parents[1]
ROUTES = {
    "overview": "app_pages/overview.py",
    "explorer": "app_pages/explorer.py",
    "methodology": "app_pages/methodology.py",
    "anomaly": "app_pages/anomaly_research.py",
}


def measure(call):
    started = time.perf_counter()
    result = call()
    return result, time.perf_counter() - started


def main():
    app, initial = measure(
        lambda: AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    )
    assert not app.exception and not app.error
    output = {"entrypoint_cold_seconds": initial, "pages": {}}
    for name, route in ROUTES.items():
        _, first_switch = measure(lambda: app.switch_page(route).run())
        assert not app.exception and not app.error
        warm = []
        for _ in range(5):
            _, elapsed = measure(app.run)
            assert not app.exception and not app.error
            warm.append(elapsed)
        output["pages"][name] = {
            "first_switch_seconds": first_switch,
            "warm_rerun_median_seconds": statistics.median(warm),
            "plotly_elements": len(app.get("plotly_chart")),
        }
        changes = {
            "overview": ("overview_baseline", "2017-2019"),
            "explorer": ("explorer_question", "Year-over-year"),
            "anomaly": ("research_model", "calendar_median"),
        }
        if name in changes:
            key, value = changes[name]
            _, elapsed = measure(lambda: app.button_group(key=key).set_value(value).run())
            assert not app.exception and not app.error
            output["pages"][name]["filter_change_seconds"] = elapsed

    cached_research.clear()
    bundle, elapsed = measure(read_research)
    output["research_cold_seconds"] = elapsed
    output["research_warm_median_seconds"] = statistics.median(
        measure(read_research)[1] for _ in range(5)
    )
    output["research_frames_deep_bytes"] = int(sum(
        frame.memory_usage(deep=True).sum()
        for frame in (bundle.daily, bundle.cases, bundle.health, bundle.episodes)
    ))
    # macOS reports bytes; Linux reports KiB. This includes all process imports.
    divisor = 1024 ** 2 if sys.platform == "darwin" else 1024
    output["process_high_water_rss_mib"] = (
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / divisor
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
