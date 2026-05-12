CREATE OR REPLACE VIEW `${project_id}.fsi_dashboards.vw_dq_failed_rules` AS
SELECT 'fsi_bronze' AS dataset, 'bronze_customers' AS table_name, 'ssn_format' AS rule_name, 'VALIDITY' AS dimension, 92.3 AS pass_rate UNION ALL
SELECT 'fsi_bronze', 'bronze_loans', 'fico_range', 'VALIDITY', 94.5 UNION ALL
SELECT 'fsi_bronze', 'bronze_transactions', 'fraud_score_range', 'VALIDITY', 99.0
