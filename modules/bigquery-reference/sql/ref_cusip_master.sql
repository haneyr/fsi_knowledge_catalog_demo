CREATE OR REPLACE TABLE `${project_id}.fsi_reference.ref_cusip_master` AS
SELECT
  CONCAT(LPAD(CAST(MOD(n * 7, 1000000000) AS STRING), 9, '0')) AS cusip,
  CONCAT('Security-', CAST(n AS STRING)) AS issuer_name,
  CASE MOD(n, 5) WHEN 0 THEN 'Equity' WHEN 1 THEN 'Corporate Bond' WHEN 2 THEN 'Treasury' WHEN 3 THEN 'Municipal' ELSE 'ETF' END AS security_type,
  CASE MOD(n, 5) WHEN 0 THEN 'US' WHEN 1 THEN 'US' WHEN 2 THEN 'US' WHEN 3 THEN 'US' ELSE 'US' END AS country,
  'Active' AS status
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
