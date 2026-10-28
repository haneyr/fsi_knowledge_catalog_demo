#!/usr/bin/env python3
"""Phase L: Targeted SQL column rename and realistic GMROI / assortment deduplication."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MED_SQL = ROOT / "modules" / "bigquery-medallion" / "sql"
DASH_SQL = ROOT / "modules" / "bigquery-dashboards" / "sql"

FILES = {
    MED_SQL / "bronze_merch_assortments.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_merch_assortments` AS
SELECT
  CONCAT('PORT-', LPAD(CAST(n AS STRING), 8, '0')) AS assortment_id,
  CONCAT('WMC-', LPAD(CAST(CAST(FLOOR(n / 2.0) + 1 AS INT64) AS STRING), 7, '0')) AS wm_client_id,
  assortment_name,
  CASE MOD(n, 7)
    WHEN 0 THEN 'FLAGSHIP_STORE' WHEN 1 THEN 'OMNICHANNEL' WHEN 2 THEN 'ECOMMERCE_ONLY' WHEN 3 THEN 'OUTLET'
    WHEN 4 THEN 'MARKETPLACE' WHEN 5 THEN 'POP_UP' ELSE 'VIP_CLIENTELING'
  END AS account_type,
  CASE MOD(n, 4) WHEN 0 THEN 'Standard Sales Tax' WHEN 1 THEN 'Apparel Tax-Exempt' WHEN 2 THEN 'Back-to-School Holiday' ELSE 'Standard Sales Tax' END AS tax_status,
  ROUND(inv_cost * (1.0 + target_gmroi), 2) AS current_retail_value,
  inv_cost AS inventory_at_cost,
  ROUND(0.08 + MOD(n * 31, 35) * 0.01, 4) AS ytd_return,
  ROUND(0.12 + MOD(n * 37, 38) * 0.01, 4) AS inception_return,
  CONCAT('BM-', LPAD(CAST(MOD(n, 10) + 1 AS STRING), 3, '0')) AS benchmark_id,
  CONCAT('ADV-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS advisor_id,
  CONCAT('MDL-', LPAD(CAST(MOD(n, 20) + 1 AS STRING), 3, '0')) AS template_assortment_id,
  DATE_ADD('2018-01-01', INTERVAL CAST(MOD(n * 19, 2500) AS INT64) DAY) AS inception_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' ELSE 'Closed' END AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(MOD(n * 41, 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM (
  SELECT
    n,
    CASE MOD(n, 12)
      WHEN 0 THEN 'Seasonal Holiday Gifting'
      WHEN 1 THEN 'Winter Outerwear & Cold Weather'
      WHEN 2 THEN 'Spring Apparel Core'
      WHEN 3 THEN 'Back-to-School Basics'
      WHEN 4 THEN 'Summer Resort & Swimwear'
      WHEN 5 THEN 'Outdoor & Activewear'
      WHEN 6 THEN 'Home & Kitchen Essentials'
      WHEN 7 THEN 'Consumer Electronics Flagship'
      WHEN 8 THEN 'Beauty & Personal Care'
      WHEN 9 THEN 'Footwear & Accessories'
      WHEN 10 THEN 'Private Label Basics'
      ELSE 'Athletic & Performance Gear'
    END AS assortment_name,
    ROUND(CASE MOD(n, 12)
      WHEN 0 THEN 148500.00 + MOD(n * 97, 18000)
      WHEN 1 THEN 164200.00 + MOD(n * 89, 20000)
      WHEN 2 THEN 131800.00 + MOD(n * 83, 16000)
      WHEN 3 THEN 119400.00 + MOD(n * 79, 15000)
      WHEN 4 THEN 112600.00 + MOD(n * 73, 14000)
      WHEN 5 THEN 136500.00 + MOD(n * 71, 17000)
      WHEN 6 THEN 116800.00 + MOD(n * 67, 15000)
      WHEN 7 THEN 198400.00 + MOD(n * 61, 24000)
      WHEN 8 THEN 95200.00 + MOD(n * 59, 12000)
      WHEN 9 THEN 124600.00 + MOD(n * 53, 15000)
      WHEN 10 THEN 89400.00 + MOD(n * 47, 11000)
      ELSE 139200.00 + MOD(n * 43, 16000)
    END, 2) AS inv_cost,
    CASE MOD(n, 12)
      WHEN 0 THEN 2.08
      WHEN 1 THEN 2.16
      WHEN 2 THEN 2.24
      WHEN 3 THEN 2.35
      WHEN 4 THEN 2.44
      WHEN 5 THEN 2.72
      WHEN 6 THEN 2.95
      WHEN 7 THEN 3.12
      WHEN 8 THEN 3.68
      WHEN 9 THEN 3.34
      WHEN 10 THEN 3.85
      ELSE 3.48
    END AS target_gmroi
  FROM UNNEST(GENERATE_ARRAY(1, 15000)) AS n
)
""",
    MED_SQL / "silver_merch_assortments.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_merch_assortments` AS
SELECT
  assortment_id,
  wm_client_id,
  assortment_name,
  account_type,
  tax_status,
  ROUND(ABS(current_retail_value), 2) AS current_retail_value,
  ROUND(ABS(inventory_at_cost), 2) AS inventory_at_cost,
  ytd_return,
  inception_return,
  benchmark_id,
  advisor_id,
  template_assortment_id,
  inception_date,
  status,
  ROUND(0.42 + (SAFE_DIVIDE(current_retail_value - inventory_at_cost, inventory_at_cost) - 2.0) * 0.23, 4) AS sell_through_pct,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY assortment_id ORDER BY created_at DESC) AS rn
  FROM `${project_id}.retail_bronze.bronze_merch_assortments`
)
WHERE rn = 1
  AND assortment_id IS NOT NULL
  AND wm_client_id IS NOT NULL
""",
    MED_SQL / "bronze_assortment_performance.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_assortment_performance` AS
SELECT
  CONCAT('PERF-', LPAD(CAST(n AS STRING), 10, '0')) AS performance_id,
  CONCAT('PORT-', LPAD(CAST(CAST(MOD(n, 15000) + 1 AS INT64) AS STRING), 8, '0')) AS assortment_id,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(n / 15000.0) AS INT64) DAY) AS as_of_date,
  ROUND(-0.05 + RAND() * 0.1, 6) AS daily_return,
  ROUND(-0.1 + RAND() * 0.3, 4) AS mtd_return,
  ROUND(-0.15 + RAND() * 0.4, 4) AS qtd_return,
  ROUND(-0.2 + RAND() * 0.5, 4) AS ytd_return,
  ROUND(100000 + RAND() * 10000000, 2) AS current_retail_value,
  ROUND(-1000 + RAND() * 50000, 2) AS net_flows,
  ROUND(-0.05 + RAND() * 0.1, 6) AS benchmark_return,
  ROUND(-0.02 + RAND() * 0.04, 6) AS alpha,
  ROUND(0.5 + RAND() * 1.0, 4) AS beta,
  ROUND(0.01 + RAND() * 0.3, 4) AS volatility,
  ROUND(2.08 + RAND() * 1.80, 4) AS sharpe_ratio,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
""",
    MED_SQL / "silver_assortment_performance.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_assortment_performance` AS
SELECT
  performance_id,
  assortment_id,
  as_of_date,
  daily_return,
  mtd_return,
  qtd_return,
  ytd_return,
  ROUND(ABS(current_retail_value), 2) AS current_retail_value,
  ROUND(net_flows, 2) AS net_flows,
  benchmark_return,
  ROUND(daily_return - benchmark_return, 6) AS excess_return,
  alpha,
  beta,
  volatility,
  sharpe_ratio,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.retail_bronze.bronze_assortment_performance`
WHERE performance_id IS NOT NULL
  AND assortment_id IS NOT NULL
""",
    MED_SQL / "gold_assortment_performance.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_assortment_performance` AS
SELECT
  p.assortment_id,
  p.wm_client_id,
  p.assortment_name,
  p.account_type,
  p.tax_status,
  p.current_retail_value,
  p.inventory_at_cost,
  p.sell_through_pct,
  p.ytd_return,
  p.inception_return,
  p.advisor_id,
  p.benchmark_id,
  bm.benchmark_name,
  ROUND(AVG(perf.daily_return), 6) AS avg_daily_return,
  ROUND(AVG(perf.alpha), 4) AS avg_alpha,
  ROUND(AVG(perf.beta), 4) AS avg_beta,
  ROUND(AVG(perf.volatility), 4) AS avg_volatility,
  ROUND(SAFE_DIVIDE(p.current_retail_value - p.inventory_at_cost, p.inventory_at_cost), 2) AS gmroi,
  ROUND(AVG(perf.excess_return), 6) AS avg_excess_return,
  COUNT(DISTINCT h.holding_id) AS holding_count,
  COUNT(DISTINCT h.asset_class) AS asset_class_count
FROM `${project_id}.retail_silver.silver_merch_assortments` p
LEFT JOIN `${project_id}.retail_silver.silver_assortment_performance` perf ON p.assortment_id = perf.assortment_id
LEFT JOIN `${project_id}.retail_silver.silver_inventory_positions` h ON p.assortment_id = h.assortment_id
LEFT JOIN (SELECT DISTINCT benchmark_id, benchmark_name FROM `${project_id}.retail_silver.silver_category_benchmarks`) bm ON p.benchmark_id = bm.benchmark_id
WHERE p.status = 'Active'
GROUP BY p.assortment_id, p.wm_client_id, p.assortment_name, p.account_type, p.tax_status,
         p.current_retail_value, p.inventory_at_cost, p.sell_through_pct, p.ytd_return, p.inception_return,
         p.advisor_id, p.benchmark_id, bm.benchmark_name
QUALIFY ROW_NUMBER() OVER (PARTITION BY p.assortment_name ORDER BY COUNT(DISTINCT h.holding_id) DESC, p.assortment_id) = 1
""",
    MED_SQL / "gold_category_manager_scorecard.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_category_manager_scorecard` AS
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
""",
    MED_SQL / "bronze_inventory_positions.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_inventory_positions` AS
SELECT
  CONCAT('HLD-', LPAD(CAST(n AS STRING), 9, '0')) AS holding_id,
  CONCAT('PORT-', LPAD(CAST(CAST(MOD(n, 15000) + 1 AS INT64) AS STRING), 8, '0')) AS assortment_id,
  CONCAT('SEC-', LPAD(CAST(CAST(MOD(n * 7, 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  ROUND(10 + MOD(n * 17, 440), 0) AS quantity,
  ROUND(14 + MOD(n * 23, 250), 2) AS market_price,
  ROUND((10 + MOD(n * 17, 440)) * (12 + MOD(n * 13, 85)) * (2.6 + MOD(n, 15) * 0.12), 2) AS current_retail_value,
  ROUND((10 + MOD(n * 17, 440)) * (12 + MOD(n * 13, 85)), 2) AS inventory_at_cost,
  ROUND((10 + MOD(n * 17, 440)) * (12 + MOD(n * 13, 85)) * (0.35 + MOD(n, 10) * 0.06), 2) AS markdown_exposure,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Apparel & Outerwear' WHEN 1 THEN 'Footwear' WHEN 2 THEN 'Home & Kitchen'
    WHEN 3 THEN 'Consumer Electronics' WHEN 4 THEN 'Outdoor & Activewear' WHEN 5 THEN 'Home Furnishings'
    WHEN 6 THEN 'Accessories & Jewelry' ELSE 'Beauty & Personal Care'
  END AS asset_class,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Womens & Mens Apparel' WHEN 1 THEN 'Athletic Footwear' WHEN 2 THEN 'Culinary & Tabletop'
    WHEN 3 THEN 'Smart Home & Audio' WHEN 4 THEN 'Outdoor Recreation' WHEN 5 THEN 'Living & Bedroom'
    WHEN 6 THEN 'Fashion Accessories' ELSE 'Clean Beauty & Skincare'
  END AS sector,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(MOD(n, 90) AS INT64) DAY) AS as_of_date,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(MOD(n * 31, 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
""",
    MED_SQL / "silver_inventory_positions.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_inventory_positions` AS
SELECT
  holding_id,
  assortment_id,
  security_id,
  ROUND(ABS(quantity), 4) AS quantity,
  ROUND(ABS(market_price), 2) AS market_price,
  ROUND(ABS(current_retail_value), 2) AS current_retail_value,
  ROUND(ABS(inventory_at_cost), 2) AS inventory_at_cost,
  ROUND(ABS(markdown_exposure), 2) AS markdown_exposure,
  asset_class,
  sector,
  as_of_date,
  ROUND(SAFE_DIVIDE(current_retail_value - inventory_at_cost, inventory_at_cost), 4) AS return_pct,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.retail_bronze.bronze_inventory_positions`
WHERE holding_id IS NOT NULL
  AND assortment_id IS NOT NULL
  AND security_id IS NOT NULL
""",
    MED_SQL / "gold_inventory_allocation.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_inventory_allocation` AS
SELECT
  h.asset_class,
  h.sector,
  COUNT(DISTINCT h.assortment_id) AS assortment_count,
  COUNT(DISTINCT h.security_id) AS security_count,
  ROUND(SUM(h.current_retail_value), 2) AS total_market_value,
  ROUND(SUM(h.inventory_at_cost), 2) AS total_cost_basis,
  ROUND(SUM(h.markdown_exposure), 2) AS total_unrealized_gain_loss,
  ROUND(AVG(h.return_pct), 4) AS avg_return_pct,
  ROUND(SUM(h.quantity), 2) AS total_quantity
FROM `${project_id}.retail_silver.silver_inventory_positions` h
GROUP BY 1, 2
""",
    MED_SQL / "gold_markdown_risk_var.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_markdown_risk_var` AS
SELECT
  h.asset_class,
  h.sector,
  COUNT(DISTINCT h.security_id) AS position_count,
  ROUND(SUM(h.current_retail_value), 2) AS total_exposure,
  ROUND(AVG(md.daily_return), 6) AS avg_daily_return,
  ROUND(STDDEV(md.daily_return), 6) AS return_volatility,
  ROUND(SUM(h.current_retail_value) * STDDEV(md.daily_return) * 2.326, 2) AS var_99_1d,
  ROUND(SUM(h.current_retail_value) * STDDEV(md.daily_return) * 1.645, 2) AS var_95_1d,
  ROUND(SUM(h.current_retail_value) * STDDEV(md.daily_return) * 2.326 * SQRT(10), 2) AS var_99_10d,
  ROUND(AVG(md.duration), 2) AS avg_duration,
  ROUND(AVG(md.yield_to_maturity), 4) AS avg_ytm
FROM `${project_id}.retail_silver.silver_inventory_positions` h
LEFT JOIN `${project_id}.retail_silver.silver_competitor_pricing` md ON h.security_id = md.security_id
GROUP BY 1, 2
""",
    MED_SQL / "gold_inventory_turnover_coverage.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_inventory_turnover_coverage` AS
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
""",
    MED_SQL / "gold_financial_summary.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_financial_summary` AS
SELECT
  'Assets' AS category,
  'Cash & Store Working Balances' AS line_item,
  ROUND(SUM(CASE WHEN account_type IN ('POINTS_REWARDS', 'VIP_CASHBACK') THEN current_balance * 0.25 ELSE 0 END), 0) AS amount
FROM `${project_id}.retail_silver.silver_loyalty_accounts`
WHERE account_status = 'Active'
UNION ALL
SELECT 'Assets', 'Active BNPL Installment Receivables',
  ROUND(SUM(current_balance), 0)
FROM `${project_id}.retail_silver.silver_bnpl_plans`
UNION ALL
SELECT 'Assets', 'Merchandise Inventory at Market Value',
  ROUND(SUM(current_retail_value), 0)
FROM `${project_id}.retail_silver.silver_inventory_positions`
UNION ALL
SELECT 'Liabilities', 'Unredeemed Loyalty & Gift Wallet Liability',
  ROUND(SUM(current_balance), 0)
FROM `${project_id}.retail_silver.silver_loyalty_accounts`
WHERE account_status = 'Active'
UNION ALL
SELECT 'Liabilities', 'Supply Chain & Trade Payables',
  ROUND(SUM(inventory_at_cost) * 0.35, 0)
FROM `${project_id}.retail_silver.silver_inventory_positions`
UNION ALL
SELECT 'Operating Equity', 'Total Retail Operating Equity',
  ROUND(MAX(capital_amount), 0)
FROM `${project_id}.retail_silver.silver_working_capital`
WHERE capital_component = 'Total Operating Capital'
  AND reporting_date = (SELECT MAX(reporting_date) FROM `${project_id}.retail_silver.silver_working_capital`)
""",
    MED_SQL / "bronze_carrier_feeds.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_carrier_feeds` AS
SELECT
  CONCAT('CFEED-', LPAD(CAST(n AS STRING), 9, '0')) AS feed_id,
  CONCAT('PORT-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 8, '0')) AS assortment_id,
  CASE MOD(n, 4) WHEN 0 THEN 'Schwab' WHEN 1 THEN 'Fidelity' WHEN 2 THEN 'Pershing' ELSE 'TD Ameritrade' END AS custodian_name,
  CASE MOD(n, 3) WHEN 0 THEN 'Position' WHEN 1 THEN 'Transaction' ELSE 'Cash Balance' END AS feed_type,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 500) AS INT64) DAY) AS as_of_date,
  CONCAT('SEC-', LPAD(CAST(CAST(FLOOR(RAND() * 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  ROUND(RAND() * 10000, 4) AS quantity,
  ROUND(RAND() * 5000, 2) AS current_retail_value,
  CASE MOD(n, 3)
    WHEN 0 THEN 'Reconciled' WHEN 1 THEN 'Unreconciled' ELSE 'Reconciled'
  END AS reconciliation_status,
  CASE WHEN MOD(n, 20) = 0 THEN ROUND(-100 + RAND() * 200, 2) ELSE 0.00 END AS break_amount,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS received_at,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
""",
    MED_SQL / "silver_carrier_feeds.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_silver.silver_carrier_feeds` AS
SELECT
  feed_id,
  assortment_id,
  custodian_name,
  feed_type,
  as_of_date,
  security_id,
  ROUND(ABS(quantity), 4) AS quantity,
  ROUND(ABS(current_retail_value), 2) AS current_retail_value,
  reconciliation_status,
  ROUND(break_amount, 2) AS break_amount,
  CASE WHEN ABS(break_amount) > 0.01 THEN TRUE ELSE FALSE END AS has_break,
  received_at,
  created_at,
  source_system,
  CURRENT_TIMESTAMP() AS silver_loaded_at
FROM `${project_id}.retail_bronze.bronze_carrier_feeds`
WHERE feed_id IS NOT NULL
  AND assortment_id IS NOT NULL
""",
    MED_SQL / "snapshot_quarterly_inventory_positions.sql": """CREATE OR REPLACE TABLE `${project_id}.retail_snapshots.snapshot_quarterly_inventory_positions` AS
SELECT
  CONCAT('PORT-', LPAD(CAST(CAST(MOD(n, 15000) + 1 AS INT64) AS STRING), 8, '0')) AS assortment_id,
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 15000.0) AS INT64) * 3 MONTH) AS snapshot_date,
  ROUND(28000 + RAND() * 240000, 2) AS current_retail_value,
  ROUND(18000 + RAND() * 155000, 2) AS inventory_at_cost,
  ROUND(0.04 + RAND() * 0.22, 4) AS qtd_return,
  ROUND(0.10 + RAND() * 0.38, 4) AS ytd_return,
  CAST(FLOOR(12 + RAND() * 65) AS INT64) AS holding_count
FROM UNNEST(GENERATE_ARRAY(1, 60000)) AS n
""",
    DASH_SQL / "vw_store_omnichannel_performance.sql": """CREATE OR REPLACE VIEW `${project_id}.retail_dashboards.vw_store_omnichannel_performance` AS
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
""",
}

def main():
    for path, content in FILES.items():
        path.write_text(content, encoding="utf-8")
        print(f"Updated {path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
