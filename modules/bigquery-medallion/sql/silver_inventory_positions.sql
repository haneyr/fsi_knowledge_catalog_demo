CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_inventory_positions` AS
SELECT
  holding_id,
  assortment_id,
  security_id,
  ROUND(ABS(quantity), 4) AS quantity,
  ROUND(ABS(market_price), 2) AS market_price,
  ROUND(ABS(current_retail_value), 2) AS current_retail_value,
  ROUND(ABS(inventory_at_cost), 2) AS inventory_at_cost,
  ROUND(ABS(markdown_exposure), 2) AS markdown_exposure,
  asset_class,
  sector,
  as_of_date,
  ROUND(SAFE_DIVIDE(current_retail_value - inventory_at_cost, inventory_at_cost), 4) AS return_pct,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.retail_bronze.bronze_inventory_positions`
WHERE holding_id IS NOT NULL
  AND assortment_id IS NOT NULL
  AND security_id IS NOT NULL
