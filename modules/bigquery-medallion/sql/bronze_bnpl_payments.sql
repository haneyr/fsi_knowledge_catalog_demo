CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_bnpl_payments` AS
SELECT
  CONCAT('LPMT-', LPAD(CAST(n AS STRING), 10, '0')) AS payment_id,
  CONCAT('LN-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 9, '0')) AS bnpl_plan_id,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(FLOOR(RAND() * 365) AS INT64) DAY) AS payment_date,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(FLOOR(RAND() * 365) AS INT64) DAY) AS due_date,
  ROUND(18 + RAND() * 240, 2) AS payment_amount,
  ROUND(15 + RAND() * 210, 2) AS principal_amount,
  ROUND(CASE WHEN MOD(n, 3) = 0 THEN 0 ELSE 1.5 + RAND() * 18 END, 2) AS interest_amount,
  ROUND(0.0, 2) AS escrow_amount,
  ROUND(CASE WHEN MOD(n, 30) = 0 THEN 5 + RAND() * 15 ELSE 0 END, 2) AS late_fee,
  CASE MOD(n, 6) WHEN 0 THEN 'Saved Debit Card' WHEN 1 THEN 'Apple Pay' WHEN 2 THEN 'Google Pay' WHEN 3 THEN 'Northwind Wallet' WHEN 4 THEN 'Auto-Pay Card' ELSE 'Saved Debit Card' END AS payment_method,
  CASE MOD(n, 10) WHEN 0 THEN 'Late' WHEN 1 THEN 'Partial' ELSE 'On Time' END AS payment_status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
