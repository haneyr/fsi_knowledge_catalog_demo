CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_customers` AS
WITH base AS (
  SELECT
    n,
    CONCAT('CUST-', LPAD(CAST(n AS STRING), 8, '0')) AS customer_id,
    CASE MOD(n, 20)
      WHEN 0 THEN 'James' WHEN 1 THEN 'Mary' WHEN 2 THEN 'Robert' WHEN 3 THEN 'Patricia'
      WHEN 4 THEN 'John' WHEN 5 THEN 'Jennifer' WHEN 6 THEN 'Michael' WHEN 7 THEN 'Linda'
      WHEN 8 THEN 'David' WHEN 9 THEN 'Elizabeth' WHEN 10 THEN 'William' WHEN 11 THEN 'Barbara'
      WHEN 12 THEN 'Richard' WHEN 13 THEN 'Susan' WHEN 14 THEN 'Joseph' WHEN 15 THEN 'Jessica'
      WHEN 16 THEN 'Thomas' WHEN 17 THEN 'Sarah' WHEN 18 THEN 'Charles' ELSE 'Karen'
    END AS first_name,
    CASE MOD(n, 15)
      WHEN 0 THEN 'Smith' WHEN 1 THEN 'Johnson' WHEN 2 THEN 'Williams' WHEN 3 THEN 'Brown'
      WHEN 4 THEN 'Jones' WHEN 5 THEN 'Garcia' WHEN 6 THEN 'Miller' WHEN 7 THEN 'Davis'
      WHEN 8 THEN 'Rodriguez' WHEN 9 THEN 'Martinez' WHEN 10 THEN 'Anderson' WHEN 11 THEN 'Taylor'
      WHEN 12 THEN 'Thomas' WHEN 13 THEN 'Hernandez' ELSE 'Moore'
    END AS last_name,
    CASE
      WHEN MOD(n, 50) = 0 THEN NULL
      ELSE CAST(DATE_ADD('1945-01-01', INTERVAL CAST(FLOOR(RAND() * 25000) AS INT64) DAY) AS STRING)
    END AS date_of_birth,
    CASE MOD(n, 80)
      WHEN 0 THEN CONCAT(CAST(100 + MOD(n, 900) AS STRING), CAST(10 + MOD(n, 90) AS STRING), CAST(1000 + MOD(n, 9000) AS STRING))
      ELSE CONCAT(CAST(100 + MOD(n, 900) AS STRING), '-', CAST(10 + MOD(n, 90) AS STRING), '-', CAST(1000 + MOD(n, 9000) AS STRING))
    END AS ssn,
    CONCAT(CAST(100 + MOD(n, 9900) AS STRING), ' ', CASE MOD(n, 8)
      WHEN 0 THEN 'Main St' WHEN 1 THEN 'Oak Ave' WHEN 2 THEN 'Elm Dr' WHEN 3 THEN 'Park Blvd'
      WHEN 4 THEN 'Cedar Ln' WHEN 5 THEN 'Maple Rd' WHEN 6 THEN 'Pine St' ELSE 'Lake Ave'
    END) AS address_line1,
    CASE MOD(n, 12)
      WHEN 0 THEN 'New York' WHEN 1 THEN 'Los Angeles' WHEN 2 THEN 'Chicago' WHEN 3 THEN 'Houston'
      WHEN 4 THEN 'Phoenix' WHEN 5 THEN 'Philadelphia' WHEN 6 THEN 'San Antonio' WHEN 7 THEN 'San Diego'
      WHEN 8 THEN 'Dallas' WHEN 9 THEN 'San Jose' WHEN 10 THEN 'Austin' ELSE 'Jacksonville'
    END AS city,
    CASE MOD(n, 12)
      WHEN 0 THEN 'NY' WHEN 1 THEN 'CA' WHEN 2 THEN 'IL' WHEN 3 THEN 'TX'
      WHEN 4 THEN 'AZ' WHEN 5 THEN 'PA' WHEN 6 THEN 'TX' WHEN 7 THEN 'CA'
      WHEN 8 THEN 'TX' WHEN 9 THEN 'CA' WHEN 10 THEN 'TX' ELSE 'FL'
    END AS state,
    LPAD(CAST(10000 + MOD(n * 7, 90000) AS STRING), 5, '0') AS zip_code,
    CONCAT('(', CAST(200 + MOD(n, 800) AS STRING), ') ', CAST(200 + MOD(n, 800) AS STRING), '-', LPAD(CAST(MOD(n, 10000) AS STRING), 4, '0')) AS phone,
    CONCAT(LOWER(CASE MOD(n, 20)
      WHEN 0 THEN 'james' WHEN 1 THEN 'mary' WHEN 2 THEN 'robert' WHEN 3 THEN 'patricia'
      WHEN 4 THEN 'john' WHEN 5 THEN 'jennifer' WHEN 6 THEN 'michael' WHEN 7 THEN 'linda'
      WHEN 8 THEN 'david' WHEN 9 THEN 'elizabeth' WHEN 10 THEN 'william' WHEN 11 THEN 'barbara'
      WHEN 12 THEN 'richard' WHEN 13 THEN 'susan' WHEN 14 THEN 'joseph' WHEN 15 THEN 'jessica'
      WHEN 16 THEN 'thomas' WHEN 17 THEN 'sarah' WHEN 18 THEN 'charles' ELSE 'karen'
    END), '.', LOWER(CASE MOD(n, 15)
      WHEN 0 THEN 'smith' WHEN 1 THEN 'johnson' WHEN 2 THEN 'williams' WHEN 3 THEN 'brown'
      WHEN 4 THEN 'jones' WHEN 5 THEN 'garcia' WHEN 6 THEN 'miller' WHEN 7 THEN 'davis'
      WHEN 8 THEN 'rodriguez' WHEN 9 THEN 'martinez' WHEN 10 THEN 'anderson' WHEN 11 THEN 'taylor'
      WHEN 12 THEN 'thomas' WHEN 13 THEN 'hernandez' ELSE 'moore'
    END), '@email.com') AS email,
    CASE MOD(n, 5)
      WHEN 0 THEN 'Individual' WHEN 1 THEN 'Joint' WHEN 2 THEN 'Trust'
      WHEN 3 THEN 'Business' ELSE 'Individual'
    END AS customer_type,
    CASE MOD(n, 6)
      WHEN 0 THEN 'Standard' WHEN 1 THEN 'Preferred' WHEN 2 THEN 'Premier'
      WHEN 3 THEN 'Private Banking' WHEN 4 THEN 'Small Business' ELSE 'Standard'
    END AS customer_segment,
    CASE MOD(n, 8)
      WHEN 0 THEN 'US Citizen' WHEN 1 THEN 'US Resident' WHEN 2 THEN 'Non-Resident Alien'
      ELSE 'US Citizen'
    END AS citizenship_status,
    LPAD(CAST(MOD(n * 13, 900000000) AS STRING), 9, '0') AS tin,
    CASE MOD(n, 10)
      WHEN 0 THEN 'Agriculture' WHEN 1 THEN 'Manufacturing' WHEN 2 THEN 'Finance'
      WHEN 3 THEN 'Technology' WHEN 4 THEN 'Healthcare' WHEN 5 THEN 'Retail'
      WHEN 6 THEN 'Real Estate' WHEN 7 THEN 'Education' WHEN 8 THEN 'Government' ELSE 'Services'
    END AS industry,
    CASE MOD(n, 4)
      WHEN 0 THEN 'Low' WHEN 1 THEN 'Medium' WHEN 2 THEN 'High' ELSE 'Medium'
    END AS kyc_risk_rating,
    CASE MOD(n, 3)
      WHEN 0 THEN 'Verified' WHEN 1 THEN 'Pending' ELSE 'Verified'
    END AS kyc_status,
    CONCAT('BR-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS home_branch_id,
    TIMESTAMP_ADD(TIMESTAMP '2010-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 5000 * 24 * 60) AS INT64) MINUTE) AS account_opened_date,
    CASE MOD(n, 3) WHEN 0 THEN 'ATLAS' WHEN 1 THEN 'ATLAS_LEGACY' ELSE 'ATLAS' END AS source_system,
    TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
  FROM UNNEST(GENERATE_ARRAY(1, 20000)) AS n
),
dupes AS (
  SELECT * FROM base WHERE MOD(n, 500) = 0
)
SELECT * EXCEPT(n) FROM base
UNION ALL
SELECT * EXCEPT(n) FROM dupes
