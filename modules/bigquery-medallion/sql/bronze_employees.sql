CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_employees` AS
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
    WHEN 0 THEN 'Teller' WHEN 1 THEN 'Personal Banker' WHEN 2 THEN 'Loan Officer'
    WHEN 3 THEN 'Branch Manager' WHEN 4 THEN 'Relationship Manager' WHEN 5 THEN 'Compliance Analyst'
    WHEN 6 THEN 'Risk Analyst' WHEN 7 THEN 'Financial Advisor' WHEN 8 THEN 'Operations Specialist'
    WHEN 9 THEN 'Credit Analyst' WHEN 10 THEN 'Fraud Investigator' ELSE 'IT Support'
  END AS title,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Retail Banking' WHEN 1 THEN 'Lending' WHEN 2 THEN 'Wealth Management'
    WHEN 3 THEN 'Operations' WHEN 4 THEN 'Risk Management' WHEN 5 THEN 'Compliance'
    WHEN 6 THEN 'Technology' ELSE 'Finance'
  END AS department,
  CONCAT('BR-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS branch_id,
  CASE WHEN MOD(n, 20) = 0 THEN NULL ELSE CONCAT('EMP-', LPAD(CAST(CAST(FLOOR(n / 5) AS INT64) AS STRING), 6, '0')) END AS manager_id,
  DATE_ADD('2010-01-01', INTERVAL CAST(FLOOR(RAND() * 5000) AS INT64) DAY) AS hire_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' ELSE 'On Leave' END AS employment_status,
  CASE WHEN MOD(n, 12) IN (5, 6, 10) THEN TRUE ELSE FALSE END AS has_finra_license,
  CASE WHEN MOD(n, 12) IN (5, 6, 10) THEN CONCAT('CRD-', LPAD(CAST(MOD(n, 999999) AS STRING), 7, '0')) ELSE NULL END AS finra_crd_number,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ATLAS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
