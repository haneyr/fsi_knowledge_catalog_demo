CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_regulatory_capital` AS
SELECT
  CONCAT('RCAP-', LPAD(CAST(n AS STRING), 5, '0')) AS capital_id,
  DATE_ADD('2022-01-01', INTERVAL CAST(FLOOR(n / 4.0) AS INT64) * 3 MONTH) AS reporting_date,
  CASE MOD(n, 4) WHEN 0 THEN 'CET1' WHEN 1 THEN 'Additional Tier 1' WHEN 2 THEN 'Tier 2' ELSE 'Total Capital' END AS capital_component,
  ROUND(CASE MOD(n, 4)
    WHEN 0 THEN 5000000000 + RAND() * 2000000000
    WHEN 1 THEN 500000000 + RAND() * 500000000
    WHEN 2 THEN 1000000000 + RAND() * 1000000000
    ELSE 6500000000 + RAND() * 3500000000
  END, 0) AS capital_amount,
  ROUND(30000000000 + RAND() * 20000000000, 0) AS risk_weighted_assets,
  ROUND(CASE MOD(n, 4) WHEN 0 THEN 0.10 + RAND() * 0.05 WHEN 1 THEN 0.012 + RAND() * 0.008 WHEN 2 THEN 0.03 + RAND() * 0.02 ELSE 0.14 + RAND() * 0.04 END, 4) AS capital_ratio,
  ROUND(CASE MOD(n, 4) WHEN 0 THEN 0.045 WHEN 1 THEN 0.06 WHEN 2 THEN 0.08 ELSE 0.105 END, 4) AS regulatory_minimum,
  ROUND(0.025, 4) AS capital_conservation_buffer,
  ROUND(CASE WHEN MOD(n, 10) = 0 THEN 0.01 ELSE 0.0 END, 4) AS countercyclical_buffer,
  CASE WHEN MOD(n, 4) = 0 THEN ROUND(40000000000 + RAND() * 10000000000, 0) ELSE NULL END AS leverage_exposure,
  CASE WHEN MOD(n, 4) = 0 THEN ROUND(0.07 + RAND() * 0.03, 4) ELSE NULL END AS leverage_ratio,
  CASE MOD(n, 3) WHEN 0 THEN 'Standardized' WHEN 1 THEN 'Advanced' ELSE 'Standardized' END AS calculation_approach,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ARGUS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 1000)) AS n
