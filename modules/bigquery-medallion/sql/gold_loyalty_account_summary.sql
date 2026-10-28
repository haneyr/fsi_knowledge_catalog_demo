CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_loyalty_account_summary` AS
SELECT
  a.account_id,
  a.customer_id,
  a.account_type,
  a.account_status,
  a.current_balance,
  a.interest_rate,
  a.open_date,
  a.store_id,
  COUNT(DISTINCT t.transaction_id) AS transaction_count_90d,
  ROUND(COALESCE(SUM(CASE WHEN t.transaction_type = 'DEBIT' THEN t.amount END), 0), 2) AS total_debits_90d,
  ROUND(COALESCE(SUM(CASE WHEN t.transaction_type = 'CREDIT' THEN t.amount END), 0), 2) AS total_credits_90d,
  ROUND(AVG(t.amount), 2) AS avg_transaction_amount,
  MAX(t.transaction_date) AS last_transaction_date,
  CASE WHEN MAX(t.transaction_date) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY) THEN TRUE ELSE FALSE END AS is_dormant
FROM `${project_id}.retail_silver.silver_loyalty_accounts` a
LEFT JOIN `${project_id}.retail_silver.silver_pos_transactions` t
  ON a.account_id = t.account_id
  AND t.transaction_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY a.account_id, a.customer_id, a.account_type, a.account_status,
         a.current_balance, a.interest_rate, a.open_date, a.store_id
