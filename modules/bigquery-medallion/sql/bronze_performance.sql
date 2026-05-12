CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_performance` AS
SELECT
  CONCAT('PERF-', LPAD(CAST(n AS STRING), 10, '0')) AS performance_id,
  CONCAT('PORT-', LPAD(CAST(CAST(MOD(n, 15000) + 1 AS INT64) AS STRING), 8, '0')) AS portfolio_id,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(n / 15000.0) AS INT64) DAY) AS as_of_date,
  ROUND(-0.05 + RAND() * 0.1, 6) AS daily_return,
  ROUND(-0.1 + RAND() * 0.3, 4) AS mtd_return,
  ROUND(-0.15 + RAND() * 0.4, 4) AS qtd_return,
  ROUND(-0.2 + RAND() * 0.5, 4) AS ytd_return,
  ROUND(100000 + RAND() * 10000000, 2) AS market_value,
  ROUND(-1000 + RAND() * 50000, 2) AS net_flows,
  ROUND(-0.05 + RAND() * 0.1, 6) AS benchmark_return,
  ROUND(-0.02 + RAND() * 0.04, 6) AS alpha,
  ROUND(0.5 + RAND() * 1.0, 4) AS beta,
  ROUND(0.01 + RAND() * 0.3, 4) AS volatility,
  ROUND(-1 + RAND() * 4, 4) AS sharpe_ratio,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
