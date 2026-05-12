CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_benchmarks` AS
SELECT
  CONCAT('BM-', LPAD(CAST(MOD(n, 10) + 1 AS STRING), 3, '0')) AS benchmark_id,
  CASE MOD(n, 10)
    WHEN 0 THEN 'S&P 500' WHEN 1 THEN 'Russell 2000' WHEN 2 THEN 'MSCI EAFE'
    WHEN 3 THEN 'Bloomberg US Agg' WHEN 4 THEN 'MSCI EM' WHEN 5 THEN 'Nasdaq 100'
    WHEN 6 THEN 'DJ Industrial Avg' WHEN 7 THEN 'Bloomberg Muni' WHEN 8 THEN 'MSCI World'
    ELSE 'US Treasury 10Y'
  END AS benchmark_name,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) DAY) AS as_of_date,
  ROUND(-0.05 + RAND() * 0.1, 6) AS daily_return,
  ROUND(-0.1 + RAND() * 0.3, 4) AS mtd_return,
  ROUND(-0.2 + RAND() * 0.5, 4) AS ytd_return,
  ROUND(1000 + RAND() * 50000, 2) AS index_level,
  ROUND(0.05 + RAND() * 0.3, 4) AS annualized_volatility,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 7000)) AS n
