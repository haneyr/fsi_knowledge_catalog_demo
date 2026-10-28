CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_inventory_turnover_coverage` AS
WITH loyalty_redemptions AS (
  SELECT
    DATE_TRUNC(open_date, QUARTER) AS quarter,
    SUM(current_balance) AS total_pos_revenue,
    SUM(CASE WHEN account_type IN ('POINTS_REWARDS', 'VIP_CASHBACK') THEN current_balance * 0.1 ELSE current_balance * 0.25 END) AS stressed_outflows
  FROM `${project_id}.retail_silver.silver_loyalty_accounts`
  WHERE account_status = 'Active'
  GROUP BY 1
),
hqla AS (
  SELECT
    DATE_TRUNC(as_of_date, QUARTER) AS quarter,
    SUM(CASE WHEN security_type IN ('Core Essentials', 'Beauty & Personal Care') THEN current_retail_value ELSE 0 END) AS level_1_hqla,
    SUM(CASE WHEN security_type = 'Outdoor & Activewear' THEN current_retail_value * 0.85 ELSE 0 END) AS level_2a_hqla,
    SUM(CASE WHEN security_type = 'Home & Living' AND credit_rating IN ('AAA', 'AA', 'Tier-1 Certified', 'Preferred Vendor') THEN current_retail_value * 0.5 ELSE 0 END) AS level_2b_hqla
  FROM `${project_id}.retail_silver.silver_product_skus` s
  JOIN `${project_id}.retail_silver.silver_inventory_positions` h ON s.security_id = h.security_id
  GROUP BY 1
)
SELECT
  d.quarter,
  d.total_pos_revenue,
  d.stressed_outflows,
  COALESCE(h.level_1_hqla, 0) AS level_1_hqla,
  COALESCE(h.level_2a_hqla, 0) AS level_2a_hqla,
  COALESCE(h.level_2b_hqla, 0) AS level_2b_hqla,
  ROUND(COALESCE(h.level_1_hqla, 0) + COALESCE(h.level_2a_hqla, 0) + COALESCE(h.level_2b_hqla, 0), 2) AS total_hqla,
  ROUND(SAFE_DIVIDE(
    COALESCE(h.level_1_hqla, 0) + COALESCE(h.level_2a_hqla, 0) + COALESCE(h.level_2b_hqla, 0),
    d.stressed_outflows
  ), 4) AS lcr_ratio
FROM loyalty_redemptions d
LEFT JOIN hqla h ON d.quarter = h.quarter
