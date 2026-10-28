CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_bnpl_delinquency_analysis` AS
SELECT
  l.plan_type,
  l.originating_store_id,
  l.naics_code AS industry_naics,
  l.delinquency_status,
  COUNT(*) AS plan_count,
  ROUND(SUM(l.current_balance), 2) AS total_balance,
  ROUND(AVG(l.current_balance), 2) AS avg_balance,
  ROUND(AVG(l.return_risk_score_at_signup), 1) AS avg_origination_risk_score,
  ROUND(AVG(l.interest_rate), 4) AS avg_rate,
  ROUND(AVG(l.ltv_ratio), 4) AS avg_ltv,
  COUNTIF(l.risk_rating IN ('Elevated', 'High Risk')) AS classified_count,
  ROUND(SAFE_DIVIDE(COUNTIF(l.risk_rating IN ('Elevated', 'High Risk')), COUNT(*)) * 100, 2) AS classified_rate_pct
FROM `${project_id}.retail_silver.silver_bnpl_plans` l
WHERE l.delinquency_status != 'Current'
GROUP BY 1, 2, 3, 4
