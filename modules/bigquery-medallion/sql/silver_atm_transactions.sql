CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_atm_transactions` AS
SELECT
  atm_transaction_id,
  account_id,
  card_id,
  transaction_type,
  ROUND(ABS(amount), 2) AS amount,
  transaction_date,
  terminal_id,
  network_type,
  surcharge_applied,
  ROUND(ABS(surcharge_amount), 2) AS surcharge_amount,
  terminal_state,
  status,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_atm_transactions`
WHERE atm_transaction_id IS NOT NULL
  AND account_id IS NOT NULL
