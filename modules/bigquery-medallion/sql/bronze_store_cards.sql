CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_store_cards` AS
SELECT
  CONCAT('CC-', LPAD(CAST(n AS STRING), 8, '0')) AS card_id,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS customer_id,
  CONCAT('ACCT-', LPAD(CAST(CAST(50000 + n AS INT64) AS STRING), 10, '0')) AS account_id,
  CASE MOD(n, 5)
    WHEN 0 THEN 'NORTHWIND_REWARDS_PLCC' WHEN 1 THEN 'NORTHWIND_VISA_SIGNATURE' WHEN 2 THEN 'VIP_INSIDER_CHARGE'
    WHEN 3 THEN 'NORTHWIND_MASTERCARD' ELSE 'STORE_REWARDS_BASIC'
  END AS card_type,
  CASE MOD(n, 5)
    WHEN 0 THEN 'Store Private Label' WHEN 1 THEN 'Visa' WHEN 2 THEN 'Store Private Label'
    WHEN 3 THEN 'Mastercard' ELSE 'Store Private Label'
  END AS network,
  CONCAT('XXXX-XXXX-XXXX-', LPAD(CAST(MOD(n, 10000) AS STRING), 4, '0')) AS masked_card_number,
  ROUND(300 + RAND() * 2700, 0) AS credit_limit,
  ROUND(25 + RAND() * 680, 2) AS current_balance,
  ROUND(200 + RAND() * 2000, 2) AS available_credit,
  ROUND(0.14 + RAND() * 0.14, 4) AS apr,
  ROUND(CASE WHEN MOD(n, 20) = 0 THEN 49 + RAND() * 50 ELSE 0 END, 2) AS annual_fee,
  CAST(8 + FLOOR(RAND() * 82) AS INT64) AS return_risk_score,
  DATE_ADD('2020-01-01', INTERVAL CAST(FLOOR(RAND() * 2000) AS INT64) DAY) AS issue_date,
  DATE_ADD('2026-01-01', INTERVAL CAST(FLOOR(RAND() * 1500) AS INT64) DAY) AS expiration_date,
  CASE MOD(n, 6) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' WHEN 4 THEN 'Frozen' ELSE 'Closed' END AS card_status,
  ROUND(CASE WHEN MOD(n, 5) = 0 THEN 10 + RAND() * 240 ELSE 0 END, 2) AS rewards_balance,
  CASE MOD(n, 4) WHEN 0 THEN 'Points' WHEN 1 THEN 'Cashback' WHEN 2 THEN 'Store Credit' ELSE 'Points' END AS rewards_type,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 15000)) AS n
