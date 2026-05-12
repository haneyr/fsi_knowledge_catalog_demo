CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_wire_transfers` AS
SELECT
  CONCAT('WIRE-', LPAD(CAST(n AS STRING), 10, '0')) AS wire_id,
  CONCAT('ACCT-', LPAD(CAST(CAST(FLOOR(RAND() * 50000) + 1 AS INT64) AS STRING), 10, '0')) AS originator_account_id,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS originator_customer_id,
  CONCAT('BNF-', LPAD(CAST(n AS STRING), 10, '0')) AS beneficiary_name,
  CONCAT('0', CAST(10000000 + MOD(n * 31, 90000000) AS STRING)) AS beneficiary_routing,
  CONCAT(CAST(1000000 + MOD(n * 17, 9000000) AS STRING)) AS beneficiary_account,
  ROUND(500 + RAND() * 99500, 2) AS amount,
  CASE MOD(n, 3) WHEN 0 THEN 'USD' WHEN 1 THEN 'EUR' ELSE 'USD' END AS currency,
  CASE MOD(n, 3) WHEN 0 THEN 'Domestic' WHEN 1 THEN 'International' ELSE 'Domestic' END AS wire_type,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS initiation_date,
  CASE MOD(n, 4) WHEN 0 THEN 'Completed' WHEN 1 THEN 'Completed' WHEN 2 THEN 'Pending' ELSE 'Completed' END AS status,
  CASE WHEN MOD(n, 20) = 0 THEN TRUE ELSE FALSE END AS ofac_hold,
  CASE WHEN MOD(n, 10) = 0 THEN TRUE ELSE FALSE END AS requires_ctr,
  CASE WHEN amount > 10000 THEN TRUE ELSE FALSE END AS above_ctr_threshold,
  CONCAT('Purpose: ', CASE MOD(n, 5) WHEN 0 THEN 'Invoice Payment' WHEN 1 THEN 'Real Estate' WHEN 2 THEN 'Personal Transfer' WHEN 3 THEN 'Business Payment' ELSE 'Other' END) AS purpose,
  CASE MOD(n, 8) WHEN 0 THEN 'US' WHEN 1 THEN 'GB' WHEN 2 THEN 'DE' WHEN 3 THEN 'CH' WHEN 4 THEN 'JP' WHEN 5 THEN 'CA' WHEN 6 THEN 'AU' ELSE 'US' END AS beneficiary_country,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ATLAS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
