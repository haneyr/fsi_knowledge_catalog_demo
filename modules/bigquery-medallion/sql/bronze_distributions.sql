CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_distributions` AS
SELECT
  CONCAT('DIST-', LPAD(CAST(n AS STRING), 9, '0')) AS distribution_id,
  CONCAT('PORT-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 8, '0')) AS portfolio_id,
  CONCAT('WMC-', LPAD(CAST(CAST(FLOOR(RAND() * 10000) + 1 AS INT64) AS STRING), 7, '0')) AS wm_client_id,
  CASE MOD(n, 6) WHEN 0 THEN 'Dividend' WHEN 1 THEN 'Interest' WHEN 2 THEN 'Capital Gain' WHEN 3 THEN 'RMD' WHEN 4 THEN 'Withdrawal' ELSE 'Return of Capital' END AS distribution_type,
  ROUND(100 + RAND() * 50000, 2) AS gross_amount,
  ROUND(RAND() * 10000, 2) AS tax_withheld,
  ROUND(100 + RAND() * 40000, 2) AS net_amount,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 500) AS INT64) DAY) AS distribution_date,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 502) AS INT64) DAY) AS settlement_date,
  CASE MOD(n, 4) WHEN 0 THEN 'ACH' WHEN 1 THEN 'Check' WHEN 2 THEN 'Reinvest' ELSE 'Wire' END AS payment_method,
  CASE MOD(n, 3) WHEN 0 THEN 'Processed' WHEN 1 THEN 'Processed' ELSE 'Pending' END AS status,
  CASE MOD(n, 4)
    WHEN 0 THEN 'Qualified Dividend' WHEN 1 THEN 'Ordinary Income' WHEN 2 THEN 'Long-Term Capital Gain' ELSE 'Tax-Exempt Interest'
  END AS tax_treatment,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
