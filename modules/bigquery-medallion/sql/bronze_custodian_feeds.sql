CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_custodian_feeds` AS
SELECT
  CONCAT('CFEED-', LPAD(CAST(n AS STRING), 9, '0')) AS feed_id,
  CONCAT('PORT-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 8, '0')) AS portfolio_id,
  CASE MOD(n, 4) WHEN 0 THEN 'Schwab' WHEN 1 THEN 'Fidelity' WHEN 2 THEN 'Pershing' ELSE 'TD Ameritrade' END AS custodian_name,
  CASE MOD(n, 3) WHEN 0 THEN 'Position' WHEN 1 THEN 'Transaction' ELSE 'Cash Balance' END AS feed_type,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 500) AS INT64) DAY) AS as_of_date,
  CONCAT('SEC-', LPAD(CAST(CAST(FLOOR(RAND() * 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  ROUND(RAND() * 10000, 4) AS quantity,
  ROUND(RAND() * 5000, 2) AS market_value,
  CASE MOD(n, 3)
    WHEN 0 THEN 'Reconciled' WHEN 1 THEN 'Unreconciled' ELSE 'Reconciled'
  END AS reconciliation_status,
  CASE WHEN MOD(n, 20) = 0 THEN ROUND(-100 + RAND() * 200, 2) ELSE 0.00 END AS break_amount,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS received_at,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
