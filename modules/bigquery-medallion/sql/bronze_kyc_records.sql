CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_kyc_records` AS
SELECT
  CONCAT('KYC-', LPAD(CAST(n AS STRING), 8, '0')) AS kyc_id,
  CONCAT('CUST-', LPAD(CAST(n AS STRING), 8, '0')) AS customer_id,
  CASE MOD(n, 3) WHEN 0 THEN 'CDD' WHEN 1 THEN 'EDD' ELSE 'SDD' END AS due_diligence_level,
  CASE MOD(n, 4) WHEN 0 THEN 'Completed' WHEN 1 THEN 'Completed' WHEN 2 THEN 'In Progress' ELSE 'Expired' END AS verification_status,
  DATE_ADD('2022-01-01', INTERVAL CAST(FLOOR(RAND() * 1200) AS INT64) DAY) AS last_review_date,
  DATE_ADD('2025-01-01', INTERVAL CAST(FLOOR(RAND() * 700) AS INT64) DAY) AS next_review_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Low' WHEN 1 THEN 'Medium' WHEN 2 THEN 'Medium' WHEN 3 THEN 'High' ELSE 'Low' END AS risk_score_category,
  CAST(FLOOR(RAND() * 100) AS INT64) AS risk_score,
  CASE WHEN MOD(n, 50) = 0 THEN TRUE ELSE FALSE END AS pep_flag,
  CASE WHEN MOD(n, 100) = 0 THEN TRUE ELSE FALSE END AS sanctions_flag,
  CASE WHEN MOD(n, 200) = 0 THEN TRUE ELSE FALSE END AS adverse_media_flag,
  CASE MOD(n, 4)
    WHEN 0 THEN 'Drivers License' WHEN 1 THEN 'Passport' WHEN 2 THEN 'State ID' ELSE 'Military ID'
  END AS id_document_type,
  CASE MOD(n, 3) WHEN 0 THEN 'US' WHEN 1 THEN 'US' ELSE CASE MOD(n, 10) WHEN 0 THEN 'GB' WHEN 1 THEN 'CA' WHEN 2 THEN 'MX' ELSE 'US' END END AS country_of_citizenship,
  CASE WHEN MOD(n, 30) = 0 THEN CONCAT('BO-', LPAD(CAST(n AS STRING), 8, '0')) ELSE NULL END AS beneficial_owner_id,
  CONCAT('ANL-', LPAD(CAST(MOD(n, 50) + 1 AS STRING), 3, '0')) AS reviewer_id,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ATLAS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 20000)) AS n
