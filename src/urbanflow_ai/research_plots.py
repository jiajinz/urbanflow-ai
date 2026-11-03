"""Plotly research exhibits; no Streamlit or analytical calculations in the UI."""

import argparse
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

COLORS = {"bus": "#147D92", "rail": "#8758AC", "total": "#334155"}
DAY_LABELS = {"W": "Weekday (W)", "A": "Saturday (A)", "U": "Sunday/holiday (U)"}


def build_figures(directory: Path) -> dict:
    monthly = pd.read_csv(directory / "monthly.csv", parse_dates=["month"])
    indices = pd.read_csv(directory / "recovery_indices.csv", parse_dates=["month"])
    baseline = indices[indices.baseline == "2019"].copy()
    figures = {}
    # Monthly totals remain distinct from recovery indices and partial periods.
    complete = monthly[monthly.complete_month]
    history = complete.groupby("month")[[f"{mode}_total" for mode in COLORS]].sum().reset_index()
    history = history.set_index("month").reindex(pd.date_range(history.month.min(), history.month.max(), freq="MS")).rename_axis("month").reset_index()
    fig = go.Figure()
    for mode, color in COLORS.items():
        fig.add_trace(go.Scatter(x=history.month, y=history[f"{mode}_total"], name=mode.title(), line_color=color, connectgaps=False))
    fig.update_layout(title="Historical monthly boardings — complete months only", yaxis_title="Boardings per calendar month", xaxis_title="Service month")
    figures["01_historical_boardings"] = fig
    baseline["Service type"] = baseline.day_type.map(DAY_LABELS)
    fig = px.line(baseline, x="month", y="total_index", color="Service type", labels={"month": "Service month", "total_index": "Recovery index (2019 = 100)"}, title="RQ1: Total boardings recovery by CTA day type")
    fig.add_hline(y=100, line_dash="dash", line_color="#64748B")
    figures["02_day_type_recovery"] = fig
    fig = make_subplots(rows=3, cols=1, subplot_titles=list(DAY_LABELS.values()), shared_xaxes=True, vertical_spacing=.09)
    for row, kind in enumerate(DAY_LABELS, 1):
        typed = baseline[baseline.day_type == kind]
        for mode in ("bus", "rail"):
            fig.add_trace(go.Scatter(x=typed.month, y=typed[f"{mode}_index"], name=mode.title(), legendgroup=mode, showlegend=row == 1, line_color=COLORS[mode]), row=row, col=1)
        fig.add_hline(y=100, line_dash="dash", line_color="#64748B", row=row, col=1)
        fig.update_yaxes(title_text="Recovery index", row=row, col=1)
    fig.update_xaxes(title_text="Service month", row=3, col=1)
    fig.update_layout(title="RQ2: Bus versus rail recovery — same-month/day-type 2019 = 100", height=1000)
    figures["03_mode_recovery"] = fig
    period = pd.read_csv(directory / "period_recovery.csv")
    chosen = period[period.year >= 2024].copy()
    chosen["Period"] = chosen.apply(lambda r: f"{r['year']} ({r['months']} complete months)", axis=1)
    chosen["Service type"] = chosen.day_type.map(DAY_LABELS)
    fig = px.scatter(chosen, x="Period", y="total_index", color="Service type", symbol="baseline", hover_data=["months"], title="Baseline sensitivity: equal-month total recovery indices", labels={"total_index": "Mean recovery index (baseline = 100)"})
    fig.add_hline(y=100, line_dash="dash")
    figures["04_baseline_sensitivity"] = fig
    year_months = complete.groupby("year").month_number.nunique()
    latest_complete_year = int(year_months[year_months == 12].index.max())
    selected = complete[(complete.day_type == "W") & complete.year.isin([2019, latest_complete_year])]
    seasonal = selected.melt(id_vars=["month_number", "year"], value_vars=["bus_daily", "rail_daily"], var_name="Mode", value_name="Average daily boardings")
    seasonal["Mode"] = seasonal.Mode.str.replace("_daily", "").str.title()
    seasonal["Year"] = seasonal.year.astype(str)
    fig = px.line(seasonal, x="month_number", y="Average daily boardings", color="Year", facet_col="Mode", markers=True, title=f"Seasonality check: weekday daily boardings, 2019 versus {latest_complete_year}", labels={"month_number": "Calendar month (1–12)"})
    figures["05_seasonal_comparison"] = fig
    import json
    coverage = json.loads((directory / "coverage.json").read_text())
    source_range = f"{coverage['first_date']}–{coverage['last_date']}"
    for name, fig in figures.items():
        fig.update_layout(template="plotly_white", font=dict(family="Arial", size=13), margin=dict(b=110), hovermode="x unified")
        fig.add_annotation(text=f"Source: Chicago CTA Daily Boarding Totals · {source_range} snapshot · Complete months only; gaps are not zero", x=0, y=-.18 if name != '03_mode_recovery' else -.07, xref="paper", yref="paper", showarrow=False, xanchor="left", font_size=11)
    return figures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, figure in build_figures(args.results).items():
        figure.write_html(args.output / f"{name}.html", include_plotlyjs="directory", full_html=True)
        figure.write_json(args.output / f"{name}.plotly.json")
    print("Saved five Plotly research exhibits and their figure specifications")


if __name__ == "__main__":
    main()
