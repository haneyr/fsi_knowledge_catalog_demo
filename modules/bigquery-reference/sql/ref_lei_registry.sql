CREATE OR REPLACE TABLE `${project_id}.fsi_reference.ref_lei_registry` AS
SELECT
  CONCAT('LEI-', LPAD(CAST(n AS STRING), 20, '0')) AS lei,
  CONCAT('Entity-', CAST(n AS STRING)) AS legal_name,
  CASE MOD(n, 5) WHEN 0 THEN 'US' WHEN 1 THEN 'GB' WHEN 2 THEN 'DE' WHEN 3 THEN 'JP' ELSE 'CA' END AS jurisdiction,
  CASE MOD(n, 4) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' ELSE 'Lapsed' END AS status,
  DATE_ADD('2020-01-01', INTERVAL CAST(FLOOR(RAND() * 2000) AS INT64) DAY) AS registration_date
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
