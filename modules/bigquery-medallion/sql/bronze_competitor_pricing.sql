CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_competitor_pricing` AS
SELECT
  CONCAT('MKT-', LPAD(CAST(n AS STRING), 10, '0')) AS market_data_id,
  CONCAT('SEC-', LPAD(CAST(CAST(MOD(n, 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(n / 5000.0) AS INT64) DAY) AS as_of_date,
  ROUND(12.0 + RAND() * 340.0, 2) AS close_price,
  ROUND(12.0 + RAND() * 345.0, 2) AS open_price,
  ROUND(14.0 + RAND() * 360.0, 2) AS high_price,
  ROUND(9.99 + RAND() * 310.0, 2) AS low_price,
  CAST(FLOOR(25 + RAND() * 4500) AS INT64) AS volume,
  ROUND(-0.15 + RAND() * 0.25, 4) AS daily_return,
  ROUND(11.5 + RAND() * 330.0, 2) AS bid_price,
  ROUND(12.5 + RAND() * 350.0, 2) AS ask_price,
  CASE WHEN MOD(n, 5000) < 2000 THEN ROUND(0.25 + RAND() * 0.40, 4) ELSE NULL END AS yield_to_maturity,
  CASE WHEN MOD(n, 5000) < 2000 THEN ROUND(14 + RAND() * 75, 1) ELSE NULL END AS duration,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'HELIOS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
