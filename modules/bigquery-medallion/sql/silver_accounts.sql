CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_accounts` AS
SELECT
  account_id,
  customer_id,
  account_type,
  account_status,
  ROUND(ABS(current_balance), 2) AS current_balance,
  ROUND(ABS(available_balance), 2) AS available_balance,
  interest_rate,
  routing_number,
  open_date,
  close_date,
  branch_id,
  currency_code,
  term_months,
  maturity_date,
  joint_account,
  origination_channel,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_accounts`
)
WHERE rn = 1
  AND account_id IS NOT NULL
  AND customer_id IS NOT NULL
