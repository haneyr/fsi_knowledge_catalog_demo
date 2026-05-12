CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_card_transactions` AS
SELECT
  card_transaction_id,
  card_id,
  transaction_type,
  ROUND(ABS(amount), 2) AS amount,
  currency,
  transaction_date,
  merchant_name,
  mcc_code,
  pos_entry_mode,
  authorization_status,
  fraud_score,
  is_disputed,
  merchant_country,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_card_transactions`
WHERE card_transaction_id IS NOT NULL
  AND card_id IS NOT NULL
