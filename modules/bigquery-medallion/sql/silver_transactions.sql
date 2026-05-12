CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_transactions` AS
SELECT
  transaction_id,
  account_id,
  transaction_type,
  ROUND(ABS(amount), 2) AS amount,
  currency,
  transaction_date,
  posted_date,
  description,
  merchant_category,
  channel,
  branch_id,
  status,
  fraud_score,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_transactions`
WHERE transaction_id IS NOT NULL
  AND account_id IS NOT NULL
  AND amount > 0
