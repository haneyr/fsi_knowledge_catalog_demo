CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_interest_rates` AS
SELECT
  CONCAT('RATE-', LPAD(CAST(n AS STRING), 8, '0')) AS rate_id,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) DAY) AS as_of_date,
  CASE MOD(n, 10)
    WHEN 0 THEN 'Fed Funds Rate' WHEN 1 THEN 'SOFR' WHEN 2 THEN 'Prime Rate'
    WHEN 3 THEN 'US Treasury 2Y' WHEN 4 THEN 'US Treasury 5Y' WHEN 5 THEN 'US Treasury 10Y'
    WHEN 6 THEN 'US Treasury 30Y' WHEN 7 THEN 'SOFR 30-Day Avg' WHEN 8 THEN 'SOFR 90-Day Avg'
    ELSE 'Discount Rate'
  END AS rate_name,
  CASE MOD(n, 10)
    WHEN 0 THEN 'Overnight' WHEN 1 THEN 'Overnight' WHEN 2 THEN 'Overnight'
    WHEN 3 THEN '2Y' WHEN 4 THEN '5Y' WHEN 5 THEN '10Y'
    WHEN 6 THEN '30Y' WHEN 7 THEN '30D' WHEN 8 THEN '90D'
    ELSE 'Overnight'
  END AS tenor,
  ROUND(0.01 + RAND() * 0.06, 6) AS rate_value,
  ROUND(-0.005 + RAND() * 0.01, 6) AS daily_change,
  CASE MOD(n, 10)
    WHEN 0 THEN 'Federal Reserve' WHEN 1 THEN 'NY Fed' WHEN 2 THEN 'WSJ'
    WHEN 3 THEN 'US Treasury' WHEN 4 THEN 'US Treasury' WHEN 5 THEN 'US Treasury'
    WHEN 6 THEN 'US Treasury' WHEN 7 THEN 'NY Fed' WHEN 8 THEN 'NY Fed'
    ELSE 'Federal Reserve'
  END AS source,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ARGUS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 7000)) AS n
