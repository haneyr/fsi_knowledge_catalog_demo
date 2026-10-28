CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_store_performance` AS
SELECT
  b.store_id,
  b.store_name,
  b.city,
  b.state,
  b.region,
  b.store_format,
  b.employee_count,
  COUNT(DISTINCT a.account_id) AS total_accounts,
  ROUND(SUM(a.current_balance), 2) AS total_pos_revenue,
  COUNT(DISTINCT l.bnpl_plan_id) AS total_bnpl_originations,
  ROUND(COALESCE(SUM(l.current_balance), 0), 2) AS total_bnpl_balance,
  COUNT(DISTINCT t.transaction_id) AS transaction_volume,
  ROUND(COALESCE(SUM(t.amount), 0), 2) AS transaction_value,
  ROUND(SAFE_DIVIDE(SUM(a.current_balance), b.employee_count), 2) AS sales_per_associate,
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT a.account_id), b.employee_count), 0) AS accounts_per_employee
FROM `${project_id}.retail_silver.silver_stores` b
LEFT JOIN `${project_id}.retail_silver.silver_loyalty_accounts` a ON b.store_id = a.store_id AND a.account_status = 'Active'
LEFT JOIN `${project_id}.retail_silver.silver_bnpl_plans` l ON b.store_id = l.originating_store_id
LEFT JOIN `${project_id}.retail_silver.silver_pos_transactions` t ON a.account_id = t.account_id
WHERE b.status = 'Open'
GROUP BY b.store_id, b.store_name, b.city, b.state, b.region, b.store_format, b.employee_count
