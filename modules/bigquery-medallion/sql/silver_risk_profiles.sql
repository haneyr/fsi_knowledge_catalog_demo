CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_risk_profiles` AS
SELECT
  risk_profile_id,
  wm_client_id,
  risk_tolerance,
  time_horizon_years,
  ROUND(ABS(annual_income), 0) AS annual_income,
  ROUND(ABS(net_worth), 0) AS net_worth,
  ROUND(ABS(liquid_net_worth), 0) AS liquid_net_worth,
  investment_experience,
  loss_tolerance,
  assessment_date,
  next_review_date,
  assessed_by,
  CASE WHEN next_review_date < CURRENT_DATE() THEN TRUE ELSE FALSE END AS review_overdue,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY risk_profile_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_risk_profiles`
)
WHERE rn = 1
  AND risk_profile_id IS NOT NULL
