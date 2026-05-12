CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_gl_accounts` AS
SELECT
  gl_account_id,
  account_number,
  account_name,
  account_type,
  category,
  level_type,
  parent_account_id,
  normal_balance,
  is_call_report_line,
  call_report_line,
  status,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY gl_account_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_gl_accounts`
)
WHERE rn = 1
  AND gl_account_id IS NOT NULL
