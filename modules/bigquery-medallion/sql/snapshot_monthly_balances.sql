CREATE OR REPLACE TABLE `${project_id}.fsi_snapshots.snapshot_monthly_balances` AS
SELECT
  CONCAT('ACCT-', LPAD(CAST(CAST(MOD(n, 50000) + 1 AS INT64) AS STRING), 10, '0')) AS account_id,
  DATE_ADD('2024-01-31', INTERVAL CAST(FLOOR(n / 50000.0) AS INT64) MONTH) AS snapshot_date,
  ROUND(500 + RAND() * 100000, 2) AS balance,
  ROUND(-1000 + RAND() * 5000, 2) AS mtd_interest_earned,
  CAST(FLOOR(RAND() * 50) AS INT64) AS transaction_count
FROM UNNEST(GENERATE_ARRAY(1, 200000)) AS n
