CREATE OR REPLACE TABLE `${project_id}.retail_staging.staging_annual_omniretail_filing` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('OMNI-', CASE MOD(n, 10) WHEN 0 THEN 'INV-1' WHEN 1 THEN 'INV-2' WHEN 2 THEN 'BNPL-1' WHEN 3 THEN 'LOY-1' WHEN 4 THEN 'WCR-1' WHEN 5 THEN 'WCR-2' WHEN 6 THEN 'GMV-1' WHEN 7 THEN 'COGS-1' WHEN 8 THEN 'OPEX-1' ELSE 'EQ-1' END) AS schedule_line,
  CASE MOD(n, 10) WHEN 0 THEN 'Consolidated Retail Assets' WHEN 1 THEN 'Merchandise Inventory' WHEN 2 THEN 'Active BNPL Receivables' WHEN 3 THEN 'Unredeemed Loyalty Liability' WHEN 4 THEN 'Risk-Adjusted Inventory Assets' WHEN 5 THEN 'Total Working Capital' WHEN 6 THEN 'Omnichannel Gross Merchandise Value' WHEN 7 THEN 'Cost of Goods Sold' WHEN 8 THEN 'Store & Fulfillment Operating Expense' ELSE 'Total Retail Operating Equity' END AS line_description,
  ROUND(15000000 + RAND() * 450000000, 0) AS amount,
  'SEC / FTC Omnichannel Retail Disclosure' AS regulatory_body,
  'Filed' AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 50)) AS n
