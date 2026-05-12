CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_fx_rates` AS
SELECT
  fx_rate_id,
  as_of_date,
  currency_pair,
  mid_rate,
  bid_rate,
  ask_rate,
  ROUND(ask_rate - bid_rate, 6) AS spread,
  source,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_fx_rates`
WHERE fx_rate_id IS NOT NULL
  AND mid_rate > 0
