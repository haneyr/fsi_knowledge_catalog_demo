CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_aml_risk_scoring` AS
SELECT
  c.customer_segment,
  c.kyc_risk_rating,
  k.due_diligence_level,
  k.risk_score_category,
  COUNT(DISTINCT c.customer_id) AS customer_count,
  ROUND(AVG(k.risk_score), 0) AS avg_risk_score,
  COUNTIF(k.pep_flag) AS pep_count,
  COUNTIF(k.sanctions_flag) AS sanctions_hit_count,
  COUNTIF(k.adverse_media_flag) AS adverse_media_count,
  COUNTIF(k.review_overdue) AS overdue_reviews,
  ROUND(SAFE_DIVIDE(COUNTIF(k.review_overdue), COUNT(*)) * 100, 2) AS overdue_rate_pct,
  COUNT(DISTINCT comp.case_id) AS compliance_cases,
  COUNTIF(comp.sar_filed) AS sar_filings,
  ROUND(SUM(CASE WHEN w.amount >= 10000 THEN w.amount ELSE 0 END), 2) AS large_wire_volume
FROM `${project_id}.fsi_silver.silver_customers` c
LEFT JOIN `${project_id}.fsi_silver.silver_kyc_records` k ON c.customer_id = k.customer_id
LEFT JOIN `${project_id}.fsi_silver.silver_compliance_cases` comp ON c.customer_id = comp.related_customer_id
LEFT JOIN `${project_id}.fsi_silver.silver_wire_transfers` w ON c.customer_id = w.originator_customer_id
GROUP BY 1, 2, 3, 4
