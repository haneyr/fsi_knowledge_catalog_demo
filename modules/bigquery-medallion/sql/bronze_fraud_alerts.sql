CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_fraud_alerts` AS
SELECT
  CONCAT('FRD-', LPAD(CAST(n AS STRING), 8, '0')) AS alert_id,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS customer_id,
  CASE WHEN MOD(n, 2) = 0
    THEN CONCAT('TXN-', LPAD(CAST(CAST(FLOOR(RAND() * 100000) + 1 AS INT64) AS STRING), 12, '0'))
    ELSE CONCAT('CTXN-', LPAD(CAST(CAST(FLOOR(RAND() * 80000) + 1 AS INT64) AS STRING), 12, '0'))
  END AS transaction_id,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Serial Wardrobing Return Pattern' WHEN 1 THEN 'Cross-Region Gift Card Velocity'
    WHEN 2 THEN 'Promo Code Stacking Abuse' WHEN 3 THEN 'Loyalty Account Takeover Attempt'
    WHEN 4 THEN 'Card-Not-Present E-Com Anomaly' WHEN 5 THEN 'Split-Receipt Refund Threshold Bypass'
    WHEN 6 THEN 'Receiptless High-Value Return' ELSE 'Synthetic Shopper Identity Indicator'
  END AS alert_type,
  ROUND(15 + RAND() * 82, 0) AS fraud_score,
  CASE MOD(n, 5)
    WHEN 0 THEN 'High' WHEN 1 THEN 'Medium' WHEN 2 THEN 'Low' WHEN 3 THEN 'Critical' ELSE 'Medium'
  END AS severity,
  CASE MOD(n, 4) WHEN 0 THEN 'Open' WHEN 1 THEN 'Investigating' WHEN 2 THEN 'Closed - Confirmed Fraud' ELSE 'Closed - False Positive' END AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS alert_date,
  CASE WHEN MOD(n, 3) != 0 THEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 200 * 24 * 60) AS INT64) MINUTE) ELSE NULL END AS resolved_date,
  CONCAT('ANL-', LPAD(CAST(MOD(n, 50) + 1 AS STRING), 3, '0')) AS assigned_analyst,
  ROUND(CASE WHEN MOD(n, 4) = 2 THEN 25 + RAND() * 650 ELSE 0 END, 2) AS loss_amount,
  CASE WHEN MOD(n, 10) = 0 THEN TRUE ELSE FALSE END AS sar_filed,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
