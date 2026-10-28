CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_gross_margin_analysis` AS
SELECT
  a.account_type AS product,
  a.store_id,
  COUNT(*) AS account_count,
  ROUND(SUM(a.current_balance), 2) AS total_balance,
  ROUND(AVG(a.interest_rate), 6) AS avg_interest_rate,
  ROUND(SUM(a.current_balance * a.interest_rate), 2) AS interest_income_est,
  ROUND(AVG(a.interest_rate) * 100, 4) AS rate_pct,
  'Loyalty Credit' AS balance_type
FROM `${project_id}.retail_silver.silver_loyalty_accounts` a
WHERE a.account_status = 'Active'
GROUP BY 1, 2
UNION ALL
SELECT
  l.plan_type AS product,
  l.originating_store_id AS store_id,
  COUNT(*) AS account_count,
  ROUND(SUM(l.current_balance), 2) AS total_balance,
  ROUND(AVG(l.interest_rate), 6) AS avg_interest_rate,
  ROUND(SUM(l.current_balance * l.interest_rate), 2) AS interest_income_est,
  ROUND(AVG(l.interest_rate) * 100, 4) AS rate_pct,
  'BNPL Plan' AS balance_type
FROM `${project_id}.retail_silver.silver_bnpl_plans` l
GROUP BY 1, 2
