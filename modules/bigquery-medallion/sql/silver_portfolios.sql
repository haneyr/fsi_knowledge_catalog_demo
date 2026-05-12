CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_portfolios` AS
SELECT
  portfolio_id,
  wm_client_id,
  portfolio_name,
  account_type,
  tax_status,
  ROUND(ABS(market_value), 2) AS market_value,
  ROUND(ABS(cost_basis), 2) AS cost_basis,
  ytd_return,
  inception_return,
  benchmark_id,
  advisor_id,
  model_portfolio_id,
  inception_date,
  status,
  ROUND(SAFE_DIVIDE(market_value - cost_basis, cost_basis), 4) AS total_return_pct,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY portfolio_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_portfolios`
)
WHERE rn = 1
  AND portfolio_id IS NOT NULL
  AND wm_client_id IS NOT NULL
