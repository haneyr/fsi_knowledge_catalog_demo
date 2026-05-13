#!/usr/bin/env python3
####################################################################################
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
####################################################################################
"""
Injects intentionally dirty data into bronze tables so that data quality
scans produce real failures. The KC agent can then cite actual DQ scores
(e.g., "97.3% pass rate on FICO validation") instead of theoretical rules.

Usage: python3 15_inject_dirty_data.py
"""

import logging
import time

from common import load_config, run_bq_query, api_call, DATAPLEX_URL

logger = logging.getLogger(__name__)


INJECTIONS = [
    {
        "table": "fsi_bronze.bronze_loans",
        "description": "Invalid FICO scores (0, 999, NULL), extreme LTV/DTI",
        "sql": """
INSERT INTO `{pid}.fsi_bronze.bronze_loans`
(loan_id, customer_id, loan_type, original_amount, current_balance, interest_rate,
 term_months, origination_date, maturity_date, fico_score_at_origination,
 ltv_ratio, dti_ratio, delinquency_status, risk_rating, source_system, created_at)
SELECT
  CONCAT('LOAN-BAD-', LPAD(CAST(n AS STRING), 6, '0')),
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND()*20000)+1 AS INT64) AS STRING), 8, '0')),
  CASE MOD(n,4) WHEN 0 THEN 'MORTGAGE' WHEN 1 THEN 'AUTO' WHEN 2 THEN 'PERSONAL' ELSE 'HELOC' END,
  ROUND(10000 + RAND()*500000, 2),
  ROUND(5000 + RAND()*400000, 2),
  ROUND(0.02 + RAND()*0.08, 4),
  CASE MOD(n,3) WHEN 0 THEN 360 WHEN 1 THEN 180 ELSE 60 END,
  DATE_ADD('2020-01-01', INTERVAL CAST(FLOOR(RAND()*1500) AS INT64) DAY),
  DATE_ADD('2030-01-01', INTERVAL CAST(FLOOR(RAND()*3000) AS INT64) DAY),
  CASE
    WHEN MOD(n,5) = 0 THEN 0
    WHEN MOD(n,5) = 1 THEN 999
    WHEN MOD(n,5) = 2 THEN 150
    WHEN MOD(n,5) = 3 THEN CAST(NULL AS INT64)
    ELSE 1200
  END,
  CASE WHEN MOD(n,3) = 0 THEN 250.0 WHEN MOD(n,3) = 1 THEN -10.0 ELSE 350.0 END,
  CASE WHEN MOD(n,2) = 0 THEN -5.0 ELSE 120.0 END,
  CASE MOD(n,3) WHEN 0 THEN 'CURRENT' WHEN 1 THEN '90_DAYS' ELSE '120_PLUS' END,
  'Substandard',
  'ATLAS',
  CURRENT_TIMESTAMP()
FROM UNNEST(GENERATE_ARRAY(1, 150)) AS n
""",
    },
    {
        "table": "fsi_bronze.bronze_accounts",
        "description": "Negative balances, NULL account types",
        "sql": """
INSERT INTO `{pid}.fsi_bronze.bronze_accounts`
(account_id, customer_id, account_type, current_balance, interest_rate,
 open_date, branch_id, account_status, source_system, created_at)
SELECT
  CONCAT('ACCT-BAD-', LPAD(CAST(n AS STRING), 6, '0')),
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND()*20000)+1 AS INT64) AS STRING), 8, '0')),
  CASE WHEN MOD(n,5) = 0 THEN CAST(NULL AS STRING) ELSE 'CHECKING' END,
  CASE WHEN MOD(n,2) = 0 THEN ROUND(-1000 - RAND()*50000, 2) ELSE ROUND(-0.01 - RAND()*100, 2) END,
  ROUND(RAND()*0.05, 4),
  DATE_ADD('2020-01-01', INTERVAL CAST(FLOOR(RAND()*1500) AS INT64) DAY),
  CONCAT('BR-', LPAD(CAST(MOD(n,500)+1 AS STRING), 4, '0')),
  'Active',
  'ATLAS',
  CURRENT_TIMESTAMP()
FROM UNNEST(GENERATE_ARRAY(1, 50)) AS n
""",
    },
    {
        "table": "fsi_bronze.bronze_customers",
        "description": "Invalid SSN format, future DOBs, NULL names",
        "sql": """
INSERT INTO `{pid}.fsi_bronze.bronze_customers`
(customer_id, first_name, last_name, date_of_birth, gender, ssn, email, phone,
 address_line1, city, state, zip_code, customer_type, customer_segment,
 kyc_risk_rating, kyc_status, home_branch_id, source_system, created_at)
SELECT
  CONCAT('CUST-BAD-', LPAD(CAST(n AS STRING), 6, '0')),
  CASE WHEN MOD(n,10) = 0 THEN CAST(NULL AS STRING) ELSE 'Test' END,
  CASE WHEN MOD(n,10) = 1 THEN CAST(NULL AS STRING) ELSE 'BadData' END,
  CASE
    WHEN MOD(n,3) = 0 THEN '2099-12-31'
    WHEN MOD(n,3) = 1 THEN '2050-06-15'
    ELSE '1800-01-01'
  END,
  'U',
  CASE
    WHEN MOD(n,4) = 0 THEN '123456789'
    WHEN MOD(n,4) = 1 THEN '12-34-5678'
    WHEN MOD(n,4) = 2 THEN 'XXX-XX-XXXX'
    ELSE ''
  END,
  CASE WHEN MOD(n,5) = 0 THEN 'not-an-email' ELSE CONCAT('bad', CAST(n AS STRING), '@test.com') END,
  '555-0000',
  '1 Bad Street',
  'Nowhere',
  CASE WHEN MOD(n,3) = 0 THEN 'ZZ' ELSE 'TX' END,
  '00000',
  'Individual',
  'Standard',
  CASE WHEN MOD(n,2) = 0 THEN 'High' ELSE 'Medium' END,
  'Expired',
  CONCAT('BR-', LPAD(CAST(MOD(n,500)+1 AS STRING), 4, '0')),
  'ATLAS',
  CURRENT_TIMESTAMP()
FROM UNNEST(GENERATE_ARRAY(1, 100)) AS n
""",
    },
    {
        "table": "fsi_bronze.bronze_securities",
        "description": "Invalid CUSIP/ISIN format, NULL tickers",
        "sql": """
INSERT INTO `{pid}.fsi_bronze.bronze_securities`
(security_id, ticker, security_name, cusip, isin, security_type, asset_class,
 sector, country, currency, exchange, last_price, dividend_yield, coupon_rate,
 maturity_date, credit_rating, created_at, source_system)
SELECT
  CONCAT('SEC-BAD-', LPAD(CAST(n AS STRING), 4, '0')),
  CASE WHEN MOD(n,3) = 0 THEN CAST(NULL AS STRING) ELSE CONCAT('BAD', CAST(n AS STRING)) END,
  CONCAT('Bad Security ', CAST(n AS STRING)),
  CASE
    WHEN MOD(n,5) = 0 THEN '12345'
    WHEN MOD(n,5) = 1 THEN 'TOOLONG1234'
    WHEN MOD(n,5) = 2 THEN '!@#$%^&*('
    WHEN MOD(n,5) = 3 THEN ''
    ELSE 'ABCDE'
  END,
  CASE
    WHEN MOD(n,4) = 0 THEN '123'
    WHEN MOD(n,4) = 1 THEN 'NOTAVALIDISINN'
    WHEN MOD(n,4) = 2 THEN ''
    ELSE 'XX0000000000'
  END,
  'Common Stock',
  'Equity',
  'Technology',
  'US',
  'USD',
  'NYSE',
  ROUND(RAND()*1000, 2),
  NULL, NULL, NULL, NULL,
  CURRENT_TIMESTAMP(),
  'FORTUNA'
FROM UNNEST(GENERATE_ARRAY(1, 75)) AS n
""",
    },
    {
        "table": "fsi_bronze.bronze_credit_cards",
        "description": "Extreme APR values (negative, >30%)",
        "sql": """
INSERT INTO `{pid}.fsi_bronze.bronze_credit_cards`
(card_id, customer_id, account_id, card_type, network, masked_card_number,
 credit_limit, current_balance, available_credit, apr, annual_fee, fico_score,
 issue_date, expiration_date, card_status, rewards_balance, rewards_type,
 created_at, source_system)
SELECT
  CONCAT('CC-BAD-', LPAD(CAST(n AS STRING), 5, '0')),
  CONCAT('CUST-', LPAD(CAST(CAST(FLOOR(RAND()*20000)+1 AS INT64) AS STRING), 8, '0')),
  CONCAT('ACCT-', LPAD(CAST(CAST(90000+n AS INT64) AS STRING), 10, '0')),
  'VISA_CLASSIC',
  'Visa',
  CONCAT('XXXX-XXXX-XXXX-', LPAD(CAST(MOD(n,10000) AS STRING), 4, '0')),
  5000.0,
  ROUND(RAND()*5000, 2),
  ROUND(RAND()*3000, 2),
  CASE
    WHEN MOD(n,3) = 0 THEN -0.05
    WHEN MOD(n,3) = 1 THEN 0.45
    ELSE 0.99
  END,
  0.0,
  CASE WHEN MOD(n,2) = 0 THEN 200 ELSE 900 END,
  '2023-01-01',
  '2027-01-01',
  'Active',
  0.0, 'Points',
  CURRENT_TIMESTAMP(),
  'ATLAS'
FROM UNNEST(GENERATE_ARRAY(1, 50)) AS n
""",
    },
    {
        "table": "fsi_bronze.bronze_wire_transfers",
        "description": "Structuring pattern ($10,000.01 amounts)",
        "sql": """
INSERT INTO `{pid}.fsi_bronze.bronze_wire_transfers`
(wire_id, account_id, wire_type, direction, amount, currency, originator_name,
 originator_bank, beneficiary_name, beneficiary_bank, beneficiary_country,
 status, ofac_hold, requires_ctr, above_ctr_threshold, purpose,
 transaction_date, created_at, source_system)
SELECT
  CONCAT('WIRE-STRUCT-', LPAD(CAST(n AS STRING), 5, '0')),
  CONCAT('ACCT-', LPAD(CAST(CAST(FLOOR(RAND()*50000)+1 AS INT64) AS STRING), 10, '0')),
  'DOMESTIC',
  'Outgoing',
  10000.01,
  'USD',
  'Suspicious Sender',
  'Meridian National Bank',
  CONCAT('Beneficiary ', CAST(n AS STRING)),
  'External Bank',
  'US',
  'Completed',
  FALSE,
  TRUE,
  TRUE,
  'Purpose: Other',
  TIMESTAMP_ADD(TIMESTAMP '2024-06-01 00:00:00 UTC', INTERVAL CAST(n * 3 AS INT64) DAY),
  CURRENT_TIMESTAMP(),
  'ATLAS'
FROM UNNEST(GENERATE_ARRAY(1, 20)) AS n
""",
    },
]


def rerun_dq_scans(cfg, tables):
    pid = cfg["project_id"]
    loc = cfg["location"]
    for ds, tbl in tables:
        layer = ds.replace("fsi_", "")
        tname = tbl.replace(f"{layer}_", "").replace("bronze_", "").replace("silver_", "").replace("gold_", "")
        for stype in ["quality", "profile"]:
            sid = f"fsi-{layer}-{tname}-{stype}".replace("_", "-")
            run_url = f"{DATAPLEX_URL}/projects/{pid}/locations/{loc}/dataScans/{sid}:run"
            try:
                api_call(run_url, "POST", {})
                logger.info("  Restarted %s", sid)
            except RuntimeError:
                pass
            time.sleep(0.5)


def main():
    cfg = load_config()
    pid = cfg["project_id"]

    logger.info("=== Injecting dirty data into bronze tables ===")

    total_injected = 0
    affected_tables = []

    for injection in INJECTIONS:
        sql = injection["sql"].replace("{pid}", pid)
        table = injection["table"]
        desc = injection["description"]

        logger.info("  %s: %s", table, desc)
        try:
            run_bq_query(cfg, sql, desc)
            ds, tbl = table.split(".")
            affected_tables.append((ds, tbl))
            total_injected += 1
        except Exception as e:
            logger.warning("  Failed: %s", str(e)[:100])

    logger.info("=== Rerunning DQ scans on affected tables ===")
    rerun_dq_scans(cfg, affected_tables)

    logger.info("=" * 60)
    logger.info("DIRTY DATA INJECTION COMPLETE")
    logger.info("  Tables injected: %d", total_injected)
    logger.info("  DQ scans restarted for: %s", ", ".join(t[1] for t in affected_tables))
    logger.info("  Note: DQ scans may take a few minutes to complete.")
    logger.info("  Check results: SELECT * FROM `%s.fsi_scan_results.*`", pid)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
