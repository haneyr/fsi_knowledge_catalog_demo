CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_promo_rules` AS
SELECT
  fee_schedule_id,
  wm_client_id,
  assortment_id,
  fee_type,
  ROUND(ABS(fee_rate_bps), 2) AS fee_rate_bps,
  billing_frequency,
  billing_method,
  ROUND(ABS(last_fee_amount), 2) AS last_fee_amount,
  last_billing_date,
  effective_date,
  end_date,
  CASE WHEN end_date IS NULL OR end_date > CURRENT_DATE() THEN TRUE ELSE FALSE END AS is_active,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY fee_schedule_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.retail_bronze.bronze_promo_rules`
)
WHERE rn = 1
  AND fee_schedule_id IS NOT NULL
