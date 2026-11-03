"""Plotly rendering of supplied frozen research; no detector calculations."""

import plotly.graph_objects as go

from .dashboard_charts import MODE_COLORS, MODE_LABELS


def observation_chart(view):
    series = view.observations
    mode = view.selection_context["filters"]["mode"]
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=series.date,
            y=series.observed,
            name="Actual boardings",
            mode="lines",
            line=dict(color=MODE_COLORS[MODE_LABELS[mode]], width=1.8),
            connectgaps=False,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=series.date,
            y=series.expected,
            name="Frozen model expectation",
            mode="lines",
            line=dict(color="#142B49", dash="dash", width=2),
            connectgaps=False,
        )
    )
    for direction, symbol, label in [
        ("high", "triangle-up", "above"),
        ("low", "triangle-down", "below"),
    ]:
        points = view.candidates[view.candidates.actual_direction == direction]
        figure.add_trace(
            go.Scatter(
                x=points.date,
                y=points.observed,
                mode="markers",
                name=f"Candidate: {label} expected",
                marker=dict(
                    symbol=symbol,
                    size=10,
                    color=MODE_COLORS[MODE_LABELS[mode]],
                    line=dict(color="#142B49", width=1),
                ),
                customdata=points[
                    [
                        "expected",
                        "signed_deviation",
                        "relative_deviation_pct",
                        "centered_score",
                        "day_type",
                        "actual_direction",
                    ]
                ].to_numpy(),
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Actual: %{y:,.0f}<br>Expected: %{customdata[0]:,.1f}<br>Deviation: %{customdata[1]:+,.1f}<br>Relative: %{customdata[2]:+.2f}%<br>Centered score: %{customdata[3]:+.2f}<br>CTA day type: %{customdata[4]}<br>Actual direction: %{customdata[5]}<extra></extra>",
            )
        )
    figure.update_layout(
        template="plotly_white",
        height=400,
        margin=dict(l=15, r=15, t=45, b=30),
        legend=dict(orientation="h", y=1.14, x=0),
        hovermode="x unified",
        font=dict(color="#142B49"),
        xaxis_title="Service date",
        yaxis_title="Daily boardings (rides)",
    )
    return figure


def health_chart(view):
    figure = go.Figure()
    for state, label, color, symbol in [
        ("clear", "Clear under research guards", "#526477", "circle"),
        ("warning", "Model-health warning", "#C08431", "diamond"),
        ("insufficient_history", "Insufficient history", "#526477", "x"),
        ("unknown_drift_or_error", "Unknown drift/error", "#526477", "square-open"),
        ("scored_data_gap", "Scored-data gap", "#C08431", "x"),
    ]:
        rows = view.health[view.health.health_status == state]
        if rows.empty:
            continue
        figure.add_trace(
            go.Scatter(
                x=rows.date,
                y=[state] * len(rows),
                mode="markers",
                name=label,
                marker=dict(color=color, symbol=symbol, size=6),
                hovertemplate="%{x|%Y-%m-%d}<br>" + label + "<extra></extra>",
            )
        )
    figure.update_layout(
        template="plotly_white",
        height=190,
        margin=dict(l=15, r=15, t=15, b=25),
        showlegend=False,
        font=dict(color="#142B49"),
        xaxis_title="Service date",
        yaxis_title="Research health state",
    )
    figure.update_yaxes(
        tickvals=[
            "clear",
            "warning",
            "insufficient_history",
            "unknown_drift_or_error",
            "scored_data_gap",
        ],
        ticktext=[
            "Clear under guards",
            "Warning",
            "Insufficient history",
            "Unknown drift/error",
            "Data gap",
        ],
    )
    return figure
