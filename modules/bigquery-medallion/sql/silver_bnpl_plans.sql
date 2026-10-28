CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_bnpl_plans` AS
SELECT
  bnpl_plan_id,
  customer_id,
  plan_type,
  ROUND(ABS(original_amount), 2) AS original_amount,
  ROUND(ABS(current_balance), 2) AS current_balance,
  interest_rate,
  rate_type,
  term_months,
  origination_date,
  maturity_date,
  delinquency_status,
  ltv_ratio,
  return_risk_score_at_signup,
  dti_ratio,
  collateral_description,
  risk_rating,
  naics_code,
  originating_store_id,
  store_associate_id,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY bnpl_plan_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.retail_bronze.bronze_bnpl_plans`
)
WHERE rn = 1
  AND bnpl_plan_id IS NOT NULL
  AND customer_id IS NOT NULL
  AND original_amount > 0
