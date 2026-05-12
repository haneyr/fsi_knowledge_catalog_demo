CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_fraud_analytics` AS
SELECT
  DATE_TRUNC(CAST(f.alert_date AS DATE), MONTH) AS alert_month,
  f.alert_type,
  f.severity,
  COUNT(*) AS alert_count,
  COUNTIF(f.status LIKE 'Closed - Confirmed%') AS confirmed_fraud_count,
  COUNTIF(f.status LIKE 'Closed - False%') AS false_positive_count,
  ROUND(SAFE_DIVIDE(COUNTIF(f.status LIKE 'Closed - False%'), COUNT(*)) * 100, 2) AS false_positive_rate_pct,
  ROUND(SUM(f.loss_amount), 2) AS total_losses,
  ROUND(AVG(f.fraud_score), 0) AS avg_fraud_score,
  ROUND(AVG(f.resolution_hours), 1) AS avg_resolution_hours,
  COUNTIF(f.sar_filed) AS sar_count
FROM `${project_id}.fsi_silver.silver_fraud_alerts` f
GROUP BY 1, 2, 3
