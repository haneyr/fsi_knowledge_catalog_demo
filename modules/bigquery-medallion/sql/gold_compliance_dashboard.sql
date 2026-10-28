CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_compliance_dashboard` AS
SELECT
  'Capital Adequacy' AS metric_category,
  rc.capital_component AS metric_name,
  rc.capital_ratio AS metric_value,
  rc.regulatory_minimum AS threshold,
  CASE WHEN rc.capital_ratio >= rc.regulatory_minimum THEN 'Pass' ELSE 'Fail' END AS status,
  rc.reporting_date AS as_of_date
FROM `${project_id}.retail_silver.silver_working_capital` rc
WHERE rc.reporting_date = (SELECT MAX(reporting_date) FROM `${project_id}.retail_silver.silver_working_capital`)
UNION ALL
SELECT
  'Promo & Return Fraud' AS metric_category,
  CONCAT('Consent Renewal Overdue Rate - ', k.risk_score_category) AS metric_name,
  ROUND(SAFE_DIVIDE(COUNTIF(k.review_overdue), COUNT(*)), 4) AS metric_value,
  0.05 AS threshold,
  CASE WHEN SAFE_DIVIDE(COUNTIF(k.review_overdue), COUNT(*)) <= 0.05 THEN 'Pass' ELSE 'Fail' END AS status,
  CURRENT_DATE() AS as_of_date
FROM `${project_id}.retail_silver.silver_privacy_consents` k
GROUP BY k.risk_score_category
UNION ALL
SELECT
  'Filing Compliance' AS metric_category,
  CONCAT('Late Filing - ', rf.report_name) AS metric_name,
  CAST(COUNTIF(rf.filed_late) AS FLOAT64) AS metric_value,
  0 AS threshold,
  CASE WHEN COUNTIF(rf.filed_late) = 0 THEN 'Pass' ELSE 'Fail' END AS status,
  CURRENT_DATE() AS as_of_date
FROM `${project_id}.retail_silver.silver_compliance_attestations` rf
GROUP BY rf.report_name
