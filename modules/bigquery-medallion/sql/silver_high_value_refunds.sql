CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_high_value_refunds` AS
SELECT
  wire_id,
  originator_account_id,
  originator_customer_id,
  beneficiary_name,
  beneficiary_routing,
  beneficiary_account,
  ROUND(ABS(amount), 2) AS amount,
  currency,
  wire_type,
  initiation_date,
  status,
  ofac_hold,
  requires_ctr,
  CASE WHEN amount >= 10000 THEN TRUE ELSE FALSE END AS above_ctr_threshold,
  purpose,
  beneficiary_country,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.retail_bronze.bronze_high_value_refunds`
WHERE wire_id IS NOT NULL
  AND originator_account_id IS NOT NULL
