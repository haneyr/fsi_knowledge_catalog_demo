CREATE OR REPLACE TABLE `${project_id}.fsi_staging.staging_call_report_rc_c` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 12.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('RC-C-', CAST(MOD(n, 12) + 1 AS STRING)) AS schedule_line,
  CASE MOD(n, 12) WHEN 0 THEN 'Loans Secured by RE' WHEN 1 THEN '1-4 Family Residential' WHEN 2 THEN 'Commercial RE' WHEN 3 THEN 'Construction and Land' WHEN 4 THEN 'C&I Loans' WHEN 5 THEN 'Consumer Loans' WHEN 6 THEN 'Credit Cards' WHEN 7 THEN 'Auto Loans' WHEN 8 THEN 'Other Consumer' WHEN 9 THEN 'Agriculture Loans' WHEN 10 THEN 'Other Loans' ELSE 'Total Loans and Leases' END AS line_description,
  ROUND(100000000 + RAND() * 10000000000, 0) AS amount,
  'Filed' AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 60)) AS n
