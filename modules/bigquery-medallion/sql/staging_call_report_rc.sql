CREATE OR REPLACE TABLE `${project_id}.fsi_staging.staging_call_report_rc` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 20.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('RC-', CASE MOD(n, 20) WHEN 0 THEN 'B1' WHEN 1 THEN 'B2' WHEN 2 THEN 'B3' WHEN 3 THEN 'C1' WHEN 4 THEN 'C2' WHEN 5 THEN 'C3' WHEN 6 THEN 'E1' WHEN 7 THEN 'E2' WHEN 8 THEN 'E3' WHEN 9 THEN '6' WHEN 10 THEN '11' WHEN 11 THEN '12' WHEN 12 THEN '14' WHEN 13 THEN '16' WHEN 14 THEN '20' WHEN 15 THEN '23' WHEN 16 THEN '26' WHEN 17 THEN '27' WHEN 18 THEN '28' ELSE '29' END) AS schedule_line,
  CONCAT('Schedule RC - ', CASE MOD(n, 20) WHEN 0 THEN 'Cash and Balances Due' WHEN 1 THEN 'Securities HTM' WHEN 2 THEN 'Securities AFS' WHEN 3 THEN 'Fed Funds Sold' WHEN 4 THEN 'Loans and Leases' WHEN 5 THEN 'ALLL' WHEN 6 THEN 'Premises' WHEN 7 THEN 'Other RE Owned' WHEN 8 THEN 'Intangible Assets' WHEN 9 THEN 'Other Assets' WHEN 10 THEN 'Total Assets' WHEN 11 THEN 'Deposits - Domestic' WHEN 12 THEN 'Fed Funds Purchased' WHEN 13 THEN 'Other Borrowed Money' WHEN 14 THEN 'Other Liabilities' WHEN 15 THEN 'Total Liabilities' WHEN 16 THEN 'Common Stock' WHEN 17 THEN 'Surplus' WHEN 18 THEN 'Retained Earnings' ELSE 'Total Equity' END) AS line_description,
  ROUND(1000000 + RAND() * 50000000000, 0) AS amount,
  'Filed' AS status,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 100)) AS n
