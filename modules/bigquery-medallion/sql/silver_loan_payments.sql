CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_loan_payments` AS
SELECT
  payment_id,
  loan_id,
  payment_date,
  due_date,
  ROUND(ABS(payment_amount), 2) AS payment_amount,
  ROUND(ABS(principal_amount), 2) AS principal_amount,
  ROUND(ABS(interest_amount), 2) AS interest_amount,
  ROUND(ABS(escrow_amount), 2) AS escrow_amount,
  ROUND(ABS(late_fee), 2) AS late_fee,
  payment_method,
  payment_status,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.fsi_bronze.bronze_loan_payments`
WHERE payment_id IS NOT NULL
  AND loan_id IS NOT NULL
