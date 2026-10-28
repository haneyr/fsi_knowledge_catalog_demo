CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_category_manager_scorecard` AS
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
  COUNT(DISTINCT p.assortment_id) AS managed_assortments,
  ROUND(AVG(p.ytd_return), 4) AS avg_assortment_ytd_return,
  ROUND(AVG(SAFE_DIVIDE(p.current_retail_value - p.inventory_at_cost, p.inventory_at_cost)), 2) AS gmroi,
  ROUND(AVG(perf.alpha), 4) AS avg_alpha,
  COUNT(DISTINCT t.trade_id) AS total_trades,
  ROUND(SUM(t.commission), 2) AS total_commissions_earned
FROM `${project_id}.retail_silver.silver_category_managers` adv
LEFT JOIN `${project_id}.retail_silver.silver_merch_assortments` p ON adv.advisor_id = p.advisor_id AND p.status = 'Active'
LEFT JOIN `${project_id}.retail_silver.silver_assortment_performance` perf ON p.assortment_id = perf.assortment_id
LEFT JOIN `${project_id}.retail_silver.silver_ecom_orders` t ON adv.advisor_id = t.advisor_id
WHERE adv.status = 'Active'
GROUP BY adv.advisor_id, adv.first_name, adv.last_name, adv.title, adv.region,
         adv.certifications, adv.years_experience, adv.total_aum, adv.client_count, adv.avg_fee_bps
