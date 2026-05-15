CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_wm_clients` AS
SELECT
  CONCAT('WMC-', LPAD(CAST(n AS STRING), 7, '0')) AS wm_client_id,
  CASE WHEN MOD(n, 3) = 0 THEN CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) ELSE NULL END AS retail_customer_id,
  CASE MOD(n, 20)
    WHEN 0 THEN 'James' WHEN 1 THEN 'Margaret' WHEN 2 THEN 'William' WHEN 3 THEN 'Catherine'
    WHEN 4 THEN 'Charles' WHEN 5 THEN 'Elizabeth' WHEN 6 THEN 'Richard' WHEN 7 THEN 'Victoria'
    WHEN 8 THEN 'Edward' WHEN 9 THEN 'Alexandra' WHEN 10 THEN 'Henry' WHEN 11 THEN 'Caroline'
    WHEN 12 THEN 'George' WHEN 13 THEN 'Eleanor' WHEN 14 THEN 'Frederick' WHEN 15 THEN 'Sophia'
    WHEN 16 THEN 'Arthur' WHEN 17 THEN 'Josephine' WHEN 18 THEN 'Theodore' ELSE 'Beatrice'
  END AS first_name,
  CASE MOD(n, 10) WHEN 0 THEN 'Rockefeller' WHEN 1 THEN 'Morgan' WHEN 2 THEN 'Vanderbilt' WHEN 3 THEN 'Carnegie' WHEN 4 THEN 'DuPont' WHEN 5 THEN 'Astor' WHEN 6 THEN 'Whitney' WHEN 7 THEN 'Mellon' WHEN 8 THEN 'Lehman' ELSE 'Goldman' END AS last_name,
  CASE MOD(n, 5)
    WHEN 0 THEN 'HNW' WHEN 1 THEN 'UHNW' WHEN 2 THEN 'HNW' WHEN 3 THEN 'Affluent' ELSE 'HNW'
  END AS client_tier,
  ROUND(CASE MOD(n, 5)
    WHEN 0 THEN 1000000 + RAND() * 9000000
    WHEN 1 THEN 10000000 + RAND() * 90000000
    WHEN 2 THEN 500000 + RAND() * 4500000
    WHEN 3 THEN 250000 + RAND() * 750000
    ELSE 1000000 + RAND() * 5000000
  END, 2) AS total_aum,
  CASE MOD(n, 6)
    WHEN 0 THEN 'Conservative' WHEN 1 THEN 'Moderate Conservative' WHEN 2 THEN 'Moderate'
    WHEN 3 THEN 'Moderate Aggressive' WHEN 4 THEN 'Aggressive' ELSE 'Moderate'
  END AS risk_tolerance,
  CASE MOD(n, 5)
    WHEN 0 THEN 'Growth' WHEN 1 THEN 'Income' WHEN 2 THEN 'Balanced'
    WHEN 3 THEN 'Capital Preservation' ELSE 'Tax Efficient'
  END AS investment_objective,
  CONCAT('ADV-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS primary_advisor_id,
  DATE_ADD('2005-01-01', INTERVAL CAST(FLOOR(RAND() * 7000) AS INT64) DAY) AS relationship_start_date,
  CASE MOD(n, 4) WHEN 0 THEN 'Individual' WHEN 1 THEN 'Joint' WHEN 2 THEN 'Trust' ELSE 'Entity' END AS account_type,
  CASE MOD(n, 3)
    WHEN 0 THEN 'Discretionary' WHEN 1 THEN 'Non-Discretionary' ELSE 'Advisory'
  END AS management_type,
  CASE MOD(n, 6) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' WHEN 4 THEN 'Prospect' ELSE 'Inactive' END AS client_status,
  CASE WHEN MOD(n, 10) = 0 THEN TRUE ELSE FALSE END AS accredited_investor,
  CASE WHEN MOD(n, 20) = 0 THEN TRUE ELSE FALSE END AS qualified_purchaser,
  LPAD(CAST(MOD(n * 13, 900000000) AS STRING), 9, '0') AS tax_id,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
