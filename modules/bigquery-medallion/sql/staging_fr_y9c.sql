CREATE OR REPLACE TABLE `${project_id}.fsi_staging.staging_fr_y9c` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('Y9C-', CASE MOD(n, 10) WHEN 0 THEN 'HC-B1' WHEN 1 THEN 'HC-B2' WHEN 2 THEN 'HC-C1' WHEN 3 THEN 'HC-E' WHEN 4 THEN 'HC-R1' WHEN 5 THEN 'HC-R2' WHEN 6 THEN 'HI-1' WHEN 7 THEN 'HI-2' WHEN 8 THEN 'HI-7' ELSE 'HC-28' END) AS schedule_line,
  CASE MOD(n, 10) WHEN 0 THEN 'Consolidated Assets' WHEN 1 THEN 'Securities' WHEN 2 THEN 'Loans' WHEN 3 THEN 'Deposits' WHEN 4 THEN 'Risk-Weighted Assets' WHEN 5 THEN 'Total Capital' WHEN 6 THEN 'Interest Income' WHEN 7 THEN 'Interest Expense' WHEN 8 THEN 'Noninterest Expense' ELSE 'Total Equity' END AS line_description,
  ROUND(1000000000 + RAND() * 100000000000, 0) AS amount,
  'Federal Reserve' AS regulatory_body,
  'Filed' AS status,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 50)) AS n
