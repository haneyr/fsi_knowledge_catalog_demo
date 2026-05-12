CREATE OR REPLACE TABLE `${project_id}.fsi_staging.staging_call_report_ri` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('RI-', CAST(MOD(n, 10) + 1 AS STRING)) AS schedule_line,
  CASE MOD(n, 10) WHEN 0 THEN 'Total Interest Income' WHEN 1 THEN 'Total Interest Expense' WHEN 2 THEN 'Net Interest Income' WHEN 3 THEN 'Provision for Credit Losses' WHEN 4 THEN 'Total Noninterest Income' WHEN 5 THEN 'Total Noninterest Expense' WHEN 6 THEN 'Income Before Taxes' WHEN 7 THEN 'Applicable Income Taxes' WHEN 8 THEN 'Net Income' ELSE 'Retained Earnings' END AS line_description,
  ROUND(100000 + RAND() * 5000000000, 0) AS amount,
  'Filed' AS status,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 50)) AS n
