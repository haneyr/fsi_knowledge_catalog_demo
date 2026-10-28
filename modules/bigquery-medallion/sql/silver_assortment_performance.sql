CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_assortment_performance` AS
SELECT
  performance_id,
  assortment_id,
  as_of_date,
  daily_return,
  mtd_return,
  qtd_return,
  ytd_return,
  ROUND(ABS(current_retail_value), 2) AS current_retail_value,
  ROUND(net_flows, 2) AS net_flows,
  benchmark_return,
  ROUND(daily_return - benchmark_return, 6) AS excess_return,
  alpha,
  beta,
  volatility,
  sharpe_ratio,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.retail_bronze.bronze_assortment_performance`
WHERE performance_id IS NOT NULL
  AND assortment_id IS NOT NULL
