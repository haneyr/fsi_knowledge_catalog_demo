CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_regulatory_dashboard` AS
SELECT
  'Capital Adequacy' AS metric_category,
  rc.capital_component AS metric_name,
  rc.capital_ratio AS metric_value,
  rc.regulatory_minimum AS threshold,
  CASE WHEN rc.capital_ratio >= rc.regulatory_minimum THEN 'Pass' ELSE 'Fail' END AS status,
  rc.reporting_date AS as_of_date
FROM `${project_id}.fsi_silver.silver_regulatory_capital` rc
WHERE rc.reporting_date = (SELECT MAX(reporting_date) FROM `${project_id}.fsi_silver.silver_regulatory_capital`)
UNION ALL
SELECT
  'BSA/AML' AS metric_category,
  CONCAT('KYC Overdue Rate - ', k.risk_score_category) AS metric_name,
  ROUND(SAFE_DIVIDE(COUNTIF(k.review_overdue), COUNT(*)), 4) AS metric_value,
  0.05 AS threshold,
  CASE WHEN SAFE_DIVIDE(COUNTIF(k.review_overdue), COUNT(*)) <= 0.05 THEN 'Pass' ELSE 'Fail' END AS status,
  CURRENT_DATE() AS as_of_date
FROM `${project_id}.fsi_silver.silver_kyc_records` k
GROUP BY k.risk_score_category
UNION ALL
SELECT
  'Filing Compliance' AS metric_category,
  CONCAT('Late Filing - ', rf.report_name) AS metric_name,
  CAST(COUNTIF(rf.filed_late) AS FLOAT64) AS metric_value,
  0 AS threshold,
  CASE WHEN COUNTIF(rf.filed_late) = 0 THEN 'Pass' ELSE 'Fail' END AS status,
  CURRENT_DATE() AS as_of_date
FROM `${project_id}.fsi_silver.silver_regulatory_filings` rf
GROUP BY rf.report_name
