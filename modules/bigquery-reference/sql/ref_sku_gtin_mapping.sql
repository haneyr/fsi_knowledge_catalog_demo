CREATE OR REPLACE TABLE `${project_id}.retail_reference.ref_sku_gtin_mapping` AS
SELECT
  CONCAT('NW-SKU-', LPAD(CAST(n AS STRING), 6, '0')) AS sku_code,
  CONCAT('0085', LPAD(CAST(MOD(n * 7, 1000000000) AS STRING), 9, '0')) AS gtin_13,
  'US' AS country_code,
  CASE MOD(n, 3) WHEN 0 THEN 'NYSE' WHEN 1 THEN 'NASDAQ' ELSE 'OTC' END AS exchange
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
