CREATE OR REPLACE TABLE `${project_id}.fsi_reference.ref_country_codes` AS
SELECT 'US' AS country_code, 'United States' AS country_name, 'USD' AS currency UNION ALL
SELECT 'GB', 'United Kingdom', 'GBP' UNION ALL SELECT 'DE', 'Germany', 'EUR' UNION ALL
SELECT 'FR', 'France', 'EUR' UNION ALL SELECT 'JP', 'Japan', 'JPY' UNION ALL
SELECT 'CA', 'Canada', 'CAD' UNION ALL SELECT 'AU', 'Australia', 'AUD' UNION ALL
SELECT 'CH', 'Switzerland', 'CHF' UNION ALL SELECT 'CN', 'China', 'CNY' UNION ALL
SELECT 'MX', 'Mexico', 'MXN' UNION ALL SELECT 'BR', 'Brazil', 'BRL' UNION ALL
SELECT 'IN', 'India', 'INR' UNION ALL SELECT 'KR', 'South Korea', 'KRW' UNION ALL
SELECT 'SG', 'Singapore', 'SGD' UNION ALL SELECT 'HK', 'Hong Kong', 'HKD' UNION ALL
SELECT 'SE', 'Sweden', 'SEK' UNION ALL SELECT 'NO', 'Norway', 'NOK' UNION ALL
SELECT 'NL', 'Netherlands', 'EUR' UNION ALL SELECT 'IE', 'Ireland', 'EUR' UNION ALL
SELECT 'IT', 'Italy', 'EUR'
