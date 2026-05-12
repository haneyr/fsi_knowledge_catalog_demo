CREATE OR REPLACE TABLE `${project_id}.fsi_gold.gold_liquidity_coverage` AS
WITH deposit_outflows AS (
  SELECT
    DATE_TRUNC(open_date, QUARTER) AS quarter,
    SUM(current_balance) AS total_deposits,
    SUM(CASE WHEN account_type IN ('CHECKING', 'SAVINGS') THEN current_balance * 0.1 ELSE current_balance * 0.25 END) AS stressed_outflows
  FROM `${project_id}.fsi_silver.silver_accounts`
  WHERE account_status = 'Active'
  GROUP BY 1
),
hqla AS (
  SELECT
    DATE_TRUNC(as_of_date, QUARTER) AS quarter,
    SUM(CASE WHEN security_type IN ('Treasury Bond', 'Money Market') THEN market_value ELSE 0 END) AS level_1_hqla,
    SUM(CASE WHEN security_type = 'Municipal Bond' THEN market_value * 0.85 ELSE 0 END) AS level_2a_hqla,
    SUM(CASE WHEN security_type = 'Corporate Bond' AND credit_rating IN ('AAA', 'AA') THEN market_value * 0.5 ELSE 0 END) AS level_2b_hqla
  FROM `${project_id}.fsi_silver.silver_securities` s
  JOIN `${project_id}.fsi_silver.silver_holdings` h ON s.security_id = h.security_id
  GROUP BY 1
)
SELECT
  d.quarter,
  d.total_deposits,
  d.stressed_outflows,
  COALESCE(h.level_1_hqla, 0) AS level_1_hqla,
  COALESCE(h.level_2a_hqla, 0) AS level_2a_hqla,
  COALESCE(h.level_2b_hqla, 0) AS level_2b_hqla,
  ROUND(COALESCE(h.level_1_hqla, 0) + COALESCE(h.level_2a_hqla, 0) + COALESCE(h.level_2b_hqla, 0), 2) AS total_hqla,
  ROUND(SAFE_DIVIDE(
    COALESCE(h.level_1_hqla, 0) + COALESCE(h.level_2a_hqla, 0) + COALESCE(h.level_2b_hqla, 0),
    d.stressed_outflows
  ), 4) AS lcr_ratio
FROM deposit_outflows d
LEFT JOIN hqla h ON d.quarter = h.quarter
