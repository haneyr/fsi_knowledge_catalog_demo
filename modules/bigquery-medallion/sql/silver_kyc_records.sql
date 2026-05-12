CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_kyc_records` AS
SELECT
  kyc_id,
  customer_id,
  due_diligence_level,
  verification_status,
  last_review_date,
  next_review_date,
  risk_score_category,
  risk_score,
  pep_flag,
  sanctions_flag,
  adverse_media_flag,
  id_document_type,
  country_of_citizenship,
  beneficial_owner_id,
  reviewer_id,
  CASE WHEN next_review_date < CURRENT_DATE() THEN TRUE ELSE FALSE END AS review_overdue,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY kyc_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_kyc_records`
)
WHERE rn = 1
  AND kyc_id IS NOT NULL
  AND customer_id IS NOT NULL
