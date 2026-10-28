CREATE OR REPLACE TABLE `${project_id}.retail_staging.staging_ccpa_dsar_log` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 12.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('CCPA-', CAST(MOD(n, 12) + 1 AS STRING)) AS schedule_line,
  CASE MOD(n, 12) WHEN 0 THEN 'Right-to-Know Requests Received' WHEN 1 THEN 'Right-to-Delete Requests Completed' WHEN 2 THEN 'Opt-Out of Sale/Sharing Requests' WHEN 3 THEN 'Authorized Agent Submissions' WHEN 4 THEN 'Loyalty Profile Export Requests' WHEN 5 THEN 'BNPL Data Access Disclosures' WHEN 6 THEN 'Store Card PII Masking Audits' WHEN 7 THEN 'Marketing Email Unsubscribes' WHEN 8 THEN 'SMS Geo-Tracking Opt-Outs' WHEN 9 THEN 'Biometric App Consent Revocations' WHEN 10 THEN 'Partially Denied (Fraud Hold)' ELSE 'Total Verified CCPA DSAR Filings' END AS line_description,
  ROUND(120 + RAND() * 4800, 0) AS amount,
  'Verified' AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 48)) AS n
