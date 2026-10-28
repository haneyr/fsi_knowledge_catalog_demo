CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_carrier_feeds` AS
SELECT
  feed_id,
  assortment_id,
  custodian_name,
  feed_type,
  as_of_date,
  security_id,
  ROUND(ABS(quantity), 4) AS quantity,
  ROUND(ABS(current_retail_value), 2) AS current_retail_value,
  reconciliation_status,
  ROUND(break_amount, 2) AS break_amount,
  CASE WHEN ABS(break_amount) > 0.01 THEN TRUE ELSE FALSE END AS has_break,
  received_at,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.retail_bronze.bronze_carrier_feeds`
WHERE feed_id IS NOT NULL
  AND assortment_id IS NOT NULL
