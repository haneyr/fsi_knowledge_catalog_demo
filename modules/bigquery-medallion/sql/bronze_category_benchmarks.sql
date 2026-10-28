CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_category_benchmarks` AS
SELECT
  CONCAT('BM-', LPAD(CAST(MOD(n, 10) + 1 AS STRING), 3, '0')) AS benchmark_id,
  CASE MOD(n, 10)
    WHEN 0 THEN 'NRF Apparel & Outerwear Index' WHEN 1 THEN 'US Specialty Footwear Benchmark' WHEN 2 THEN 'Omnichannel Home & Kitchen Index'
    WHEN 3 THEN 'Consumer Electronics Margin Index' WHEN 4 THEN 'Prestige Beauty & Skincare Index' WHEN 5 THEN 'Outdoor & Athletic Retail Index'
    WHEN 6 THEN 'North America Department Store Avg' WHEN 7 THEN 'Private Label Essentials Benchmark' WHEN 8 THEN 'Holiday Gifting & Seasonal Index'
    ELSE 'Accessories & Fine Jewelry Index'
  END AS benchmark_name,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) DAY) AS as_of_date,
  ROUND(-0.02 + RAND() * 0.05, 6) AS daily_return,
  ROUND(-0.04 + RAND() * 0.12, 4) AS mtd_return,
  ROUND(0.05 + RAND() * 0.38, 4) AS ytd_return,
  ROUND(100 + RAND() * 180, 2) AS index_level,
  ROUND(0.04 + RAND() * 0.18, 4) AS annualized_volatility,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 7000)) AS n
