CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_branches` AS
SELECT
  CONCAT('BR-', LPAD(CAST(n AS STRING), 4, '0')) AS branch_id,
  CONCAT('Meridian ', CASE MOD(n, 15)
    WHEN 0 THEN 'Downtown' WHEN 1 THEN 'Midtown' WHEN 2 THEN 'Westside' WHEN 3 THEN 'Eastside'
    WHEN 4 THEN 'North' WHEN 5 THEN 'South' WHEN 6 THEN 'Central' WHEN 7 THEN 'Harbor'
    WHEN 8 THEN 'University' WHEN 9 THEN 'Airport' WHEN 10 THEN 'Lakeside' WHEN 11 THEN 'Heights'
    WHEN 12 THEN 'Plaza' WHEN 13 THEN 'Village' ELSE 'Park'
  END, ' Branch') AS branch_name,
  CONCAT(CAST(100 + MOD(n, 9900) AS STRING), ' ', CASE MOD(n, 6) WHEN 0 THEN 'Main St' WHEN 1 THEN 'Broadway' WHEN 2 THEN 'Market St' WHEN 3 THEN 'First Ave' WHEN 4 THEN 'Commerce Dr' ELSE 'Financial Blvd' END) AS address,
  CASE MOD(n, 10)
    WHEN 0 THEN 'New York' WHEN 1 THEN 'Los Angeles' WHEN 2 THEN 'Chicago' WHEN 3 THEN 'Houston'
    WHEN 4 THEN 'Miami' WHEN 5 THEN 'Dallas' WHEN 6 THEN 'Seattle' WHEN 7 THEN 'Boston'
    WHEN 8 THEN 'San Francisco' ELSE 'Atlanta'
  END AS city,
  CASE MOD(n, 10)
    WHEN 0 THEN 'NY' WHEN 1 THEN 'CA' WHEN 2 THEN 'IL' WHEN 3 THEN 'TX'
    WHEN 4 THEN 'FL' WHEN 5 THEN 'TX' WHEN 6 THEN 'WA' WHEN 7 THEN 'MA'
    WHEN 8 THEN 'CA' ELSE 'GA'
  END AS state,
  CASE MOD(n, 4) WHEN 0 THEN 'Full Service' WHEN 1 THEN 'Full Service' WHEN 2 THEN 'Limited Service' ELSE 'Private Banking' END AS branch_type,
  CASE MOD(n, 5)
    WHEN 0 THEN 'Northeast' WHEN 1 THEN 'West' WHEN 2 THEN 'Midwest' WHEN 3 THEN 'South' ELSE 'Southeast'
  END AS region,
  CONCAT('DM-', LPAD(CAST(MOD(n, 20) + 1 AS STRING), 3, '0')) AS district_manager_id,
  CAST(5 + FLOOR(RAND() * 30) AS INT64) AS employee_count,
  ROUND(-90 + RAND() * 50, 6) AS longitude,
  ROUND(25 + RAND() * 25, 6) AS latitude,
  DATE_ADD('2000-01-01', INTERVAL CAST(FLOOR(RAND() * 8000) AS INT64) DAY) AS open_date,
  CASE MOD(n, 4) WHEN 0 THEN 'Open' WHEN 1 THEN 'Open' WHEN 2 THEN 'Open' ELSE CASE WHEN MOD(n, 50) = 0 THEN 'Closed' ELSE 'Open' END END AS status,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ATLAS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 500)) AS n
