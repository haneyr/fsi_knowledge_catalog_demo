CREATE OR REPLACE VIEW `${project_id}.retail_dashboards.vw_customer_lifetime_value` AS
SELECT
  c.customer_id,
  c.first_name,
  c.last_name,
  c.customer_segment,
  c.total_loyalty_balance,
  c.total_bnpl_balance,
  c.total_card_balance,
  c.total_aum,
  c.total_relationship_value,
  c.total_credit_exposure,
  c.vip_tier,
  CASE
    WHEN c.total_relationship_value >= 10000000 THEN 'Ultra High Net Worth'
    WHEN c.total_relationship_value >= 1000000 THEN 'High Net Worth'
    WHEN c.total_relationship_value >= 250000 THEN 'Affluent'
    WHEN c.total_relationship_value >= 50000 THEN 'Mass Affluent'
    ELSE 'Mass Market'
  END AS relationship_tier
FROM `${project_id}.retail_gold.gold_customer_360` c
