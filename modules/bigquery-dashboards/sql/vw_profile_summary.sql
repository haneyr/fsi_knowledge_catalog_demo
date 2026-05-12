CREATE OR REPLACE VIEW `${project_id}.fsi_dashboards.vw_profile_summary` AS
SELECT 'fsi_bronze' AS dataset, 'bronze_customers' AS table_name, 20040 AS row_count, 22 AS column_count, 'customer_id' AS pk_column UNION ALL
SELECT 'fsi_bronze', 'bronze_accounts', 50000, 18, 'account_id' UNION ALL
SELECT 'fsi_bronze', 'bronze_transactions', 100000, 16, 'transaction_id' UNION ALL
SELECT 'fsi_silver', 'silver_customers', 20000, 23, 'customer_id' UNION ALL
SELECT 'fsi_silver', 'silver_accounts', 50000, 19, 'account_id' UNION ALL
SELECT 'fsi_gold', 'gold_customer_360', 20000, 18, 'customer_id'
