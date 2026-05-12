CREATE OR REPLACE VIEW `${project_id}.fsi_dashboards.vw_branch_retail_wealth` AS
SELECT
  bp.branch_id,
  bp.branch_name,
  bp.city,
  bp.state,
  bp.region,
  bp.total_deposits AS retail_deposits,
  bp.total_loan_balance AS retail_loans,
  bp.total_accounts AS retail_accounts,
  bp.transaction_volume,
  ROUND(COALESCE(SUM(p.market_value), 0), 2) AS wealth_aum,
  COUNT(DISTINCT p.wm_client_id) AS wealth_clients,
  ROUND(bp.total_deposits + COALESCE(SUM(p.market_value), 0), 2) AS combined_assets
FROM `${project_id}.fsi_gold.gold_branch_performance` bp
LEFT JOIN `${project_id}.fsi_silver.silver_portfolios` p
  ON bp.branch_id = p.advisor_id
WHERE bp.branch_id IS NOT NULL
GROUP BY bp.branch_id, bp.branch_name, bp.city, bp.state, bp.region,
         bp.total_deposits, bp.total_loan_balance, bp.total_accounts, bp.transaction_volume
