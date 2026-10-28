CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_reward_redemptions` AS
SELECT
  distribution_id,
  assortment_id,
  wm_client_id,
  distribution_type,
  ROUND(ABS(gross_amount), 2) AS gross_amount,
  ROUND(ABS(tax_withheld), 2) AS tax_withheld,
  ROUND(ABS(net_amount), 2) AS net_amount,
  distribution_date,
  settlement_date,
  payment_method,
  status,
  tax_treatment,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.retail_bronze.bronze_reward_redemptions`
WHERE distribution_id IS NOT NULL
  AND assortment_id IS NOT NULL
