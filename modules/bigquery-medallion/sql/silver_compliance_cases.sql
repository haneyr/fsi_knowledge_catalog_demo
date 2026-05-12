CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_compliance_cases` AS
SELECT
  case_id,
  case_type,
  severity,
  related_customer_id,
  related_account_id,
  opened_date,
  closed_date,
  status,
  assigned_analyst,
  sar_filed,
  sar_filing_id,
  narrative_summary,
  CASE WHEN closed_date IS NOT NULL THEN DATE_DIFF(closed_date, opened_date, DAY) ELSE NULL END AS resolution_days,
  CASE WHEN closed_date IS NULL AND DATE_DIFF(CURRENT_DATE(), opened_date, DAY) > 30 THEN TRUE ELSE FALSE END AS aging_flag,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY case_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_compliance_cases`
)
WHERE rn = 1
  AND case_id IS NOT NULL
