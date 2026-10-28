CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_category_managers` AS
SELECT
  CONCAT('ADV-', LPAD(CAST(n AS STRING), 4, '0')) AS advisor_id,
  CASE MOD(n, 15) WHEN 0 THEN 'James' WHEN 1 THEN 'Sarah' WHEN 2 THEN 'Michael' WHEN 3 THEN 'Emily' WHEN 4 THEN 'Robert' WHEN 5 THEN 'Laura' WHEN 6 THEN 'David' WHEN 7 THEN 'Jennifer' WHEN 8 THEN 'William' WHEN 9 THEN 'Amanda' WHEN 10 THEN 'Thomas' WHEN 11 THEN 'Rebecca' WHEN 12 THEN 'Charles' WHEN 13 THEN 'Diana' ELSE 'Andrew' END AS first_name,
  CASE MOD(n, 8) WHEN 0 THEN 'Mercer' WHEN 1 THEN 'Callahan' WHEN 2 THEN 'Sterling' WHEN 3 THEN 'Prescott' WHEN 4 THEN 'Hawthorne' WHEN 5 THEN 'Kensington' WHEN 6 THEN 'Vance' ELSE 'Ashford' END AS last_name,
  CASE MOD(n, 5) WHEN 0 THEN 'CPIM, CSCP' WHEN 1 THEN 'NRF Merchandising Cert' WHEN 2 THEN 'Six Sigma Black Belt' WHEN 3 THEN 'GS1 Standards Specialist' ELSE 'Omnichannel Planning Cert' END AS certifications,
  CASE MOD(n, 4) WHEN 0 THEN 'Senior Category Manager' WHEN 1 THEN 'Assortment Buyer' WHEN 2 THEN 'Omnichannel Merchandising Lead' ELSE 'VP of Divisional Merchandising' END AS title,
  CASE MOD(n, 5) WHEN 0 THEN 'Northeast' WHEN 1 THEN 'West' WHEN 2 THEN 'Midwest' WHEN 3 THEN 'South' ELSE 'Southeast' END AS region,
  CONCAT('BR-', LPAD(CAST(MOD(n, 100) + 1 AS STRING), 4, '0')) AS assigned_store_id,
  CONCAT('MERCH-', LPAD(CAST(100000 + MOD(n * 97, 800000) AS STRING), 6, '0')) AS finra_crd_number,
  CAST(FLOOR(3 + RAND() * 22) AS INT64) AS years_experience,
  ROUND(1500000 + RAND() * 14000000, 0) AS total_aum,
  CAST(FLOOR(8 + RAND() * 45) AS INT64) AS client_count,
  ROUND(32 + RAND() * 28, 2) AS avg_fee_bps,
  DATE_ADD('2012-01-01', INTERVAL CAST(FLOOR(RAND() * 4200) AS INT64) DAY) AS hire_date,
  CASE MOD(n, 6) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' WHEN 4 THEN 'Active' ELSE 'On Leave' END AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 500)) AS n
