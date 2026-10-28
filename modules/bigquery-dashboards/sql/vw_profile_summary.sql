CREATE OR REPLACE VIEW `${project_id}.retail_dashboards.vw_profile_summary` AS
SELECT 'retail_bronze' AS dataset, 'bronze_customers' AS table_name, 20040 AS row_count, 22 AS column_count, 'customer_id' AS pk_column UNION ALL
SELECT 'retail_bronze', 'bronze_loyalty_accounts', 50000, 18, 'account_id' UNION ALL
SELECT 'retail_bronze', 'bronze_pos_transactions', 100000, 16, 'transaction_id' UNION ALL
SELECT 'retail_silver', 'silver_customers', 20000, 23, 'customer_id' UNION ALL
SELECT 'retail_silver', 'silver_loyalty_accounts', 50000, 19, 'account_id' UNION ALL
SELECT 'retail_gold', 'gold_customer_360', 20000, 18, 'customer_id'
