CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_stress_tests` AS
SELECT
  stress_test_id,
  scenario_name,
  metric_type,
  projection_quarter,
  ROUND(projected_impact, 0) AS projected_impact,
  projected_capital_ratio,
  projected_loss_rate,
  result_status,
  reporting_year,
  regulatory_body,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_stress_tests`
WHERE stress_test_id IS NOT NULL
