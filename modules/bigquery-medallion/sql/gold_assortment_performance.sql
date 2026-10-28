CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_assortment_performance` AS
SELECT
  p.assortment_id,
  p.wm_client_id,
  p.assortment_name,
  p.account_type,
  p.tax_status,
  p.current_retail_value,
  p.inventory_at_cost,
  p.sell_through_pct,
  p.ytd_return,
  p.inception_return,
  p.advisor_id,
  p.benchmark_id,
  bm.benchmark_name,
  ROUND(AVG(perf.daily_return), 6) AS avg_daily_return,
  ROUND(AVG(perf.alpha), 4) AS avg_alpha,
  ROUND(AVG(perf.beta), 4) AS avg_beta,
  ROUND(AVG(perf.volatility), 4) AS avg_volatility,
  ROUND(SAFE_DIVIDE(p.current_retail_value - p.inventory_at_cost, p.inventory_at_cost), 2) AS gmroi,
  ROUND(AVG(perf.excess_return), 6) AS avg_excess_return,
  COUNT(DISTINCT h.holding_id) AS holding_count,
  COUNT(DISTINCT h.asset_class) AS asset_class_count
FROM `${project_id}.retail_silver.silver_merch_assortments` p
LEFT JOIN `${project_id}.retail_silver.silver_assortment_performance` perf ON p.assortment_id = perf.assortment_id
LEFT JOIN `${project_id}.retail_silver.silver_inventory_positions` h ON p.assortment_id = h.assortment_id
LEFT JOIN (SELECT DISTINCT benchmark_id, benchmark_name FROM `${project_id}.retail_silver.silver_category_benchmarks`) bm ON p.benchmark_id = bm.benchmark_id
WHERE p.status = 'Active'
GROUP BY p.assortment_id, p.wm_client_id, p.assortment_name, p.account_type, p.tax_status,
         p.current_retail_value, p.inventory_at_cost, p.sell_through_pct, p.ytd_return, p.inception_return,
         p.advisor_id, p.benchmark_id, bm.benchmark_name
QUALIFY ROW_NUMBER() OVER (PARTITION BY p.assortment_name ORDER BY COUNT(DISTINCT h.holding_id) DESC, p.assortment_id) = 1
