CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_interest_rates` AS
SELECT
  rate_id,
  as_of_date,
  rate_name,
  tenor,
  rate_value,
  daily_change,
  source,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_interest_rates`
WHERE rate_id IS NOT NULL
  AND rate_value >= 0
