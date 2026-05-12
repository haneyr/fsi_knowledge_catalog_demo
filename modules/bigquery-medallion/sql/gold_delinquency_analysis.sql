CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_delinquency_analysis` AS
SELECT
  l.loan_type,
  l.originating_branch_id,
  l.naics_code AS industry_naics,
  l.delinquency_status,
  COUNT(*) AS loan_count,
  ROUND(SUM(l.current_balance), 2) AS total_balance,
  ROUND(AVG(l.current_balance), 2) AS avg_balance,
  ROUND(AVG(l.fico_score_at_origination), 0) AS avg_origination_fico,
  ROUND(AVG(l.interest_rate), 4) AS avg_rate,
  ROUND(AVG(l.ltv_ratio), 4) AS avg_ltv,
  COUNTIF(l.risk_rating IN ('Substandard', 'Doubtful')) AS classified_count,
  ROUND(SAFE_DIVIDE(COUNTIF(l.risk_rating IN ('Substandard', 'Doubtful')), COUNT(*)) * 100, 2) AS classified_rate_pct
FROM `${project_id}.fsi_silver.silver_loans` l
WHERE l.delinquency_status != 'Current'
GROUP BY 1, 2, 3, 4
