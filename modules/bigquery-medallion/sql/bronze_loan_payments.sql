CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_loan_payments` AS
SELECT
  CONCAT('LPMT-', LPAD(CAST(n AS STRING), 10, '0')) AS payment_id,
  CONCAT('LN-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 9, '0')) AS loan_id,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(RAND() * 900) AS INT64) DAY) AS payment_date,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(n / 2) AS INT64) DAY) AS due_date,
  ROUND(200 + RAND() * 5000, 2) AS payment_amount,
  ROUND(50 + RAND() * 2000, 2) AS principal_amount,
  ROUND(50 + RAND() * 1500, 2) AS interest_amount,
  ROUND(CASE WHEN MOD(n, 50) = 0 THEN 10 + RAND() * 100 ELSE 0 END, 2) AS escrow_amount,
  ROUND(CASE WHEN MOD(n, 30) = 0 THEN 25 + RAND() * 100 ELSE 0 END, 2) AS late_fee,
  CASE MOD(n, 6) WHEN 0 THEN 'ACH' WHEN 1 THEN 'Check' WHEN 2 THEN 'Wire' WHEN 3 THEN 'Online' WHEN 4 THEN 'Auto-Debit' ELSE 'ACH' END AS payment_method,
  CASE MOD(n, 10) WHEN 0 THEN 'Late' WHEN 1 THEN 'Partial' ELSE 'On Time' END AS payment_status,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ATLAS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
