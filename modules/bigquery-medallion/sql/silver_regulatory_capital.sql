CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_regulatory_capital` AS
SELECT
  capital_id,
  reporting_date,
  capital_component,
  ROUND(ABS(capital_amount), 0) AS capital_amount,
  ROUND(ABS(risk_weighted_assets), 0) AS risk_weighted_assets,
  capital_ratio,
  regulatory_minimum,
  capital_conservation_buffer,
  countercyclical_buffer,
  ROUND(ABS(leverage_exposure), 0) AS leverage_exposure,
  leverage_ratio,
  calculation_approach,
  ROUND(capital_ratio - regulatory_minimum, 4) AS buffer_above_minimum,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_regulatory_capital`
WHERE capital_id IS NOT NULL
