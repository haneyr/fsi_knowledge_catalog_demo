CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_markdown_rates` AS
SELECT
  CONCAT('RATE-', LPAD(CAST(n AS STRING), 8, '0')) AS rate_id,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) DAY) AS as_of_date,
  CASE MOD(n, 10)
    WHEN 0 THEN 'First Markdown — 20% Off' WHEN 1 THEN 'Second Markdown — 40% Off' WHEN 2 THEN 'Final Clearance — 65% Off'
    WHEN 3 THEN 'End-of-Season Apparel Curve' WHEN 4 THEN 'Holiday Doorbuster Promo' WHEN 5 THEN 'VIP Early Access Discount'
    WHEN 6 THEN 'Outlet Transfer Markdown' WHEN 7 THEN 'Slow-Mover 30-Day Markdown' WHEN 8 THEN 'Overstock 60-Day Markdown'
    ELSE 'Damaged Box / Open-Item Discount'
  END AS rate_name,
  CASE MOD(n, 10)
    WHEN 0 THEN '14D' WHEN 1 THEN '30D' WHEN 2 THEN '60D'
    WHEN 3 THEN '90D' WHEN 4 THEN '7D' WHEN 5 THEN '14D'
    WHEN 6 THEN '120D' WHEN 7 THEN '30D' WHEN 8 THEN '60D'
    ELSE 'Immediate'
  END AS tenor,
  ROUND(0.10 + RAND() * 0.55, 4) AS rate_value,
  ROUND(-0.02 + RAND() * 0.04, 4) AS daily_change,
  CASE MOD(n, 4)
    WHEN 0 THEN 'Northwind Pricing Engine' WHEN 1 THEN 'Merchandising Promo Desk' WHEN 2 THEN 'Clearance Optimization Model'
    ELSE 'Omnichannel Dynamic Pricing'
  END AS source,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'HELIOS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 7000)) AS n
