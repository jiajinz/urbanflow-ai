SELECT service_date, day_type, total_rides, 'Highest' AS extreme
FROM filtered WHERE total_rides = (SELECT MAX(total_rides) FROM filtered)
UNION ALL
SELECT service_date, day_type, total_rides, 'Lowest' AS extreme
FROM filtered WHERE total_rides = (SELECT MIN(total_rides) FROM filtered)
ORDER BY extreme, service_date
