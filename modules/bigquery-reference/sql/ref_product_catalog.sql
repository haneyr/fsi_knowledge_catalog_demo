CREATE OR REPLACE TABLE `${project_id}.fsi_reference.ref_product_catalog` AS
SELECT 'CHECKING' AS product_code, 'Personal Checking' AS product_name, 'Deposit' AS category, 'Retail' AS division UNION ALL
SELECT 'SAVINGS', 'Personal Savings', 'Deposit', 'Retail' UNION ALL
SELECT 'MONEY_MARKET', 'Money Market Account', 'Deposit', 'Retail' UNION ALL
SELECT 'CD', 'Certificate of Deposit', 'Deposit', 'Retail' UNION ALL
SELECT 'IRA', 'Individual Retirement Account', 'Deposit', 'Retail' UNION ALL
SELECT 'MORTGAGE', 'Residential Mortgage', 'Loan', 'Lending' UNION ALL
SELECT 'AUTO', 'Auto Loan', 'Loan', 'Lending' UNION ALL
SELECT 'PERSONAL', 'Personal Loan', 'Loan', 'Lending' UNION ALL
SELECT 'HELOC', 'Home Equity Line of Credit', 'Loan', 'Lending' UNION ALL
SELECT 'COMMERCIAL', 'Commercial Loan', 'Loan', 'Commercial' UNION ALL
SELECT 'SBA', 'SBA Loan', 'Loan', 'Commercial' UNION ALL
SELECT 'VISA_PLATINUM', 'Visa Platinum Card', 'Card', 'Cards' UNION ALL
SELECT 'MC_GOLD', 'Mastercard Gold', 'Card', 'Cards' UNION ALL
SELECT 'VISA_SIGNATURE', 'Visa Signature Card', 'Card', 'Cards' UNION ALL
SELECT 'MC_WORLD', 'Mastercard World', 'Card', 'Cards' UNION ALL
SELECT 'VISA_CLASSIC', 'Visa Classic Card', 'Card', 'Cards' UNION ALL
SELECT 'BROKERAGE', 'Brokerage Account', 'Investment', 'Wealth' UNION ALL
SELECT 'IRA_WM', 'IRA - Wealth Managed', 'Investment', 'Wealth' UNION ALL
SELECT 'ROTH_IRA', 'Roth IRA', 'Investment', 'Wealth' UNION ALL
SELECT '401K', '401(k) Plan', 'Investment', 'Wealth' UNION ALL
SELECT 'TRUST', 'Trust Account', 'Investment', 'Wealth'
