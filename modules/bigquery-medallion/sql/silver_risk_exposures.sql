CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_risk_exposures` AS
SELECT
  exposure_id,
  risk_type,
  risk_subcategory,
  counterparty_id,
  ROUND(ABS(gross_exposure), 2) AS gross_exposure,
  ROUND(ABS(net_exposure), 2) AS net_exposure,
  ROUND(ABS(collateral_value), 2) AS collateral_value,
  probability_of_default,
  loss_given_default,
  ROUND(ABS(expected_loss), 2) AS expected_loss,
  industry_sector,
  country,
  as_of_date,
  ROUND(SAFE_DIVIDE(collateral_value, gross_exposure), 4) AS collateralization_ratio,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_risk_exposures`
WHERE exposure_id IS NOT NULL
