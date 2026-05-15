CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_market_data` AS
SELECT
  CONCAT('MKT-', LPAD(CAST(n AS STRING), 10, '0')) AS market_data_id,
  CONCAT('SEC-', LPAD(CAST(CAST(MOD(n, 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(n / 5000.0) AS INT64) DAY) AS as_of_date,
  ROUND(0.5 + RAND() * 5000, 2) AS close_price,
  ROUND(0.5 + RAND() * 5100, 2) AS open_price,
  ROUND(0.5 + RAND() * 5200, 2) AS high_price,
  ROUND(0.4 + RAND() * 4800, 2) AS low_price,
  CAST(FLOOR(1000 + RAND() * 10000000) AS INT64) AS volume,
  ROUND(-0.1 + RAND() * 0.2, 4) AS daily_return,
  ROUND(0.01 + RAND() * 5000, 2) AS bid_price,
  ROUND(0.01 + RAND() * 5000, 2) AS ask_price,
  CASE WHEN MOD(n, 5000) < 2000 THEN ROUND(0 + RAND() * 0.08, 4) ELSE NULL END AS yield_to_maturity,
  CASE WHEN MOD(n, 5000) < 2000 THEN ROUND(0.5 + RAND() * 15, 2) ELSE NULL END AS duration,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ARGUS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
