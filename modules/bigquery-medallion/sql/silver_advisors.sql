CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_advisors` AS
SELECT
  advisor_id,
  first_name,
  last_name,
  certifications,
  title,
  region,
  office_branch_id,
  finra_crd_number,
  years_experience,
  ROUND(ABS(total_aum), 0) AS total_aum,
  client_count,
  ROUND(ABS(avg_fee_bps), 2) AS avg_fee_bps,
  hire_date,
  status,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY advisor_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_advisors`
)
WHERE rn = 1
  AND advisor_id IS NOT NULL
