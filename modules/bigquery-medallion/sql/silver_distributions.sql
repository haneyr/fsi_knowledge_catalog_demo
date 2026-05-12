CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_distributions` AS
SELECT
  distribution_id,
  portfolio_id,
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
FROM `${project_id}.fsi_bronze.bronze_distributions`
WHERE distribution_id IS NOT NULL
  AND portfolio_id IS NOT NULL
