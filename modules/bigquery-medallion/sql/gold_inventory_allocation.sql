CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_inventory_allocation` AS
SELECT
  h.asset_class,
  h.sector,
  COUNT(DISTINCT h.assortment_id) AS assortment_count,
  COUNT(DISTINCT h.security_id) AS security_count,
  ROUND(SUM(h.current_retail_value), 2) AS total_market_value,
  ROUND(SUM(h.inventory_at_cost), 2) AS total_cost_basis,
  ROUND(SUM(h.markdown_exposure), 2) AS total_unrealized_gain_loss,
  ROUND(AVG(h.return_pct), 4) AS avg_return_pct,
  ROUND(SUM(h.quantity), 2) AS total_quantity
FROM `${project_id}.retail_silver.silver_inventory_positions` h
GROUP BY 1, 2
