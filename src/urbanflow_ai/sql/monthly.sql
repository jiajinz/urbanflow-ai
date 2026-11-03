, monthly AS (
    SELECT CAST(date_trunc('month', service_date) AS DATE) AS month,
           SUM(CASE WHEN included = 1 THEN total_rides END) AS total_rides,
           SUM(included) AS observed_days,
           CASE WHEN MIN(service_date) = CAST(date_trunc('month', MIN(service_date)) AS DATE)
             AND MAX(service_date) = CAST(date_trunc('month', MIN(service_date)) + INTERVAL '1 month' - INTERVAL '1 day' AS DATE)
             AND COUNT(*) = COUNT(total_rides)
             AND (SELECT day_filter FROM bounds) = 'All'
           THEN TRUE ELSE FALSE END AS complete_month
    FROM selected GROUP BY date_trunc('month', service_date)
), previous AS (
    SELECT *, LAG(total_rides) OVER (ORDER BY month) AS previous_total,
              LAG(complete_month) OVER (ORDER BY month) AS previous_complete
    FROM monthly
)
SELECT *, CASE WHEN complete_month AND previous_complete
                   THEN (total_rides - previous_total) * 1.0 / NULLIF(previous_total, 0)
          END AS month_over_month_change
FROM previous ORDER BY month
