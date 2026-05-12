CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_transaction_patterns` AS
SELECT
  DATE_TRUNC(CAST(t.transaction_date AS DATE), MONTH) AS month,
  t.channel,
  t.merchant_category,
  t.transaction_type,
  COUNT(*) AS transaction_count,
  ROUND(SUM(t.amount), 2) AS total_amount,
  ROUND(AVG(t.amount), 2) AS avg_amount,
  ROUND(APPROX_QUANTILES(t.amount, 100)[OFFSET(50)], 2) AS median_amount,
  COUNT(DISTINCT t.account_id) AS unique_accounts,
  COUNTIF(t.fraud_score IS NOT NULL AND t.fraud_score > 70) AS high_fraud_score_count
FROM `${project_id}.fsi_silver.silver_transactions` t
WHERE t.transaction_date IS NOT NULL
GROUP BY 1, 2, 3, 4
