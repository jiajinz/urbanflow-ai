"""Executive Overview presentation model; reuses approved 4A calculations."""

import pandas as pd

from .dashboard_metrics import executive_model


def overview_model(data, baseline="2019", chart_years=None):
    """Return executive evidence and a comparable monthly chart window.

    KPI/evidence periods stay independent of the chart window. No baseline is
    recalculated here. Missing chart months are explicit nulls, never interpolated.
    Insufficient annual/baseline evidence returns None; invalid windows raise.
    """
    model = executive_model(data, baseline)
    if model is None:
        return None
    trend = model['trend']
    years = tuple(sorted(int(year) for year in trend.year.unique()))
    if not years:
        return None
    first_year, last_year = chart_years if chart_years is not None else (years[0], years[-1])
    if first_year not in years or last_year not in years or first_year > last_year:
        raise ValueError("Select an ordered chart window within available recovery years")
    selected = trend[trend.year.between(first_year, last_year)].copy()
    if selected.empty:
        raise ValueError("No comparable monthly recovery data exists in this window")
    grid = pd.date_range(selected.month.min(), selected.month.max(), freq="MS")
    parts = []
    for kind, table in selected.groupby('day_type'):
        expanded = table.set_index('month').reindex(grid).rename_axis('month').reset_index()
        expanded['day_type'], expanded['baseline'] = kind, baseline
        expanded['year'] = expanded.month.dt.year
        parts.append(expanded)
    selected = pd.concat(parts, ignore_index=True)
    weekday = model['period'].set_index('day_type').loc['W']
    metrics = model['metrics']
    if metrics['A'] > metrics['W'] and metrics['U'] > metrics['W']:
        summary = f"In {model['year']}, Saturday and Sunday/holiday demand recovered further than weekday demand."
    else:
        summary = f"In {model['year']}, recovery levels varied across CTA service day types."
    summary += f" Weekday bus and rail indices were {weekday.bus_index:.2f} and {weekday.rail_index:.2f} ({baseline} baseline = 100)."
    notes = [
        dict(title="Service-day recovery calls for separate planning assumptions",
             evidence=model['findings'][0],
             interpretation="Same-month/day-type comparisons reduce differences caused by the number of service days; they do not identify trip purpose.",
             planning="Review Saturday and Sunday/holiday loads alongside weekday needs before changing service allocation.",
             limitation="U includes holidays on calendar weekdays. Systemwide averages cannot locate route-level crowding.",
             source="4A finding 1 · recovery_indices → standardized_periods"),
        dict(title="Track bus and rail recovery separately",
             evidence=model['findings'][1],
             interpretation="A systemwide recovery total can conceal mode-specific differences. Recovery levels and recent growth are different measures.",
             planning="Investigate delivered service, reliability, and corridor demand before choosing separate bus and rail service assumptions.",
             limitation="These counts cannot establish modal substitution, remote-work effects, or the causes of the recovery gap.",
             source="4A finding 2 · recovery_indices → standardized_periods"),
    ]
    if len(model['findings']) > 2:
        notes.append(dict(title="Demand composition changed under a common calendar",
                          evidence=model['findings'][2],
                          interpretation="The shift remains after applying the same 2019 month/day-type day counts; calendar composition alone does not explain it.",
                          planning="Reassess mode assumptions using comparable months and absolute boardings, together with service-supply evidence.",
                          limitation="This matched-month window is not a complete-year comparison or a causal model. Fixed 2019 weights do not change with the recovery baseline selector.",
                          source="4A finding 3 · matched_composition"))
    return {**model, 'summary': summary, 'insights': notes, 'available_years': years,
            'chart_years': (first_year, last_year), 'chart_trend': selected,
            'chart_period': f"{grid.min():%b %Y}–{grid.max():%b %Y}",
            'mode_trend': selected[selected.day_type == 'W'].copy()}
