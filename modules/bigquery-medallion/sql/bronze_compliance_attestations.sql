CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_compliance_attestations` AS
SELECT
  CONCAT('FILING-', LPAD(CAST(n AS STRING), 5, '0')) AS filing_id,
  CASE MOD(n, 8)
    WHEN 0 THEN 'PCI-DSS v4.0 Report on Compliance (ROC)' WHEN 1 THEN 'CPRA / CCPA Annual DSAR Metrics Filing' WHEN 2 THEN 'SOC 2 Type II E-Commerce Attestation'
    WHEN 3 THEN 'CCPA Annual Privacy Audit' WHEN 4 THEN 'Promo Abuse Incident Report' WHEN 5 THEN 'High-Value Refund Audit Log'
    WHEN 6 THEN 'FTC Mail & Online Order Rule Review' ELSE 'GS1 Barcode & Supply Chain Traceability Audit'
  END AS report_name,
  CASE MOD(n, 8)
    WHEN 0 THEN 'PCI-SSC' WHEN 1 THEN 'California Privacy Protection Agency (CPPA)' WHEN 2 THEN 'AICPA / External Auditor'
    WHEN 3 THEN 'California Privacy Protection Agency (CPPA)' WHEN 4 THEN 'NRF Loss Prevention Council' WHEN 5 THEN 'Internal Audit Committee'
    WHEN 6 THEN 'FTC Consumer Protection' ELSE 'GS1 US Standards Body'
  END AS regulatory_body,
  CASE MOD(n, 4) WHEN 0 THEN 'Quarterly' WHEN 1 THEN 'Quarterly' WHEN 2 THEN 'Monthly' ELSE 'Annual' END AS filing_frequency,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(RAND() * 800) AS INT64) DAY) AS reporting_period_end,
  DATE_ADD('2023-02-01', INTERVAL CAST(FLOOR(RAND() * 830) AS INT64) DAY) AS filing_due_date,
  DATE_ADD('2023-02-01', INTERVAL CAST(FLOOR(RAND() * 825) AS INT64) DAY) AS actual_filing_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Filed' WHEN 1 THEN 'Filed' WHEN 2 THEN 'Filed' WHEN 3 THEN 'In Progress' ELSE 'Amendment Filed' END AS filing_status,
  CONCAT('PREP-', LPAD(CAST(MOD(n, 20) + 1 AS STRING), 3, '0')) AS preparer_id,
  CONCAT('REV-', LPAD(CAST(MOD(n, 10) + 1 AS STRING), 3, '0')) AS reviewer_id,
  CASE WHEN MOD(n, 10) = 0 THEN 'Minor POS scope reconciliation update' ELSE NULL END AS amendment_notes,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'HELIOS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 500)) AS n
