CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_client_revenue` AS
SELECT
  wc.wm_client_id,
  wc.first_name,
  wc.last_name,
  wc.client_tier,
  wc.primary_advisor_id,
  wc.total_aum,
  COUNT(DISTINCT fs.fee_schedule_id) AS active_fee_schedules,
  ROUND(SUM(fs.last_fee_amount), 2) AS total_fees_billed,
  ROUND(AVG(fs.fee_rate_bps), 2) AS avg_fee_rate_bps,
  ROUND(SUM(t.commission), 2) AS total_commissions,
  ROUND(SUM(t.fees), 2) AS total_trade_fees,
  ROUND(COALESCE(SUM(fs.last_fee_amount), 0) + COALESCE(SUM(t.commission), 0) + COALESCE(SUM(t.fees), 0), 2) AS total_revenue,
  ROUND(SAFE_DIVIDE(
    COALESCE(SUM(fs.last_fee_amount), 0) + COALESCE(SUM(t.commission), 0) + COALESCE(SUM(t.fees), 0),
    wc.total_aum
  ) * 10000, 2) AS revenue_yield_bps
FROM `${project_id}.fsi_silver.silver_wm_clients` wc
LEFT JOIN `${project_id}.fsi_silver.silver_fee_schedules` fs ON wc.wm_client_id = fs.wm_client_id AND fs.is_active
LEFT JOIN `${project_id}.fsi_silver.silver_portfolios` p ON wc.wm_client_id = p.wm_client_id
LEFT JOIN `${project_id}.fsi_silver.silver_trades` t ON p.portfolio_id = t.portfolio_id
WHERE wc.client_status = 'Active'
GROUP BY wc.wm_client_id, wc.first_name, wc.last_name, wc.client_tier,
         wc.primary_advisor_id, wc.total_aum
