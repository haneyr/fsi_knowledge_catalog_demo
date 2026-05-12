CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_performance` AS
SELECT
  performance_id,
  portfolio_id,
  as_of_date,
  daily_return,
  mtd_return,
  qtd_return,
  ytd_return,
  ROUND(ABS(market_value), 2) AS market_value,
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
FROM `${project_id}.fsi_bronze.bronze_performance`
WHERE performance_id IS NOT NULL
  AND portfolio_id IS NOT NULL
