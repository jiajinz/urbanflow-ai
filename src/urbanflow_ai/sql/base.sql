WITH bounds AS (
    SELECT CAST(%s AS DATE) AS start_date, CAST(%s AS DATE) AS end_date,
           CAST(%s AS TEXT) AS day_filter
), calendar AS (
    SELECT CAST(day AS DATE) AS service_date
    FROM bounds, generate_series(start_date, end_date - INTERVAL '1 day', INTERVAL '1 day') AS series(day)
), selected AS (
    SELECT c.service_date, r.day_type, r.bus, r.rail_boardings, r.total_rides,
           CASE WHEN EXTRACT(ISODOW FROM c.service_date) IN (6, 7)
                THEN 'Weekend' ELSE 'Weekday' END AS calendar_type,
           CASE WHEN r.service_date IS NOT NULL AND
                (b.day_filter = 'All' OR r.day_type = b.day_filter) THEN 1 ELSE 0 END AS included
    FROM calendar c CROSS JOIN bounds b
    LEFT JOIN daily_ridership r ON c.service_date = r.service_date
), filtered AS (
    SELECT * FROM selected WHERE included = 1
)
