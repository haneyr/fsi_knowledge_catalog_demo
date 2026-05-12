CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_transactions` AS
SELECT
  CONCAT('TXN-', LPAD(CAST(n AS STRING), 12, '0')) AS transaction_id,
  CONCAT('ACCT-', LPAD(CAST(CAST(FLOOR(RAND() * 50000) + 1 AS INT64) AS STRING), 10, '0')) AS account_id,
  CASE MOD(n, 10)
    WHEN 0 THEN 'DEBIT' WHEN 1 THEN 'CREDIT' WHEN 2 THEN 'DEBIT'
    WHEN 3 THEN 'TRANSFER_OUT' WHEN 4 THEN 'TRANSFER_IN' WHEN 5 THEN 'DEBIT'
    WHEN 6 THEN 'CREDIT' WHEN 7 THEN 'FEE' WHEN 8 THEN 'INTEREST' ELSE 'DEBIT'
  END AS transaction_type,
  ROUND(CASE MOD(n, 10)
    WHEN 7 THEN 5 + RAND() * 50
    WHEN 8 THEN 0.01 + RAND() * 500
    ELSE 1 + RAND() * 5000
  END, 2) AS amount,
  'USD' AS currency,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS transaction_date,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60 + 60) AS INT64) MINUTE) AS posted_date,
  CASE MOD(n, 15)
    WHEN 0 THEN 'POS Purchase' WHEN 1 THEN 'Direct Deposit' WHEN 2 THEN 'Online Bill Pay'
    WHEN 3 THEN 'ACH Debit' WHEN 4 THEN 'ACH Credit' WHEN 5 THEN 'Wire Transfer'
    WHEN 6 THEN 'ATM Withdrawal' WHEN 7 THEN 'Check Deposit' WHEN 8 THEN 'Mobile Deposit'
    WHEN 9 THEN 'Recurring Payment' WHEN 10 THEN 'Payroll' WHEN 11 THEN 'Merchant Refund'
    WHEN 12 THEN 'Internal Transfer' WHEN 13 THEN 'Fee Assessment' ELSE 'Interest Payment'
  END AS description,
  CASE MOD(n, 12)
    WHEN 0 THEN 'Grocery' WHEN 1 THEN 'Dining' WHEN 2 THEN 'Utilities'
    WHEN 3 THEN 'Entertainment' WHEN 4 THEN 'Healthcare' WHEN 5 THEN 'Transportation'
    WHEN 6 THEN 'Shopping' WHEN 7 THEN 'Insurance' WHEN 8 THEN 'Rent/Mortgage'
    WHEN 9 THEN 'Travel' WHEN 10 THEN 'Education' ELSE 'Other'
  END AS merchant_category,
  CASE MOD(n, 6)
    WHEN 0 THEN 'Online' WHEN 1 THEN 'Branch' WHEN 2 THEN 'ATM'
    WHEN 3 THEN 'Mobile' WHEN 4 THEN 'POS' ELSE 'Phone'
  END AS channel,
  CONCAT('BR-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS branch_id,
  CASE MOD(n, 3) WHEN 0 THEN 'Posted' WHEN 1 THEN 'Posted' ELSE 'Pending' END AS status,
  CASE WHEN MOD(n, 200) = 0 THEN ROUND(RAND() * 100, 0) ELSE NULL END AS fraud_score,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ATLAS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 100000)) AS n
