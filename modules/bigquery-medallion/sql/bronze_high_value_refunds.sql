CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_high_value_refunds` AS
SELECT
  CONCAT('WIRE-', LPAD(CAST(n AS STRING), 10, '0')) AS wire_id,
  CONCAT('ACCT-', LPAD(CAST(CAST(FLOOR(RAND() * 50000) + 1 AS INT64) AS STRING), 10, '0')) AS originator_account_id,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS originator_customer_id,
  CONCAT('SHOPPER-', LPAD(CAST(n AS STRING), 8, '0')) AS beneficiary_name,
  CONCAT('0', CAST(10000000 + MOD(n * 31, 90000000) AS STRING)) AS beneficiary_routing,
  CONCAT(CAST(1000000 + MOD(n * 17, 9000000) AS STRING)) AS beneficiary_account,
  ROUND(45 + RAND() * 1450, 2) AS amount,
  CASE MOD(n, 3) WHEN 0 THEN 'USD' WHEN 1 THEN 'CAD' ELSE 'USD' END AS currency,
  CASE MOD(n, 3) WHEN 0 THEN 'In-Store POS Refund' WHEN 1 THEN 'Omnichannel Mail Return' ELSE 'E-Commerce Original Tender' END AS wire_type,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS initiation_date,
  CASE MOD(n, 4) WHEN 0 THEN 'Completed' WHEN 1 THEN 'Completed' WHEN 2 THEN 'Pending Manager Override' ELSE 'Completed' END AS status,
  CASE WHEN MOD(n, 20) = 0 THEN TRUE ELSE FALSE END AS ofac_hold,
  CASE WHEN MOD(n, 10) = 0 THEN TRUE ELSE FALSE END AS requires_ctr,
  CASE WHEN MOD(n, 25) = 0 THEN TRUE ELSE FALSE END AS above_ctr_threshold,
  CONCAT('Return Reason: ', CASE MOD(n, 5) WHEN 0 THEN 'Defective Apparel Item' WHEN 1 THEN 'Damaged Home Furnishings' WHEN 2 THEN 'Size / Fit Exchange' WHEN 3 THEN 'Unopened Electronics Return' ELSE 'Order Cancelled in Transit' END) AS purpose,
  CASE MOD(n, 8) WHEN 0 THEN 'US' WHEN 1 THEN 'CA' WHEN 2 THEN 'US' WHEN 3 THEN 'US' WHEN 4 THEN 'GB' WHEN 5 THEN 'CA' WHEN 6 THEN 'US' ELSE 'US' END AS beneficiary_country,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
