CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_bnpl_plan_summary` AS
SELECT
  l.plan_type,
  l.risk_rating,
  l.delinquency_status,
  COUNT(*) AS plan_count,
  ROUND(SUM(l.original_amount), 2) AS total_originated,
  ROUND(SUM(l.current_balance), 2) AS total_outstanding,
  ROUND(AVG(l.interest_rate), 4) AS avg_interest_rate,
  ROUND(AVG(l.return_risk_score_at_signup), 1) AS avg_return_risk_score,
  ROUND(AVG(l.ltv_ratio), 4) AS avg_ltv,
  ROUND(AVG(l.dti_ratio), 4) AS avg_dti,
  ROUND(AVG(l.term_months), 1) AS avg_term_months,
  COUNTIF(l.delinquency_status != 'Current') AS delinquent_count,
  ROUND(SAFE_DIVIDE(COUNTIF(l.delinquency_status != 'Current'), COUNT(*)) * 100, 2) AS delinquency_rate_pct
FROM `${project_id}.retail_silver.silver_bnpl_plans` l
GROUP BY 1, 2, 3
