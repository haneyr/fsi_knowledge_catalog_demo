CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_stress_tests` AS
SELECT
  CONCAT('STRESS-', LPAD(CAST(n AS STRING), 6, '0')) AS stress_test_id,
  CASE MOD(n, 4) WHEN 0 THEN 'DFAST Baseline' WHEN 1 THEN 'DFAST Adverse' WHEN 2 THEN 'DFAST Severely Adverse' ELSE 'Internal Scenario' END AS scenario_name,
  CASE MOD(n, 6)
    WHEN 0 THEN 'Credit Losses' WHEN 1 THEN 'NII Impact' WHEN 2 THEN 'Trading Losses'
    WHEN 3 THEN 'Operational Losses' WHEN 4 THEN 'Capital Impact' ELSE 'Liquidity Impact'
  END AS metric_type,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(n / 24.0) AS INT64) * 3 MONTH) AS projection_quarter,
  ROUND(-5000000000 + RAND() * 10000000000, 0) AS projected_impact,
  ROUND(0.05 + RAND() * 0.15, 4) AS projected_capital_ratio,
  ROUND(RAND() * 0.05, 4) AS projected_loss_rate,
  CASE MOD(n, 3) WHEN 0 THEN 'Pass' WHEN 1 THEN 'Pass' ELSE 'Marginal' END AS result_status,
  CONCAT('FY', CAST(2024 + CAST(FLOOR(n / 96.0) AS INT64) AS STRING)) AS reporting_year,
  CASE MOD(n, 3) WHEN 0 THEN 'Federal Reserve' WHEN 1 THEN 'OCC' ELSE 'Internal' END AS regulatory_body,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ARGUS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 2000)) AS n
