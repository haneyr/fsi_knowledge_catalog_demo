CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_advisors` AS
SELECT
  CONCAT('ADV-', LPAD(CAST(n AS STRING), 4, '0')) AS advisor_id,
  CASE MOD(n, 15) WHEN 0 THEN 'James' WHEN 1 THEN 'Sarah' WHEN 2 THEN 'Michael' WHEN 3 THEN 'Emily' WHEN 4 THEN 'Robert' WHEN 5 THEN 'Laura' WHEN 6 THEN 'David' WHEN 7 THEN 'Jennifer' WHEN 8 THEN 'William' WHEN 9 THEN 'Amanda' WHEN 10 THEN 'Thomas' WHEN 11 THEN 'Rebecca' WHEN 12 THEN 'Charles' WHEN 13 THEN 'Diana' ELSE 'Andrew' END AS first_name,
  CASE MOD(n, 8) WHEN 0 THEN 'Wellington' WHEN 1 THEN 'Bancroft' WHEN 2 THEN 'Sterling' WHEN 3 THEN 'Prescott' WHEN 4 THEN 'Hartford' WHEN 5 THEN 'Pemberton' WHEN 6 THEN 'Worthington' ELSE 'Ashford' END AS last_name,
  CASE MOD(n, 5) WHEN 0 THEN 'CFP' WHEN 1 THEN 'CFA' WHEN 2 THEN 'CFP, CIMA' WHEN 3 THEN 'CFA, CFP' ELSE 'ChFC' END AS certifications,
  CASE MOD(n, 4) WHEN 0 THEN 'Senior Financial Advisor' WHEN 1 THEN 'Financial Advisor' WHEN 2 THEN 'Wealth Manager' ELSE 'Managing Director' END AS title,
  CASE MOD(n, 5) WHEN 0 THEN 'Northeast' WHEN 1 THEN 'West' WHEN 2 THEN 'Midwest' WHEN 3 THEN 'South' ELSE 'Southeast' END AS region,
  CONCAT('BR-', LPAD(CAST(MOD(n, 100) + 1 AS STRING), 4, '0')) AS office_branch_id,
  CONCAT('CRD-', LPAD(CAST(1000000 + MOD(n * 97, 8000000) AS STRING), 7, '0')) AS finra_crd_number,
  CAST(FLOOR(5 + RAND() * 30) AS INT64) AS years_experience,
  ROUND(10000000 + RAND() * 490000000, 0) AS total_aum,
  CAST(FLOOR(10 + RAND() * 200) AS INT64) AS client_count,
  ROUND(50 + RAND() * 150, 2) AS avg_fee_bps,
  DATE_ADD('2005-01-01', INTERVAL CAST(FLOOR(RAND() * 7000) AS INT64) DAY) AS hire_date,
  CASE MOD(n, 6) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' WHEN 4 THEN 'Active' ELSE 'On Leave' END AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'FORTUNA' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 500)) AS n
