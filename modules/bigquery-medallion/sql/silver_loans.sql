CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_loans` AS
SELECT
  loan_id,
  customer_id,
  loan_type,
  ROUND(ABS(original_amount), 2) AS original_amount,
  ROUND(ABS(current_balance), 2) AS current_balance,
  interest_rate,
  rate_type,
  term_months,
  origination_date,
  maturity_date,
  delinquency_status,
  ltv_ratio,
  fico_score_at_origination,
  dti_ratio,
  collateral_description,
  risk_rating,
  naics_code,
  originating_branch_id,
  loan_officer_id,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY loan_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_loans`
)
WHERE rn = 1
  AND loan_id IS NOT NULL
  AND customer_id IS NOT NULL
  AND original_amount > 0
