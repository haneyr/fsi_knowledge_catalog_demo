CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_gl_entries` AS
SELECT
  CONCAT('GL-', LPAD(CAST(n AS STRING), 12, '0')) AS gl_entry_id,
  CONCAT('GLACCT-', LPAD(CAST(CAST(FLOOR(RAND() * 5000) + 1 AS INT64) AS STRING), 6, '0')) AS gl_account_id,
  CONCAT('CC-', LPAD(CAST(CAST(FLOOR(RAND() * 500) + 1 AS INT64) AS STRING), 4, '0')) AS cost_center_id,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 500) AS INT64) DAY) AS posting_date,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 500) AS INT64) DAY) AS effective_date,
  CASE MOD(n, 2) WHEN 0 THEN 'Debit' ELSE 'Credit' END AS entry_type,
  ROUND(0.01 + RAND() * 1000000, 2) AS amount,
  'USD' AS currency,
  CONCAT('JE-', LPAD(CAST(CAST(FLOOR(n / 3.0) AS INT64) AS STRING), 10, '0')) AS journal_entry_id,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Interest Income' WHEN 1 THEN 'Fee Revenue' WHEN 2 THEN 'Loan Loss Provision'
    WHEN 3 THEN 'Operating Expense' WHEN 4 THEN 'Depreciation' WHEN 5 THEN 'Tax Expense'
    WHEN 6 THEN 'Intercompany' ELSE 'Adjustment'
  END AS description,
  CASE MOD(n, 5) WHEN 0 THEN 'Auto' WHEN 1 THEN 'Manual' WHEN 2 THEN 'Auto' WHEN 3 THEN 'Interface' ELSE 'Auto' END AS source_type,
  CONCAT('BATCH-', LPAD(CAST(CAST(FLOOR(n / 100.0) AS INT64) AS STRING), 8, '0')) AS batch_id,
  CASE MOD(n, 3) WHEN 0 THEN 'Posted' WHEN 1 THEN 'Posted' ELSE 'Pending' END AS status,
  CASE WHEN MOD(n, 100) = 0 THEN TRUE ELSE FALSE END AS is_reversal,
  CASE WHEN MOD(n, 50) = 0 THEN CONCAT('GL-', LPAD(CAST(n - 1 AS STRING), 12, '0')) ELSE NULL END AS reversal_of,
  CONCAT('FY', CAST(2024 + CAST(FLOOR(RAND() * 2) AS INT64) AS STRING)) AS fiscal_year,
  CAST(FLOOR(1 + RAND() * 12) AS INT64) AS fiscal_period,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ARGUS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
