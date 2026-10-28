CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_ecom_orders` AS
SELECT
  CONCAT('TRD-', LPAD(CAST(n AS STRING), 10, '0')) AS trade_id,
  CONCAT('PORT-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 8, '0')) AS assortment_id,
  CONCAT('SEC-', LPAD(CAST(CAST(FLOOR(RAND() * 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  CASE MOD(n, 4) WHEN 0 THEN 'PURCHASE' WHEN 1 THEN 'RETURN' WHEN 2 THEN 'PURCHASE' ELSE 'EXCHANGE' END AS trade_type,
  ROUND(1 + FLOOR(RAND() * 6), 0) AS quantity,
  ROUND(18 + RAND() * 165, 2) AS price,
  ROUND((1 + FLOOR(RAND() * 6)) * (18 + RAND() * 165), 2) AS gross_amount,
  ROUND(0 + RAND() * 12, 2) AS commission,
  ROUND(0 + RAND() * 7.99, 2) AS fees,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS trade_date,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 502) AS INT64) DAY) AS settlement_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Delivered' WHEN 1 THEN 'Shipped' WHEN 2 THEN 'Delivered' WHEN 3 THEN 'Fulfilled BOPIS' ELSE 'Processing' END AS status,
  CASE MOD(n, 4) WHEN 0 THEN 'Standard Shipping' WHEN 1 THEN 'BOPIS Same-Day' WHEN 2 THEN 'Express 2-Day' ELSE 'Ship-From-Store' END AS order_type,
  CONCAT('ADV-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS advisor_id,
  CASE MOD(n, 3) WHEN 0 THEN 'Organic Web' WHEN 1 THEN 'Loyalty App Push' ELSE 'Stylist Clienteling Link' END AS solicitation_type,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 30000)) AS n
