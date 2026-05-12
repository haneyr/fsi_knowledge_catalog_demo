CREATE OR REPLACE TABLE `${project_id}.fsi_reference.ref_naics_codes` AS
SELECT '11' AS naics_code, 'Agriculture, Forestry, Fishing and Hunting' AS description UNION ALL
SELECT '21', 'Mining, Quarrying, and Oil and Gas Extraction' UNION ALL
SELECT '22', 'Utilities' UNION ALL
SELECT '23', 'Construction' UNION ALL
SELECT '31', 'Manufacturing - Food, Beverage, Textile' UNION ALL
SELECT '32', 'Manufacturing - Wood, Paper, Chemical' UNION ALL
SELECT '33', 'Manufacturing - Metal, Machinery, Electronics' UNION ALL
SELECT '42', 'Wholesale Trade' UNION ALL
SELECT '44', 'Retail Trade - Motor Vehicle, Furniture, Electronics' UNION ALL
SELECT '45', 'Retail Trade - General, Food, Health' UNION ALL
SELECT '48', 'Transportation and Warehousing' UNION ALL
SELECT '49', 'Transportation - Postal, Warehousing' UNION ALL
SELECT '51', 'Information' UNION ALL
SELECT '52', 'Finance and Insurance' UNION ALL
SELECT '53', 'Real Estate and Rental and Leasing' UNION ALL
SELECT '54', 'Professional, Scientific, and Technical Services' UNION ALL
SELECT '55', 'Management of Companies and Enterprises' UNION ALL
SELECT '56', 'Administrative and Support Services' UNION ALL
SELECT '61', 'Educational Services' UNION ALL
SELECT '62', 'Health Care and Social Assistance' UNION ALL
SELECT '71', 'Arts, Entertainment, and Recreation' UNION ALL
SELECT '72', 'Accommodation and Food Services' UNION ALL
SELECT '81', 'Other Services' UNION ALL
SELECT '92', 'Public Administration'
