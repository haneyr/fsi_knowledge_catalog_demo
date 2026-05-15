CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_cost_centers` AS
SELECT
  CONCAT('CC-', LPAD(CAST(n AS STRING), 4, '0')) AS cost_center_id,
  CASE MOD(n, 20)
    WHEN 0 THEN 'Retail Banking Ops' WHEN 1 THEN 'Lending Operations' WHEN 2 THEN 'Wealth Management'
    WHEN 3 THEN 'Treasury' WHEN 4 THEN 'Risk Management' WHEN 5 THEN 'Compliance'
    WHEN 6 THEN 'Internal Audit' WHEN 7 THEN 'Legal' WHEN 8 THEN 'Technology'
    WHEN 9 THEN 'Human Resources' WHEN 10 THEN 'Marketing' WHEN 11 THEN 'Finance'
    WHEN 12 THEN 'Credit Administration' WHEN 13 THEN 'Card Services' WHEN 14 THEN 'Mortgage'
    WHEN 15 THEN 'Commercial Banking' WHEN 16 THEN 'Trust Services' WHEN 17 THEN 'Private Banking'
    WHEN 18 THEN 'Insurance' ELSE 'Corporate'
  END AS cost_center_name,
  CASE MOD(n, 5)
    WHEN 0 THEN 'Revenue' WHEN 1 THEN 'Support' WHEN 2 THEN 'Revenue'
    WHEN 3 THEN 'Corporate' ELSE 'Support'
  END AS center_type,
  CASE MOD(n, 5)
    WHEN 0 THEN 'Retail Banking' WHEN 1 THEN 'Wealth Management' WHEN 2 THEN 'Commercial Banking'
    WHEN 3 THEN 'Risk & Compliance' ELSE 'Corporate Services'
  END AS division,
  CONCAT('VP-', LPAD(CAST(MOD(n, 50) + 1 AS STRING), 3, '0')) AS manager_id,
  ROUND(100000 + RAND() * 5000000, 0) AS annual_budget,
  CASE MOD(n, 4) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' ELSE CASE WHEN MOD(n, 30) = 0 THEN 'Closed' ELSE 'Active' END END AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ARGUS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 500)) AS n
