CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_credit_cards` AS
SELECT
  card_id,
  customer_id,
  account_id,
  card_type,
  network,
  masked_card_number,
  ROUND(ABS(credit_limit), 0) AS credit_limit,
  ROUND(ABS(current_balance), 2) AS current_balance,
  ROUND(ABS(available_credit), 2) AS available_credit,
  apr,
  ROUND(ABS(annual_fee), 2) AS annual_fee,
  fico_score,
  issue_date,
  expiration_date,
  card_status,
  ROUND(ABS(rewards_balance), 2) AS rewards_balance,
  rewards_type,
  ROUND(SAFE_DIVIDE(current_balance, credit_limit), 4) AS utilization_ratio,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY card_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_credit_cards`
)
WHERE rn = 1
  AND card_id IS NOT NULL
