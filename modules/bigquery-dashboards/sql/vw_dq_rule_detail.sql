CREATE OR REPLACE VIEW `${project_id}.retail_dashboards.vw_dq_rule_detail` AS
SELECT 'retail_silver' AS dataset, 'silver_customers' AS table_name, 'pk_unique' AS rule_name, 'UNIQUENESS' AS dimension, 'customer_id' AS column_name, 100.0 AS pass_rate, 20000 AS rows_evaluated, 0 AS rows_failed UNION ALL
SELECT 'retail_silver', 'silver_customers', 'member_tin_masked_format', 'VALIDITY', 'member_tin_masked', 99.8, 20000, 40 UNION ALL
SELECT 'retail_silver', 'silver_bnpl_plans', 'interest_rate_range', 'VALIDITY', 'interest_rate', 100.0, 15000, 0
