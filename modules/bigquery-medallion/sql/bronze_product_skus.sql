CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_product_skus` AS
SELECT
  CONCAT('SEC-', LPAD(CAST(n AS STRING), 6, '0')) AS security_id,
  UPPER(CONCAT(
    CASE MOD(n, 8) WHEN 0 THEN 'APP' WHEN 1 THEN 'ACC' WHEN 2 THEN 'HOM' WHEN 3 THEN 'ESS' WHEN 4 THEN 'OUT' WHEN 5 THEN 'BND' WHEN 6 THEN 'SEA' ELSE 'BTY' END,
    '-',
    LPAD(CAST(MOD(n, 999) + 1 AS STRING), 3, '0')
  )) AS ticker,
  CONCAT(
    CASE MOD(n, 8)
      WHEN 0 THEN 'Northwind Merino Knit ' WHEN 1 THEN 'Artisan Leather Tote ' WHEN 2 THEN 'Cast-Iron Dutch Oven '
      WHEN 3 THEN 'Organic Cotton Tee ' WHEN 4 THEN 'Trailhead Waterproof Shell ' WHEN 5 THEN 'Everyday Travel Pack '
      WHEN 6 THEN 'Holiday Cashmere Throw ' ELSE 'Botanical Facial Serum '
    END,
    CAST(n AS STRING)
  ) AS security_name,
  CASE
    WHEN MOD(n, 67) = 0 THEN CONCAT('BAD-GTIN-', CAST(MOD(n, 999) AS STRING))
    ELSE CONCAT('0085', LPAD(CAST(MOD(n * 7, 1000000000) AS STRING), 9, '0'))
  END AS gtin_13,
  CONCAT('NW-SKU-', LPAD(CAST(n AS STRING), 6, '0')) AS sku_code,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Apparel & Footwear' WHEN 1 THEN 'Accessories & Jewelry' WHEN 2 THEN 'Home & Living'
    WHEN 3 THEN 'Core Essentials' WHEN 4 THEN 'Outdoor & Activewear' WHEN 5 THEN 'Essentials Bundle'
    WHEN 6 THEN 'Seasonal & Gifting' ELSE 'Beauty & Personal Care'
  END AS security_type,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Apparel & Outerwear' WHEN 1 THEN 'Accessories & Jewelry' WHEN 2 THEN 'Home & Kitchen'
    WHEN 3 THEN 'Everyday Essentials' WHEN 4 THEN 'Outdoor & Activewear' WHEN 5 THEN 'Footwear'
    WHEN 6 THEN 'Seasonal & Promotional' ELSE 'Beauty & Personal Care'
  END AS asset_class,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Womens & Mens Apparel' WHEN 1 THEN 'Fashion Accessories' WHEN 2 THEN 'Culinary & Tabletop'
    WHEN 3 THEN 'Private Label Basics' WHEN 4 THEN 'Outdoor Recreation' WHEN 5 THEN 'Athletic Footwear'
    WHEN 6 THEN 'Seasonal Gifting' ELSE 'Clean Beauty & Skincare'
  END AS sector,
  CASE MOD(n, 5) WHEN 0 THEN 'US' WHEN 1 THEN 'US' WHEN 2 THEN 'VN' WHEN 3 THEN 'IT' ELSE 'PT' END AS country,
  'USD' AS currency,
  CASE MOD(n, 6) WHEN 0 THEN 'DIRECT_BRAND' WHEN 1 THEN 'PRIVATE_LABEL' WHEN 2 THEN 'WHOLESALE_DIST' WHEN 3 THEN 'EXCLUSIVE_COLLAB' WHEN 4 THEN 'MARKETPLACE_CURATED' ELSE 'DIRECT_BRAND' END AS exchange,
  ROUND(12.0 + RAND() * 340.0, 2) AS last_price,
  ROUND(0.32 + RAND() * 0.35, 2) AS dividend_yield,
  CASE WHEN MOD(n, 4) = 0 THEN ROUND(0.10 + RAND() * 0.25, 4) ELSE NULL END AS coupon_rate,
  DATE_ADD(CURRENT_DATE(), INTERVAL CAST(FLOOR(RAND() * 365) + 30 AS INT64) DAY) AS maturity_date,
  CASE MOD(n, 4) WHEN 0 THEN 'Tier-1 Certified' WHEN 1 THEN 'Preferred Vendor' WHEN 2 THEN 'Standard Supplier' ELSE 'Probationary' END AS credit_rating,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
