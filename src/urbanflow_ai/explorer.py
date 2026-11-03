"""Ridership Explorer view models; reuse 4A analytics without Streamlit dependencies."""

from datetime import timedelta

import pandas as pd

from .dashboard_metrics import explorer_series, selected_daily, selected_monthly
from .research import monthly_changes

QUESTIONS = ('Trend', 'Recovery', 'Year-over-year', 'Seasonal')
AGGREGATIONS = ('Monthly', 'Annual', 'Daily')


def period_coverage(data, filters):
    """Audit calendar coverage before day-type filtering; never infer missing types."""
    rows = []
    dates = pd.to_datetime(data.daily.service_date)
    available = set(dates.dt.date)
    for period in pd.period_range(filters.start_date, filters.end_date - timedelta(days=1), freq='M'):
        if period.year not in filters.years:
            continue
        first = period.start_time.date()
        end = (period + 1).start_time.date()
        left, right = max(first, filters.start_date), min(end, filters.end_date)
        calendar = pd.date_range(left, right - timedelta(days=1), freq='D')
        count = sum(day.date() in available for day in calendar)
        full_selection = left == first and right == end
        status = ('Partial selection' if not full_selection else
                  'Missing validated dates' if count != period.days_in_month else 'Complete')
        rows.append(dict(month=period.start_time, year=period.year,
                         selected_calendar_days=len(calendar), available_calendar_days=count,
                         expected_calendar_days=period.days_in_month, status=status))
    return pd.DataFrame(rows, columns=['month', 'year', 'selected_calendar_days',
                                      'available_calendar_days', 'expected_calendar_days', 'status'])


def yoy_series(data, filters):
    """Reuse 4A same-month/day-type daily-average YoY, including reference evidence.

    Only complete fully selected target months qualify. Reference cells come
    from full history, independently of the target date/year selection.
    """
    columns = ['date', 'year', 'day_type', 'mode', 'value', 'current_daily', 'previous_daily',
               'reference_month', 'current_service_days', 'previous_service_days', 'comparison_status']
    target = selected_monthly(data, filters)
    if target.empty:
        return pd.DataFrame(columns=columns)
    changes = monthly_changes(data.monthly)
    target = changes.merge(target[['month', 'day_type']], on=['month', 'day_type'], validate='one_to_one')
    references = data.monthly[data.monthly.complete_month][['month', 'day_type', 'service_days']].copy()
    references['month'] = references.month + pd.DateOffset(years=1)
    references = references.rename(columns={'service_days': 'previous_service_days'})
    target = target.merge(references, on=['month', 'day_type'], how='left', validate='one_to_one')
    rows = []
    for row in target.itertuples():
        for mode in filters.modes:
            current = getattr(row, f'{mode}_daily')
            previous = getattr(row, f'{mode}_prior_yoy')
            value = getattr(row, f'{mode}_daily_yoy_pct')
            status = ('Reference unavailable' if pd.isna(previous) else
                      'Zero reference' if previous == 0 else 'Comparable')
            rows.append(dict(date=row.month, year=row.year, day_type=row.day_type, mode=mode,
                             value=value, current_daily=current, previous_daily=previous,
                             reference_month=row.month - pd.DateOffset(years=1),
                             current_service_days=row.service_days, previous_service_days=row.previous_service_days,
                             comparison_status=status))
    tidy = pd.DataFrame(rows, columns=columns)
    # Missing target months stay explicit so a line cannot bridge an absent month.
    grid = pd.date_range(pd.Timestamp(filters.start_date).replace(day=1),
                         pd.Timestamp(filters.end_date) - pd.Timedelta(days=1), freq='MS')
    grid = grid[grid.year.isin(filters.years)]
    groups = []
    for (mode, kind), group in tidy.groupby(['mode', 'day_type']):
        expanded = group.set_index('date').reindex(grid).rename_axis('date').reset_index()
        expanded['mode'], expanded['day_type'] = mode, kind
        expanded['year'] = expanded.date.dt.year
        expanded['comparison_status'] = expanded.comparison_status.fillna('Target month unavailable')
        groups.append(expanded)
    return pd.concat(groups, ignore_index=True)


def explorer_model(data, filters, question='Recovery', aggregation='Monthly'):
    """One consistent chart/export result plus coverage, definitions, and limits."""
    if question not in QUESTIONS or aggregation not in AGGREGATIONS:
        raise ValueError('Unsupported analytical question or aggregation')
    selected = selected_daily(data, filters)
    coverage = period_coverage(data, filters)
    if question == 'Year-over-year':
        series = yoy_series(data, filters)
        view = 'YoY'
        definition = ('Percent change in same-month, same-CTA-day-type average daily boardings versus the previous year. '
                      'Both calendar months must be complete. The reference month is read from full history, even outside the target date range.')
        unit = 'Change in average daily boardings (%)'
        limitation = 'Day-type normalization does not align individual holidays, weather, special events, or service supply. A zero reference has no defined percentage change.'
    else:
        view = {'Trend': {'Annual': 'Yearly', 'Daily': 'Daily', 'Monthly': 'Monthly'}[aggregation],
                'Recovery': 'Recovery', 'Seasonal': 'Seasonal'}[question]
        series = explorer_series(data, filters, view)
        definitions = {
            'Daily': 'Observed daily boardings. A trailing mean requires seven consecutive observed, selected calendar dates within this range.',
            'Monthly': 'Average daily boardings within each fully selected, complete calendar month and CTA day type. Missing dates are not zero-filled.',
            'Yearly': 'Observed-day-weighted average daily boardings by CTA day type for fully selected, complete calendar years. This is not an annual total.',
            'Seasonal': 'Same-type monthly daily averages aligned by calendar month across selected years. Unavailable months remain gaps; partial years are not annual comparisons.',
            'Recovery': f'Same-month/day-type average daily boardings divided by the {filters.baseline} baseline × 100. Baseline denominators use full history. Target months must be fully selected, complete, and post-2019.',
        }
        definition = definitions[view]
        unit = 'Recovery index (baseline = 100)' if view == 'Recovery' else 'Boardings per service date' if view == 'Daily' else 'Average daily boardings'
        limitation = ('U includes holidays on calendar weekdays. Same-month comparison is not formal seasonal adjustment. '
                      'Boardings are rides, not unique people; these observations do not establish causes or justify service changes alone.')
    if not series.empty:
        if view in ('Monthly', 'Recovery', 'YoY'):
            series['year'] = pd.to_datetime(series.date).dt.year
        elif view == 'Yearly':
            series['year'] = series.date.astype(int)
        series['available'] = series.value.notna()
    missing_days = int((coverage.selected_calendar_days - coverage.available_calendar_days).sum()) if not coverage.empty else 0
    missing_periods = int(coverage.status.ne('Complete').sum()) if not coverage.empty else 0
    valid_points = int(series.value.notna().sum()) if not series.empty else 0
    years = []
    for year in filters.years:
        months = coverage[coverage.year == year]
        years.append(dict(year=year, selected_months=len(months),
                          complete_months=int(months.status.eq('Complete').sum()),
                          eligible=len(months) == 12 and months.status.eq('Complete').all()))
    year_coverage = pd.DataFrame(years, columns=['year', 'selected_months', 'complete_months', 'eligible'])
    unavailable_references = int(series.comparison_status.isin(['Reference unavailable', 'Zero reference']).sum()) if view == 'YoY' and not series.empty else 0
    return dict(unavailable_references=unavailable_references, year_coverage=year_coverage, series=series, view=view, definition=definition, unit=unit, limitation=limitation,
                selected_dates=len(selected), missing_days=missing_days, coverage=coverage,
                excluded_months=missing_periods, valid_points=valid_points,
                rolling_available=set(filters.day_types) == {'W', 'A', 'U'} and
                                  view == 'Daily' and not series.empty and series.rolling_average.notna().any())
