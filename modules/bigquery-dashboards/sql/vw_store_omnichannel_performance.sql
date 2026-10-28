CREATE OR REPLACE VIEW `${project_id}.retail_dashboards.vw_store_omnichannel_performance` AS
SELECT
  bp.store_id,
  bp.store_name,
  bp.city,
  bp.state,
  bp.region,
  bp.total_pos_revenue AS store_pos_sales,
  bp.total_bnpl_balance AS store_bnpl_volume,
  bp.total_accounts AS retail_accounts,
  bp.transaction_volume,
  ROUND(COALESCE(SUM(p.current_retail_value), 0), 2) AS vip_digital_gmv,
  COUNT(DISTINCT p.wm_client_id) AS vip_members_count,
  ROUND(bp.total_pos_revenue + COALESCE(SUM(p.current_retail_value), 0), 2) AS combined_assets
FROM `${project_id}.retail_gold.gold_store_performance` bp
LEFT JOIN `${project_id}.retail_silver.silver_merch_assortments` p
  ON bp.store_id = p.advisor_id
WHERE bp.store_id IS NOT NULL
GROUP BY bp.store_id, bp.store_name, bp.city, bp.state, bp.region,
         bp.total_pos_revenue, bp.total_bnpl_balance, bp.total_accounts, bp.transaction_volume
