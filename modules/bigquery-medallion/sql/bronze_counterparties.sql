CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_counterparties` AS
SELECT
  CONCAT('CPT-', LPAD(CAST(n AS STRING), 6, '0')) AS counterparty_id,
  CONCAT('Counterparty ', CAST(n AS STRING)) AS counterparty_name,
  CASE MOD(n, 6)
    WHEN 0 THEN 'Corporate' WHEN 1 THEN 'Financial Institution' WHEN 2 THEN 'Government'
    WHEN 3 THEN 'Sovereign' WHEN 4 THEN 'SME' ELSE 'Individual'
  END AS counterparty_type,
  CONCAT('LEI-', LPAD(CAST(MOD(n * 31, 999999999) AS STRING), 9, '0'), LPAD(CAST(MOD(n * 17, 999999999) AS STRING), 9, '0'), CAST(MOD(n, 10) AS STRING), '0') AS lei,
  CASE MOD(n, 5) WHEN 0 THEN 'US' WHEN 1 THEN 'GB' WHEN 2 THEN 'DE' WHEN 3 THEN 'JP' ELSE 'CA' END AS country,
  CASE MOD(n, 11) WHEN 0 THEN 'Technology' WHEN 1 THEN 'Healthcare' WHEN 2 THEN 'Real Estate' WHEN 3 THEN 'Energy' WHEN 4 THEN 'Manufacturing' WHEN 5 THEN 'Retail' WHEN 6 THEN 'Financial Services' WHEN 7 THEN 'Government' WHEN 8 THEN 'Agriculture' WHEN 9 THEN 'Transportation' ELSE 'Utilities' END AS industry,
  CASE MOD(n, 7) WHEN 0 THEN 'AAA' WHEN 1 THEN 'AA' WHEN 2 THEN 'A' WHEN 3 THEN 'BBB' WHEN 4 THEN 'BB' WHEN 5 THEN 'B' ELSE 'NR' END AS internal_rating,
  CASE MOD(n, 5) WHEN 0 THEN 'Aaa' WHEN 1 THEN 'Aa1' WHEN 2 THEN 'A1' WHEN 3 THEN 'Baa1' ELSE 'NR' END AS external_rating_moodys,
  ROUND(0 + RAND() * 100000000, 2) AS total_exposure,
  ROUND(0 + RAND() * 50000000, 2) AS credit_limit,
  CASE MOD(n, 4) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' ELSE 'Watchlist' END AS status,
  DATE_ADD('2022-01-01', INTERVAL CAST(FLOOR(RAND() * 1200) AS INT64) DAY) AS last_review_date,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ARGUS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
