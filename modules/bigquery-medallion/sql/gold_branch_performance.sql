CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_branch_performance` AS
SELECT
  b.branch_id,
  b.branch_name,
  b.city,
  b.state,
  b.region,
  b.branch_type,
  b.employee_count,
  COUNT(DISTINCT a.account_id) AS total_accounts,
  ROUND(SUM(a.current_balance), 2) AS total_deposits,
  COUNT(DISTINCT l.loan_id) AS total_loans,
  ROUND(COALESCE(SUM(l.current_balance), 0), 2) AS total_loan_balance,
  COUNT(DISTINCT t.transaction_id) AS transaction_volume,
  ROUND(COALESCE(SUM(t.amount), 0), 2) AS transaction_value,
  ROUND(SAFE_DIVIDE(SUM(a.current_balance), b.employee_count), 2) AS deposits_per_employee,
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT a.account_id), b.employee_count), 0) AS accounts_per_employee
FROM `${project_id}.fsi_silver.silver_branches` b
LEFT JOIN `${project_id}.fsi_silver.silver_accounts` a ON b.branch_id = a.branch_id AND a.account_status = 'Active'
LEFT JOIN `${project_id}.fsi_silver.silver_loans` l ON b.branch_id = l.originating_branch_id
LEFT JOIN `${project_id}.fsi_silver.silver_transactions` t ON a.account_id = t.account_id
WHERE b.status = 'Open'
GROUP BY b.branch_id, b.branch_name, b.city, b.state, b.region, b.branch_type, b.employee_count
