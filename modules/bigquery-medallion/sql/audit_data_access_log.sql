CREATE OR REPLACE TABLE `${project_id}.fsi_audit.audit_data_access_log` AS
SELECT
  CONCAT('DAL-', LPAD(CAST(n AS STRING), 10, '0')) AS log_id,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS access_timestamp,
  CONCAT('EMP-', LPAD(CAST(CAST(FLOOR(RAND() * 5000) + 1 AS INT64) AS STRING), 6, '0')) AS user_id,
  CASE MOD(n, 6) WHEN 0 THEN 'BigQuery' WHEN 1 THEN 'ATLAS' WHEN 2 THEN 'FORTUNA' WHEN 3 THEN 'ARGUS' WHEN 4 THEN 'Looker' ELSE 'Data Catalog' END AS system,
  CASE MOD(n, 5) WHEN 0 THEN 'READ' WHEN 1 THEN 'READ' WHEN 2 THEN 'QUERY' WHEN 3 THEN 'EXPORT' ELSE 'MODIFY' END AS access_type,
  CONCAT('fsi_', CASE MOD(n, 3) WHEN 0 THEN 'silver' WHEN 1 THEN 'gold' ELSE 'bronze' END, '.', CASE MOD(n, 6) WHEN 0 THEN 'silver_customers' WHEN 1 THEN 'gold_customer_360' WHEN 2 THEN 'silver_loans' WHEN 3 THEN 'gold_loan_portfolio_summary' WHEN 4 THEN 'silver_transactions' ELSE 'bronze_customers' END) AS resource_path,
  CAST(FLOOR(RAND() * 10000) AS INT64) AS rows_accessed,
  CASE MOD(n, 4) WHEN 0 THEN 'Contains PII' WHEN 1 THEN 'Contains Financial Data' WHEN 2 THEN 'Aggregated' ELSE 'Non-Sensitive' END AS sensitivity_flag,
  CASE MOD(n, 5) WHEN 0 THEN 'Granted' WHEN 1 THEN 'Granted' WHEN 2 THEN 'Granted' WHEN 3 THEN 'Granted' ELSE 'Denied' END AS access_result,
  CONCAT(CAST(FLOOR(10 + RAND() * 240) AS STRING), '.', CAST(FLOOR(RAND() * 255) AS STRING), '.', CAST(FLOOR(RAND() * 255) AS STRING), '.', CAST(FLOOR(RAND() * 255) AS STRING)) AS source_ip
FROM UNNEST(GENERATE_ARRAY(1, 20000)) AS n
