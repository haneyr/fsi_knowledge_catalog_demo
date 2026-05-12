CREATE OR REPLACE VIEW `${project_id}.fsi_dashboards.vw_dq_scorecard` AS
SELECT 'fsi_bronze' AS dataset, 'bronze_customers' AS table_name, 'COMPLETENESS' AS dimension, 95.2 AS score UNION ALL
SELECT 'fsi_bronze', 'bronze_accounts', 'COMPLETENESS', 98.7 UNION ALL
SELECT 'fsi_bronze', 'bronze_transactions', 'VALIDITY', 97.1 UNION ALL
SELECT 'fsi_silver', 'silver_customers', 'UNIQUENESS', 100.0 UNION ALL
SELECT 'fsi_silver', 'silver_loans', 'VALIDITY', 99.3 UNION ALL
SELECT 'fsi_gold', 'gold_customer_360', 'CONSISTENCY', 98.5 UNION ALL
SELECT 'fsi_gold', 'gold_loan_portfolio_summary', 'VALIDITY', 99.8
