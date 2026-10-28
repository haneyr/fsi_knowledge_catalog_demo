CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_vip_members` AS
SELECT
  CONCAT('WMC-', LPAD(CAST(n AS STRING), 7, '0')) AS wm_client_id,
  CASE WHEN MOD(n, 2) = 0 THEN CONCAT('CUST-', LPAD(CAST(MOD(n * 2, 20000) + 1 AS STRING), 8, '0')) ELSE NULL END AS retail_customer_id,
  CASE MOD(n, 20)
    WHEN 0 THEN 'James' WHEN 1 THEN 'Maya' WHEN 2 THEN 'Liam' WHEN 3 THEN 'Chloe'
    WHEN 4 THEN 'Noah' WHEN 5 THEN 'Elena' WHEN 6 THEN 'Lucas' WHEN 7 THEN 'Zoe'
    WHEN 8 THEN 'Ethan' WHEN 9 THEN 'Aria' WHEN 10 THEN 'Mason' WHEN 11 THEN 'Lily'
    WHEN 12 THEN 'Logan' WHEN 13 THEN 'Nora' WHEN 14 THEN 'Caleb' WHEN 15 THEN ' Sophia'
    WHEN 16 THEN 'Owen' WHEN 17 THEN 'Hannah' WHEN 18 THEN 'Isaac' ELSE 'Claire'
  END AS first_name,
  CASE MOD(n, 10) WHEN 0 THEN 'Chen' WHEN 1 THEN 'Patel' WHEN 2 THEN 'Nguyen' WHEN 3 THEN 'Kim' WHEN 4 THEN 'Reyes' WHEN 5 THEN 'Okafor' WHEN 6 THEN 'Silva' WHEN 7 THEN 'Kowalski' WHEN 8 THEN 'Bennett' ELSE 'Sullivan' END AS last_name,
  CASE MOD(n, 5)
    WHEN 0 THEN 'Platinum VIP' WHEN 1 THEN 'Diamond VIP' WHEN 2 THEN 'Platinum VIP' WHEN 3 THEN 'Gold Insider' ELSE 'Platinum VIP'
  END AS client_tier,
  ROUND(CASE MOD(n, 5)
    WHEN 0 THEN 2200 + RAND() * 4800
    WHEN 1 THEN 6500 + RAND() * 12000
    WHEN 2 THEN 1800 + RAND() * 3600
    WHEN 3 THEN 950 + RAND() * 1900
    ELSE 2400 + RAND() * 5200
  END, 2) AS total_aum,
  CASE MOD(n, 6)
    WHEN 0 THEN 'Low Return Risk' WHEN 1 THEN 'Standard Return Profile' WHEN 2 THEN 'Frequent Size Exchange'
    WHEN 3 THEN 'High-Bracket Seasonal' WHEN 4 THEN 'Elevated Return Velocity' ELSE 'Standard Return Profile'
  END AS risk_tolerance,
  CASE MOD(n, 5)
    WHEN 0 THEN 'Seasonal Wardrobe Curation' WHEN 1 THEN 'Early Access Capsule Drops' WHEN 2 THEN 'Omnichannel Concierge Styling'
    WHEN 3 THEN 'Cashback & Points Maximization' ELSE 'Sustainable & Eco Brands'
  END AS investment_objective,
  CONCAT('ADV-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS primary_advisor_id,
  DATE_ADD('2016-01-01', INTERVAL CAST(FLOOR(RAND() * 3200) AS INT64) DAY) AS relationship_start_date,
  CASE MOD(n, 4) WHEN 0 THEN 'Individual Member' WHEN 1 THEN 'Household Shared' WHEN 2 THEN 'VIP Styling Suite' ELSE 'Corporate Gifting' END AS account_type,
  CASE MOD(n, 3)
    WHEN 0 THEN 'Stylist-Curated' WHEN 1 THEN 'Self-Directed' ELSE 'Concierge Assisted'
  END AS management_type,
  CASE MOD(n, 6) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' WHEN 4 THEN 'Waitlist' ELSE 'Inactive' END AS client_status,
  CASE WHEN MOD(n, 10) = 0 THEN TRUE ELSE FALSE END AS accredited_investor,
  CASE WHEN MOD(n, 20) = 0 THEN TRUE ELSE FALSE END AS qualified_purchaser,
  LPAD(CAST(MOD(n * 13, 900000000) AS STRING), 9, '0') AS tax_id,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
