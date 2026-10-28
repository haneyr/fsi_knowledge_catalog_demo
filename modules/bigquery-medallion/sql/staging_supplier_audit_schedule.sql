CREATE OR REPLACE TABLE `${project_id}.retail_staging.staging_supplier_audit_schedule` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 8.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('WC-', CAST(MOD(n, 8) + 1 AS STRING)) AS schedule_line,
  CASE MOD(n, 8) WHEN 0 THEN 'Total Inventory at Risk' WHEN 1 THEN 'Core Working Capital' WHEN 2 THEN 'Inventory Buffer Reserve' WHEN 3 THEN 'Total Operating Capital' WHEN 4 THEN 'Core Working Capital Ratio' WHEN 5 THEN 'Quick Liquidity Ratio' WHEN 6 THEN 'Operating Capital Ratio' ELSE 'Inventory Turnover Ratio' END AS line_description,
  ROUND(CASE WHEN MOD(n, 8) >= 4 THEN 0.12 + RAND() * 0.22 ELSE 15000000 + RAND() * 85000000 END, CASE WHEN MOD(n, 8) >= 4 THEN 4 ELSE 0 END) AS amount,
  'Filed' AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 40)) AS n
