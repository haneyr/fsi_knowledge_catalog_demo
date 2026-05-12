CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_wm_clients` AS
SELECT
  wm_client_id,
  retail_customer_id,
  first_name,
  last_name,
  client_tier,
  ROUND(ABS(total_aum), 2) AS total_aum,
  risk_tolerance,
  investment_objective,
  primary_advisor_id,
  relationship_start_date,
  account_type,
  management_type,
  client_status,
  accredited_investor,
  qualified_purchaser,
  CONCAT('XXX-XX-', SUBSTR(tax_id, 6, 4)) AS tax_id_masked,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY wm_client_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_wm_clients`
)
WHERE rn = 1
  AND wm_client_id IS NOT NULL
