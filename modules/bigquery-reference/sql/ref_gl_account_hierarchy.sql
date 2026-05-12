CREATE OR REPLACE TABLE `${project_id}.fsi_reference.ref_gl_account_hierarchy` AS
SELECT 'Asset' AS l1_type, 'Cash and Due From' AS l2_category, '1000-1099' AS account_range, 'RC-B1' AS call_report_line UNION ALL
SELECT 'Asset', 'Investment Securities', '1100-1299', 'RC-B2' UNION ALL
SELECT 'Asset', 'Loans and Leases', '1300-1599', 'RC-C1' UNION ALL
SELECT 'Asset', 'Allowance for Loan Losses', '1600-1699', 'RC-C2' UNION ALL
SELECT 'Asset', 'Fixed Assets', '1700-1799', 'RC-6' UNION ALL
SELECT 'Asset', 'Other Assets', '1800-1999', 'RC-11' UNION ALL
SELECT 'Liability', 'Deposits - Domestic', '2000-2199', 'RC-E1' UNION ALL
SELECT 'Liability', 'Deposits - Foreign', '2200-2299', 'RC-E2' UNION ALL
SELECT 'Liability', 'Borrowed Funds', '2300-2499', 'RC-14' UNION ALL
SELECT 'Liability', 'Other Liabilities', '2500-2999', 'RC-20' UNION ALL
SELECT 'Equity', 'Common Stock', '3000-3099', 'RC-26' UNION ALL
SELECT 'Equity', 'Retained Earnings', '3100-3199', 'RC-26a' UNION ALL
SELECT 'Revenue', 'Interest Income', '4000-4499', 'RI-1' UNION ALL
SELECT 'Revenue', 'Noninterest Income', '4500-4999', 'RI-5' UNION ALL
SELECT 'Expense', 'Interest Expense', '5000-5499', 'RI-2' UNION ALL
SELECT 'Expense', 'Provision for Loan Losses', '5500-5599', 'RI-4' UNION ALL
SELECT 'Expense', 'Noninterest Expense', '5600-5999', 'RI-7'
