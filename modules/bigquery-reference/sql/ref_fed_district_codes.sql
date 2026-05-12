CREATE OR REPLACE TABLE `${project_id}.fsi_reference.ref_fed_district_codes` AS
SELECT 1 AS district_number, 'Boston' AS district_name, '01' AS routing_prefix UNION ALL
SELECT 2, 'New York', '02' UNION ALL SELECT 3, 'Philadelphia', '03' UNION ALL
SELECT 4, 'Cleveland', '04' UNION ALL SELECT 5, 'Richmond', '05' UNION ALL
SELECT 6, 'Atlanta', '06' UNION ALL SELECT 7, 'Chicago', '07' UNION ALL
SELECT 8, 'St. Louis', '08' UNION ALL SELECT 9, 'Minneapolis', '09' UNION ALL
SELECT 10, 'Kansas City', '10' UNION ALL SELECT 11, 'Dallas', '11' UNION ALL
SELECT 12, 'San Francisco', '12'
