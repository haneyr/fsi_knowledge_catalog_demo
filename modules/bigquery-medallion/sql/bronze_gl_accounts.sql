CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_gl_accounts` AS
SELECT
  CONCAT('GLACCT-', LPAD(CAST(n AS STRING), 6, '0')) AS gl_account_id,
  LPAD(CAST(1000 + n AS STRING), 6, '0') AS account_number,
  CONCAT('GL Account ', CAST(n AS STRING)) AS account_name,
  CASE MOD(n, 5)
    WHEN 0 THEN 'Asset' WHEN 1 THEN 'Liability' WHEN 2 THEN 'Equity'
    WHEN 3 THEN 'Revenue' ELSE 'Expense'
  END AS account_type,
  CASE MOD(n, 10)
    WHEN 0 THEN 'Cash and Due From' WHEN 1 THEN 'Loans and Leases' WHEN 2 THEN 'Investment Securities'
    WHEN 3 THEN 'Deposits' WHEN 4 THEN 'Borrowed Funds' WHEN 5 THEN 'Equity Capital'
    WHEN 6 THEN 'Interest Income' WHEN 7 THEN 'Noninterest Income' WHEN 8 THEN 'Interest Expense'
    ELSE 'Noninterest Expense'
  END AS category,
  CASE MOD(n, 3) WHEN 0 THEN 'Detail' WHEN 1 THEN 'Summary' ELSE 'Detail' END AS level_type,
  CASE WHEN MOD(n, 3) = 1 THEN CONCAT('GLACCT-', LPAD(CAST(CAST(FLOOR(n / 10) * 10 AS INT64) AS STRING), 6, '0')) ELSE NULL END AS parent_account_id,
  CASE MOD(n, 3) WHEN 0 THEN 'Normal Debit' ELSE 'Normal Credit' END AS normal_balance,
  CASE MOD(n, 4) WHEN 0 THEN TRUE ELSE FALSE END AS is_call_report_line,
  CASE WHEN MOD(n, 4) = 0 THEN CONCAT('RC-', CASE MOD(n, 8) WHEN 0 THEN 'B1' WHEN 1 THEN 'B2' WHEN 2 THEN 'B3' WHEN 3 THEN 'C1' WHEN 4 THEN 'E1' WHEN 5 THEN 'E2' ELSE 'M1' END) ELSE NULL END AS call_report_line,
  CASE MOD(n, 6) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' WHEN 4 THEN 'Active' ELSE 'Inactive' END AS status,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ARGUS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
