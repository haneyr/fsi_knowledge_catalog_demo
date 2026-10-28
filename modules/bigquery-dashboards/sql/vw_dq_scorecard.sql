CREATE OR REPLACE VIEW `${project_id}.retail_dashboards.vw_dq_scorecard` AS
SELECT 'retail_bronze' AS dataset, 'bronze_customers' AS table_name, 'COMPLETENESS' AS dimension, 95.2 AS score UNION ALL
SELECT 'retail_bronze', 'bronze_loyalty_accounts', 'COMPLETENESS', 98.7 UNION ALL
SELECT 'retail_bronze', 'bronze_pos_transactions', 'VALIDITY', 97.1 UNION ALL
SELECT 'retail_silver', 'silver_customers', 'UNIQUENESS', 100.0 UNION ALL
SELECT 'retail_silver', 'silver_bnpl_plans', 'VALIDITY', 99.3 UNION ALL
SELECT 'retail_gold', 'gold_customer_360', 'CONSISTENCY', 98.5 UNION ALL
SELECT 'retail_gold', 'gold_bnpl_plan_summary', 'VALIDITY', 99.8
