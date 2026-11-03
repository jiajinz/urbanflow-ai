SELECT CAST(date_trunc('week', service_date) AS DATE) AS week_start,
       SUM(CASE WHEN included = 1 THEN total_rides END) AS total_rides,
       SUM(included) AS observed_days,
       COUNT(total_rides) AS available_days,
       CASE WHEN COUNT(*) = 7 AND COUNT(total_rides) = 7 THEN TRUE ELSE FALSE END AS complete_week
FROM selected
GROUP BY date_trunc('week', service_date)
ORDER BY week_start
