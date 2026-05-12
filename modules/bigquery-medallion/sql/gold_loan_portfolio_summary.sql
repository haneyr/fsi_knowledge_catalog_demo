CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_loan_portfolio_summary` AS
SELECT
  l.loan_type,
  l.risk_rating,
  l.delinquency_status,
  COUNT(*) AS loan_count,
  ROUND(SUM(l.original_amount), 2) AS total_originated,
  ROUND(SUM(l.current_balance), 2) AS total_outstanding,
  ROUND(AVG(l.interest_rate), 4) AS avg_interest_rate,
  ROUND(AVG(l.fico_score_at_origination), 0) AS avg_fico,
  ROUND(AVG(l.ltv_ratio), 4) AS avg_ltv,
  ROUND(AVG(l.dti_ratio), 4) AS avg_dti,
  ROUND(AVG(l.term_months), 0) AS avg_term_months,
  COUNTIF(l.delinquency_status != 'Current') AS delinquent_count,
  ROUND(SAFE_DIVIDE(COUNTIF(l.delinquency_status != 'Current'), COUNT(*)) * 100, 2) AS delinquency_rate_pct
FROM `${project_id}.fsi_silver.silver_loans` l
GROUP BY 1, 2, 3
