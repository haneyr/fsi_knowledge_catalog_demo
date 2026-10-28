CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_financial_summary` AS
SELECT
  'Assets' AS category,
  'Cash & Store Working Balances' AS line_item,
  ROUND(SUM(CASE WHEN account_type IN ('POINTS_REWARDS', 'VIP_CASHBACK') THEN current_balance * 0.25 ELSE 0 END), 0) AS amount
FROM `${project_id}.retail_silver.silver_loyalty_accounts`
WHERE account_status = 'Active'
UNION ALL
SELECT 'Assets', 'Active BNPL Installment Receivables',
  ROUND(SUM(current_balance), 0)
FROM `${project_id}.retail_silver.silver_bnpl_plans`
UNION ALL
SELECT 'Assets', 'Merchandise Inventory at Market Value',
  ROUND(SUM(current_retail_value), 0)
FROM `${project_id}.retail_silver.silver_inventory_positions`
UNION ALL
SELECT 'Liabilities', 'Unredeemed Loyalty & Gift Wallet Liability',
  ROUND(SUM(current_balance), 0)
FROM `${project_id}.retail_silver.silver_loyalty_accounts`
WHERE account_status = 'Active'
UNION ALL
SELECT 'Liabilities', 'Supply Chain & Trade Payables',
  ROUND(SUM(inventory_at_cost) * 0.35, 0)
FROM `${project_id}.retail_silver.silver_inventory_positions`
UNION ALL
SELECT 'Operating Equity', 'Total Retail Operating Equity',
  ROUND(MAX(capital_amount), 0)
FROM `${project_id}.retail_silver.silver_working_capital`
WHERE capital_component = 'Total Operating Capital'
  AND reporting_date = (SELECT MAX(reporting_date) FROM `${project_id}.retail_silver.silver_working_capital`)
