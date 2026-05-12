CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_balance_sheet_summary` AS
SELECT
  'Assets' AS category,
  'Cash and Due From Banks' AS line_item,
  ROUND(SUM(CASE WHEN account_type IN ('CHECKING', 'SAVINGS') THEN current_balance * 0.05 ELSE 0 END), 0) AS amount
FROM `${project_id}.fsi_silver.silver_accounts`
WHERE account_status = 'Active'
UNION ALL
SELECT 'Assets', 'Total Loans and Leases',
  ROUND(SUM(current_balance), 0)
FROM `${project_id}.fsi_silver.silver_loans`
UNION ALL
SELECT 'Assets', 'Investment Securities',
  ROUND(SUM(market_value), 0)
FROM `${project_id}.fsi_silver.silver_holdings`
UNION ALL
SELECT 'Liabilities', 'Total Deposits',
  ROUND(SUM(current_balance), 0)
FROM `${project_id}.fsi_silver.silver_accounts`
WHERE account_status = 'Active'
UNION ALL
SELECT 'Liabilities', 'Other Borrowed Funds',
  ROUND(SUM(current_balance) * 0.15, 0)
FROM `${project_id}.fsi_silver.silver_accounts`
WHERE account_status = 'Active'
UNION ALL
SELECT 'Equity', 'Total Equity Capital',
  ROUND(MAX(capital_amount), 0)
FROM `${project_id}.fsi_silver.silver_regulatory_capital`
WHERE capital_component = 'Total Capital'
  AND reporting_date = (SELECT MAX(reporting_date) FROM `${project_id}.fsi_silver.silver_regulatory_capital`)
