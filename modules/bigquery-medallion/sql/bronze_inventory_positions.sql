CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_inventory_positions` AS
SELECT
  CONCAT('HLD-', LPAD(CAST(n AS STRING), 9, '0')) AS holding_id,
  CONCAT('PORT-', LPAD(CAST(CAST(MOD(n, 15000) + 1 AS INT64) AS STRING), 8, '0')) AS assortment_id,
  CONCAT('SEC-', LPAD(CAST(CAST(MOD(n * 7, 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  ROUND(10 + MOD(n * 17, 440), 0) AS quantity,
  ROUND(14 + MOD(n * 23, 250), 2) AS market_price,
  ROUND((10 + MOD(n * 17, 440)) * (12 + MOD(n * 13, 85)) * (2.6 + MOD(n, 15) * 0.12), 2) AS current_retail_value,
  ROUND((10 + MOD(n * 17, 440)) * (12 + MOD(n * 13, 85)), 2) AS inventory_at_cost,
  ROUND((10 + MOD(n * 17, 440)) * (12 + MOD(n * 13, 85)) * (0.35 + MOD(n, 10) * 0.06), 2) AS markdown_exposure,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Apparel & Outerwear' WHEN 1 THEN 'Footwear' WHEN 2 THEN 'Home & Kitchen'
    WHEN 3 THEN 'Consumer Electronics' WHEN 4 THEN 'Outdoor & Activewear' WHEN 5 THEN 'Home Furnishings'
    WHEN 6 THEN 'Accessories & Jewelry' ELSE 'Beauty & Personal Care'
  END AS asset_class,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Womens & Mens Apparel' WHEN 1 THEN 'Athletic Footwear' WHEN 2 THEN 'Culinary & Tabletop'
    WHEN 3 THEN 'Smart Home & Audio' WHEN 4 THEN 'Outdoor Recreation' WHEN 5 THEN 'Living & Bedroom'
    WHEN 6 THEN 'Fashion Accessories' ELSE 'Clean Beauty & Skincare'
  END AS sector,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(MOD(n, 90) AS INT64) DAY) AS as_of_date,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(MOD(n * 31, 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
