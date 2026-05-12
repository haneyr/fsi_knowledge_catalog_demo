CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_asset_allocation` AS
SELECT
  h.asset_class,
  h.sector,
  COUNT(DISTINCT h.portfolio_id) AS portfolio_count,
  COUNT(DISTINCT h.security_id) AS security_count,
  ROUND(SUM(h.market_value), 2) AS total_market_value,
  ROUND(SUM(h.cost_basis), 2) AS total_cost_basis,
  ROUND(SUM(h.unrealized_gain_loss), 2) AS total_unrealized_gain_loss,
  ROUND(AVG(h.return_pct), 4) AS avg_return_pct,
  ROUND(SUM(h.quantity), 2) AS total_quantity
FROM `${project_id}.fsi_silver.silver_holdings` h
GROUP BY 1, 2
