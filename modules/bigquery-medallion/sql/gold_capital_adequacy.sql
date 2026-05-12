CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_capital_adequacy` AS
SELECT
  rc.reporting_date,
  rc.capital_component,
  rc.capital_amount,
  rc.risk_weighted_assets,
  rc.capital_ratio,
  rc.regulatory_minimum,
  rc.capital_conservation_buffer,
  rc.countercyclical_buffer,
  ROUND(rc.regulatory_minimum + rc.capital_conservation_buffer + rc.countercyclical_buffer, 4) AS fully_loaded_minimum,
  rc.buffer_above_minimum,
  rc.leverage_exposure,
  rc.leverage_ratio,
  rc.calculation_approach
FROM `${project_id}.fsi_silver.silver_regulatory_capital` rc
