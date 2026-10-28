CREATE OR REPLACE TABLE `${project_id}.retail_reference.ref_product_catalog` AS
SELECT 'POINTS_REWARDS' AS product_code, 'Northwind Points Rewards' AS product_name, 'Loyalty Tier' AS category, 'Customer Loyalty' AS division UNION ALL
SELECT 'VIP_CASHBACK', 'VIP Cashback Tier', 'Loyalty Tier', 'Customer Loyalty' UNION ALL
SELECT 'STORE_CREDIT', 'Omnichannel Store Credit Wallet', 'Loyalty Tier', 'Customer Loyalty' UNION ALL
SELECT 'GIFT_WALLET', 'Digital Gift Card & eWallet', 'Loyalty Tier', 'Customer Loyalty' UNION ALL
SELECT 'EMPLOYEE_PERKS', 'Associate & Family Perks Tier', 'Loyalty Tier', 'Customer Loyalty' UNION ALL
SELECT 'PAY_IN_4', 'Pay-in-4 Biweekly Zero-APR Plan', 'BNPL Plan', 'Checkout Financing' UNION ALL
SELECT 'MONTHLY_3M', '3-Month Express Installment Plan', 'BNPL Plan', 'Checkout Financing' UNION ALL
SELECT 'MONTHLY_6M', '6-Month Standard Installment Plan', 'BNPL Plan', 'Checkout Financing' UNION ALL
SELECT 'SEASONAL_PROMO_12M', '12-Month Holiday Promotional Plan', 'BNPL Plan', 'Checkout Financing' UNION ALL
SELECT 'APPLIANCE_FINANCING_18M', '18-Month Home & Appliance Financing', 'BNPL Plan', 'Checkout Financing' UNION ALL
SELECT 'VIP_FLEX_PAY', 'VIP Insider Flexible Pay Plan', 'BNPL Plan', 'Checkout Financing' UNION ALL
SELECT 'NORTHWIND_REWARDS_PLCC', 'Northwind Rewards Store Card (PLCC)', 'Store Card', 'Payment Tenders' UNION ALL
SELECT 'NORTHWIND_VISA_SIGNATURE', 'Northwind Co-Brand Visa Signature', 'Store Card', 'Payment Tenders' UNION ALL
SELECT 'VIP_INSIDER_CHARGE', 'VIP Insider Charge Card', 'Store Card', 'Payment Tenders' UNION ALL
SELECT 'NORTHWIND_MASTERCARD', 'Northwind World Mastercard', 'Store Card', 'Payment Tenders' UNION ALL
SELECT 'STORE_REWARDS_BASIC', 'Northwind Basic Store Card', 'Store Card', 'Payment Tenders' UNION ALL
SELECT 'FLAGSHIP_STORE', 'Flagship Store Assortment', 'Merchandising Channel', 'Merchandising' UNION ALL
SELECT 'OMNICHANNEL', 'Omnichannel Core Assortment', 'Merchandising Channel', 'Merchandising' UNION ALL
SELECT 'ECOMMERCE_ONLY', 'Digital-First E-Commerce Assortment', 'Merchandising Channel', 'Merchandising' UNION ALL
SELECT 'OUTLET', 'Northwind Rack & Outlet Assortment', 'Merchandising Channel', 'Merchandising' UNION ALL
SELECT 'VIP_CLIENTELING', 'VIP Clienteling Capsule Assortment', 'Merchandising Channel', 'Merchandising'
