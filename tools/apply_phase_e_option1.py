#!/usr/bin/env python3
"""
Phase E (F2) Option 1: Purge surviving FSI semantics from SQL values and distributions
while keeping all table and column names unchanged and preserving all intentional DQ defects.
"""
from pathlib import Path

REPO = Path("/home/aelitchfield/knowledge_catalog_demo")
MED_SQL = REPO / "modules" / "bigquery-medallion" / "sql"
REF_SQL = REPO / "modules" / "bigquery-reference" / "sql"

FILES = {}

# 1. bronze_bnpl_plans.sql
FILES[MED_SQL / "bronze_bnpl_plans.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_bnpl_plans` AS
SELECT
  CONCAT('LN-', LPAD(CAST(n AS STRING), 9, '0')) AS bnpl_plan_id,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS customer_id,
  CASE MOD(n, 6)
    WHEN 0 THEN 'PAY_IN_4' WHEN 1 THEN 'MONTHLY_3M' WHEN 2 THEN 'MONTHLY_6M'
    WHEN 3 THEN 'SEASONAL_PROMO_12M' WHEN 4 THEN 'APPLIANCE_FINANCING_18M' ELSE 'VIP_FLEX_PAY'
  END AS plan_type,
  ROUND(CASE MOD(n, 6)
    WHEN 0 THEN 50 + RAND() * 190
    WHEN 1 THEN 75 + RAND() * 250
    WHEN 2 THEN 110 + RAND() * 380
    WHEN 3 THEN 140 + RAND() * 520
    WHEN 4 THEN 250 + RAND() * 1650
    ELSE 85 + RAND() * 340
  END, 2) AS original_amount,
  ROUND(CASE MOD(n, 6)
    WHEN 0 THEN 35 + RAND() * 130
    WHEN 1 THEN 50 + RAND() * 180
    WHEN 2 THEN 75 + RAND() * 260
    WHEN 3 THEN 95 + RAND() * 360
    WHEN 4 THEN 180 + RAND() * 1150
    ELSE 60 + RAND() * 240
  END, 2) AS current_balance,
  ROUND(CASE WHEN MOD(n, 6) = 0 THEN 0.0 ELSE 0.04 + RAND() * 0.14 END, 4) AS interest_rate,
  CASE MOD(n, 5) WHEN 0 THEN 'ZERO_APR_PROMO' WHEN 1 THEN 'FIXED_INSTALLMENT' WHEN 2 THEN 'FIXED_INSTALLMENT' WHEN 3 THEN 'DEFERRED_INTEREST' ELSE 'FIXED_INSTALLMENT' END AS rate_type,
  CAST(CASE MOD(n, 6)
    WHEN 0 THEN 2 WHEN 1 THEN 3 WHEN 2 THEN 6 WHEN 3 THEN 12 WHEN 4 THEN 18 ELSE 6
  END AS INT64) AS term_months,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(FLOOR(RAND() * 540) + 15 AS INT64) DAY) AS origination_date,
  DATE_ADD(CURRENT_DATE(), INTERVAL CAST(FLOOR(RAND() * 360) + 30 AS INT64) DAY) AS maturity_date,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Current' WHEN 1 THEN 'Current' WHEN 2 THEN 'Current' WHEN 3 THEN 'Current'
    WHEN 4 THEN '30 Days Past Due' WHEN 5 THEN '60 Days Past Due'
    WHEN 6 THEN '90+ Days Past Due' ELSE 'Current'
  END AS delinquency_status,
  CASE WHEN MOD(n, 6) IN (3, 4) THEN ROUND(0.50 + RAND() * 0.45, 2) ELSE NULL END AS ltv_ratio,
  CAST(CASE MOD(n, 10)
    WHEN 5 THEN 32 + FLOOR(RAND() * 18)
    WHEN 6 THEN 55 + FLOOR(RAND() * 18)
    WHEN 7 THEN 76 + FLOOR(RAND() * 22)
    ELSE 8 + FLOOR(RAND() * 20)
  END AS INT64) AS return_risk_score_at_signup,
  ROUND(0.05 + RAND() * 0.30, 2) AS dti_ratio,
  CASE MOD(n, 6) WHEN 4 THEN 'High-Ticket Home & Appliance Basket' ELSE NULL END AS collateral_description,
  CASE MOD(n, 10)
    WHEN 0 THEN 'Low' WHEN 1 THEN 'Low' WHEN 2 THEN 'Low' WHEN 3 THEN 'Low'
    WHEN 4 THEN 'Low' WHEN 5 THEN 'Watch' WHEN 6 THEN 'Elevated'
    WHEN 7 THEN 'High Risk' WHEN 8 THEN 'Low' ELSE 'Low'
  END AS risk_rating,
  CASE MOD(n, 10)
    WHEN 0 THEN '4481' WHEN 1 THEN '4482' WHEN 2 THEN '4421' WHEN 3 THEN '4431' WHEN 4 THEN '4461'
    WHEN 5 THEN '4511' WHEN 6 THEN '4522' WHEN 7 THEN '4541' WHEN 8 THEN '4483' ELSE '4532'
  END AS naics_code,
  CONCAT('BR-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS originating_store_id,
  CONCAT('LO-', LPAD(CAST(MOD(n, 200) + 1 AS STRING), 4, '0')) AS store_associate_id,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 15000)) AS n
"""

# 2. gold_bnpl_delinquency_analysis.sql
FILES[MED_SQL / "gold_bnpl_delinquency_analysis.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_bnpl_delinquency_analysis` AS
SELECT
  l.plan_type,
  l.originating_store_id,
  l.naics_code AS industry_naics,
  l.delinquency_status,
  COUNT(*) AS plan_count,
  ROUND(SUM(l.current_balance), 2) AS total_balance,
  ROUND(AVG(l.current_balance), 2) AS avg_balance,
  ROUND(AVG(l.return_risk_score_at_signup), 1) AS avg_origination_risk_score,
  ROUND(AVG(l.interest_rate), 4) AS avg_rate,
  ROUND(AVG(l.ltv_ratio), 4) AS avg_ltv,
  COUNTIF(l.risk_rating IN ('Elevated', 'High Risk')) AS classified_count,
  ROUND(SAFE_DIVIDE(COUNTIF(l.risk_rating IN ('Elevated', 'High Risk')), COUNT(*)) * 100, 2) AS classified_rate_pct
FROM `${project_id}.retail_silver.silver_bnpl_plans` l
WHERE l.delinquency_status != 'Current'
GROUP BY 1, 2, 3, 4
"""

# 3. gold_bnpl_plan_summary.sql (round avg_return_risk_score to 1 decimal for 0-100 scale clarity)
FILES[MED_SQL / "gold_bnpl_plan_summary.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_bnpl_plan_summary` AS
SELECT
  l.plan_type,
  l.risk_rating,
  l.delinquency_status,
  COUNT(*) AS plan_count,
  ROUND(SUM(l.original_amount), 2) AS total_originated,
  ROUND(SUM(l.current_balance), 2) AS total_outstanding,
  ROUND(AVG(l.interest_rate), 4) AS avg_interest_rate,
  ROUND(AVG(l.return_risk_score_at_signup), 1) AS avg_return_risk_score,
  ROUND(AVG(l.ltv_ratio), 4) AS avg_ltv,
  ROUND(AVG(l.dti_ratio), 4) AS avg_dti,
  ROUND(AVG(l.term_months), 1) AS avg_term_months,
  COUNTIF(l.delinquency_status != 'Current') AS delinquent_count,
  ROUND(SAFE_DIVIDE(COUNTIF(l.delinquency_status != 'Current'), COUNT(*)) * 100, 2) AS delinquency_rate_pct
FROM `${project_id}.retail_silver.silver_bnpl_plans` l
GROUP BY 1, 2, 3
"""

# 4. bronze_bnpl_payments.sql
FILES[MED_SQL / "bronze_bnpl_payments.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_bnpl_payments` AS
SELECT
  CONCAT('LPMT-', LPAD(CAST(n AS STRING), 10, '0')) AS payment_id,
  CONCAT('LN-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 9, '0')) AS bnpl_plan_id,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(FLOOR(RAND() * 365) AS INT64) DAY) AS payment_date,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(FLOOR(RAND() * 365) AS INT64) DAY) AS due_date,
  ROUND(18 + RAND() * 240, 2) AS payment_amount,
  ROUND(15 + RAND() * 210, 2) AS principal_amount,
  ROUND(CASE WHEN MOD(n, 3) = 0 THEN 0 ELSE 1.5 + RAND() * 18 END, 2) AS interest_amount,
  ROUND(0.0, 2) AS escrow_amount,
  ROUND(CASE WHEN MOD(n, 30) = 0 THEN 5 + RAND() * 15 ELSE 0 END, 2) AS late_fee,
  CASE MOD(n, 6) WHEN 0 THEN 'Saved Debit Card' WHEN 1 THEN 'Apple Pay' WHEN 2 THEN 'Google Pay' WHEN 3 THEN 'Northwind Wallet' WHEN 4 THEN 'Auto-Pay Card' ELSE 'Saved Debit Card' END AS payment_method,
  CASE MOD(n, 10) WHEN 0 THEN 'Late' WHEN 1 THEN 'Partial' ELSE 'On Time' END AS payment_status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
"""

# 5. bronze_privacy_consents.sql
FILES[MED_SQL / "bronze_privacy_consents.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_privacy_consents` AS
SELECT
  CONCAT('CNS-', LPAD(CAST(n AS STRING), 8, '0')) AS kyc_id,
  CONCAT('CUST-', LPAD(CAST(n AS STRING), 8, '0')) AS customer_id,
  CASE MOD(n, 3) WHEN 0 THEN 'STANDARD_OPT_IN' WHEN 1 THEN 'ENHANCED_PRIVACY_REVIEW' ELSE 'EXPRESS_CHECKOUT_CONSENT' END AS due_diligence_level,
  CASE MOD(n, 4) WHEN 0 THEN 'Completed' WHEN 1 THEN 'Completed' WHEN 2 THEN 'In Progress' ELSE 'Expired' END AS verification_status,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(30 + MOD(n, 300) AS INT64) DAY) AS last_review_date,
  CASE
    WHEN MOD(n, 5) IN (0, 4) THEN
      CASE WHEN MOD(n, 100) = 0
        THEN DATE_SUB(CURRENT_DATE(), INTERVAL CAST(1 + MOD(n, 25) AS INT64) DAY)
        ELSE DATE_ADD(CURRENT_DATE(), INTERVAL CAST(15 + MOD(n, 320) AS INT64) DAY)
      END
    WHEN MOD(n, 5) IN (1, 2) THEN
      CASE WHEN MOD(n, 25) = 0
        THEN DATE_SUB(CURRENT_DATE(), INTERVAL CAST(1 + MOD(n, 35) AS INT64) DAY)
        ELSE DATE_ADD(CURRENT_DATE(), INTERVAL CAST(10 + MOD(n, 280) AS INT64) DAY)
      END
    ELSE
      CASE WHEN MOD(n, 11) = 0
        THEN DATE_SUB(CURRENT_DATE(), INTERVAL CAST(1 + MOD(n, 45) AS INT64) DAY)
        ELSE DATE_ADD(CURRENT_DATE(), INTERVAL CAST(7 + MOD(n, 240) AS INT64) DAY)
      END
  END AS next_review_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Low' WHEN 1 THEN 'Watch' WHEN 2 THEN 'Elevated' WHEN 3 THEN 'High Risk' ELSE 'Low' END AS risk_score_category,
  CAST(CASE MOD(n, 5)
    WHEN 0 THEN 6 + FLOOR(RAND() * 18)
    WHEN 4 THEN 8 + FLOOR(RAND() * 18)
    WHEN 1 THEN 30 + FLOOR(RAND() * 18)
    WHEN 2 THEN 52 + FLOOR(RAND() * 18)
    ELSE 74 + FLOOR(RAND() * 24)
  END AS INT64) AS risk_score,
  CASE WHEN MOD(n, 50) = 0 THEN TRUE ELSE FALSE END AS pep_flag,
  CASE WHEN MOD(n, 100) = 0 THEN TRUE ELSE FALSE END AS sanctions_flag,
  CASE WHEN MOD(n, 200) = 0 THEN TRUE ELSE FALSE END AS adverse_media_flag,
  CASE MOD(n, 4)
    WHEN 0 THEN 'Email Double Opt-In' WHEN 1 THEN 'SMS OTP Verification' WHEN 2 THEN 'Loyalty App Passkey' ELSE 'In-Store POS Consent'
  END AS id_document_type,
  CASE MOD(n, 3) WHEN 0 THEN 'US' WHEN 1 THEN 'US' ELSE CASE MOD(n, 10) WHEN 0 THEN 'GB' WHEN 1 THEN 'CA' WHEN 2 THEN 'MX' ELSE 'US' END END AS country_of_citizenship,
  CASE WHEN MOD(n, 30) = 0 THEN CONCAT('HH-', LPAD(CAST(n AS STRING), 8, '0')) ELSE NULL END AS beneficial_owner_id,
  CONCAT('ANL-', LPAD(CAST(MOD(n, 50) + 1 AS STRING), 3, '0')) AS reviewer_id,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 20000)) AS n
"""

# 6. bronze_fraud_alerts.sql
FILES[MED_SQL / "bronze_fraud_alerts.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_fraud_alerts` AS
SELECT
  CONCAT('FRD-', LPAD(CAST(n AS STRING), 8, '0')) AS alert_id,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS customer_id,
  CASE WHEN MOD(n, 2) = 0
    THEN CONCAT('TXN-', LPAD(CAST(CAST(FLOOR(RAND() * 100000) + 1 AS INT64) AS STRING), 12, '0'))
    ELSE CONCAT('CTXN-', LPAD(CAST(CAST(FLOOR(RAND() * 80000) + 1 AS INT64) AS STRING), 12, '0'))
  END AS transaction_id,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Serial Wardrobing Return Pattern' WHEN 1 THEN 'Cross-Region Gift Card Velocity'
    WHEN 2 THEN 'Promo Code Stacking Abuse' WHEN 3 THEN 'Loyalty Account Takeover Attempt'
    WHEN 4 THEN 'Card-Not-Present E-Com Anomaly' WHEN 5 THEN 'Split-Receipt Refund Threshold Bypass'
    WHEN 6 THEN 'Receiptless High-Value Return' ELSE 'Synthetic Shopper Identity Indicator'
  END AS alert_type,
  ROUND(15 + RAND() * 82, 0) AS fraud_score,
  CASE MOD(n, 5)
    WHEN 0 THEN 'High' WHEN 1 THEN 'Medium' WHEN 2 THEN 'Low' WHEN 3 THEN 'Critical' ELSE 'Medium'
  END AS severity,
  CASE MOD(n, 4) WHEN 0 THEN 'Open' WHEN 1 THEN 'Investigating' WHEN 2 THEN 'Closed - Confirmed Fraud' ELSE 'Closed - False Positive' END AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS alert_date,
  CASE WHEN MOD(n, 3) != 0 THEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 200 * 24 * 60) AS INT64) MINUTE) ELSE NULL END AS resolved_date,
  CONCAT('ANL-', LPAD(CAST(MOD(n, 50) + 1 AS STRING), 3, '0')) AS assigned_analyst,
  ROUND(CASE WHEN MOD(n, 4) = 2 THEN 25 + RAND() * 650 ELSE 0 END, 2) AS loss_amount,
  CASE WHEN MOD(n, 10) = 0 THEN TRUE ELSE FALSE END AS sar_filed,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
"""

# 7. bronze_promo_abuse_cases.sql
FILES[MED_SQL / "bronze_promo_abuse_cases.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_promo_abuse_cases` AS
SELECT
  CONCAT('COMP-', LPAD(CAST(n AS STRING), 7, '0')) AS case_id,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Serial Return Abuse Investigation' WHEN 1 THEN 'High-Value Refund Review' WHEN 2 THEN 'Reseller Bulk Purchase Violation'
    WHEN 3 THEN 'Chargeback Dispute Escalation' WHEN 4 THEN 'CCPA Deletion Verification' WHEN 5 THEN 'Employee Discount Misuse Review'
    WHEN 6 THEN 'Promo Stacking & Coupon Fraud Alert' ELSE 'Loyalty Points Transfer Abuse'
  END AS case_type,
  CASE MOD(n, 5) WHEN 0 THEN 'High' WHEN 1 THEN 'Medium' WHEN 2 THEN 'Low' WHEN 3 THEN 'Critical' ELSE 'Medium' END AS severity,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS related_customer_id,
  CASE WHEN MOD(n, 2) = 0 THEN CONCAT('ACCT-', LPAD(CAST(CAST(FLOOR(RAND() * 50000) + 1 AS INT64) AS STRING), 10, '0')) ELSE NULL END AS related_account_id,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(RAND() * 800) AS INT64) DAY) AS opened_date,
  CASE WHEN MOD(n, 3) != 0 THEN DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 500) AS INT64) DAY) ELSE NULL END AS closed_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Open' WHEN 1 THEN 'Under Review' WHEN 2 THEN 'Closed - No Action' WHEN 3 THEN 'Closed - Fraud Report Filed' ELSE 'Escalated' END AS status,
  CONCAT('ANL-', LPAD(CAST(MOD(n, 50) + 1 AS STRING), 3, '0')) AS assigned_analyst,
  CASE WHEN MOD(n, 5) = 3 THEN TRUE ELSE FALSE END AS sar_filed,
  CASE WHEN MOD(n, 5) = 3 THEN CONCAT('FRD-', LPAD(CAST(n AS STRING), 8, '0')) ELSE NULL END AS sar_filing_id,
  CONCAT('Loss Prevention review for case ', CAST(n AS STRING)) AS narrative_summary,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'HELIOS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 3000)) AS n
"""

# 8. bronze_high_value_refunds.sql
FILES[MED_SQL / "bronze_high_value_refunds.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_high_value_refunds` AS
SELECT
  CONCAT('WIRE-', LPAD(CAST(n AS STRING), 10, '0')) AS wire_id,
  CONCAT('ACCT-', LPAD(CAST(CAST(FLOOR(RAND() * 50000) + 1 AS INT64) AS STRING), 10, '0')) AS originator_account_id,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS originator_customer_id,
  CONCAT('SHOPPER-', LPAD(CAST(n AS STRING), 8, '0')) AS beneficiary_name,
  CONCAT('0', CAST(10000000 + MOD(n * 31, 90000000) AS STRING)) AS beneficiary_routing,
  CONCAT(CAST(1000000 + MOD(n * 17, 9000000) AS STRING)) AS beneficiary_account,
  ROUND(45 + RAND() * 1450, 2) AS amount,
  CASE MOD(n, 3) WHEN 0 THEN 'USD' WHEN 1 THEN 'CAD' ELSE 'USD' END AS currency,
  CASE MOD(n, 3) WHEN 0 THEN 'In-Store POS Refund' WHEN 1 THEN 'Omnichannel Mail Return' ELSE 'E-Commerce Original Tender' END AS wire_type,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS initiation_date,
  CASE MOD(n, 4) WHEN 0 THEN 'Completed' WHEN 1 THEN 'Completed' WHEN 2 THEN 'Pending Manager Override' ELSE 'Completed' END AS status,
  CASE WHEN MOD(n, 20) = 0 THEN TRUE ELSE FALSE END AS ofac_hold,
  CASE WHEN MOD(n, 10) = 0 THEN TRUE ELSE FALSE END AS requires_ctr,
  CASE WHEN MOD(n, 25) = 0 THEN TRUE ELSE FALSE END AS above_ctr_threshold,
  CONCAT('Return Reason: ', CASE MOD(n, 5) WHEN 0 THEN 'Defective Apparel Item' WHEN 1 THEN 'Damaged Home Furnishings' WHEN 2 THEN 'Size / Fit Exchange' WHEN 3 THEN 'Unopened Electronics Return' ELSE 'Order Cancelled in Transit' END) AS purpose,
  CASE MOD(n, 8) WHEN 0 THEN 'US' WHEN 1 THEN 'CA' WHEN 2 THEN 'US' WHEN 3 THEN 'US' WHEN 4 THEN 'GB' WHEN 5 THEN 'CA' WHEN 6 THEN 'US' ELSE 'US' END AS beneficiary_country,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
"""

# 9. bronze_customers.sql (preserve exact DOB nulls, member_tin unformatted rows, and dupes!)
FILES[MED_SQL / "bronze_customers.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_customers` AS
WITH base AS (
  SELECT
    n,
    CONCAT('CUST-', LPAD(CAST(n AS STRING), 8, '0')) AS customer_id,
    CASE MOD(n, 20)
      WHEN 0 THEN 'James' WHEN 1 THEN 'Mary' WHEN 2 THEN 'Robert' WHEN 3 THEN 'Patricia'
      WHEN 4 THEN 'John' WHEN 5 THEN 'Jennifer' WHEN 6 THEN 'Michael' WHEN 7 THEN 'Linda'
      WHEN 8 THEN 'David' WHEN 9 THEN 'Elizabeth' WHEN 10 THEN 'William' WHEN 11 THEN 'Barbara'
      WHEN 12 THEN 'Richard' WHEN 13 THEN 'Susan' WHEN 14 THEN 'Joseph' WHEN 15 THEN 'Jessica'
      WHEN 16 THEN 'Thomas' WHEN 17 THEN 'Sarah' WHEN 18 THEN 'Charles' ELSE 'Karen'
    END AS first_name,
    CASE MOD(n, 15)
      WHEN 0 THEN 'Smith' WHEN 1 THEN 'Johnson' WHEN 2 THEN 'Williams' WHEN 3 THEN 'Brown'
      WHEN 4 THEN 'Jones' WHEN 5 THEN 'Garcia' WHEN 6 THEN 'Miller' WHEN 7 THEN 'Davis'
      WHEN 8 THEN 'Rodriguez' WHEN 9 THEN 'Martinez' WHEN 10 THEN 'Anderson' WHEN 11 THEN 'Taylor'
      WHEN 12 THEN 'Thomas' WHEN 13 THEN 'Hernandez' ELSE 'Moore'
    END AS last_name,
    CASE
      WHEN MOD(n, 50) = 0 THEN NULL
      ELSE CAST(DATE_ADD('1945-01-01', INTERVAL CAST(FLOOR(RAND() * 25000) AS INT64) DAY) AS STRING)
    END AS date_of_birth,
    CASE MOD(n, 80)
      WHEN 0 THEN CONCAT(CAST(100 + MOD(n, 900) AS STRING), CAST(10 + MOD(n, 90) AS STRING), CAST(1000 + MOD(n, 9000) AS STRING))
      ELSE CONCAT(CAST(100 + MOD(n, 900) AS STRING), '-', CAST(10 + MOD(n, 90) AS STRING), '-', CAST(1000 + MOD(n, 9000) AS STRING))
    END AS member_tin,
    CONCAT(CAST(100 + MOD(n, 9900) AS STRING), ' ', CASE MOD(n, 8)
      WHEN 0 THEN 'Main St' WHEN 1 THEN 'Oak Ave' WHEN 2 THEN 'Elm Dr' WHEN 3 THEN 'Park Blvd'
      WHEN 4 THEN 'Cedar Ln' WHEN 5 THEN 'Maple Rd' WHEN 6 THEN 'Pine St' ELSE 'Lake Ave'
    END) AS address_line1,
    CASE MOD(n, 12)
      WHEN 0 THEN 'New York' WHEN 1 THEN 'Los Angeles' WHEN 2 THEN 'Chicago' WHEN 3 THEN 'Houston'
      WHEN 4 THEN 'Phoenix' WHEN 5 THEN 'Philadelphia' WHEN 6 THEN 'San Antonio' WHEN 7 THEN 'San Diego'
      WHEN 8 THEN 'Dallas' WHEN 9 THEN 'San Jose' WHEN 10 THEN 'Austin' ELSE 'Jacksonville'
    END AS city,
    CASE MOD(n, 12)
      WHEN 0 THEN 'NY' WHEN 1 THEN 'CA' WHEN 2 THEN 'IL' WHEN 3 THEN 'TX'
      WHEN 4 THEN 'AZ' WHEN 5 THEN 'PA' WHEN 6 THEN 'TX' WHEN 7 THEN 'CA'
      WHEN 8 THEN 'TX' WHEN 9 THEN 'CA' WHEN 10 THEN 'TX' ELSE 'FL'
    END AS state,
    LPAD(CAST(10000 + MOD(n * 7, 90000) AS STRING), 5, '0') AS zip_code,
    CONCAT('(', CAST(200 + MOD(n, 800) AS STRING), ') ', CAST(200 + MOD(n, 800) AS STRING), '-', LPAD(CAST(MOD(n, 10000) AS STRING), 4, '0')) AS phone,
    CONCAT(LOWER(CASE MOD(n, 20)
      WHEN 0 THEN 'james' WHEN 1 THEN 'mary' WHEN 2 THEN 'robert' WHEN 3 THEN 'patricia'
      WHEN 4 THEN 'john' WHEN 5 THEN 'jennifer' WHEN 6 THEN 'michael' WHEN 7 THEN 'linda'
      WHEN 8 THEN 'david' WHEN 9 THEN 'elizabeth' WHEN 10 THEN 'william' WHEN 11 THEN 'barbara'
      WHEN 12 THEN 'richard' WHEN 13 THEN 'susan' WHEN 14 THEN 'joseph' WHEN 15 THEN 'jessica'
      WHEN 16 THEN 'thomas' WHEN 17 THEN 'sarah' WHEN 18 THEN 'charles' ELSE 'karen'
    END), '.', LOWER(CASE MOD(n, 15)
      WHEN 0 THEN 'smith' WHEN 1 THEN 'johnson' WHEN 2 THEN 'williams' WHEN 3 THEN 'brown'
      WHEN 4 THEN 'jones' WHEN 5 THEN 'garcia' WHEN 6 THEN 'miller' WHEN 7 THEN 'davis'
      WHEN 8 THEN 'rodriguez' WHEN 9 THEN 'martinez' WHEN 10 THEN 'anderson' WHEN 11 THEN 'taylor'
      WHEN 12 THEN 'thomas' WHEN 13 THEN 'hernandez' ELSE 'moore'
    END), '@email.com') AS email,
    CASE MOD(n, 5)
      WHEN 0 THEN 'Individual Shopper' WHEN 1 THEN 'Family Household' WHEN 2 THEN 'VIP Insider'
      WHEN 3 THEN 'Pro & Trade Buyer' ELSE 'Individual Shopper'
    END AS customer_type,
    CASE MOD(n, 6)
      WHEN 0 THEN 'Core Shopper' WHEN 1 THEN 'Preferred Member' WHEN 2 THEN 'Premier Loyalist'
      WHEN 3 THEN 'VIP Clienteling' WHEN 4 THEN 'Designer Trade' ELSE 'Core Shopper'
    END AS customer_segment,
    CASE MOD(n, 8)
      WHEN 0 THEN 'US Domestic' WHEN 1 THEN 'US Domestic' WHEN 2 THEN 'International Visitor'
      ELSE 'US Domestic'
    END AS citizenship_status,
    LPAD(CAST(MOD(n * 13, 900000000) AS STRING), 9, '0') AS tin,
    CASE MOD(n, 10)
      WHEN 0 THEN 'Apparel & Fashion' WHEN 1 THEN 'Outdoor & Fitness' WHEN 2 THEN 'Home & Interior Design'
      WHEN 3 THEN 'Consumer Electronics' WHEN 4 THEN 'Beauty & Wellness' WHEN 5 THEN 'Footwear & Athletic'
      WHEN 6 THEN 'Home Furnishings' WHEN 7 THEN 'Gifting & Seasonal' WHEN 8 THEN 'Kids & Family' ELSE 'Everyday Essentials'
    END AS industry,
    CASE MOD(n, 5)
      WHEN 0 THEN 'Low' WHEN 1 THEN 'Watch' WHEN 2 THEN 'Elevated' WHEN 3 THEN 'High Risk' ELSE 'Low'
    END AS kyc_risk_rating,
    CASE MOD(n, 3)
      WHEN 0 THEN 'Verified' WHEN 1 THEN 'Pending' ELSE 'Verified'
    END AS kyc_status,
    CONCAT('BR-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS primary_store_id,
    TIMESTAMP_ADD(TIMESTAMP '2015-01-01 00:00:00 UTC', INTERVAL CAST(FLOOR(RAND() * 3600 * 24 * 60) AS INT64) MINUTE) AS account_opened_date,
    CASE MOD(n, 3) WHEN 0 THEN 'ORION' WHEN 1 THEN 'ORION_LEGACY' ELSE 'ORION' END AS source_system,
    TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
  FROM UNNEST(GENERATE_ARRAY(1, 20000)) AS n
),
dupes AS (
  SELECT * FROM base WHERE MOD(n, 500) = 0
)
SELECT * EXCEPT(n) FROM base
UNION ALL
SELECT * EXCEPT(n) FROM dupes
"""

# 10. bronze_vip_members.sql
FILES[MED_SQL / "bronze_vip_members.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_vip_members` AS
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
"""

# 11. bronze_loyalty_accounts.sql
FILES[MED_SQL / "bronze_loyalty_accounts.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_loyalty_accounts` AS
SELECT
  CONCAT('ACCT-', LPAD(CAST(n AS STRING), 10, '0')) AS account_id,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(n / 3.0) + 1 AS INT64) AS STRING), 8, '0')) AS customer_id,
  CASE MOD(n, 8)
    WHEN 0 THEN 'POINTS_REWARDS' WHEN 1 THEN 'VIP_CASHBACK' WHEN 2 THEN 'STORE_CREDIT'
    WHEN 3 THEN 'GIFT_WALLET' WHEN 4 THEN 'POINTS_REWARDS' WHEN 5 THEN 'VIP_CASHBACK'
    WHEN 6 THEN 'EMPLOYEE_PERKS' ELSE 'POINTS_REWARDS'
  END AS account_type,
  CASE MOD(n, 4)
    WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' ELSE 'Dormant'
  END AS account_status,
  ROUND(CASE MOD(n, 8)
    WHEN 0 THEN 25 + RAND() * 220
    WHEN 1 THEN 80 + RAND() * 520
    WHEN 2 THEN 40 + RAND() * 310
    WHEN 3 THEN 20 + RAND() * 250
    WHEN 6 THEN 60 + RAND() * 450
    ELSE 15 + RAND() * 160
  END, 2) AS current_balance,
  ROUND(CASE MOD(n, 8)
    WHEN 0 THEN 20 + RAND() * 190
    WHEN 1 THEN 65 + RAND() * 460
    ELSE 10 + RAND() * 140
  END, 2) AS available_balance,
  ROUND(CASE MOD(n, 8)
    WHEN 0 THEN 0.02 WHEN 1 THEN 0.05
    WHEN 2 THEN 0.00 WHEN 3 THEN 0.00
    WHEN 6 THEN 0.10 ELSE 0.03
  END, 4) AS interest_rate,
  CONCAT('NW-RWD-', CAST(100000 + MOD(n * 17, 900000) AS STRING)) AS routing_number,
  DATE_ADD('2016-01-01', INTERVAL CAST(FLOOR(RAND() * 3200) AS INT64) DAY) AS open_date,
  CASE WHEN MOD(n, 25) = 0 THEN DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(RAND() * 700) AS INT64) DAY) ELSE NULL END AS close_date,
  CONCAT('BR-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS store_id,
  'USD' AS currency_code,
  CASE MOD(n, 8) WHEN 3 THEN CAST(MOD(n, 12) + 6 AS INT64) ELSE NULL END AS term_months,
  CASE MOD(n, 8) WHEN 3 THEN DATE_ADD(DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 400) AS INT64) DAY), INTERVAL CAST(MOD(n, 12) + 6 AS INT64) MONTH) ELSE NULL END AS maturity_date,
  CASE WHEN MOD(n, 20) = 0 THEN TRUE ELSE FALSE END AS joint_account,
  CASE MOD(n, 5) WHEN 0 THEN 'Online' WHEN 1 THEN 'Store' WHEN 2 THEN 'Mobile App' WHEN 3 THEN 'Checkout Prompt' ELSE 'Online' END AS origination_channel,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
"""

# 12. bronze_store_cards.sql
FILES[MED_SQL / "bronze_store_cards.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_store_cards` AS
SELECT
  CONCAT('CC-', LPAD(CAST(n AS STRING), 8, '0')) AS card_id,
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND() * 20000) + 1 AS INT64) AS STRING), 8, '0')) AS customer_id,
  CONCAT('ACCT-', LPAD(CAST(CAST(50000 + n AS INT64) AS STRING), 10, '0')) AS account_id,
  CASE MOD(n, 5)
    WHEN 0 THEN 'NORTHWIND_REWARDS_PLCC' WHEN 1 THEN 'NORTHWIND_VISA_SIGNATURE' WHEN 2 THEN 'VIP_INSIDER_CHARGE'
    WHEN 3 THEN 'NORTHWIND_MASTERCARD' ELSE 'STORE_REWARDS_BASIC'
  END AS card_type,
  CASE MOD(n, 5)
    WHEN 0 THEN 'Store Private Label' WHEN 1 THEN 'Visa' WHEN 2 THEN 'Store Private Label'
    WHEN 3 THEN 'Mastercard' ELSE 'Store Private Label'
  END AS network,
  CONCAT('XXXX-XXXX-XXXX-', LPAD(CAST(MOD(n, 10000) AS STRING), 4, '0')) AS masked_card_number,
  ROUND(300 + RAND() * 2700, 0) AS credit_limit,
  ROUND(25 + RAND() * 680, 2) AS current_balance,
  ROUND(200 + RAND() * 2000, 2) AS available_credit,
  ROUND(0.14 + RAND() * 0.14, 4) AS apr,
  ROUND(CASE WHEN MOD(n, 20) = 0 THEN 49 + RAND() * 50 ELSE 0 END, 2) AS annual_fee,
  CAST(8 + FLOOR(RAND() * 82) AS INT64) AS return_risk_score,
  DATE_ADD('2020-01-01', INTERVAL CAST(FLOOR(RAND() * 2000) AS INT64) DAY) AS issue_date,
  DATE_ADD('2026-01-01', INTERVAL CAST(FLOOR(RAND() * 1500) AS INT64) DAY) AS expiration_date,
  CASE MOD(n, 6) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' WHEN 4 THEN 'Frozen' ELSE 'Closed' END AS card_status,
  ROUND(CASE WHEN MOD(n, 5) = 0 THEN 10 + RAND() * 240 ELSE 0 END, 2) AS rewards_balance,
  CASE MOD(n, 4) WHEN 0 THEN 'Points' WHEN 1 THEN 'Cashback' WHEN 2 THEN 'Store Credit' ELSE 'Points' END AS rewards_type,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 15000)) AS n
"""

# 13. bronze_product_skus.sql (include ~1.5% malformed GTIN-13s so silver_product_skus also surfaces GTIN DQ issues!)
FILES[MED_SQL / "bronze_product_skus.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_product_skus` AS
SELECT
  CONCAT('SEC-', LPAD(CAST(n AS STRING), 6, '0')) AS security_id,
  UPPER(CONCAT(
    CASE MOD(n, 8) WHEN 0 THEN 'APP' WHEN 1 THEN 'ACC' WHEN 2 THEN 'HOM' WHEN 3 THEN 'ESS' WHEN 4 THEN 'OUT' WHEN 5 THEN 'BND' WHEN 6 THEN 'SEA' ELSE 'BTY' END,
    '-',
    LPAD(CAST(MOD(n, 999) + 1 AS STRING), 3, '0')
  )) AS ticker,
  CONCAT(
    CASE MOD(n, 8)
      WHEN 0 THEN 'Northwind Merino Knit ' WHEN 1 THEN 'Artisan Leather Tote ' WHEN 2 THEN 'Cast-Iron Dutch Oven '
      WHEN 3 THEN 'Organic Cotton Tee ' WHEN 4 THEN 'Trailhead Waterproof Shell ' WHEN 5 THEN 'Everyday Travel Pack '
      WHEN 6 THEN 'Holiday Cashmere Throw ' ELSE 'Botanical Facial Serum '
    END,
    CAST(n AS STRING)
  ) AS security_name,
  CASE
    WHEN MOD(n, 67) = 0 THEN CONCAT('BAD-GTIN-', CAST(MOD(n, 999) AS STRING))
    ELSE CONCAT('0085', LPAD(CAST(MOD(n * 7, 1000000000) AS STRING), 9, '0'))
  END AS gtin_13,
  CONCAT('NW-SKU-', LPAD(CAST(n AS STRING), 6, '0')) AS sku_code,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Apparel & Footwear' WHEN 1 THEN 'Accessories & Jewelry' WHEN 2 THEN 'Home & Living'
    WHEN 3 THEN 'Core Essentials' WHEN 4 THEN 'Outdoor & Activewear' WHEN 5 THEN 'Essentials Bundle'
    WHEN 6 THEN 'Seasonal & Gifting' ELSE 'Beauty & Personal Care'
  END AS security_type,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Apparel & Outerwear' WHEN 1 THEN 'Accessories & Jewelry' WHEN 2 THEN 'Home & Kitchen'
    WHEN 3 THEN 'Everyday Essentials' WHEN 4 THEN 'Outdoor & Activewear' WHEN 5 THEN 'Footwear'
    WHEN 6 THEN 'Seasonal & Promotional' ELSE 'Beauty & Personal Care'
  END AS asset_class,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Womens & Mens Apparel' WHEN 1 THEN 'Fashion Accessories' WHEN 2 THEN 'Culinary & Tabletop'
    WHEN 3 THEN 'Private Label Basics' WHEN 4 THEN 'Outdoor Recreation' WHEN 5 THEN 'Athletic Footwear'
    WHEN 6 THEN 'Seasonal Gifting' ELSE 'Clean Beauty & Skincare'
  END AS sector,
  CASE MOD(n, 5) WHEN 0 THEN 'US' WHEN 1 THEN 'US' WHEN 2 THEN 'VN' WHEN 3 THEN 'IT' ELSE 'PT' END AS country,
  'USD' AS currency,
  CASE MOD(n, 6) WHEN 0 THEN 'DIRECT_BRAND' WHEN 1 THEN 'PRIVATE_LABEL' WHEN 2 THEN 'WHOLESALE_DIST' WHEN 3 THEN 'EXCLUSIVE_COLLAB' WHEN 4 THEN 'MARKETPLACE_CURATED' ELSE 'DIRECT_BRAND' END AS exchange,
  ROUND(12.0 + RAND() * 340.0, 2) AS last_price,
  ROUND(0.32 + RAND() * 0.35, 2) AS dividend_yield,
  CASE WHEN MOD(n, 4) = 0 THEN ROUND(0.10 + RAND() * 0.25, 4) ELSE NULL END AS coupon_rate,
  DATE_ADD(CURRENT_DATE(), INTERVAL CAST(FLOOR(RAND() * 365) + 30 AS INT64) DAY) AS maturity_date,
  CASE MOD(n, 4) WHEN 0 THEN 'Tier-1 Certified' WHEN 1 THEN 'Preferred Vendor' WHEN 2 THEN 'Standard Supplier' ELSE 'Probationary' END AS credit_rating,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
"""

# 14. bronze_inventory_positions.sql
FILES[MED_SQL / "bronze_inventory_positions.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_inventory_positions` AS
SELECT
  CONCAT('HLD-', LPAD(CAST(n AS STRING), 9, '0')) AS holding_id,
  CONCAT('PORT-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 8, '0')) AS assortment_id,
  CONCAT('SEC-', LPAD(CAST(CAST(FLOOR(RAND() * 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  ROUND(10 + RAND() * 450, 0) AS quantity,
  ROUND(14 + RAND() * 260, 2) AS market_price,
  ROUND((10 + RAND() * 450) * (14 + RAND() * 260), 2) AS market_value,
  ROUND((10 + RAND() * 450) * (8 + RAND() * 165), 2) AS cost_basis,
  ROUND(-4500 + RAND() * 14000, 2) AS unrealized_gain_loss,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Apparel & Outerwear' WHEN 1 THEN 'Footwear' WHEN 2 THEN 'Home & Kitchen'
    WHEN 3 THEN 'Consumer Electronics' WHEN 4 THEN 'Outdoor & Activewear' WHEN 5 THEN 'Home Furnishings'
    WHEN 6 THEN 'Accessories & Jewelry' ELSE 'Beauty & Personal Care'
  END AS asset_class,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Womens & Mens Apparel' WHEN 1 THEN 'Athletic Footwear' WHEN 2 THEN 'Culinary & Tabletop'
    WHEN 3 THEN 'Smart Home & Audio' WHEN 4 THEN 'Outdoor Recreation' WHEN 5 THEN 'Living & Bedroom'
    WHEN 6 THEN 'Fashion Accessories' ELSE 'Clean Beauty & Skincare'
  END AS sector,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(FLOOR(RAND() * 90) AS INT64) DAY) AS as_of_date,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
"""

# 15. bronze_merch_assortments.sql
FILES[MED_SQL / "bronze_merch_assortments.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_merch_assortments` AS
SELECT
  CONCAT('PORT-', LPAD(CAST(n AS STRING), 8, '0')) AS assortment_id,
  CONCAT('WMC-', LPAD(CAST(CAST(FLOOR(n / 2.0) + 1 AS INT64) AS STRING), 7, '0')) AS wm_client_id,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Spring Apparel Core' WHEN 1 THEN 'Outdoor & Activewear' WHEN 2 THEN 'Home & Kitchen Essentials'
    WHEN 3 THEN 'Consumer Electronics Flagship' WHEN 4 THEN 'Beauty & Personal Care' WHEN 5 THEN 'Seasonal Holiday Gifting'
    WHEN 6 THEN 'Footwear & Accessories' ELSE 'Private Label Basics'
  END AS assortment_name,
  CASE MOD(n, 7)
    WHEN 0 THEN 'FLAGSHIP_STORE' WHEN 1 THEN 'OMNICHANNEL' WHEN 2 THEN 'ECOMMERCE_ONLY' WHEN 3 THEN 'OUTLET'
    WHEN 4 THEN 'MARKETPLACE' WHEN 5 THEN 'POP_UP' ELSE 'VIP_CLIENTELING'
  END AS account_type,
  CASE MOD(n, 4) WHEN 0 THEN 'Standard Sales Tax' WHEN 1 THEN 'Apparel Tax-Exempt' WHEN 2 THEN 'Back-to-School Holiday' ELSE 'Standard Sales Tax' END AS tax_status,
  ROUND(CASE MOD(n, 5)
    WHEN 0 THEN 45000 + RAND() * 180000
    WHEN 1 THEN 85000 + RAND() * 320000
    WHEN 2 THEN 25000 + RAND() * 95000
    ELSE 55000 + RAND() * 210000
  END, 2) AS market_value,
  ROUND(CASE MOD(n, 5)
    WHEN 0 THEN 28000 + RAND() * 115000
    WHEN 1 THEN 52000 + RAND() * 200000
    ELSE 32000 + RAND() * 130000
  END, 2) AS cost_basis,
  ROUND(0.08 + RAND() * 0.42, 4) AS ytd_return,
  ROUND(0.12 + RAND() * 0.48, 4) AS inception_return,
  CONCAT('BM-', LPAD(CAST(MOD(n, 10) + 1 AS STRING), 3, '0')) AS benchmark_id,
  CONCAT('ADV-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS advisor_id,
  CONCAT('MDL-', LPAD(CAST(MOD(n, 20) + 1 AS STRING), 3, '0')) AS template_assortment_id,
  DATE_ADD('2018-01-01', INTERVAL CAST(FLOOR(RAND() * 2500) AS INT64) DAY) AS inception_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' ELSE 'Closed' END AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 15000)) AS n
"""

# 16. bronze_competitor_pricing.sql
FILES[MED_SQL / "bronze_competitor_pricing.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_competitor_pricing` AS
SELECT
  CONCAT('MKT-', LPAD(CAST(n AS STRING), 10, '0')) AS market_data_id,
  CONCAT('SEC-', LPAD(CAST(CAST(MOD(n, 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(n / 5000.0) AS INT64) DAY) AS as_of_date,
  ROUND(12.0 + RAND() * 340.0, 2) AS close_price,
  ROUND(12.0 + RAND() * 345.0, 2) AS open_price,
  ROUND(14.0 + RAND() * 360.0, 2) AS high_price,
  ROUND(9.99 + RAND() * 310.0, 2) AS low_price,
  CAST(FLOOR(25 + RAND() * 4500) AS INT64) AS volume,
  ROUND(-0.15 + RAND() * 0.25, 4) AS daily_return,
  ROUND(11.5 + RAND() * 330.0, 2) AS bid_price,
  ROUND(12.5 + RAND() * 350.0, 2) AS ask_price,
  CASE WHEN MOD(n, 5000) < 2000 THEN ROUND(0.25 + RAND() * 0.40, 4) ELSE NULL END AS yield_to_maturity,
  CASE WHEN MOD(n, 5000) < 2000 THEN ROUND(14 + RAND() * 75, 1) ELSE NULL END AS duration,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'HELIOS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 50000)) AS n
"""

# 17. bronze_category_benchmarks.sql
FILES[MED_SQL / "bronze_category_benchmarks.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_category_benchmarks` AS
SELECT
  CONCAT('BM-', LPAD(CAST(MOD(n, 10) + 1 AS STRING), 3, '0')) AS benchmark_id,
  CASE MOD(n, 10)
    WHEN 0 THEN 'NRF Apparel & Outerwear Index' WHEN 1 THEN 'US Specialty Footwear Benchmark' WHEN 2 THEN 'Omnichannel Home & Kitchen Index'
    WHEN 3 THEN 'Consumer Electronics Margin Index' WHEN 4 THEN 'Prestige Beauty & Skincare Index' WHEN 5 THEN 'Outdoor & Athletic Retail Index'
    WHEN 6 THEN 'North America Department Store Avg' WHEN 7 THEN 'Private Label Essentials Benchmark' WHEN 8 THEN 'Holiday Gifting & Seasonal Index'
    ELSE 'Accessories & Fine Jewelry Index'
  END AS benchmark_name,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) DAY) AS as_of_date,
  ROUND(-0.02 + RAND() * 0.05, 6) AS daily_return,
  ROUND(-0.04 + RAND() * 0.12, 4) AS mtd_return,
  ROUND(0.05 + RAND() * 0.38, 4) AS ytd_return,
  ROUND(100 + RAND() * 180, 2) AS index_level,
  ROUND(0.04 + RAND() * 0.18, 4) AS annualized_volatility,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 7000)) AS n
"""

# 18. bronze_markdown_rates.sql
FILES[MED_SQL / "bronze_markdown_rates.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_markdown_rates` AS
SELECT
  CONCAT('RATE-', LPAD(CAST(n AS STRING), 8, '0')) AS rate_id,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) DAY) AS as_of_date,
  CASE MOD(n, 10)
    WHEN 0 THEN 'First Markdown — 20% Off' WHEN 1 THEN 'Second Markdown — 40% Off' WHEN 2 THEN 'Final Clearance — 65% Off'
    WHEN 3 THEN 'End-of-Season Apparel Curve' WHEN 4 THEN 'Holiday Doorbuster Promo' WHEN 5 THEN 'VIP Early Access Discount'
    WHEN 6 THEN 'Outlet Transfer Markdown' WHEN 7 THEN 'Slow-Mover 30-Day Markdown' WHEN 8 THEN 'Overstock 60-Day Markdown'
    ELSE 'Damaged Box / Open-Item Discount'
  END AS rate_name,
  CASE MOD(n, 10)
    WHEN 0 THEN '14D' WHEN 1 THEN '30D' WHEN 2 THEN '60D'
    WHEN 3 THEN '90D' WHEN 4 THEN '7D' WHEN 5 THEN '14D'
    WHEN 6 THEN '120D' WHEN 7 THEN '30D' WHEN 8 THEN '60D'
    ELSE 'Immediate'
  END AS tenor,
  ROUND(0.10 + RAND() * 0.55, 4) AS rate_value,
  ROUND(-0.02 + RAND() * 0.04, 4) AS daily_change,
  CASE MOD(n, 4)
    WHEN 0 THEN 'Northwind Pricing Engine' WHEN 1 THEN 'Merchandising Promo Desk' WHEN 2 THEN 'Clearance Optimization Model'
    ELSE 'Omnichannel Dynamic Pricing'
  END AS source,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'HELIOS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 7000)) AS n
"""

# 19. bronze_ecom_orders.sql
FILES[MED_SQL / "bronze_ecom_orders.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_ecom_orders` AS
SELECT
  CONCAT('TRD-', LPAD(CAST(n AS STRING), 10, '0')) AS trade_id,
  CONCAT('PORT-', LPAD(CAST(CAST(FLOOR(RAND() * 15000) + 1 AS INT64) AS STRING), 8, '0')) AS assortment_id,
  CONCAT('SEC-', LPAD(CAST(CAST(FLOOR(RAND() * 5000) + 1 AS INT64) AS STRING), 6, '0')) AS security_id,
  CASE MOD(n, 4) WHEN 0 THEN 'PURCHASE' WHEN 1 THEN 'RETURN' WHEN 2 THEN 'PURCHASE' ELSE 'EXCHANGE' END AS trade_type,
  ROUND(1 + FLOOR(RAND() * 6), 0) AS quantity,
  ROUND(18 + RAND() * 165, 2) AS price,
  ROUND((1 + FLOOR(RAND() * 6)) * (18 + RAND() * 165), 2) AS gross_amount,
  ROUND(0 + RAND() * 12, 2) AS commission,
  ROUND(0 + RAND() * 7.99, 2) AS fees,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS trade_date,
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(RAND() * 502) AS INT64) DAY) AS settlement_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Delivered' WHEN 1 THEN 'Shipped' WHEN 2 THEN 'Delivered' WHEN 3 THEN 'Fulfilled BOPIS' ELSE 'Processing' END AS status,
  CASE MOD(n, 4) WHEN 0 THEN 'Standard Shipping' WHEN 1 THEN 'BOPIS Same-Day' WHEN 2 THEN 'Express 2-Day' ELSE 'Ship-From-Store' END AS order_type,
  CONCAT('ADV-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS advisor_id,
  CASE MOD(n, 3) WHEN 0 THEN 'Organic Web' WHEN 1 THEN 'Loyalty App Push' ELSE 'Stylist Clienteling Link' END AS solicitation_type,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 30000)) AS n
"""

# 20. bronze_working_capital.sql
FILES[MED_SQL / "bronze_working_capital.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_working_capital` AS
SELECT
  CONCAT('RCAP-', LPAD(CAST(n AS STRING), 5, '0')) AS capital_id,
  DATE_ADD('2022-01-01', INTERVAL CAST(FLOOR(n / 4.0) AS INT64) * 3 MONTH) AS reporting_date,
  CASE MOD(n, 4) WHEN 0 THEN 'Core Working Capital' WHEN 1 THEN 'Inventory Buffer Reserve' WHEN 2 THEN 'Seasonal Liquidity Facility' ELSE 'Total Operating Capital' END AS capital_component,
  ROUND(CASE MOD(n, 4)
    WHEN 0 THEN 42000000 + RAND() * 18000000
    WHEN 1 THEN 12000000 + RAND() * 6000000
    WHEN 2 THEN 18000000 + RAND() * 9000000
    ELSE 72000000 + RAND() * 33000000
  END, 0) AS capital_amount,
  ROUND(240000000 + RAND() * 85000000, 0) AS risk_weighted_assets,
  ROUND(CASE MOD(n, 4) WHEN 0 THEN 0.16 + RAND() * 0.05 WHEN 1 THEN 0.05 + RAND() * 0.02 WHEN 2 THEN 0.08 + RAND() * 0.03 ELSE 0.28 + RAND() * 0.06 END, 4) AS capital_ratio,
  ROUND(CASE MOD(n, 4) WHEN 0 THEN 0.120 WHEN 1 THEN 0.040 WHEN 2 THEN 0.060 ELSE 0.220 END, 4) AS regulatory_minimum,
  ROUND(0.025, 4) AS capital_conservation_buffer,
  ROUND(CASE WHEN MOD(n, 10) = 0 THEN 0.015 ELSE 0.0 END, 4) AS countercyclical_buffer,
  CASE WHEN MOD(n, 4) = 0 THEN ROUND(310000000 + RAND() * 75000000, 0) ELSE NULL END AS leverage_exposure,
  CASE WHEN MOD(n, 4) = 0 THEN ROUND(0.14 + RAND() * 0.04, 4) ELSE NULL END AS leverage_ratio,
  CASE MOD(n, 3) WHEN 0 THEN 'Retail Inventory Cost Method' WHEN 1 THEN 'Omnichannel Working Capital Policy' ELSE 'Retail Inventory Cost Method' END AS calculation_approach,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'HELIOS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 1000)) AS n
"""

# 21. gold_financial_summary.sql
FILES[MED_SQL / "gold_financial_summary.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_gold.gold_financial_summary` AS
SELECT
  'Assets' AS category,
  'Cash & Store Working Balances' AS line_item,
  ROUND(SUM(CASE WHEN account_type IN ('POINTS_REWARDS', 'VIP_CASHBACK') THEN current_balance * 0.25 ELSE 0 END), 0) AS amount
FROM `${project_id}.retail_silver.silver_loyalty_accounts`
WHERE account_status = 'Active'
UNION ALL
SELECT 'Assets', 'Active BNPL Installment Receivables',
  ROUND(SUM(current_balance), 0)
FROM `${project_id}.retail_silver.silver_bnpl_plans`
UNION ALL
SELECT 'Assets', 'Merchandise Inventory at Market Value',
  ROUND(SUM(market_value), 0)
FROM `${project_id}.retail_silver.silver_inventory_positions`
UNION ALL
SELECT 'Liabilities', 'Unredeemed Loyalty & Gift Wallet Liability',
  ROUND(SUM(current_balance), 0)
FROM `${project_id}.retail_silver.silver_loyalty_accounts`
WHERE account_status = 'Active'
UNION ALL
SELECT 'Liabilities', 'Supply Chain & Trade Payables',
  ROUND(SUM(cost_basis) * 0.35, 0)
FROM `${project_id}.retail_silver.silver_inventory_positions`
UNION ALL
SELECT 'Operating Equity', 'Total Retail Operating Equity',
  ROUND(MAX(capital_amount), 0)
FROM `${project_id}.retail_silver.silver_working_capital`
WHERE capital_component = 'Total Operating Capital'
  AND reporting_date = (SELECT MAX(reporting_date) FROM `${project_id}.retail_silver.silver_working_capital`)
"""

# 22. bronze_category_managers.sql
FILES[MED_SQL / "bronze_category_managers.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_category_managers` AS
SELECT
  CONCAT('ADV-', LPAD(CAST(n AS STRING), 4, '0')) AS advisor_id,
  CASE MOD(n, 15) WHEN 0 THEN 'James' WHEN 1 THEN 'Sarah' WHEN 2 THEN 'Michael' WHEN 3 THEN 'Emily' WHEN 4 THEN 'Robert' WHEN 5 THEN 'Laura' WHEN 6 THEN 'David' WHEN 7 THEN 'Jennifer' WHEN 8 THEN 'William' WHEN 9 THEN 'Amanda' WHEN 10 THEN 'Thomas' WHEN 11 THEN 'Rebecca' WHEN 12 THEN 'Charles' WHEN 13 THEN 'Diana' ELSE 'Andrew' END AS first_name,
  CASE MOD(n, 8) WHEN 0 THEN 'Mercer' WHEN 1 THEN 'Callahan' WHEN 2 THEN 'Sterling' WHEN 3 THEN 'Prescott' WHEN 4 THEN 'Hawthorne' WHEN 5 THEN 'Kensington' WHEN 6 THEN 'Vance' ELSE 'Ashford' END AS last_name,
  CASE MOD(n, 5) WHEN 0 THEN 'CPIM, CSCP' WHEN 1 THEN 'NRF Merchandising Cert' WHEN 2 THEN 'Six Sigma Black Belt' WHEN 3 THEN 'GS1 Standards Specialist' ELSE 'Omnichannel Planning Cert' END AS certifications,
  CASE MOD(n, 4) WHEN 0 THEN 'Senior Category Manager' WHEN 1 THEN 'Assortment Buyer' WHEN 2 THEN 'Omnichannel Merchandising Lead' ELSE 'VP of Divisional Merchandising' END AS title,
  CASE MOD(n, 5) WHEN 0 THEN 'Northeast' WHEN 1 THEN 'West' WHEN 2 THEN 'Midwest' WHEN 3 THEN 'South' ELSE 'Southeast' END AS region,
  CONCAT('BR-', LPAD(CAST(MOD(n, 100) + 1 AS STRING), 4, '0')) AS assigned_store_id,
  CONCAT('MERCH-', LPAD(CAST(100000 + MOD(n * 97, 800000) AS STRING), 6, '0')) AS finra_crd_number,
  CAST(FLOOR(3 + RAND() * 22) AS INT64) AS years_experience,
  ROUND(1500000 + RAND() * 14000000, 0) AS total_aum,
  CAST(FLOOR(8 + RAND() * 45) AS INT64) AS client_count,
  ROUND(32 + RAND() * 28, 2) AS avg_fee_bps,
  DATE_ADD('2012-01-01', INTERVAL CAST(FLOOR(RAND() * 4200) AS INT64) DAY) AS hire_date,
  CASE MOD(n, 6) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' WHEN 4 THEN 'Active' ELSE 'On Leave' END AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 500)) AS n
"""

# 23. bronze_store_associates.sql
FILES[MED_SQL / "bronze_store_associates.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_store_associates` AS
SELECT
  CONCAT('EMP-', LPAD(CAST(n AS STRING), 6, '0')) AS employee_id,
  CASE MOD(n, 20)
    WHEN 0 THEN 'James' WHEN 1 THEN 'Mary' WHEN 2 THEN 'Robert' WHEN 3 THEN 'Patricia'
    WHEN 4 THEN 'John' WHEN 5 THEN 'Jennifer' WHEN 6 THEN 'Michael' WHEN 7 THEN 'Linda'
    WHEN 8 THEN 'David' WHEN 9 THEN 'Elizabeth' WHEN 10 THEN 'William' WHEN 11 THEN 'Barbara'
    WHEN 12 THEN 'Richard' WHEN 13 THEN 'Susan' WHEN 14 THEN 'Joseph' WHEN 15 THEN 'Jessica'
    WHEN 16 THEN 'Thomas' WHEN 17 THEN 'Sarah' WHEN 18 THEN 'Charles' ELSE 'Karen'
  END AS first_name,
  CASE MOD(n, 10) WHEN 0 THEN 'Smith' WHEN 1 THEN 'Johnson' WHEN 2 THEN 'Williams' WHEN 3 THEN 'Brown' WHEN 4 THEN 'Jones' WHEN 5 THEN 'Garcia' WHEN 6 THEN 'Miller' WHEN 7 THEN 'Davis' WHEN 8 THEN 'Rodriguez' ELSE 'Wilson' END AS last_name,
  CASE MOD(n, 12)
    WHEN 0 THEN 'POS Cashier' WHEN 1 THEN 'Clienteling Stylist' WHEN 2 THEN 'BNPL & Loyalty Specialist'
    WHEN 3 THEN 'Store Manager' WHEN 4 THEN 'Visual Merchandiser' WHEN 5 THEN 'Privacy & PCI Compliance Lead'
    WHEN 6 THEN 'Inventory Control Specialist' WHEN 7 THEN 'VIP Personal Shopper' WHEN 8 THEN 'BOPIS Fulfillment Lead'
    WHEN 9 THEN 'Loss Prevention Analyst' WHEN 10 THEN 'Returns & Promo Fraud Specialist' ELSE 'Store Systems Support'
  END AS title,
  CASE MOD(n, 8)
    WHEN 0 THEN 'Store Operations' WHEN 1 THEN 'Customer Loyalty & BNPL' WHEN 2 THEN 'Omnichannel Clienteling'
    WHEN 3 THEN 'Fulfillment & BOPIS' WHEN 4 THEN 'Loss Prevention' WHEN 5 THEN 'Privacy & PCI Governance'
    WHEN 6 THEN 'Retail Technology' ELSE 'Merchandising & Inventory'
  END AS department,
  CONCAT('BR-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS store_id,
  CASE WHEN MOD(n, 20) = 0 THEN NULL ELSE CONCAT('EMP-', LPAD(CAST(CAST(FLOOR(n / 5) AS INT64) AS STRING), 6, '0')) END AS manager_id,
  DATE_ADD('2015-01-01', INTERVAL CAST(FLOOR(RAND() * 3500) AS INT64) DAY) AS hire_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Active' WHEN 3 THEN 'Active' ELSE 'On Leave' END AS employment_status,
  CASE WHEN MOD(n, 12) IN (5, 6, 10) THEN TRUE ELSE FALSE END AS has_finra_license,
  CASE WHEN MOD(n, 12) IN (5, 6, 10) THEN CONCAT('PCI-CERT-', LPAD(CAST(MOD(n, 99999) AS STRING), 5, '0')) ELSE NULL END AS finra_crd_number,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'ORION' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
"""

# 24. bronze_compliance_attestations.sql
FILES[MED_SQL / "bronze_compliance_attestations.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_compliance_attestations` AS
SELECT
  CONCAT('FILING-', LPAD(CAST(n AS STRING), 5, '0')) AS filing_id,
  CASE MOD(n, 8)
    WHEN 0 THEN 'PCI-DSS v4.0 Report on Compliance (ROC)' WHEN 1 THEN 'CPRA / CCPA Annual DSAR Metrics Filing' WHEN 2 THEN 'SOC 2 Type II E-Commerce Attestation'
    WHEN 3 THEN 'CCPA Annual Privacy Audit' WHEN 4 THEN 'Promo Abuse Incident Report' WHEN 5 THEN 'High-Value Refund Audit Log'
    WHEN 6 THEN 'FTC Mail & Online Order Rule Review' ELSE 'GS1 Barcode & Supply Chain Traceability Audit'
  END AS report_name,
  CASE MOD(n, 8)
    WHEN 0 THEN 'PCI-SSC' WHEN 1 THEN 'California Privacy Protection Agency (CPPA)' WHEN 2 THEN 'AICPA / External Auditor'
    WHEN 3 THEN 'California Privacy Protection Agency (CPPA)' WHEN 4 THEN 'NRF Loss Prevention Council' WHEN 5 THEN 'Internal Audit Committee'
    WHEN 6 THEN 'FTC Consumer Protection' ELSE 'GS1 US Standards Body'
  END AS regulatory_body,
  CASE MOD(n, 4) WHEN 0 THEN 'Quarterly' WHEN 1 THEN 'Quarterly' WHEN 2 THEN 'Monthly' ELSE 'Annual' END AS filing_frequency,
  DATE_ADD('2023-01-01', INTERVAL CAST(FLOOR(RAND() * 800) AS INT64) DAY) AS reporting_period_end,
  DATE_ADD('2023-02-01', INTERVAL CAST(FLOOR(RAND() * 830) AS INT64) DAY) AS filing_due_date,
  DATE_ADD('2023-02-01', INTERVAL CAST(FLOOR(RAND() * 825) AS INT64) DAY) AS actual_filing_date,
  CASE MOD(n, 5) WHEN 0 THEN 'Filed' WHEN 1 THEN 'Filed' WHEN 2 THEN 'Filed' WHEN 3 THEN 'In Progress' ELSE 'Amendment Filed' END AS filing_status,
  CONCAT('PREP-', LPAD(CAST(MOD(n, 20) + 1 AS STRING), 3, '0')) AS preparer_id,
  CONCAT('REV-', LPAD(CAST(MOD(n, 10) + 1 AS STRING), 3, '0')) AS reviewer_id,
  CASE WHEN MOD(n, 10) = 0 THEN 'Minor POS scope reconciliation update' ELSE NULL END AS amendment_notes,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'HELIOS' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 500)) AS n
"""

# 25. bronze_return_risk_profiles.sql
FILES[MED_SQL / "bronze_return_risk_profiles.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_bronze.bronze_return_risk_profiles` AS
SELECT
  CONCAT('RP-', LPAD(CAST(n AS STRING), 7, '0')) AS risk_profile_id,
  CONCAT('WMC-', LPAD(CAST(n AS STRING), 7, '0')) AS wm_client_id,
  CASE MOD(n, 4)
    WHEN 0 THEN 'Low' WHEN 1 THEN 'Watch' WHEN 2 THEN 'Elevated' ELSE 'High Risk'
  END AS risk_tolerance,
  CAST(FLOOR(1 + RAND() * 12) AS INT64) AS time_horizon_years,
  ROUND(CASE MOD(n, 4) WHEN 0 THEN 45000 + RAND() * 65000 WHEN 3 THEN 65000 + RAND() * 110000 ELSE 55000 + RAND() * 85000 END, 0) AS annual_income,
  ROUND(CASE MOD(n, 4) WHEN 0 THEN 800 + RAND() * 2400 WHEN 3 THEN 2500 + RAND() * 9500 ELSE 1200 + RAND() * 4800 END, 0) AS net_worth,
  ROUND(CASE MOD(n, 4) WHEN 0 THEN 400 + RAND() * 1200 WHEN 3 THEN 1200 + RAND() * 4500 ELSE 600 + RAND() * 2200 END, 0) AS liquid_net_worth,
  CASE MOD(n, 4) WHEN 0 THEN 'Occasional Returner (<5%)' WHEN 1 THEN 'Bracket Size Shopper (15%)' WHEN 2 THEN 'Frequent Seasonal Returner (30%)' ELSE 'Serial Wardrobing Flag (>45%)' END AS investment_experience,
  CASE MOD(n, 4) WHEN 0 THEN 'Low' WHEN 1 THEN 'Watch' WHEN 2 THEN 'Elevated' ELSE 'High Risk' END AS loss_tolerance,
  DATE_SUB(CURRENT_DATE(), INTERVAL CAST(30 + MOD(n, 300) AS INT64) DAY) AS assessment_date,
  CASE
    WHEN MOD(n, 4) = 0 THEN CASE WHEN MOD(n, 100) = 0 THEN DATE_SUB(CURRENT_DATE(), INTERVAL 10 DAY) ELSE DATE_ADD(CURRENT_DATE(), INTERVAL 180 DAY) END
    WHEN MOD(n, 4) = 1 THEN CASE WHEN MOD(n, 25) = 0 THEN DATE_SUB(CURRENT_DATE(), INTERVAL 12 DAY) ELSE DATE_ADD(CURRENT_DATE(), INTERVAL 120 DAY) END
    WHEN MOD(n, 4) = 2 THEN CASE WHEN MOD(n, 11) = 0 THEN DATE_SUB(CURRENT_DATE(), INTERVAL 15 DAY) ELSE DATE_ADD(CURRENT_DATE(), INTERVAL 90 DAY) END
    ELSE CASE WHEN MOD(n, 6) = 0 THEN DATE_SUB(CURRENT_DATE(), INTERVAL 20 DAY) ELSE DATE_ADD(CURRENT_DATE(), INTERVAL 60 DAY) END
  END AS next_review_date,
  CONCAT('ADV-', LPAD(CAST(MOD(n, 500) + 1 AS STRING), 4, '0')) AS assessed_by,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at,
  'LUMEN' AS source_system
FROM UNNEST(GENERATE_ARRAY(1, 10000)) AS n
"""

# 26. snapshot_daily_competitor_pricing.sql, snapshot_monthly_loyalty_balances.sql, snapshot_quarterly_inventory_positions.sql
FILES[MED_SQL / "snapshot_daily_competitor_pricing.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_snapshots.snapshot_daily_competitor_pricing` AS
SELECT
  DATE_ADD('2024-01-01', INTERVAL CAST(FLOOR(n / 100.0) AS INT64) DAY) AS snapshot_date,
  CASE MOD(n, 10)
    WHEN 0 THEN 'Apparel & Outerwear CPI' WHEN 1 THEN 'Footwear Price Index' WHEN 2 THEN 'Home & Kitchen Basket' WHEN 3 THEN 'Consumer Electronics CPI'
    WHEN 4 THEN 'Markdown Depth Avg %' WHEN 5 THEN 'BNPL Default Benchmark %' WHEN 6 THEN 'CAD/USD Retail FX'
    WHEN 7 THEN 'Omnichannel Promo Intensity' WHEN 8 THEN 'Cotton & Textile Spot' ELSE 'Parcel Freight Index'
  END AS indicator,
  ROUND(CASE MOD(n, 10)
    WHEN 0 THEN 105 + RAND() * 18 WHEN 1 THEN 112 + RAND() * 15
    WHEN 2 THEN 98 + RAND() * 22 WHEN 3 THEN 92 + RAND() * 14
    WHEN 4 THEN 18.5 + RAND() * 12.0 WHEN 5 THEN 2.4 + RAND() * 1.8
    WHEN 6 THEN 0.72 + RAND() * 0.06 WHEN 7 THEN 24 + RAND() * 18
    WHEN 8 THEN 78 + RAND() * 25 ELSE 115 + RAND() * 30
  END, 2) AS value,
  ROUND(-0.02 + RAND() * 0.04, 4) AS daily_change_pct
FROM UNNEST(GENERATE_ARRAY(1, 5000)) AS n
"""

FILES[MED_SQL / "snapshot_monthly_loyalty_balances.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_snapshots.snapshot_monthly_loyalty_balances` AS
SELECT
  CONCAT('ACCT-', LPAD(CAST(CAST(MOD(n, 50000) + 1 AS INT64) AS STRING), 10, '0')) AS account_id,
  DATE_ADD('2024-01-31', INTERVAL CAST(FLOOR(n / 50000.0) AS INT64) MONTH) AS snapshot_date,
  ROUND(20 + RAND() * 420, 2) AS balance,
  ROUND(2 + RAND() * 35, 2) AS mtd_interest_earned,
  CAST(FLOOR(1 + RAND() * 14) AS INT64) AS transaction_count
FROM UNNEST(GENERATE_ARRAY(1, 200000)) AS n
"""

FILES[MED_SQL / "snapshot_quarterly_inventory_positions.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_snapshots.snapshot_quarterly_inventory_positions` AS
SELECT
  CONCAT('PORT-', LPAD(CAST(CAST(MOD(n, 15000) + 1 AS INT64) AS STRING), 8, '0')) AS assortment_id,
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 15000.0) AS INT64) * 3 MONTH) AS snapshot_date,
  ROUND(28000 + RAND() * 240000, 2) AS market_value,
  ROUND(18000 + RAND() * 155000, 2) AS cost_basis,
  ROUND(0.04 + RAND() * 0.22, 4) AS qtd_return,
  ROUND(0.10 + RAND() * 0.38, 4) AS ytd_return,
  CAST(FLOOR(12 + RAND() * 65) AS INT64) AS holding_count
FROM UNNEST(GENERATE_ARRAY(1, 60000)) AS n
"""

# 27. Staging tables with surviving FSI literals
FILES[MED_SQL / "staging_supplier_audit_schedule.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_staging.staging_supplier_audit_schedule` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 8.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('WC-', CAST(MOD(n, 8) + 1 AS STRING)) AS schedule_line,
  CASE MOD(n, 8) WHEN 0 THEN 'Total Inventory at Risk' WHEN 1 THEN 'Core Working Capital' WHEN 2 THEN 'Inventory Buffer Reserve' WHEN 3 THEN 'Total Operating Capital' WHEN 4 THEN 'Core Working Capital Ratio' WHEN 5 THEN 'Quick Liquidity Ratio' WHEN 6 THEN 'Operating Capital Ratio' ELSE 'Inventory Turnover Ratio' END AS line_description,
  ROUND(CASE WHEN MOD(n, 8) >= 4 THEN 0.12 + RAND() * 0.22 ELSE 15000000 + RAND() * 85000000 END, CASE WHEN MOD(n, 8) >= 4 THEN 4 ELSE 0 END) AS amount,
  'Filed' AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 40)) AS n
"""

FILES[MED_SQL / "staging_annual_omniretail_filing.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_staging.staging_annual_omniretail_filing` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('OMNI-', CASE MOD(n, 10) WHEN 0 THEN 'BS-1' WHEN 1 THEN 'BS-2' WHEN 2 THEN 'BS-3' WHEN 3 THEN 'BS-4' WHEN 4 THEN 'WC-1' WHEN 5 THEN 'WC-2' WHEN 6 THEN 'IS-1' WHEN 7 THEN 'IS-2' WHEN 8 THEN 'IS-3' ELSE 'EQ-1' END) AS schedule_line,
  CASE MOD(n, 10) WHEN 0 THEN 'Consolidated Retail Assets' WHEN 1 THEN 'Merchandise Inventory SKUs' WHEN 2 THEN 'BNPL Installment Receivables' WHEN 3 THEN 'Unredeemed Loyalty Balances' WHEN 4 THEN 'Markdown-Exposed Inventory' WHEN 5 THEN 'Total Operating Capital' WHEN 6 THEN 'Gross Merchandise Revenue' WHEN 7 THEN 'Cost of Goods Sold (COGS)' WHEN 8 THEN 'Store & Fulfillment OpEx' ELSE 'Total Retail Operating Equity' END AS line_description,
  ROUND(5000000 + RAND() * 120000000, 0) AS amount,
  'SEC / FTC Omnichannel Retail Disclosure' AS regulatory_body,
  'Filed' AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 40)) AS n
"""

FILES[MED_SQL / "staging_ccpa_dsar_log.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_staging.staging_ccpa_dsar_log` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 12.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('CCPA-', CAST(MOD(n, 12) + 1 AS STRING)) AS schedule_line,
  CASE MOD(n, 12) WHEN 0 THEN 'Right-to-Know Requests Received' WHEN 1 THEN 'Right-to-Delete Requests Completed' WHEN 2 THEN 'Opt-Out of Sale/Sharing Requests' WHEN 3 THEN 'Authorized Agent Submissions' WHEN 4 THEN 'Loyalty Profile Export Requests' WHEN 5 THEN 'BNPL Data Access Disclosures' WHEN 6 THEN 'Store Card PII Masking Audits' WHEN 7 THEN 'Marketing Email Unsubscribes' WHEN 8 THEN 'SMS Geo-Tracking Opt-Outs' WHEN 9 THEN 'Biometric App Consent Revocations' WHEN 10 THEN 'Partially Denied (Fraud Hold)' ELSE 'Total Verified CCPA DSAR Filings' END AS line_description,
  ROUND(120 + RAND() * 4800, 0) AS amount,
  'Verified' AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 48)) AS n
"""

FILES[MED_SQL / "staging_channel_revenue_recon.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_staging.staging_channel_revenue_recon` AS
SELECT
  DATE_ADD('2024-03-31', INTERVAL CAST(FLOOR(n / 10.0) AS INT64) * 3 MONTH) AS reporting_date,
  CONCAT('REV-', CAST(MOD(n, 10) + 1 AS STRING)) AS schedule_line,
  CASE MOD(n, 10) WHEN 0 THEN 'Flagship Store POS Gross Sales' WHEN 1 THEN 'E-Commerce Web & App Sales' WHEN 2 THEN 'BOPIS & Curbside Revenue' WHEN 3 THEN 'Returns & Markdown Allowances' WHEN 4 THEN 'Net Merchandise Revenue' WHEN 5 THEN 'Cost of Merchandise Sold' WHEN 6 THEN 'Gross Margin Before Shrinkage' WHEN 7 THEN 'Fulfillment & Outbound Freight' WHEN 8 THEN 'Net Omnichannel Operating Income' ELSE 'Retained Retail Earnings' END AS line_description,
  ROUND(1500000 + RAND() * 65000000, 0) AS amount,
  'Reconciled' AS status,
  TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL CAST(FLOOR(RAND() * 500 * 24 * 60) AS INT64) MINUTE) AS created_at
FROM UNNEST(GENERATE_ARRAY(1, 40)) AS n
"""

# 28. ref_product_catalog.sql
FILES[REF_SQL / "ref_product_catalog.sql"] = """CREATE OR REPLACE TABLE `${project_id}.retail_reference.ref_product_catalog` AS
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
"""


def main():
    updated = 0
    for path, content in FILES.items():
        path.write_text(content, encoding="utf-8")
        updated += 1
        print(f"Updated {path.relative_to(REPO)}")
    print(f"Total base SQL files rewritten: {updated}")


if __name__ == "__main__":
    main()
