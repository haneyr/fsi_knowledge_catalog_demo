CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_compliance_cases` AS
SELECT
  CONCAT('COMP-', LPAD(CAST(n AS STRING), 7, '0')) AS case_id,
  CASE MOD(n, 8)
    WHEN 0 THEN 'SAR Investigation' WHEN 1 THEN 'CTR Review' WHEN 2 THEN 'OFAC Match'
    WHEN 3 THEN 'Reg E Dispute' WHEN 4 THEN 'Consumer Complaint' WHEN 5 THEN 'Fair Lending Review'
    WHEN 6 THEN 'BSA/AML Alert' ELSE 'Internal Policy Violation'
  END AS case_type,
  CASE MOD(n, 5) WHEN 0 THEN 'High' WHEN 1 THEN 'Medium' WHEN 2 THEN 'Low' WHEN 3 THEN 'Critical' ELSE 'Medium' END AS severity,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS related_customer_id,
  CASE WHEN MOD(n, 2) = 0 THEN CONCAT('ACCT-', LPAD(CAST(CAST(FLOOR(RAND() * 50000) + 1 AS INT64) AS STRING), 10, '0')) ELSE NULL END AS related_account_id,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(RAND() * 800) AS INT64) DAY) AS opened_date,
  CASE WHEN MOD(n, 3) != 0 THEN DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 500) AS INT64) DAY) ELSE NULL END AS closed_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Open' WHEN 1 THEN 'Under Review' WHEN 2 THEN 'Closed - No Action' WHEN 3 THEN 'Closed - SAR Filed' ELSE 'Escalated' END AS status,
  CONCAT('ANL-', LPAD(CAST(MOD(n, 50) + 1 AS STRING), 3, '0')) AS assigned_analyst,
  CASE WHEN MOD(n, 5) = 3 THEN TRUE ELSE FALSE END AS sar_filed,
  CASE WHEN MOD(n, 5) = 3 THEN CONCAT('SAR-', LPAD(CAST(n AS STRING), 8, '0')) ELSE NULL END AS sar_filing_id,
  CONCAT('Summary of case ', CAST(n AS STRING)) AS narrative_summary,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ARGUS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 3000)) AS n
