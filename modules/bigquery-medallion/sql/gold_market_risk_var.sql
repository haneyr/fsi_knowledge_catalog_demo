CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_market_risk_var` AS
SELECT
  h.asset_class,
  h.sector,
  COUNT(DISTINCT h.security_id) AS position_count,
  ROUND(SUM(h.market_value), 2) AS total_exposure,
  ROUND(AVG(md.daily_return), 6) AS avg_daily_return,
  ROUND(STDDEV(md.daily_return), 6) AS return_volatility,
  ROUND(SUM(h.market_value) * STDDEV(md.daily_return) * 2.326, 2) AS var_99_1d,
  ROUND(SUM(h.market_value) * STDDEV(md.daily_return) * 1.645, 2) AS var_95_1d,
  ROUND(SUM(h.market_value) * STDDEV(md.daily_return) * 2.326 * SQRT(10), 2) AS var_99_10d,
  ROUND(AVG(md.duration), 2) AS avg_duration,
  ROUND(AVG(md.yield_to_maturity), 4) AS avg_ytm
FROM `${project_id}.fsi_silver.silver_holdings` h
LEFT JOIN `${project_id}.fsi_silver.silver_market_data` md ON h.security_id = md.security_id
GROUP BY 1, 2
