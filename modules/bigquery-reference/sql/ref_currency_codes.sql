CREATE OR REPLACE TABLE `${project_id}.fsi_reference.ref_currency_codes` AS
SELECT 'USD' AS currency_code, 'US Dollar' AS currency_name, '$' AS symbol, 2 AS decimals UNION ALL
SELECT 'EUR', 'Euro', '€', 2 UNION ALL SELECT 'GBP', 'British Pound', '£', 2 UNION ALL
SELECT 'JPY', 'Japanese Yen', '¥', 0 UNION ALL SELECT 'CHF', 'Swiss Franc', 'CHF', 2 UNION ALL
SELECT 'CAD', 'Canadian Dollar', 'C$', 2 UNION ALL SELECT 'AUD', 'Australian Dollar', 'A$', 2 UNION ALL
SELECT 'CNY', 'Chinese Yuan', '¥', 2 UNION ALL SELECT 'MXN', 'Mexican Peso', 'Mex$', 2 UNION ALL
SELECT 'BRL', 'Brazilian Real', 'R$', 2 UNION ALL SELECT 'INR', 'Indian Rupee', '₹', 2 UNION ALL
SELECT 'KRW', 'South Korean Won', '₩', 0 UNION ALL SELECT 'SGD', 'Singapore Dollar', 'S$', 2 UNION ALL
SELECT 'HKD', 'Hong Kong Dollar', 'HK$', 2 UNION ALL SELECT 'SEK', 'Swedish Krona', 'kr', 2 UNION ALL
SELECT 'NOK', 'Norwegian Krone', 'kr', 2
