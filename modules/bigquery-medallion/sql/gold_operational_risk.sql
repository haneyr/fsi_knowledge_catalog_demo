CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_operational_risk` AS
SELECT
  DATE_TRUNC(CAST(ae.event_timestamp AS DATE), MONTH) AS event_month,
  ae.system_name,
  ae.event_type,
  COUNT(*) AS event_count,
  COUNTIF(ae.result = 'Failed') AS failed_count,
  ROUND(SAFE_DIVIDE(COUNTIF(ae.result = 'Failed'), COUNT(*)) * 100, 2) AS failure_rate_pct,
  COUNTIF(ae.sox_relevant) AS sox_relevant_count,
  COUNT(DISTINCT ae.user_id) AS unique_users,
  COUNT(DISTINCT ae.source_ip) AS unique_ips,
  COUNT(DISTINCT comp.case_id) AS compliance_cases
FROM `${project_id}.fsi_silver.silver_audit_events` ae
LEFT JOIN `${project_id}.fsi_silver.silver_compliance_cases` comp
  ON DATE_TRUNC(CAST(ae.event_timestamp AS DATE), MONTH) = DATE_TRUNC(comp.opened_date, MONTH)
GROUP BY 1, 2, 3
