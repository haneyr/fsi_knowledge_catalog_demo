CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_client_goals` AS
SELECT
  CONCAT('GOAL-', LPAD(CAST(n AS STRING), 7, '0')) AS goal_id,
  CONCAT('WMC-', LPAD(CAST(CAST(FLOOR(RAND() * 10000) + 1 AS INT64) AS STRING), 7, '0')) AS wm_client_id,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Retirement' WHEN 1 THEN 'Education' WHEN 2 THEN 'Home Purchase'
    WHEN 3 THEN 'Legacy/Estate' WHEN 4 THEN 'Major Purchase' WHEN 5 THEN 'Emergency Fund'
    WHEN 6 THEN 'Charitable Giving' ELSE 'Business Succession'
  END AS goal_type,
  CONCAT(CASE MOD(n, 8) WHEN 0 THEN 'Retire by 65' WHEN 1 THEN 'College Fund' WHEN 2 THEN 'Down Payment' WHEN 3 THEN 'Estate Plan' WHEN 4 THEN 'Vacation Home' WHEN 5 THEN '6mo Emergency' WHEN 6 THEN 'Foundation' ELSE 'Business Exit' END) AS goal_name,
  ROUND(CASE MOD(n, 8)
    WHEN 0 THEN 2000000 + RAND() * 8000000
    WHEN 1 THEN 200000 + RAND() * 300000
    WHEN 2 THEN 100000 + RAND() * 400000
    WHEN 3 THEN 5000000 + RAND() * 20000000
    ELSE 50000 + RAND() * 1000000
  END, 0) AS target_amount,
  ROUND(CASE MOD(n, 8)
    WHEN 0 THEN 500000 + RAND() * 5000000
    WHEN 1 THEN 50000 + RAND() * 200000
    ELSE 10000 + RAND() * 500000
  END, 0) AS current_amount,
  ROUND(RAND(), 2) AS progress_pct,
  DATE_ADD('2025-01-01', INTERVAL CAST(FLOOR(RAND() * 10000) AS INT64) DAY) AS target_date,
  CASE MOD(n, 4) WHEN 0 THEN 'On Track' WHEN 1 THEN 'At Risk' WHEN 2 THEN 'On Track' ELSE 'Ahead' END AS status,
  CAST(FLOOR(1 + RAND() * 10) AS INT64) AS priority_rank,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
