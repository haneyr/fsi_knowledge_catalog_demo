CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_merch_assortments` AS
SELECT
  CONCAT('PORT-', LPAD(CAST(n AS STRING), 8, '0')) AS assortment_id,
  CONCAT('WMC-', LPAD(CAST(CAST(FLOOR(n / 2.0) + 1 AS INT64) AS STRING), 7, '0')) AS wm_client_id,
  assortment_name,
  CASE MOD(n, 7)
    WHEN 0 THEN 'FLAGSHIP_STORE' WHEN 1 THEN 'OMNICHANNEL' WHEN 2 THEN 'ECOMMERCE_ONLY' WHEN 3 THEN 'OUTLET'
    WHEN 4 THEN 'MARKETPLACE' WHEN 5 THEN 'POP_UP' ELSE 'VIP_CLIENTELING'
  END AS account_type,
  CASE MOD(n, 4) WHEN 0 THEN 'Standard Sales Tax' WHEN 1 THEN 'Apparel Tax-Exempt' WHEN 2 THEN 'Back-to-School Holiday' ELSE 'Standard Sales Tax' END AS tax_status,
  ROUND(inv_cost * (1.0 + target_gmroi), 2) AS current_retail_value,
  inv_cost AS inventory_at_cost,
  ROUND(0.08 + MOD(n * 31, 35) * 0.01, 4) AS ytd_return,
  ROUND(0.12 + MOD(n * 37, 38) * 0.01, 4) AS inception_return,
  CONCAT('BM-', LPAD(CAST(MOD(n, 10) + 1 AS STRING), 3, '0')) AS benchmark_id,
  CONCAT('ADV-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS advisor_id,
  CONCAT('MDL-', LPAD(CAST(MOD(n, 20) + 1 AS STRING), 3, '0')) AS template_assortment_id,
  DATE_ADD('2018-01-01', INTERVAL CAST(MOD(n * 19, 2500) AS INT64) DAY) AS inception_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' ELSE 'Closed' END AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(MOD(n * 41, 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM (
  SELECT
    n,
    CASE MOD(n, 12)
      WHEN 0 THEN 'Seasonal Holiday Gifting'
      WHEN 1 THEN 'Winter Outerwear & Cold Weather'
      WHEN 2 THEN 'Spring Apparel Core'
      WHEN 3 THEN 'Back-to-School Basics'
      WHEN 4 THEN 'Summer Resort & Swimwear'
      WHEN 5 THEN 'Outdoor & Activewear'
      WHEN 6 THEN 'Home & Kitchen Essentials'
      WHEN 7 THEN 'Consumer Electronics Flagship'
      WHEN 8 THEN 'Beauty & Personal Care'
      WHEN 9 THEN 'Footwear & Accessories'
      WHEN 10 THEN 'Private Label Basics'
      ELSE 'Athletic & Performance Gear'
    END AS assortment_name,
    ROUND(CASE MOD(n, 12)
      WHEN 0 THEN 148500.00 + MOD(n * 97, 18000)
      WHEN 1 THEN 164200.00 + MOD(n * 89, 20000)
      WHEN 2 THEN 131800.00 + MOD(n * 83, 16000)
      WHEN 3 THEN 119400.00 + MOD(n * 79, 15000)
      WHEN 4 THEN 112600.00 + MOD(n * 73, 14000)
      WHEN 5 THEN 136500.00 + MOD(n * 71, 17000)
      WHEN 6 THEN 116800.00 + MOD(n * 67, 15000)
      WHEN 7 THEN 198400.00 + MOD(n * 61, 24000)
      WHEN 8 THEN 95200.00 + MOD(n * 59, 12000)
      WHEN 9 THEN 124600.00 + MOD(n * 53, 15000)
      WHEN 10 THEN 89400.00 + MOD(n * 47, 11000)
      ELSE 139200.00 + MOD(n * 43, 16000)
    END, 2) AS inv_cost,
    CASE MOD(n, 12)
      WHEN 0 THEN 2.08
      WHEN 1 THEN 2.16
      WHEN 2 THEN 2.24
      WHEN 3 THEN 2.35
      WHEN 4 THEN 2.44
      WHEN 5 THEN 2.72
      WHEN 6 THEN 2.95
      WHEN 7 THEN 3.12
      WHEN 8 THEN 3.68
      WHEN 9 THEN 3.34
      WHEN 10 THEN 3.85
      ELSE 3.48
    END AS target_gmroi
  FROM UNNEST(GENERATE_ARRAY(1, 15000)) AS n
)
