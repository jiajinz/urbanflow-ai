SELECT COUNT(*) AS observed_days,
       COALESCE(SUM(total_rides), 0) AS total_rides,
       AVG(bus) AS average_daily_bus, AVG(rail_boardings) AS average_daily_rail,
       SUM(bus) * 1.0 / NULLIF(SUM(total_rides), 0) AS bus_share,
       SUM(rail_boardings) * 1.0 / NULLIF(SUM(total_rides), 0) AS rail_share,
       (SELECT COUNT(*) FROM selected WHERE total_rides IS NULL) AS missing_days,
       (SELECT COUNT(*) FROM selected) AS calendar_days
FROM filtered
