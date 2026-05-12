CREATE OR REPLACE TABLE `${project_id}.fsi_silver.silver_fraud_alerts` AS
SELECT
  alert_id,
  customer_id,
  transaction_id,
  alert_type,
  CAST(fraud_score AS INT64) AS fraud_score,
  severity,
  status,
  alert_date,
  resolved_date,
  assigned_analyst,
  ROUND(ABS(loss_amount), 2) AS loss_amount,
  sar_filed,
  CASE WHEN resolved_date IS NOT NULL THEN TIMESTAMP_DIFF(resolved_date, alert_date, HOUR) ELSE NULL END AS resolution_hours,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY alert_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.fsi_bronze.bronze_fraud_alerts`
)
WHERE rn = 1
  AND alert_id IS NOT NULL
