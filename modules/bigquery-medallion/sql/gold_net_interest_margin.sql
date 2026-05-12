CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_net_interest_margin` AS
SELECT
  a.account_type AS product,
  a.branch_id,
  COUNT(*) AS account_count,
  ROUND(SUM(a.current_balance), 2) AS total_balance,
  ROUND(AVG(a.interest_rate), 6) AS avg_interest_rate,
  ROUND(SUM(a.current_balance * a.interest_rate), 2) AS interest_income_est,
  ROUND(AVG(a.interest_rate) * 100, 4) AS rate_pct,
  'Deposit' AS balance_type
FROM `${project_id}.fsi_silver.silver_accounts` a
WHERE a.account_status = 'Active'
GROUP BY 1, 2
UNION ALL
SELECT
  l.loan_type AS product,
  l.originating_branch_id AS branch_id,
  COUNT(*) AS account_count,
  ROUND(SUM(l.current_balance), 2) AS total_balance,
  ROUND(AVG(l.interest_rate), 6) AS avg_interest_rate,
  ROUND(SUM(l.current_balance * l.interest_rate), 2) AS interest_income_est,
  ROUND(AVG(l.interest_rate) * 100, 4) AS rate_pct,
  'Loan' AS balance_type
FROM `${project_id}.fsi_silver.silver_loans` l
GROUP BY 1, 2
