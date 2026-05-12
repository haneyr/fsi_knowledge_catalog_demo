CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_regulatory_filings` AS
SELECT
  filing_id,
  report_name,
  regulatory_body,
  filing_frequency,
  reporting_period_end,
  filing_due_date,
  actual_filing_date,
  filing_status,
  preparer_id,
  reviewer_id,
  amendment_notes,
  CASE WHEN actual_filing_date > filing_due_date THEN TRUE ELSE FALSE END AS filed_late,
  CASE WHEN actual_filing_date IS NOT NULL THEN DATE_DIFF(filing_due_date, actual_filing_date, DAY) ELSE NULL END AS days_before_deadline,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY filing_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_regulatory_filings`
)
WHERE rn = 1
  AND filing_id IS NOT NULL
