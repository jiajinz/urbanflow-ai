-- One row per complete/incomplete calendar month and CTA service day type.
-- Completeness is computed before splitting by day type; missing days stay missing.
WITH month_coverage AS (
    SELECT CAST(date_trunc('month', service_date) AS DATE) AS month,
           COUNT(*) AS observed_calendar_days,
           CAST(EXTRACT(DAY FROM date_trunc('month', service_date) + INTERVAL '1 month' - INTERVAL '1 day') AS INTEGER) AS expected_calendar_days
    FROM daily_ridership
    WHERE service_date >= %s AND service_date < %s
    GROUP BY date_trunc('month', service_date),
             EXTRACT(DAY FROM date_trunc('month', service_date) + INTERVAL '1 month' - INTERVAL '1 day')
)
SELECT c.month, r.day_type, COUNT(*) AS service_days,
       SUM(r.bus) AS bus_total, SUM(r.rail_boardings) AS rail_total,
       SUM(r.total_rides) AS total_total,
       AVG(r.bus) AS bus_daily, AVG(r.rail_boardings) AS rail_daily,
       AVG(r.total_rides) AS total_daily,
       c.observed_calendar_days, c.expected_calendar_days,
       c.observed_calendar_days = c.expected_calendar_days AS complete_month
FROM daily_ridership r JOIN month_coverage c
ON CAST(date_trunc('month', r.service_date) AS DATE) = c.month
WHERE r.service_date >= %s AND r.service_date < %s
GROUP BY c.month, r.day_type, c.observed_calendar_days, c.expected_calendar_days
ORDER BY c.month, r.day_type
