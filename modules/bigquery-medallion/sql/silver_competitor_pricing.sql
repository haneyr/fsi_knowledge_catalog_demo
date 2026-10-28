CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_competitor_pricing` AS
SELECT
  market_data_id,
  security_id,
  as_of_date,
  ROUND(ABS(close_price), 2) AS close_price,
  ROUND(ABS(open_price), 2) AS open_price,
  ROUND(ABS(high_price), 2) AS high_price,
  ROUND(ABS(low_price), 2) AS low_price,
  volume,
  daily_return,
  ROUND(ABS(bid_price), 2) AS bid_price,
  ROUND(ABS(ask_price), 2) AS ask_price,
  yield_to_maturity,
  duration,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.retail_bronze.bronze_competitor_pricing`
WHERE market_data_id IS NOT NULL
  AND security_id IS NOT NULL
  AND close_price > 0
