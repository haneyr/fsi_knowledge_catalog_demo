CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_gl_entries` AS
SELECT
  gl_entry_id,
  gl_account_id,
  cost_center_id,
  posting_date,
  effective_date,
  entry_type,
  ROUND(ABS(amount), 2) AS amount,
  currency,
  journal_entry_id,
  description,
  source_type,
  batch_id,
  status,
  is_reversal,
  reversal_of,
  fiscal_year,
  fiscal_period,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_gl_entries`
WHERE gl_entry_id IS NOT NULL
  AND gl_account_id IS NOT NULL
  AND status = 'Posted'
