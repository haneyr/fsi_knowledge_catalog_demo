CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_customers` AS
SELECT
  customer_id,
  first_name,
  last_name,
  SAFE.PARSE_DATE('%Y-%m-%d', date_of_birth) AS date_of_birth,
  CASE WHEN REGEXP_CONTAINS(ssn, r'^\d{3}-\d{2}-\d{4}$') THEN CONCAT('XXX-XX-', SUBSTR(ssn, 8, 4))
       WHEN REGEXP_CONTAINS(ssn, r'^\d{9}$') THEN CONCAT('XXX-XX-', SUBSTR(ssn, 6, 4))
       ELSE NULL END AS ssn_masked,
  address_line1,
  city,
  state,
  zip_code,
  phone,
  LOWER(email) AS email,
  customer_type,
  customer_segment,
  citizenship_status,
  CONCAT('XXX-XX-', SUBSTR(tin, 6, 4)) AS tin_masked,
  industry,
  kyc_risk_rating,
  kyc_status,
  home_branch_id,
  account_opened_date,
  source_system,
  created_at,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_customers`
)
WHERE rn = 1
  AND customer_id IS NOT NULL
