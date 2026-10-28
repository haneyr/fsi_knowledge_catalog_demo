CREATE OR REPLACE TABLE `${project_id}.retail_snapshots.snapshot_daily_competitor_pricing` AS
SELECT
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(n / 100.0) AS INT64) DAY) AS snapshot_date,
  CASE MOD(n, 10)
    WHEN 0 THEN 'Apparel & Outerwear CPI' WHEN 1 THEN 'Footwear Price Index' WHEN 2 THEN 'Home & Kitchen Basket' WHEN 3 THEN 'Consumer Electronics CPI'
    WHEN 4 THEN 'Markdown Depth Avg %' WHEN 5 THEN 'BNPL Default Benchmark %' WHEN 6 THEN 'CAD/USD Retail FX'
    WHEN 7 THEN 'Omnichannel Promo Intensity' WHEN 8 THEN 'Cotton & Textile Spot' ELSE 'Parcel Freight Index'
  END AS indicator,
  ROUND(CASE MOD(n, 10)
    WHEN 0 THEN 105 + RAND() * 18 WHEN 1 THEN 112 + RAND() * 15
    WHEN 2 THEN 98 + RAND() * 22 WHEN 3 THEN 92 + RAND() * 14
    WHEN 4 THEN 18.5 + RAND() * 12.0 WHEN 5 THEN 2.4 + RAND() * 1.8
    WHEN 6 THEN 0.72 + RAND() * 0.06 WHEN 7 THEN 24 + RAND() * 18
    WHEN 8 THEN 78 + RAND() * 25 ELSE 115 + RAND() * 30
  END, 2) AS value,
  ROUND(-0.02 + RAND() * 0.04, 4) AS daily_change_pct
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
