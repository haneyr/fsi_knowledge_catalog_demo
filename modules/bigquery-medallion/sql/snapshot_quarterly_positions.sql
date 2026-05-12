CREATE OR REPLACE TABLE `${project_id}.fsi_snapshots.snapshot_quarterly_positions` AS
SELECT
  CONCAT('PORT-', LPAD(CAST(CAST(MOD(n, 15000) + 1 AS INT64) AS STRING), 8, '0')) AS portfolio_id,
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 15000.0) AS INT64) * 3 MONTH) AS snapshot_date,
  ROUND(50000 + RAND() * 10000000, 2) AS market_value,
  ROUND(40000 + RAND() * 8000000, 2) AS cost_basis,
  ROUND(-0.1 + RAND() * 0.3, 4) AS qtd_return,
  ROUND(-0.15 + RAND() * 0.4, 4) AS ytd_return,
  CAST(FLOOR(5 + RAND() * 50) AS INT64) AS holding_count
FROM UNNEST(GENERATE_ARRAY(1, 60000)) AS n
