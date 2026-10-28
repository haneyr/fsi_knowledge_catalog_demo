CREATE OR REPLACE TABLE `${project_id}.retail_snapshots.snapshot_monthly_loyalty_balances` AS
SELECT
  CONCAT('ACCT-', LPAD(CAST(CAST(MOD(n, 50000) + 1 AS INT64) AS STRING), 10, '0')) AS account_id,
  DATE_ADD('2024-01-31', INTERVAL CAST(FLOOR(n / 50000.0) AS INT64) MONTH) AS snapshot_date,
  ROUND(20 + RAND() * 420, 2) AS balance,
  ROUND(2 + RAND() * 35, 2) AS mtd_interest_earned,
  CAST(FLOOR(1 + RAND() * 14) AS INT64) AS transaction_count
FROM UNNEST(GENERATE_ARRAY(1, 200000)) AS n
