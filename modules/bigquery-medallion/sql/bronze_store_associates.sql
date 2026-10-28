CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_store_associates` AS
SELECT
  CONCAT('EMP-', LPAD(CAST(n AS STRING), 6, '0')) AS employee_id,
  CASE MOD(n, 20)
    WHEN 0 THEN 'James' WHEN 1 THEN 'Mary' WHEN 2 THEN 'Robert' WHEN 3 THEN 'Patricia'
    WHEN 4 THEN 'John' WHEN 5 THEN 'Jennifer' WHEN 6 THEN 'Michael' WHEN 7 THEN 'Linda'
    WHEN 8 THEN 'David' WHEN 9 THEN 'Elizabeth' WHEN 10 THEN 'William' WHEN 11 THEN 'Barbara'
    WHEN 12 THEN 'Richard' WHEN 13 THEN 'Susan' WHEN 14 THEN 'Joseph' WHEN 15 THEN 'Jessica'
    WHEN 16 THEN 'Thomas' WHEN 17 THEN 'Sarah' WHEN 18 THEN 'Charles' ELSE 'Karen'
  END AS first_name,
  CASE MOD(n, 10) WHEN 0 THEN 'Smith' WHEN 1 THEN 'Johnson' WHEN 2 THEN 'Williams' WHEN 3 THEN 'Brown' WHEN 4 THEN 'Jones' WHEN 5 THEN 'Garcia' WHEN 6 THEN 'Miller' WHEN 7 THEN 'Davis' WHEN 8 THEN 'Rodriguez' ELSE 'Wilson' END AS last_name,
  CASE MOD(n, 12)
    WHEN 0 THEN 'POS Cashier' WHEN 1 THEN 'Clienteling Stylist' WHEN 2 THEN 'BNPL & Loyalty Specialist'
    WHEN 3 THEN 'Store Manager' WHEN 4 THEN 'Visual Merchandiser' WHEN 5 THEN 'Privacy & PCI Compliance Lead'
    WHEN 6 THEN 'Inventory Control Specialist' WHEN 7 THEN 'VIP Personal Shopper' WHEN 8 THEN 'BOPIS Fulfillment Lead'
    WHEN 9 THEN 'Loss Prevention Analyst' WHEN 10 THEN 'Returns & Promo Fraud Specialist' ELSE 'Store Systems Support'
  END AS title,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Store Operations' WHEN 1 THEN 'Customer Loyalty & BNPL' WHEN 2 THEN 'Omnichannel Clienteling'
    WHEN 3 THEN 'Fulfillment & BOPIS' WHEN 4 THEN 'Loss Prevention' WHEN 5 THEN 'Privacy & PCI Governance'
    WHEN 6 THEN 'Retail Technology' ELSE 'Merchandising & Inventory'
  END AS department,
  CONCAT('BR-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS store_id,
  CASE WHEN MOD(n, 20) = 0 THEN NULL ELSE CONCAT('EMP-', LPAD(CAST(CAST(FLOOR(n / 5) AS INT64) AS STRING), 6, '0')) END AS manager_id,
  DATE_ADD('2015-01-01', INTERVAL CAST(FLOOR(RAND() * 3500) AS INT64) DAY) AS hire_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' ELSE 'On Leave' END AS employment_status,
  CASE WHEN MOD(n, 12) IN (5, 6, 10) THEN TRUE ELSE FALSE END AS has_finra_license,
  CASE WHEN MOD(n, 12) IN (5, 6, 10) THEN CONCAT('PCI-CERT-', LPAD(CAST(MOD(n, 99999) AS STRING), 5, '0')) ELSE NULL END AS finra_crd_number,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
