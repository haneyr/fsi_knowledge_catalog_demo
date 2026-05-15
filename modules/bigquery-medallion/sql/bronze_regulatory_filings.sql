CREATE OR REPLACE TABLE `${project_id}.fsi_bronze.bronze_regulatory_filings` AS
SELECT
  CONCAT('FILING-', LPAD(CAST(n AS STRING), 5, '0')) AS filing_id,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Call Report (FFIEC 031)' WHEN 1 THEN 'FR Y-9C' WHEN 2 THEN 'FR 2052a (LCR)'
    WHEN 3 THEN 'DFAST Summary' WHEN 4 THEN 'SAR Filing' WHEN 5 THEN 'CTR Filing'
    WHEN 6 THEN 'HMDA LAR' ELSE 'CRA Data'
  END AS report_name,
  CASE MOD(n, 8)
    WHEN 0 THEN 'FDIC/OCC' WHEN 1 THEN 'Federal Reserve' WHEN 2 THEN 'Federal Reserve'
    WHEN 3 THEN 'Federal Reserve' WHEN 4 THEN 'FinCEN' WHEN 5 THEN 'FinCEN'
    WHEN 6 THEN 'CFPB' ELSE 'FFIEC'
  END AS regulatory_body,
  CASE MOD(n, 4) WHEN 0 THEN 'Quarterly' WHEN 1 THEN 'Quarterly' WHEN 2 THEN 'Monthly' ELSE 'Annual' END AS filing_frequency,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(RAND() * 800) AS INT64) DAY) AS reporting_period_end,
  DATE_ADD('2023-02-01', INTERVAL CAST(FLOOR(RAND() * 830) AS INT64) DAY) AS filing_due_date,
  DATE_ADD('2023-02-01', INTERVAL CAST(FLOOR(RAND() * 825) AS INT64) DAY) AS actual_filing_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Filed' WHEN 1 THEN 'Filed' WHEN 2 THEN 'Filed' WHEN 3 THEN 'In Progress' ELSE 'Amendment Filed' END AS filing_status,
  CONCAT('PREP-', LPAD(CAST(MOD(n, 20) + 1 AS STRING), 3, '0')) AS preparer_id,
  CONCAT('REV-', LPAD(CAST(MOD(n, 10) + 1 AS STRING), 3, '0')) AS reviewer_id,
  CASE WHEN MOD(n, 10) = 0 THEN 'Minor data corrections' ELSE NULL END AS amendment_notes,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ARGUS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 500)) AS n
