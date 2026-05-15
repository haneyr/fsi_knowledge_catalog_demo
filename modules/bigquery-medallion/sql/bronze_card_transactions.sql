CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_card_transactions` AS
SELECT
  CONCAT('CTXN-', LPAD(CAST(n AS STRING), 12, '0')) AS card_transaction_id,
  CONCAT('CC-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 8, '0')) AS card_id,
  CASE MOD(n, 6)
    WHEN 0 THEN 'PURCHASE' WHEN 1 THEN 'PURCHASE' WHEN 2 THEN 'PURCHASE'
    WHEN 3 THEN 'RETURN' WHEN 4 THEN 'CASH_ADVANCE' ELSE 'PURCHASE'
  END AS transaction_type,
  ROUND(1 + RAND() * 2000, 2) AS amount,
  'USD' AS currency,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS transaction_date,
  CASE MOD(n, 20)
    WHEN 0 THEN 'Amazon' WHEN 1 THEN 'Walmart' WHEN 2 THEN 'Target' WHEN 3 THEN 'Costco'
    WHEN 4 THEN 'Starbucks' WHEN 5 THEN 'Shell Gas' WHEN 6 THEN 'Netflix' WHEN 7 THEN 'Uber'
    WHEN 8 THEN 'Whole Foods' WHEN 9 THEN 'Home Depot' WHEN 10 THEN 'Best Buy'
    WHEN 11 THEN 'CVS Pharmacy' WHEN 12 THEN 'McDonalds' WHEN 13 THEN 'Apple Store'
    WHEN 14 THEN 'Delta Airlines' WHEN 15 THEN 'Marriott Hotel' WHEN 16 THEN 'Chevron'
    WHEN 17 THEN 'Kroger' WHEN 18 THEN 'United Airlines' ELSE 'Trader Joes'
  END AS merchant_name,
  CASE MOD(n, 10)
    WHEN 0 THEN '5411' WHEN 1 THEN '5812' WHEN 2 THEN '5541' WHEN 3 THEN '4899'
    WHEN 4 THEN '5311' WHEN 5 THEN '5912' WHEN 6 THEN '3000' WHEN 7 THEN '4121'
    WHEN 8 THEN '5200' ELSE '5999'
  END AS mcc_code,
  CASE MOD(n, 5) WHEN 0 THEN 'Online' WHEN 1 THEN 'In-Store' WHEN 2 THEN 'In-Store' WHEN 3 THEN 'In-Store' ELSE 'Contactless' END AS pos_entry_mode,
  CASE MOD(n, 3) WHEN 0 THEN 'Approved' WHEN 1 THEN 'Approved' ELSE CASE WHEN MOD(n, 50) = 0 THEN 'Declined' ELSE 'Approved' END END AS authorization_status,
  CASE WHEN MOD(n, 100) = 0 THEN ROUND(50 + RAND() * 50, 0) ELSE NULL END AS fraud_score,
  CASE WHEN MOD(n, 200) = 0 THEN TRUE ELSE FALSE END AS is_disputed,
  CONCAT(CASE MOD(n, 8) WHEN 0 THEN 'US' WHEN 1 THEN 'US' WHEN 2 THEN 'US' WHEN 3 THEN 'US' WHEN 4 THEN 'GB' WHEN 5 THEN 'CA' WHEN 6 THEN 'MX' ELSE 'US' END) AS merchant_country,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ATLAS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 80000)) AS n
