CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_portfolio_performance` AS
SELECT
  p.portfolio_id,
  p.wm_client_id,
  p.portfolio_name,
  p.account_type,
  p.tax_status,
  p.market_value,
  p.cost_basis,
  p.total_return_pct,
  p.ytd_return,
  p.inception_return,
  p.advisor_id,
  p.benchmark_id,
  bm.benchmark_name,
  ROUND(AVG(perf.daily_return), 6) AS avg_daily_return,
  ROUND(AVG(perf.alpha), 4) AS avg_alpha,
  ROUND(AVG(perf.beta), 4) AS avg_beta,
  ROUND(AVG(perf.volatility), 4) AS avg_volatility,
  ROUND(AVG(perf.sharpe_ratio), 4) AS avg_sharpe_ratio,
  ROUND(AVG(perf.excess_return), 6) AS avg_excess_return,
  COUNT(DISTINCT h.holding_id) AS holding_count,
  COUNT(DISTINCT h.asset_class) AS asset_class_count
FROM `${project_id}.fsi_silver.silver_portfolios` p
LEFT JOIN `${project_id}.fsi_silver.silver_performance` perf ON p.portfolio_id = perf.portfolio_id
LEFT JOIN `${project_id}.fsi_silver.silver_holdings` h ON p.portfolio_id = h.portfolio_id
LEFT JOIN (SELECT DISTINCT benchmark_id, benchmark_name FROM `${project_id}.fsi_silver.silver_benchmarks`) bm ON p.benchmark_id = bm.benchmark_id
WHERE p.status = 'Active'
GROUP BY p.portfolio_id, p.wm_client_id, p.portfolio_name, p.account_type, p.tax_status,
         p.market_value, p.cost_basis, p.total_return_pct, p.ytd_return, p.inception_return,
         p.advisor_id, p.benchmark_id, bm.benchmark_name
