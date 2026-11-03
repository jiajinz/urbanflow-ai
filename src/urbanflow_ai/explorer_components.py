"""Explorer-only presentation using the approved Overview visual tokens."""

import streamlit as st

from .ui_design import page_styles

# Reuse the approved design with a separate namespace; Overview is not restyled.
EXPLORER_CSS = page_styles('ridership_explorer', 'explorer')


def apply_explorer_styles():
    st.html(EXPLORER_CSS + """<style>
.st-key-ridership_explorer :is(.st-key-explorer_question_control, .st-key-explorer_mode_control,
 .st-key-explorer_type_control, .st-key-explorer_aggregation_control) button[role] {
  min-height: 40px; color: #142B49; border-color: #73859A;
}
.st-key-ridership_explorer :is(.st-key-explorer_question_control, .st-key-explorer_mode_control,
 .st-key-explorer_type_control, .st-key-explorer_aggregation_control) button[aria-checked="true"] {
  background: #087E83 !important; color: #FFFFFF !important;
}
.st-key-ridership_explorer button[role] p { color: inherit; }
</style>""")


def explorer_plot(series, view, unit, *, show_rolling=False):
    """Reuse ordinary Explorer charts; render YoY with the same mode semantics."""
    from .dashboard_charts import explorer_chart, style, MODE_COLORS
    import plotly.express as px
    if view != 'YoY':
        figure = explorer_chart(series, view, show_rolling=show_rolling)
    else:
        from .dashboard_charts import DAY_LABELS, MODE_LABELS
        table = series.assign(Mode=series['mode'].map(MODE_LABELS), Service=series.day_type.map(DAY_LABELS))
        figure = px.line(table, x='date', y='value', color='Mode', facet_row='Service', color_discrete_map=MODE_COLORS,
                         hover_data={'current_daily': ':.1f', 'previous_daily': ':.1f', 'reference_month': True, 'comparison_status': True},
                         labels={'date': 'Target month', 'value': 'YoY daily-mean change (%)', 'current_daily': 'Target daily mean', 'previous_daily': 'Previous-year daily mean', 'reference_month': 'Reference month', 'comparison_status': 'Comparability'})
        figure.update_traces(connectgaps=False)
        figure.add_hline(y=0, line_dash='dash', line_color='#526477')
        figure = style(figure, y_title=unit, x_title='Target service month', height=max(420, 235 * table.Service.nunique()))
    figure = refine_explorer_figure(figure, view)
    st.plotly_chart(figure, width='stretch', config={'displaylogo': False, 'scrollZoom': False},
                    alt=f'Filtered CTA {view} comparison, measured in {unit}. Unavailable observations are gaps.')



def refine_explorer_figure(figure, view):
    """Keep trace values/colors intact; clarify facet labels and reference lines."""
    domains = [value['domain'] for key, value in figure.layout.to_plotly_json().items()
               if key.startswith('yaxis') and 'domain' in value]
    for label in figure.layout.annotations:
        if label.text.startswith('Service='):
            domain = next((bounds for bounds in domains if bounds[0] <= label.y <= bounds[1]), [0, 1])
            label.update(text=label.text.split('=', 1)[-1], textangle=0, x=0,
                         y=domain[1], xanchor='left', xshift=0, yshift=4, yanchor='bottom')
    figure.update_layout(margin=dict(l=18, r=18, t=70, b=35),
                         legend=dict(title=None, orientation='h', y=1.15, x=0))
    if view in ('Recovery', 'YoY'):
        reference = 'Baseline = 100' if view == 'Recovery' else 'No change = 0%'
        figure.add_annotation(text=reference, x=1, y=1.04, xref='paper', yref='paper',
                              showarrow=False, xanchor='right', font=dict(color='#526477', size=12))
    return figure
