CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_holdings` AS
SELECT
  CONCAT('HLD-', LPAD(CAST(n AS STRING), 9, '0')) AS holding_id,
  CONCAT('PORT-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 8, '0')) AS portfolio_id,
  CONCAT('SEC-', LPAD(CAST(CAST(FLOOR(RAND() * 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  ROUND(1 + RAND() * 10000, 4) AS quantity,
  ROUND(1 + RAND() * 5000, 2) AS market_price,
  ROUND((1 + RAND() * 10000) * (1 + RAND() * 5000), 2) AS market_value,
  ROUND((1 + RAND() * 10000) * (0.5 + RAND() * 4000), 2) AS cost_basis,
  ROUND(-5000 + RAND() * 50000, 2) AS unrealized_gain_loss,
  CASE MOD(n, 8)
    WHEN 0 THEN 'US Large Cap Equity' WHEN 1 THEN 'US Small Cap Equity' WHEN 2 THEN 'International Equity'
    WHEN 3 THEN 'Fixed Income' WHEN 4 THEN 'Municipal Bonds' WHEN 5 THEN 'Real Estate'
    WHEN 6 THEN 'Alternatives' ELSE 'Cash & Equivalents'
  END AS asset_class,
  CASE MOD(n, 11)
    WHEN 0 THEN 'Technology' WHEN 1 THEN 'Healthcare' WHEN 2 THEN 'Financial Services'
    WHEN 3 THEN 'Consumer Discretionary' WHEN 4 THEN 'Industrials' WHEN 5 THEN 'Energy'
    WHEN 6 THEN 'Utilities' WHEN 7 THEN 'Real Estate' WHEN 8 THEN 'Materials'
    WHEN 9 THEN 'Communication Services' ELSE 'Consumer Staples'
  END AS sector,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 500) AS INT64) DAY) AS as_of_date,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
