CREATE OR REPLACE TABLE `${project_id}.retail_staging.staging_channel_revenue_recon` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('REV-', CAST(MOD(n, 10) + 1 AS STRING)) AS schedule_line,
  CASE MOD(n, 10) WHEN 0 THEN 'Flagship Store POS Gross Sales' WHEN 1 THEN 'E-Commerce Web & App Sales' WHEN 2 THEN 'BOPIS & Curbside Revenue' WHEN 3 THEN 'Returns & Markdown Allowances' WHEN 4 THEN 'Net Merchandise Revenue' WHEN 5 THEN 'Cost of Merchandise Sold' WHEN 6 THEN 'Gross Margin Before Shrinkage' WHEN 7 THEN 'Fulfillment & Outbound Freight' WHEN 8 THEN 'Net Omnichannel Operating Income' ELSE 'Retained Retail Earnings' END AS line_description,
  ROUND(1500000 + RAND() * 65000000, 0) AS amount,
  'Reconciled' AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 40)) AS n
