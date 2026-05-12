CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_securities` AS
SELECT
  security_id,
  ticker,
  security_name,
  cusip,
  isin,
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
  FROM `${project_id}.fsi_bronze.bronze_securities`
)
WHERE rn = 1
  AND security_id IS NOT NULL
