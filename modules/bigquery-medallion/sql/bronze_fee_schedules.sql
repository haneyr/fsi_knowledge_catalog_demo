CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_fee_schedules` AS
SELECT
  CONCAT('FEE-', LPAD(CAST(n AS STRING), 6, '0')) AS fee_schedule_id,
  CONCAT('WMC-', LPAD(CAST(CAST(FLOOR(RAND() * 10000) + 1 AS INT64) AS STRING), 7, '0')) AS wm_client_id,
  CONCAT('PORT-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 8, '0')) AS portfolio_id,
  CASE MOD(n, 5) WHEN 0 THEN 'Advisory Fee' WHEN 1 THEN 'Management Fee' WHEN 2 THEN 'Performance Fee' WHEN 3 THEN 'Custody Fee' ELSE 'Transaction Fee' END AS fee_type,
  ROUND(CASE MOD(n, 5) WHEN 0 THEN 50 + RAND() * 150 WHEN 1 THEN 25 + RAND() * 100 WHEN 2 THEN 100 + RAND() * 400 WHEN 3 THEN 5 + RAND() * 20 ELSE 10 + RAND() * 30 END, 2) AS fee_rate_bps,
  CASE MOD(n, 4) WHEN 0 THEN 'Quarterly' WHEN 1 THEN 'Monthly' WHEN 2 THEN 'Annual' ELSE 'Quarterly' END AS billing_frequency,
  CASE MOD(n, 3) WHEN 0 THEN 'Advance' WHEN 1 THEN 'Arrears' ELSE 'Advance' END AS billing_method,
  ROUND(100 + RAND() * 50000, 2) AS last_fee_amount,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 365) AS INT64) DAY) AS last_billing_date,
  DATE_ADD('2020-01-01', INTERVAL CAST(FLOOR(RAND() * 2000) AS INT64) DAY) AS effective_date,
  CASE WHEN MOD(n, 20) = 0 THEN DATE_ADD('2025-01-01', INTERVAL CAST(FLOOR(RAND() * 365) AS INT64) DAY) ELSE NULL END AS end_date,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
