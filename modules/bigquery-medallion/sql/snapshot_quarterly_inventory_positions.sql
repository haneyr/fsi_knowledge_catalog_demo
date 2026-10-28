CREATE OR REPLACE TABLE `${project_id}.retail_snapshots.snapshot_quarterly_inventory_positions` AS
SELECT
  CONCAT('PORT-', LPAD(CAST(CAST(MOD(n, 15000) + 1 AS INT64) AS STRING), 8, '0')) AS assortment_id,
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 15000.0) AS INT64) * 3 MONTH) AS snapshot_date,
  ROUND(28000 + RAND() * 240000, 2) AS current_retail_value,
  ROUND(18000 + RAND() * 155000, 2) AS inventory_at_cost,
  ROUND(0.04 + RAND() * 0.22, 4) AS qtd_return,
  ROUND(0.10 + RAND() * 0.38, 4) AS ytd_return,
  CAST(FLOOR(12 + RAND() * 65) AS INT64) AS holding_count
FROM UNNEST(GENERATE_ARRAY(1, 60000)) AS n
