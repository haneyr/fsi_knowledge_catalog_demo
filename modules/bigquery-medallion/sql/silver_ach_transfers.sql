CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_ach_transfers` AS
SELECT
  ach_id,
  account_id,
  direction,
  sec_code,
  ROUND(ABS(amount), 2) AS amount,
  effective_date,
  settlement_date,
  status,
  return_code,
  originator_name,
  originating_dfi,
  batch_id,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_ach_transfers`
WHERE ach_id IS NOT NULL
  AND account_id IS NOT NULL
