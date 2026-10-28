CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_working_capital` AS
SELECT
  CONCAT('RCAP-', LPAD(CAST(n AS STRING), 5, '0')) AS capital_id,
  DATE_ADD('2022-01-01', INTERVAL CAST(FLOOR(n / 4.0) AS INT64) * 3 MONTH) AS reporting_date,
  CASE MOD(n, 4) WHEN 0 THEN 'Core Working Capital' WHEN 1 THEN 'Inventory Buffer Reserve' WHEN 2 THEN 'Seasonal Liquidity Facility' ELSE 'Total Operating Capital' END AS capital_component,
  ROUND(CASE MOD(n, 4)
    WHEN 0 THEN 42000000 + RAND() * 18000000
    WHEN 1 THEN 12000000 + RAND() * 6000000
    WHEN 2 THEN 18000000 + RAND() * 9000000
    ELSE 72000000 + RAND() * 33000000
  END, 0) AS capital_amount,
  ROUND(240000000 + RAND() * 85000000, 0) AS risk_weighted_assets,
  ROUND(CASE MOD(n, 4) WHEN 0 THEN 0.16 + RAND() * 0.05 WHEN 1 THEN 0.05 + RAND() * 0.02 WHEN 2 THEN 0.08 + RAND() * 0.03 ELSE 0.28 + RAND() * 0.06 END, 4) AS capital_ratio,
  ROUND(CASE MOD(n, 4) WHEN 0 THEN 0.120 WHEN 1 THEN 0.040 WHEN 2 THEN 0.060 ELSE 0.220 END, 4) AS regulatory_minimum,
  ROUND(0.025, 4) AS capital_conservation_buffer,
  ROUND(CASE WHEN MOD(n, 10) = 0 THEN 0.015 ELSE 0.0 END, 4) AS countercyclical_buffer,
  CASE WHEN MOD(n, 4) = 0 THEN ROUND(310000000 + RAND() * 75000000, 0) ELSE NULL END AS leverage_exposure,
  CASE WHEN MOD(n, 4) = 0 THEN ROUND(0.14 + RAND() * 0.04, 4) ELSE NULL END AS leverage_ratio,
  CASE MOD(n, 3) WHEN 0 THEN 'Retail Inventory Cost Method' WHEN 1 THEN 'Omnichannel Working Capital Policy' ELSE 'Retail Inventory Cost Method' END AS calculation_approach,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'HELIOS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 1000)) AS n
