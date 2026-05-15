CREATE OR REPLACE TABLE `${project_id}.fsi_staging.staging_call_report_rc_r` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 8.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('RC-R-', CAST(MOD(n, 8) + 1 AS STRING)) AS schedule_line,
  CASE MOD(n, 8) WHEN 0 THEN 'Total RWA' WHEN 1 THEN 'CET1 Capital' WHEN 2 THEN 'Tier 1 Capital' WHEN 3 THEN 'Total Capital' WHEN 4 THEN 'CET1 Ratio' WHEN 5 THEN 'Tier 1 Ratio' WHEN 6 THEN 'Total Capital Ratio' ELSE 'Leverage Ratio' END AS line_description,
  ROUND(CASE WHEN MOD(n, 8) >= 4 THEN 0.05 + RAND() * 0.15 ELSE 1000000000 + RAND() * 50000000000 END, CASE WHEN MOD(n, 8) >= 4 THEN 4 ELSE 0 END) AS amount,
  'Filed' AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 40)) AS n
