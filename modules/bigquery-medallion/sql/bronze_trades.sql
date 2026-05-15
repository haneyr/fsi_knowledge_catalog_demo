CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_trades` AS
SELECT
  CONCAT('TRD-', LPAD(CAST(n AS STRING), 10, '0')) AS trade_id,
  CONCAT('PORT-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 8, '0')) AS portfolio_id,
  CONCAT('SEC-', LPAD(CAST(CAST(FLOOR(RAND() * 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  CASE MOD(n, 4) WHEN 0 THEN 'BUY' WHEN 1 THEN 'SELL' WHEN 2 THEN 'BUY' ELSE 'EXCHANGE' END AS trade_type,
  ROUND(1 + RAND() * 5000, 4) AS quantity,
  ROUND(1 + RAND() * 5000, 2) AS price,
  ROUND((1 + RAND() * 5000) * (1 + RAND() * 5000), 2) AS gross_amount,
  ROUND(5 + RAND() * 50, 2) AS commission,
  ROUND(0 + RAND() * 10, 2) AS fees,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS trade_date,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 502) AS INT64) DAY) AS settlement_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Executed' WHEN 1 THEN 'Executed' WHEN 2 THEN 'Settled' WHEN 3 THEN 'Settled' ELSE 'Pending' END AS status,
  CASE MOD(n, 4) WHEN 0 THEN 'Market' WHEN 1 THEN 'Limit' WHEN 2 THEN 'Market' ELSE 'Stop' END AS order_type,
  CONCAT('ADV-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS advisor_id,
  CASE MOD(n, 3) WHEN 0 THEN 'Solicited' WHEN 1 THEN 'Unsolicited' ELSE 'Discretionary' END AS solicitation_type,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 30000)) AS n
