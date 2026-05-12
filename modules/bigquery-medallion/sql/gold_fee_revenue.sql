CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_fee_revenue` AS
SELECT
  fs.fee_type,
  fs.billing_frequency,
  wc.client_tier,
  COUNT(DISTINCT fs.wm_client_id) AS client_count,
  COUNT(*) AS schedule_count,
  ROUND(AVG(fs.fee_rate_bps), 2) AS avg_fee_rate_bps,
  ROUND(SUM(fs.last_fee_amount), 2) AS total_fees,
  ROUND(AVG(fs.last_fee_amount), 2) AS avg_fee_amount,
  ROUND(MIN(fs.fee_rate_bps), 2) AS min_fee_rate_bps,
  ROUND(MAX(fs.fee_rate_bps), 2) AS max_fee_rate_bps
FROM `${project_id}.fsi_silver.silver_fee_schedules` fs
JOIN `${project_id}.fsi_silver.silver_wm_clients` wc ON fs.wm_client_id = wc.wm_client_id
WHERE fs.is_active
GROUP BY 1, 2, 3
