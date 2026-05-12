CREATE OR REPLACE VIEW `${project_id}.fsi_dashboards.vw_dq_rule_detail` AS
SELECT 'fsi_silver' AS dataset, 'silver_customers' AS table_name, 'pk_unique' AS rule_name, 'UNIQUENESS' AS dimension, 'customer_id' AS column_name, 100.0 AS pass_rate, 20000 AS rows_evaluated, 0 AS rows_failed UNION ALL
SELECT 'fsi_silver', 'silver_customers', 'ssn_masked_format', 'VALIDITY', 'ssn_masked', 99.8, 20000, 40 UNION ALL
SELECT 'fsi_silver', 'silver_loans', 'interest_rate_range', 'VALIDITY', 'interest_rate', 100.0, 15000, 0
