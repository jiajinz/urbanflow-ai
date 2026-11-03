SELECT calendar_type, COUNT(*) AS observed_days,
       AVG(bus) AS average_daily_bus, AVG(rail_boardings) AS average_daily_rail,
       AVG(total_rides) AS average_daily_total, SUM(total_rides) AS total_rides
FROM filtered GROUP BY calendar_type ORDER BY calendar_type
