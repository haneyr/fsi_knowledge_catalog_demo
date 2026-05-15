CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_risk_exposures` AS
SELECT
  CONCAT('REXP-', LPAD(CAST(n AS STRING), 8, '0')) AS exposure_id,
  CASE MOD(n, 4) WHEN 0 THEN 'Credit' WHEN 1 THEN 'Market' WHEN 2 THEN 'Operational' ELSE 'Liquidity' END AS risk_type,
  CASE MOD(n, 10)
    WHEN 0 THEN 'Commercial Real Estate' WHEN 1 THEN 'C&I Loans' WHEN 2 THEN 'Consumer Mortgage'
    WHEN 3 THEN 'Interest Rate' WHEN 4 THEN 'Equity' WHEN 5 THEN 'FX'
    WHEN 6 THEN 'Technology Failure' WHEN 7 THEN 'Fraud' WHEN 8 THEN 'Funding'
    ELSE 'Regulatory'
  END AS risk_subcategory,
  CONCAT('CPT-', LPAD(CAST(CAST(FLOOR(RAND() * 5000) + 1 AS INT64) AS STRING), 6, '0')) AS counterparty_id,
  ROUND(100000 + RAND() * 50000000, 2) AS gross_exposure,
  ROUND(50000 + RAND() * 40000000, 2) AS net_exposure,
  ROUND(RAND() * 10000000, 2) AS collateral_value,
  ROUND(0.001 + RAND() * 0.05, 4) AS probability_of_default,
  ROUND(0.1 + RAND() * 0.9, 2) AS loss_given_default,
  ROUND(100000 + RAND() * 5000000, 2) AS expected_loss,
  CASE MOD(n, 11) WHEN 0 THEN 'Technology' WHEN 1 THEN 'Healthcare' WHEN 2 THEN 'Real Estate' WHEN 3 THEN 'Energy' WHEN 4 THEN 'Manufacturing' WHEN 5 THEN 'Retail' WHEN 6 THEN 'Financial Services' WHEN 7 THEN 'Government' WHEN 8 THEN 'Agriculture' WHEN 9 THEN 'Transportation' ELSE 'Utilities' END AS industry_sector,
  CASE MOD(n, 5) WHEN 0 THEN 'US' WHEN 1 THEN 'US' WHEN 2 THEN 'GB' WHEN 3 THEN 'DE' ELSE 'JP' END AS country,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 500) AS INT64) DAY) AS as_of_date,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ARGUS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
