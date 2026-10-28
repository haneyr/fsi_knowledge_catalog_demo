CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_product_skus` AS
SELECT
  security_id,
  ticker,
  security_name,
  gtin_13,
  sku_code,
  security_type,
  asset_class,
  sector,
  country,
  currency,
  exchange,
  ROUND(ABS(last_price), 2) AS last_price,
  dividend_yield,
  coupon_rate,
  maturity_date,
  credit_rating,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY security_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.retail_bronze.bronze_product_skus`
)
WHERE rn = 1
  AND security_id IS NOT NULL
