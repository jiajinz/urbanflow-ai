SELECT service_date, day_type,
       CASE WHEN included = 1 THEN bus END AS bus,
       CASE WHEN included = 1 THEN rail_boardings END AS rail_boardings,
       CASE WHEN included = 1 THEN total_rides END AS total_rides,
       CASE WHEN SUM(included) OVER seven_days = 7 THEN
           AVG(CASE WHEN included = 1 THEN total_rides END) OVER seven_days
       END AS rolling_average_7d,
       CASE WHEN SUM(included) OVER seven_days = 7 THEN
           AVG(CASE WHEN included = 1 THEN bus END) OVER seven_days
       END AS bus_rolling_average_7d,
       CASE WHEN SUM(included) OVER seven_days = 7 THEN
           AVG(CASE WHEN included = 1 THEN rail_boardings END) OVER seven_days
       END AS rail_rolling_average_7d
FROM selected
WINDOW seven_days AS (ORDER BY service_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
ORDER BY service_date
