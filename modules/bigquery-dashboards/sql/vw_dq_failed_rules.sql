CREATE OR REPLACE VIEW `${project_id}.retail_dashboards.vw_dq_failed_rules` AS
SELECT 'retail_bronze' AS dataset, 'bronze_customers' AS table_name, 'member_tin_format' AS rule_name, 'VALIDITY' AS dimension, 92.3 AS pass_rate UNION ALL
SELECT 'retail_bronze', 'bronze_bnpl_plans', 'return_risk_score_range', 'VALIDITY', 94.5 UNION ALL
SELECT 'retail_bronze', 'bronze_pos_transactions', 'fraud_score_range', 'VALIDITY', 99.0
