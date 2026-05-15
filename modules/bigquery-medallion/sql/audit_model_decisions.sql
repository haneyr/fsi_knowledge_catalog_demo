CREATE OR REPLACE TABLE `${project_id}.fsi_audit.audit_model_decisions` AS
SELECT
  CONCAT('MDL-', LPAD(CAST(n AS STRING), 10, '0')) AS decision_id,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS decision_timestamp,
  CASE MOD(n, 5) WHEN 0 THEN 'Credit Scoring' WHEN 1 THEN 'Fraud Detection' WHEN 2 THEN 'AML Screening' WHEN 3 THEN 'Loan Pricing' ELSE 'Risk Rating' END AS model_name,
  CONCAT('v', CAST(1 + MOD(n, 5) AS STRING), '.', CAST(MOD(n, 10) AS STRING)) AS model_version,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS subject_id,
  CASE MOD(n, 4) WHEN 0 THEN 'Approve' WHEN 1 THEN 'Decline' WHEN 2 THEN 'Refer' ELSE 'Approve' END AS decision,
  ROUND(RAND() * 100, 2) AS confidence_score,
  CONCAT('Feature1:', CAST(ROUND(RAND(), 3) AS STRING), '; Feature2:', CAST(ROUND(RAND(), 3) AS STRING)) AS key_factors,
  CASE WHEN MOD(n, 10) = 0 THEN TRUE ELSE FALSE END AS manual_override,
  CASE WHEN MOD(n, 10) = 0 THEN CONCAT('EMP-', LPAD(CAST(CAST(FLOOR(RAND() * 100) + 1 AS INT64) AS STRING), 6, '0')) ELSE NULL END AS override_by
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
