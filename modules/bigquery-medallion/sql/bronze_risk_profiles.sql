CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_risk_profiles` AS
SELECT
  CONCAT('RP-', LPAD(CAST(n AS STRING), 7, '0')) AS risk_profile_id,
  CONCAT('WMC-', LPAD(CAST(n AS STRING), 7, '0')) AS wm_client_id,
  CASE MOD(n, 6)
    WHEN 0 THEN 'Conservative' WHEN 1 THEN 'Moderate Conservative' WHEN 2 THEN 'Moderate'
    WHEN 3 THEN 'Moderate Aggressive' WHEN 4 THEN 'Aggressive' ELSE 'Moderate'
  END AS risk_tolerance,
  CAST(FLOOR(1 + RAND() * 30) AS INT64) AS time_horizon_years,
  ROUND(CASE MOD(n, 6) WHEN 0 THEN 10000 + RAND() * 50000 WHEN 4 THEN 100000 + RAND() * 500000 ELSE 30000 + RAND() * 200000 END, 0) AS annual_income,
  ROUND(CASE MOD(n, 6) WHEN 0 THEN 100000 + RAND() * 500000 WHEN 4 THEN 1000000 + RAND() * 10000000 ELSE 200000 + RAND() * 2000000 END, 0) AS net_worth,
  ROUND(CASE MOD(n, 6) WHEN 0 THEN 50000 + RAND() * 200000 WHEN 4 THEN 500000 + RAND() * 5000000 ELSE 100000 + RAND() * 1000000 END, 0) AS liquid_net_worth,
  CASE MOD(n, 5) WHEN 0 THEN 'Limited' WHEN 1 THEN 'Moderate' WHEN 2 THEN 'Extensive' WHEN 3 THEN 'Sophisticated' ELSE 'Moderate' END AS investment_experience,
  CASE MOD(n, 4) WHEN 0 THEN 'Low' WHEN 1 THEN 'Moderate' WHEN 2 THEN 'High' ELSE 'Moderate' END AS loss_tolerance,
  DATE_ADD('2022-01-01', INTERVAL CAST(FLOOR(RAND() * 1200) AS INT64) DAY) AS assessment_date,
  DATE_ADD('2025-06-01', INTERVAL CAST(FLOOR(RAND() * 365) AS INT64) DAY) AS next_review_date,
  CONCAT('ADV-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS assessed_by,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
