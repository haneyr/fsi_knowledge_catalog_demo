CREATE OR REPLACE TABLE `${project_id}.fsi_reference.ref_fee_tiers` AS
SELECT 'Standard' AS tier_name, 0 AS min_aum, 249999 AS max_aum, 150 AS advisory_fee_bps, 75 AS management_fee_bps UNION ALL
SELECT 'Preferred', 250000, 999999, 125, 60 UNION ALL
SELECT 'Premier', 1000000, 4999999, 100, 50 UNION ALL
SELECT 'Private Banking', 5000000, 24999999, 75, 40 UNION ALL
SELECT 'Ultra HNW', 25000000, 999999999, 50, 25
