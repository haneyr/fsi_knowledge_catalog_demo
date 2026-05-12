CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_advisor_scorecard` AS
SELECT
  adv.advisor_id,
  adv.first_name,
  adv.last_name,
  adv.title,
  adv.region,
  adv.certifications,
  adv.years_experience,
  adv.total_aum,
  adv.client_count,
  adv.avg_fee_bps,
  COUNT(DISTINCT p.portfolio_id) AS managed_portfolios,
  ROUND(AVG(p.ytd_return), 4) AS avg_portfolio_ytd_return,
  ROUND(AVG(perf.sharpe_ratio), 4) AS avg_sharpe_ratio,
  ROUND(AVG(perf.alpha), 4) AS avg_alpha,
  COUNT(DISTINCT t.trade_id) AS total_trades,
  ROUND(SUM(t.commission), 2) AS total_commissions_earned
FROM `${project_id}.fsi_silver.silver_advisors` adv
LEFT JOIN `${project_id}.fsi_silver.silver_portfolios` p ON adv.advisor_id = p.advisor_id AND p.status = 'Active'
LEFT JOIN `${project_id}.fsi_silver.silver_performance` perf ON p.portfolio_id = perf.portfolio_id
LEFT JOIN `${project_id}.fsi_silver.silver_trades` t ON adv.advisor_id = t.advisor_id
WHERE adv.status = 'Active'
GROUP BY adv.advisor_id, adv.first_name, adv.last_name, adv.title, adv.region,
         adv.certifications, adv.years_experience, adv.total_aum, adv.client_count, adv.avg_fee_bps
