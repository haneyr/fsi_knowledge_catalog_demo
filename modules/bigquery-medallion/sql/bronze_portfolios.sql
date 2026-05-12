CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_portfolios` AS
SELECT
  CONCAT('PORT-', LPAD(CAST(n AS STRING), 8, '0')) AS portfolio_id,
  CONCAT('WMC-', LPAD(CAST(CAST(FLOOR(n / 2.0) + 1 AS INT64) AS STRING), 7, '0')) AS wm_client_id,
  CONCAT('Portfolio ', CASE MOD(n, 6)
    WHEN 0 THEN 'Growth' WHEN 1 THEN 'Income' WHEN 2 THEN 'Balanced'
    WHEN 3 THEN 'Tax-Managed' WHEN 4 THEN 'ESG Impact' ELSE 'Core'
  END) AS portfolio_name,
  CASE MOD(n, 8)
    WHEN 0 THEN 'BROKERAGE' WHEN 1 THEN 'IRA' WHEN 2 THEN 'ROTH_IRA' WHEN 3 THEN '401K'
    WHEN 4 THEN 'TRUST' WHEN 5 THEN 'UGMA' WHEN 6 THEN 'SEP_IRA' ELSE 'BROKERAGE'
  END AS account_type,
  CASE MOD(n, 5) WHEN 0 THEN 'Taxable' WHEN 1 THEN 'Tax-Deferred' WHEN 2 THEN 'Tax-Exempt' WHEN 3 THEN 'Tax-Deferred' ELSE 'Taxable' END AS tax_status,
  ROUND(CASE MOD(n, 5)
    WHEN 0 THEN 100000 + RAND() * 5000000
    WHEN 1 THEN 500000 + RAND() * 10000000
    WHEN 2 THEN 50000 + RAND() * 2000000
    ELSE 200000 + RAND() * 3000000
  END, 2) AS market_value,
  ROUND(CASE MOD(n, 5)
    WHEN 0 THEN 80000 + RAND() * 4000000
    WHEN 1 THEN 300000 + RAND() * 8000000
    ELSE 100000 + RAND() * 2000000
  END, 2) AS cost_basis,
  ROUND(-0.05 + RAND() * 0.25, 4) AS ytd_return,
  ROUND(-0.1 + RAND() * 0.3, 4) AS inception_return,
  CONCAT('BM-', LPAD(CAST(MOD(n, 10) + 1 AS STRING), 3, '0')) AS benchmark_id,
  CONCAT('ADV-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS advisor_id,
  CONCAT('MDL-', LPAD(CAST(MOD(n, 20) + 1 AS STRING), 3, '0')) AS model_portfolio_id,
  DATE_ADD('2010-01-01', INTERVAL CAST(FLOOR(RAND() * 5000) AS INT64) DAY) AS inception_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' ELSE 'Closed' END AS status,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 15000)) AS n
