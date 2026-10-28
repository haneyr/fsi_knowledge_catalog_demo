CREATE OR REPLACE TABLE `${project_id}.retail_reference.ref_gtin_master` AS
SELECT
  CONCAT(CONCAT('0085', LPAD(CAST(MOD(n * 7, 1000000000) AS STRING), 9, '0'))) AS gtin_13,
  CONCAT('Security-', CAST(n AS STRING)) AS issuer_name,
  CASE MOD(n, 5) WHEN 0 THEN 'Softlines' WHEN 1 THEN 'Home & Living' WHEN 2 THEN 'Core Essentials' WHEN 3 THEN 'Outdoor & Activewear' ELSE 'Essentials Bundle' END AS security_type,
  CASE MOD(n, 5) WHEN 0 THEN 'US' WHEN 1 THEN 'US' WHEN 2 THEN 'US' WHEN 3 THEN 'US' ELSE 'US' END AS country,
  'Active' AS status
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
