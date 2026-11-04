"""Plotly rendering functions for analytical view models; no SQL or metric formulas."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

MODE_LABELS = {"bus": "Bus", "rail": "Rail", "total": "Total"}
DAY_LABELS = {"W": "Weekday (W)", "A": "Saturday (A)", "U": "Sunday / holiday (U)"}
MODE_COLORS = {"Bus": "#0072B2", "Rail": "#D55E00", "Total": "#34495E"}
DAY_COLORS = {"Weekday (W)": "#0072B2", "Saturday (A)": "#D55E00", "Sunday / holiday (U)": "#008567"}


def style(figure, *, y_title, x_title, height=390):
    # Redundant line styles support comparisons without relying on color alone.
    dashes = {"Bus": "solid", "Rail": "dash", "Total": "dot",
              "Weekday (W)": "solid", "Saturday (A)": "dash", "Sunday / holiday (U)": "dot"}
    for trace in figure.data:
        if trace.type == "scatter" and trace.name in dashes:
            trace.line.dash = dashes[trace.name]
    figure.update_layout(template="plotly_white", height=height,
                         font=dict(family="Arial", color="#23364A", size=13),
                         margin=dict(l=18, r=18, t=65, b=35),
                         legend=dict(title=None, orientation="h", y=1.13, x=0),
                         hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)")
    figure.update_xaxes(title=x_title, showgrid=False)
    figure.update_yaxes(title=y_title, gridcolor="#E8EDF2", separatethousands=True)
    return figure


def recovery_trend(table):
    table = table.assign(Service=table.day_type.map(DAY_LABELS))
    figure = px.line(table, x="month", y="total_index", color="Service", color_discrete_map=DAY_COLORS,
                     labels={"month": "Service month", "total_index": "Recovery index"},
                     hover_data={"year": True, "baseline": True})
    figure.add_hline(y=100, line_dash="dash", line_color="#68798B", annotation_text="Baseline = 100")
    return style(figure, y_title="Total recovery index (baseline = 100)", x_title="Service month")


def weekday_mode_trend(table):
    """Render supplied monthly mode indices; preserve missing observations."""
    figure = go.Figure()
    for mode, column in (("Bus", "bus_index"), ("Rail", "rail_index")):
        figure.add_trace(go.Scatter(
            x=table.month, y=table[column], name=mode,
            mode="lines", line=dict(color=MODE_COLORS[mode], width=2.5),
            connectgaps=False,
            hovertemplate=f"{mode} · %{{x|%b %Y}}<br>Recovery index: %{{y:.2f}}<extra></extra>",
        ))
    figure.add_hline(y=100, line_dash="dash", line_color="#68798B", annotation_text="Baseline = 100")
    return style(figure, y_title="Weekday recovery index (baseline = 100)", x_title="Service month")


def mode_comparison(period):
    table = period.melt(id_vars=["day_type"], value_vars=["bus_index", "rail_index"], var_name="Mode", value_name="Recovery index")
    table["Mode"] = table.Mode.map({"bus_index": "Bus", "rail_index": "Rail"})
    table["Service"] = table.day_type.map(DAY_LABELS)
    figure = px.bar(table, x="Service", y="Recovery index", color="Mode", barmode="group", color_discrete_map=MODE_COLORS,
                    text_auto=".1f", category_orders={"Service": list(DAY_LABELS.values())})
    figure.add_hline(y=100, line_dash="dash", line_color="#68798B")
    return style(figure, y_title="Mean monthly recovery index", x_title="CTA service day type")


def explorer_chart(series, view, *, show_rolling=True):
    table = series.copy()
    table["Mode"] = table['mode'].map(MODE_LABELS)
    if view == "Daily":
        figure = go.Figure()
        for mode, group in table.groupby("Mode", sort=False):
            figure.add_trace(go.Scatter(x=group.date, y=group.value, name=mode, line=dict(color=MODE_COLORS[mode], width=1), connectgaps=False))
            if show_rolling:
                figure.add_trace(go.Scatter(x=group.date, y=group.rolling_average, name=f"{mode} · 7-day mean", line=dict(color=MODE_COLORS[mode], width=3, dash="dash"), connectgaps=False))
        return style(figure, y_title="Boardings per service date", x_title="Service date", height=450)
    table["Service"] = table.day_type.map(DAY_LABELS)
    if view == "Seasonal":
        table["Comparison year"] = table.year.astype(int).astype(str)
        figure = px.line(table, x="date", y="value", color="Mode", line_dash="Comparison year", facet_row="Service", markers=True, color_discrete_map=MODE_COLORS,
                         labels={"date": "Calendar month", "value": "Daily boardings"})
        figure.update_xaxes(tickmode="array", tickvals=list(range(1, 13)), ticktext=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    else:
        figure = px.line(table, x="date", y="value", color="Mode", facet_row="Service", color_discrete_map=MODE_COLORS,
                         markers=view == "Yearly", labels={"date": "Service period", "value": "Value"})
        if view == "Recovery":
            figure.add_hline(y=100, line_dash="dash", line_color="#68798B")
        if view == "Yearly":
            figure.update_xaxes(dtick=1)
    figure.update_traces(connectgaps=False)
    index = view == "Recovery"
    axis = "Recovery index" if index else "Mean daily boardings"
    x_axis = "Calendar month" if view == "Seasonal" else "Year (complete years only)" if view == "Yearly" else "Service month"
    return style(figure, y_title=axis, x_title=x_axis, height=max(420, 235 * table.Service.nunique()))
