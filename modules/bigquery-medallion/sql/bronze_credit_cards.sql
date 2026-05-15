CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_credit_cards` AS
SELECT
  CONCAT('CC-', LPAD(CAST(n AS STRING), 8, '0')) AS card_id,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS customer_id,
  CONCAT('ACCT-', LPAD(CAST(CAST(50000 + n AS INT64) AS STRING), 10, '0')) AS account_id,
  CASE MOD(n, 5)
    WHEN 0 THEN 'VISA_PLATINUM' WHEN 1 THEN 'MC_GOLD' WHEN 2 THEN 'VISA_SIGNATURE'
    WHEN 3 THEN 'MC_WORLD' ELSE 'VISA_CLASSIC'
  END AS card_type,
  CASE MOD(n, 5)
    WHEN 0 THEN 'Visa' WHEN 1 THEN 'Mastercard' WHEN 2 THEN 'Visa'
    WHEN 3 THEN 'Mastercard' ELSE 'Visa'
  END AS network,
  CONCAT('XXXX-XXXX-XXXX-', LPAD(CAST(MOD(n, 10000) AS STRING), 4, '0')) AS masked_card_number,
  ROUND(1000 + RAND() * 49000, 0) AS credit_limit,
  ROUND(RAND() * 40000, 2) AS current_balance,
  ROUND(RAND() * 5000, 2) AS available_credit,
  ROUND(0.12 + RAND() * 0.15, 4) AS apr,
  ROUND(CASE WHEN MOD(n, 20) = 0 THEN 50 + RAND() * 500 ELSE 0 END, 2) AS annual_fee,
  CAST(FLOOR(300 + RAND() * 550) AS INT64) AS fico_score,
  DATE_ADD('2020-01-01', INTERVAL CAST(FLOOR(RAND() * 2000) AS INT64) DAY) AS issue_date,
  DATE_ADD('2026-01-01', INTERVAL CAST(FLOOR(RAND() * 1500) AS INT64) DAY) AS expiration_date,
  CASE MOD(n, 6) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' WHEN 4 THEN 'Frozen' ELSE 'Closed' END AS card_status,
  ROUND(CASE WHEN MOD(n, 5) = 0 THEN RAND() * 500 ELSE 0 END, 2) AS rewards_balance,
  CASE MOD(n, 4) WHEN 0 THEN 'Points' WHEN 1 THEN 'Cashback' WHEN 2 THEN 'Miles' ELSE 'Points' END AS rewards_type,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ATLAS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 15000)) AS n
