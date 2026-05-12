CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_atm_transactions` AS
SELECT
  CONCAT('ATM-', LPAD(CAST(n AS STRING), 10, '0')) AS atm_transaction_id,
  CONCAT('ACCT-', LPAD(CAST(CAST(FLOOR(RAND() * 50000) + 1 AS INT64) AS STRING), 10, '0')) AS account_id,
  CONCAT('CC-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 8, '0')) AS card_id,
  CASE MOD(n, 5) WHEN 0 THEN 'Withdrawal' WHEN 1 THEN 'Withdrawal' WHEN 2 THEN 'Balance Inquiry' WHEN 3 THEN 'Deposit' ELSE 'Transfer' END AS transaction_type,
  ROUND(CASE MOD(n, 5) WHEN 2 THEN 0 ELSE 20 + RAND() * 980 END, 2) AS amount,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS transaction_date,
  CONCAT('ATM-TERM-', LPAD(CAST(MOD(n, 2000) + 1 AS STRING), 5, '0')) AS terminal_id,
  CASE MOD(n, 3) WHEN 0 THEN 'On-Us' WHEN 1 THEN 'Network' ELSE 'On-Us' END AS network_type,
  CASE MOD(n, 3) WHEN 1 THEN TRUE ELSE FALSE END AS surcharge_applied,
  ROUND(CASE MOD(n, 3) WHEN 1 THEN 2.5 + RAND() * 2 ELSE 0 END, 2) AS surcharge_amount,
  CASE MOD(n, 10) WHEN 0 THEN 'NY' WHEN 1 THEN 'CA' WHEN 2 THEN 'TX' WHEN 3 THEN 'FL' WHEN 4 THEN 'IL' WHEN 5 THEN 'PA' WHEN 6 THEN 'OH' WHEN 7 THEN 'GA' WHEN 8 THEN 'WA' ELSE 'MA' END AS terminal_state,
  CASE MOD(n, 6) WHEN 0 THEN 'Approved' WHEN 1 THEN 'Approved' WHEN 2 THEN 'Approved' WHEN 3 THEN 'Approved' WHEN 4 THEN 'Declined - NSF' ELSE 'Approved' END AS status,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ATLAS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 20000)) AS n
