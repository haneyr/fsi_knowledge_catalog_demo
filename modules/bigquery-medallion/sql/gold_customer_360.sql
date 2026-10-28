CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_customer_360` AS
SELECT
  c.customer_id,
  c.first_name,
  c.last_name,
  c.customer_type,
  c.customer_segment,
  c.primary_store_id,
  c.kyc_risk_rating,
  c.kyc_status,
  c.account_opened_date,
  c.state,
  c.industry,
  COUNT(DISTINCT a.account_id) AS total_accounts,
  ROUND(SUM(a.current_balance), 2) AS total_loyalty_balance,
  COUNT(DISTINCT l.bnpl_plan_id) AS total_bnpl_originations,
  ROUND(COALESCE(SUM(l.current_balance), 0), 2) AS total_bnpl_balance,
  COUNT(DISTINCT cc.card_id) AS total_cards,
  ROUND(COALESCE(SUM(cc.current_balance), 0), 2) AS total_card_balance,
  wm.wm_client_id,
  wm.client_tier AS vip_tier,
  ROUND(COALESCE(wm.total_aum, 0), 2) AS total_aum,
  ROUND(
    COALESCE(SUM(a.current_balance), 0) +
    COALESCE(SUM(cc.available_credit), 0) +
    COALESCE(wm.total_aum, 0), 2
  ) AS total_relationship_value,
  ROUND(
    COALESCE(SUM(l.current_balance), 0) +
    COALESCE(SUM(cc.current_balance), 0), 2
  ) AS total_credit_exposure
FROM `${project_id}.retail_silver.silver_customers` c
LEFT JOIN `${project_id}.retail_silver.silver_loyalty_accounts` a ON c.customer_id = a.customer_id AND a.account_status = 'Active'
LEFT JOIN `${project_id}.retail_silver.silver_bnpl_plans` l ON c.customer_id = l.customer_id
LEFT JOIN `${project_id}.retail_silver.silver_store_cards` cc ON c.customer_id = cc.customer_id AND cc.card_status = 'Active'
LEFT JOIN `${project_id}.retail_silver.silver_vip_members` wm ON c.customer_id = wm.retail_customer_id
GROUP BY c.customer_id, c.first_name, c.last_name, c.customer_type, c.customer_segment,
         c.primary_store_id, c.kyc_risk_rating, c.kyc_status, c.account_opened_date, c.state,
         c.industry, wm.wm_client_id, wm.client_tier, wm.total_aum
