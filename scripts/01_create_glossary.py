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
Creates a comprehensive Dataplex Business Glossary for Meridian National Bank.

Provisions: 1 glossary, 10 L1 categories, ~20 L2 sub-categories, 80+ terms,
overviews, contacts, data quality rules, synonym links, related links.

Usage: python3 01_create_glossary.py
"""

import logging
import sys
import time

from common import load_config, api_call, poll_operation, DATAPLEX_URL as BASE_URL, GLOSSARY_ID

logger = logging.getLogger(__name__)


def glossary_exists(cfg):
    url = f"{BASE_URL}/projects/{cfg['project_id']}/locations/{cfg['multi_region']}/glossaries/{GLOSSARY_ID}"
    try:
        api_call(url, "GET")
        return True
    except RuntimeError as e:
        if "404" in str(e):
            return False
        raise


def create_glossary(cfg):
    url = (
        f"{BASE_URL}/projects/{cfg['project_id']}/locations/{cfg['multi_region']}"
        f"/glossaries?glossaryId={GLOSSARY_ID}"
    )
    body = {
        "displayName": "Meridian National Bank Business Glossary",
        "description": (
            "Comprehensive business glossary for Meridian National Bank covering "
            "retail banking, wealth management, lending, risk, compliance, and financial reporting."
        ),
    }
    result = api_call(url, "POST", body)
    if "name" in result and result.get("done") is not True:
        poll_operation(result["name"])
    logger.info("Created glossary: %s", GLOSSARY_ID)


def create_category(cfg, category_id, display_name, description, parent_category_id=None):
    url = (
        f"{BASE_URL}/projects/{cfg['project_id']}/locations/{cfg['multi_region']}"
        f"/glossaries/{GLOSSARY_ID}/categories?categoryId={category_id}"
    )
    if parent_category_id:
        parent = (
            f"projects/{cfg['project_id']}/locations/{cfg['multi_region']}"
            f"/glossaries/{GLOSSARY_ID}/categories/{parent_category_id}"
        )
    else:
        parent = (
            f"projects/{cfg['project_id']}/locations/{cfg['multi_region']}"
            f"/glossaries/{GLOSSARY_ID}"
        )
    body = {"displayName": display_name, "description": description, "parent": parent}
    api_call(url, "POST", body)
    logger.info("Created category: %s", category_id)


def create_term(cfg, term_id, display_name, description, category_id):
    url = (
        f"{BASE_URL}/projects/{cfg['project_id']}/locations/{cfg['multi_region']}"
        f"/glossaries/{GLOSSARY_ID}/terms?termId={term_id}"
    )
    parent = (
        f"projects/{cfg['project_id']}/locations/{cfg['multi_region']}"
        f"/glossaries/{GLOSSARY_ID}/categories/{category_id}"
    )
    body = {"displayName": display_name, "description": description, "parent": parent}
    api_call(url, "POST", body)
    logger.info("Created term: %s", term_id)


def _entry_path(cfg, term_id):
    pn = cfg["project_number"]
    loc = cfg["multi_region"]
    return (
        f"projects/{pn}/locations/{loc}/entryGroups/@dataplex/entries/"
        f"projects/{pn}/locations/{loc}/glossaries/{GLOSSARY_ID}/terms/{term_id}"
    )


def set_term_overview(cfg, term_id, html):
    entry = _entry_path(cfg, term_id)
    url = (
        f"{BASE_URL}/{entry}"
        "?updateMask=aspects&deleteMissingAspects=false"
        "&aspect_keys=dataplex-types.global.overview"
    )
    body = {
        "aspects": {
            "dataplex-types.global.overview": {
                "aspectType": "projects/dataplex-types/locations/global/aspectTypes/overview",
                "data": {"content": html},
            }
        }
    }
    api_call(url, "PATCH", body)


def set_term_contacts(cfg, term_id, steward_name, steward_email, owner_name, owner_email):
    entry = _entry_path(cfg, term_id)
    url = (
        f"{BASE_URL}/{entry}"
        "?updateMask=aspects&deleteMissingAspects=false"
        "&aspect_keys=dataplex-types.global.contacts"
    )
    body = {
        "aspects": {
            "dataplex-types.global.contacts": {
                "aspectType": "projects/dataplex-types/locations/global/aspectTypes/contacts",
                "data": {
                    "identities": [
                        {"role": "Data Steward", "name": steward_name, "id": steward_email},
                        {"role": "Data Owner", "name": owner_name, "id": owner_email},
                    ]
                },
            }
        }
    }
    api_call(url, "PATCH", body)


def create_entry_link(cfg, link_id, term_a, term_b, link_type):
    url = (
        f"{BASE_URL}/projects/{cfg['project_id']}/locations/{cfg['multi_region']}"
        f"/entryGroups/@dataplex/entryLinks?entryLinkId={link_id}"
    )
    entry_a = _entry_path(cfg, term_a)
    entry_b = _entry_path(cfg, term_b)
    body = {
        "entryLinkType": f"projects/dataplex-types/locations/global/entryLinkTypes/{link_type}",
        "entryReferences": [
            {"name": entry_a, "type": "UNSPECIFIED"},
            {"name": entry_b, "type": "UNSPECIFIED"},
        ],
    }
    api_call(url, "POST", body)
    logger.info("Created %s link: %s <-> %s", link_type, term_a, term_b)


# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

CATEGORIES = [
    {
        "id": "customer-identity",
        "display_name": "Customer & Identity",
        "description": "Customer identification, KYC/AML, due diligence, and beneficial ownership",
        "subs": [
            ("kyc-aml", "KYC / AML", "Know Your Customer and Anti-Money Laundering processes and data"),
            ("customer-management", "Customer Management", "Customer demographics, segmentation, and relationship data"),
        ],
    },
    {
        "id": "deposits-accounts",
        "display_name": "Deposits & Accounts",
        "description": "Deposit account types, balances, interest, and FDIC coverage",
        "subs": [
            ("account-types", "Account Types", "Checking, savings, CD, money market, and IRA products"),
            ("account-operations", "Account Operations", "Account servicing, dormancy, and transaction processing"),
        ],
    },
    {
        "id": "lending-credit",
        "display_name": "Lending & Credit",
        "description": "Loan products, underwriting, servicing, delinquency, and credit risk",
        "subs": [
            ("loan-products", "Loan Products", "Mortgage, auto, personal, HELOC, commercial, and SBA loans"),
            ("credit-risk", "Credit Risk Assessment", "FICO scores, LTV, DTI, risk ratings, and delinquency tracking"),
        ],
    },
    {
        "id": "cards-payments",
        "display_name": "Cards & Payments",
        "description": "Credit/debit cards, payment networks, interchange, and fraud detection",
        "subs": [
            ("card-products", "Card Products", "Card types, rewards, limits, and APR"),
            ("payment-processing", "Payment Processing", "ACH, wire transfers, ATM, and settlement"),
        ],
    },
    {
        "id": "wealth-investments",
        "display_name": "Wealth & Investments",
        "description": "Portfolio management, AUM, advisory services, and investment performance",
        "subs": [
            ("portfolio-management", "Portfolio Management", "Portfolios, holdings, asset allocation, and benchmarks"),
            ("advisory-services", "Advisory Services", "Financial advisors, fee schedules, and fiduciary duties"),
        ],
    },
    {
        "id": "trading-securities",
        "display_name": "Trading & Securities",
        "description": "Security master, trade execution, settlement, and market data",
        "subs": [
            ("security-reference", "Security Reference Data", "CUSIP, ISIN, tickers, and security classification"),
            ("trade-execution", "Trade Execution", "Order types, settlement, and trade compliance"),
        ],
    },
    {
        "id": "risk-management",
        "display_name": "Risk Management",
        "description": "Credit, market, operational, and liquidity risk measurement",
        "subs": [
            ("market-risk", "Market Risk", "VaR, duration, interest rate risk, and FX exposure"),
            ("operational-risk", "Operational Risk", "Loss events, KRIs, and business continuity"),
        ],
    },
    {
        "id": "regulatory-compliance",
        "display_name": "Regulatory & Compliance",
        "description": "BSA/AML, SAR/CTR, Basel III, DFAST, and regulatory filings",
        "subs": [
            ("bsa-aml", "BSA / AML", "Bank Secrecy Act, suspicious activity, and currency transaction reporting"),
            ("capital-regulation", "Capital Regulation", "Basel III/IV, DFAST, CCAR, and stress testing"),
        ],
    },
    {
        "id": "financial-reporting",
        "display_name": "Financial Reporting",
        "description": "General ledger, NIM, ROAA, efficiency ratio, and call reports",
        "subs": [
            ("income-statement", "Income Statement", "Interest income, noninterest income, and expense management"),
            ("balance-sheet", "Balance Sheet", "Asset, liability, and equity composition"),
        ],
    },
    {
        "id": "operations-infrastructure",
        "display_name": "Operations & Infrastructure",
        "description": "Branches, channels, core systems, and operational metrics",
        "subs": [],
    },
]

CONTACTS = {
    "customer-identity": ("KYC Data Steward", "kyc-team@meridianbank.com", "Chief Compliance Officer", "cco@meridianbank.com"),
    "deposits-accounts": ("Deposit Operations Steward", "deposit-ops@meridianbank.com", "Head of Retail Banking", "retail-head@meridianbank.com"),
    "lending-credit": ("Credit Data Steward", "credit-data@meridianbank.com", "Chief Credit Officer", "cco-credit@meridianbank.com"),
    "cards-payments": ("Card Operations Steward", "card-ops@meridianbank.com", "Head of Card Services", "cards-head@meridianbank.com"),
    "wealth-investments": ("Wealth Data Steward", "wealth-data@meridianbank.com", "Chief Investment Officer", "cio@meridianbank.com"),
    "trading-securities": ("Trading Data Steward", "trading-data@meridianbank.com", "Head of Trading", "trading-head@meridianbank.com"),
    "risk-management": ("Risk Data Steward", "risk-data@meridianbank.com", "Chief Risk Officer", "cro@meridianbank.com"),
    "regulatory-compliance": ("Compliance Data Steward", "compliance-data@meridianbank.com", "Chief Compliance Officer", "cco@meridianbank.com"),
    "financial-reporting": ("Finance Data Steward", "finance-data@meridianbank.com", "Chief Financial Officer", "cfo@meridianbank.com"),
    "operations-infrastructure": ("Operations Data Steward", "ops-data@meridianbank.com", "Chief Operating Officer", "coo@meridianbank.com"),
}

_L2_TO_L1 = {}
for cat in CATEGORIES:
    for sub_id, _, _ in cat["subs"]:
        _L2_TO_L1[sub_id] = cat["id"]
    _L2_TO_L1[cat["id"]] = cat["id"]


def _contacts_for(category_id):
    l1 = _L2_TO_L1.get(category_id, category_id)
    return CONTACTS[l1]


TERMS = [
    # --- Customer & Identity ---
    ("customer-id", "Customer ID", "customer-management",
     "A unique identifier assigned to each customer within the bank's core systems, used to link all accounts, products, and interactions."),
    ("kyc", "Know Your Customer (KYC)", "kyc-aml",
     "The regulatory process of verifying a customer's identity and assessing their risk profile before and during the banking relationship."),
    ("cdd", "Customer Due Diligence (CDD)", "kyc-aml",
     "The standard level of KYC review applied to all customers, including identity verification, risk assessment, and ongoing monitoring."),
    ("edd", "Enhanced Due Diligence (EDD)", "kyc-aml",
     "Additional scrutiny applied to high-risk customers including PEPs, foreign correspondents, and those in high-risk jurisdictions."),
    ("beneficial-owner", "Beneficial Owner", "kyc-aml",
     "Any individual who directly or indirectly owns 25% or more of an entity customer, or who exercises significant control, as required by the CDD Rule."),
    ("pep", "Politically Exposed Person (PEP)", "kyc-aml",
     "An individual who holds or has held a prominent public function, presenting higher risk for potential involvement in bribery and corruption."),
    ("customer-segment", "Customer Segment", "customer-management",
     "Classification of customers into groups based on relationship value, product usage, and service needs (Standard, Preferred, Premier, Private Banking)."),
    ("tin", "Tax Identification Number (TIN)", "customer-management",
     "A nine-digit number (SSN for individuals, EIN for entities) used for tax reporting and regulatory filings. Classified as PII."),

    # --- Deposits & Accounts ---
    ("checking-account", "Checking Account", "account-types",
     "A demand deposit account (DDA) that allows unlimited withdrawals and deposits, typically used for everyday transactions."),
    ("savings-account", "Savings Account", "account-types",
     "An interest-bearing deposit account designed for accumulating funds, historically subject to Regulation D withdrawal limits."),
    ("certificate-of-deposit", "Certificate of Deposit (CD)", "account-types",
     "A time deposit with a fixed term and interest rate. Early withdrawal incurs a penalty. Reported on Call Report Schedule RC-E."),
    ("money-market-account", "Money Market Account", "account-types",
     "A higher-yield deposit account that may offer limited check-writing privileges, combining features of savings and checking accounts."),
    ("fdic-coverage", "FDIC Insurance Coverage", "account-types",
     "Federal Deposit Insurance Corporation coverage protecting depositors up to $250,000 per depositor, per insured bank, per ownership category."),
    ("dormant-account", "Dormant Account", "account-operations",
     "An account with no customer-initiated activity for a specified period (typically 12 months), subject to escheatment under state unclaimed property laws."),
    ("account-balance", "Account Balance", "account-operations",
     "The current monetary value held in an account, including ledger balance (all posted transactions) and available balance (funds available for withdrawal)."),

    # --- Lending & Credit ---
    ("mortgage", "Mortgage Loan", "loan-products",
     "A loan secured by residential real property. The largest loan category for most banks, reported on Call Report Schedule RC-C line 1."),
    ("auto-loan", "Auto Loan", "loan-products",
     "A secured installment loan for the purchase of a motor vehicle, with the vehicle serving as collateral."),
    ("heloc", "Home Equity Line of Credit (HELOC)", "loan-products",
     "A revolving credit line secured by the borrower's home equity. Subject to TILA/RESPA disclosure requirements."),
    ("commercial-loan", "Commercial Loan (C&I)", "loan-products",
     "A loan to a business for working capital, equipment, or expansion. C&I loans are reported on Call Report Schedule RC-C line 4."),
    ("fico-score", "FICO Score", "credit-risk",
     "A credit score ranging from 300 to 850 produced by Fair Isaac Corporation, used in consumer lending decisions. The primary credit scoring model used by US banks."),
    ("ltv-ratio", "Loan-to-Value Ratio (LTV)", "credit-risk",
     "The ratio of a loan amount to the appraised value of the collateral property. A key underwriting metric for mortgage and real estate lending."),
    ("dti-ratio", "Debt-to-Income Ratio (DTI)", "credit-risk",
     "The percentage of a borrower's gross monthly income consumed by debt payments. A key measure of a borrower's ability to repay."),
    ("delinquency", "Delinquency", "credit-risk",
     "A loan payment status indicating the borrower has failed to make a scheduled payment. Categorized as 30, 60, 90, or 120+ days past due."),
    ("risk-rating", "Risk Rating", "credit-risk",
     "An internal classification of loan credit quality: Pass, Special Mention, Substandard, Doubtful, or Loss. Required for regulatory reporting."),
    ("charge-off", "Charge-Off", "credit-risk",
     "The act of writing off a loan balance as uncollectible, typically after 120-180 days of delinquency. Reported as a reduction in the loan portfolio."),

    # --- Cards & Payments ---
    ("credit-card", "Credit Card", "card-products",
     "A revolving credit product issued under Visa or Mastercard networks allowing purchases up to an approved credit limit."),
    ("apr", "Annual Percentage Rate (APR)", "card-products",
     "The annualized interest rate charged on outstanding credit card balances, including the base rate plus any margin."),
    ("interchange-fee", "Interchange Fee", "card-products",
     "The fee paid by the merchant's bank to the card-issuing bank for each card transaction, regulated by the Durbin Amendment for debit cards."),
    ("chargeback", "Chargeback", "card-products",
     "A forced reversal of a card transaction initiated by the cardholder's bank, typically due to fraud, disputes, or authorization errors."),
    ("ach", "ACH Transfer", "payment-processing",
     "An electronic funds transfer through the Automated Clearing House network, governed by NACHA rules. Includes payroll, bill payments, and P2P transfers."),
    ("wire-transfer", "Wire Transfer", "payment-processing",
     "A same-day electronic funds transfer between banks, processed through Fedwire or SWIFT. Subject to BSA/AML monitoring and OFAC screening."),
    ("ctr", "Currency Transaction Report (CTR)", "payment-processing",
     "A FinCEN-required report filed for cash transactions exceeding $10,000 in a single business day. Filed on FinCEN Form 112."),

    # --- Wealth & Investments ---
    ("aum", "Assets Under Management (AUM)", "portfolio-management",
     "The total market value of all investment assets managed on behalf of clients by the wealth management division."),
    ("portfolio", "Investment Portfolio", "portfolio-management",
     "A collection of investment holdings managed under a single account, aligned to a client's investment objective and risk tolerance."),
    ("asset-allocation", "Asset Allocation", "portfolio-management",
     "The strategic distribution of portfolio assets across asset classes (equities, fixed income, alternatives, cash) based on the client's risk profile."),
    ("benchmark", "Benchmark Index", "portfolio-management",
     "A market index (S&P 500, Bloomberg US Agg, etc.) used to evaluate portfolio performance and calculate alpha."),
    ("alpha", "Alpha", "portfolio-management",
     "The excess return of a portfolio relative to its benchmark index. Positive alpha indicates the advisor has added value beyond passive market returns."),
    ("sharpe-ratio", "Sharpe Ratio", "portfolio-management",
     "A risk-adjusted return metric calculated as (portfolio return - risk-free rate) / portfolio standard deviation. Higher values indicate better risk-adjusted performance."),
    ("financial-advisor", "Financial Advisor", "advisory-services",
     "A FINRA-registered representative who provides investment advice and manages client portfolios, subject to suitability or fiduciary obligations."),
    ("advisory-fee", "Advisory Fee", "advisory-services",
     "The fee charged for investment advisory services, typically expressed in basis points (bps) of AUM and billed quarterly."),
    ("fiduciary-duty", "Fiduciary Duty", "advisory-services",
     "The legal obligation of an investment advisor to act in the client's best interest, as required under the Investment Advisers Act of 1940."),
    ("accredited-investor", "Accredited Investor", "advisory-services",
     "An individual or entity meeting SEC income or net worth thresholds, eligible to invest in unregistered securities and private placements."),

    # --- Trading & Securities ---
    ("cusip", "CUSIP", "security-reference",
     "Committee on Uniform Securities Identification Procedures — a 9-character alphanumeric code uniquely identifying a North American security."),
    ("isin", "ISIN", "security-reference",
     "International Securities Identification Number — a 12-character code (2-letter country + 9-char CUSIP + check digit) for global security identification."),
    ("ticker-symbol", "Ticker Symbol", "security-reference",
     "A short alphabetic code assigned to a publicly traded security for exchange identification and trading purposes."),
    ("trade-settlement", "Trade Settlement", "trade-execution",
     "The process of transferring securities and funds between buyer and seller. US equities settle T+1 (one business day after trade date)."),
    ("order-type", "Order Type", "trade-execution",
     "The instruction type for executing a trade: Market (immediate at best price), Limit (at specified price or better), or Stop (triggered at threshold)."),

    # --- Risk Management ---
    ("var", "Value at Risk (VaR)", "market-risk",
     "A statistical measure of the maximum expected loss on a portfolio over a given time horizon at a specified confidence level (e.g., 99% 1-day VaR)."),
    ("credit-risk", "Credit Risk", "credit-risk",
     "The risk of financial loss arising from a borrower's or counterparty's failure to meet their contractual obligations."),
    ("market-risk", "Market Risk", "market-risk",
     "The risk of losses in on- and off-balance-sheet positions arising from movements in market prices (interest rates, equity, FX, commodities)."),
    ("operational-risk", "Operational Risk", "operational-risk",
     "The risk of loss resulting from inadequate or failed internal processes, people, systems, or from external events. Includes fraud, IT failures, and compliance breaches."),
    ("liquidity-risk", "Liquidity Risk", "market-risk",
     "The risk that the bank cannot meet its financial obligations as they come due without incurring unacceptable losses."),
    ("counterparty-risk", "Counterparty Risk", "market-risk",
     "The risk that the other party in a financial transaction will default on its contractual obligation before the final settlement."),
    ("stress-testing", "Stress Testing", "market-risk",
     "Forward-looking analysis evaluating the impact of hypothetical adverse economic scenarios on the bank's capital, earnings, and liquidity."),

    # --- Regulatory & Compliance ---
    ("sar", "Suspicious Activity Report (SAR)", "bsa-aml",
     "A FinCEN filing (Form 111) required when a bank detects known or suspected violations of law, suspicious transactions, or structuring patterns."),
    ("bsa", "Bank Secrecy Act (BSA)", "bsa-aml",
     "Federal legislation requiring financial institutions to maintain records and file reports that help detect and prevent money laundering and terrorist financing."),
    ("ofac-screening", "OFAC Screening", "bsa-aml",
     "The process of checking customers, transactions, and counterparties against the Office of Foreign Assets Control sanctions lists (SDN, SSI, etc.)."),
    ("basel-iii", "Basel III", "capital-regulation",
     "The international regulatory framework for banks establishing minimum capital requirements (CET1, Tier 1, Total Capital) and liquidity standards (LCR, NSFR)."),
    ("cet1-ratio", "CET1 Capital Ratio", "capital-regulation",
     "Common Equity Tier 1 capital divided by risk-weighted assets. The most stringent measure of bank capital adequacy. Minimum requirement: 4.5% + buffers."),
    ("dfast", "DFAST (Dodd-Frank Act Stress Test)", "capital-regulation",
     "Annual stress test required for banks with >$100B in assets, projecting capital ratios under baseline, adverse, and severely adverse economic scenarios."),
    ("call-report", "Call Report (FFIEC 031/041)", "capital-regulation",
     "Quarterly regulatory filing submitted to the FDIC/OCC containing detailed financial data including balance sheet, income statement, and asset quality."),

    # --- Financial Reporting ---
    ("net-interest-margin", "Net Interest Margin (NIM)", "income-statement",
     "The difference between interest income earned and interest expense paid, divided by average earning assets. The primary profitability metric for banks."),
    ("efficiency-ratio", "Efficiency Ratio", "income-statement",
     "Noninterest expense divided by total revenue (net interest income + noninterest income). Lower is better — measures how much it costs to generate $1 of revenue."),
    ("roaa", "Return on Average Assets (ROAA)", "income-statement",
     "Net income divided by average total assets. A key profitability measure indicating how effectively the bank uses its assets to generate earnings."),
    ("provision-for-credit-losses", "Provision for Credit Losses", "income-statement",
     "The expense recorded on the income statement to build the allowance for credit losses (ALLL/ACL) in anticipation of future loan defaults."),
    ("general-ledger", "General Ledger (GL)", "balance-sheet",
     "The master accounting record containing all financial transactions organized by account. The authoritative source for financial statement preparation."),
    ("risk-weighted-assets", "Risk-Weighted Assets (RWA)", "balance-sheet",
     "Total assets and off-balance-sheet exposures adjusted by risk weight factors (0%-150%) prescribed by Basel III. The denominator for capital ratio calculations."),
    ("allowance-for-credit-losses", "Allowance for Credit Losses (ACL)", "balance-sheet",
     "A contra-asset account representing management's estimate of expected lifetime credit losses on the loan portfolio, per CECL (ASC 326)."),

    # --- Operations & Infrastructure ---
    ("branch", "Branch", "operations-infrastructure",
     "A physical bank location offering deposit, lending, and advisory services. Branches are cost centers tracked for performance and regulatory reporting."),
    ("core-banking-system", "Core Banking System", "operations-infrastructure",
     "The central platform (ATLAS for Meridian) processing deposits, loans, and customer transactions in real-time."),
    ("digital-channel", "Digital Channel", "operations-infrastructure",
     "Online banking, mobile banking, and ATM services enabling self-service transactions outside branch hours."),

    # --- Abbreviation aliases ---
    ("kyc-abbr", "KYC", "kyc-aml", "Abbreviation for Know Your Customer."),
    ("cdd-abbr", "CDD", "kyc-aml", "Abbreviation for Customer Due Diligence."),
    ("edd-abbr", "EDD", "kyc-aml", "Abbreviation for Enhanced Due Diligence."),
    ("aum-abbr", "AUM", "portfolio-management", "Abbreviation for Assets Under Management."),
    ("var-abbr", "VaR", "market-risk", "Abbreviation for Value at Risk."),
    ("sar-abbr", "SAR", "bsa-aml", "Abbreviation for Suspicious Activity Report."),
    ("ctr-abbr", "CTR", "payment-processing", "Abbreviation for Currency Transaction Report."),
    ("nim-abbr", "NIM", "income-statement", "Abbreviation for Net Interest Margin."),
    ("rwa-abbr", "RWA", "balance-sheet", "Abbreviation for Risk-Weighted Assets."),
    ("acl-abbr", "ACL", "balance-sheet", "Abbreviation for Allowance for Credit Losses."),
    ("ltv-abbr", "LTV", "credit-risk", "Abbreviation for Loan-to-Value Ratio."),
    ("dti-abbr", "DTI", "credit-risk", "Abbreviation for Debt-to-Income Ratio."),
]


def _build_overviews():
    o = {}
    o["customer-id"] = "<h2>Customer ID</h2><p>The unique identifier for each customer in the ATLAS core banking system. Format: CUST-NNNNNNNN. Links all accounts, loans, cards, and KYC records for a single customer relationship.</p><h3>Cross-System Mapping</h3><p>Retail customers may also have a wealth management ID (WMC-NNNNNNN) in FORTUNA. The gold_customer_360 table joins both identifiers for a unified view.</p>"
    o["kyc"] = "<h2>Know Your Customer (KYC)</h2><p>KYC is the regulatory process mandated by the BSA/AML framework requiring banks to verify customer identity, assess risk, and monitor ongoing activity.</p><h3>KYC Tiers</h3><ul><li><strong>SDD:</strong> Simplified Due Diligence — low-risk customers</li><li><strong>CDD:</strong> Standard due diligence — all customers at onboarding</li><li><strong>EDD:</strong> Enhanced due diligence — PEPs, high-risk jurisdictions, complex structures</li></ul>"
    o["fico-score"] = "<h2>FICO Score</h2><p>A credit score ranging from 300-850 used in consumer lending decisions. At Meridian, FICO is captured at loan origination and monitored quarterly for the existing portfolio.</p><h3>Score Ranges</h3><ul><li><strong>Exceptional:</strong> 800-850</li><li><strong>Very Good:</strong> 740-799</li><li><strong>Good:</strong> 670-739</li><li><strong>Fair:</strong> 580-669</li><li><strong>Poor:</strong> 300-579</li></ul>"
    o["sar"] = "<h2>Suspicious Activity Report (SAR)</h2><p>Filed with FinCEN (Form 111) when the bank detects transactions or patterns that suggest money laundering, terrorist financing, fraud, or other criminal activity.</p><h3>Filing Requirements</h3><ul><li>Must be filed within 30 calendar days of initial detection</li><li>No dollar threshold — any suspicious activity must be evaluated</li><li>Confidential — cannot be disclosed to the subject of the report</li><li>Retention: 5 years from filing date</li></ul>"
    o["cet1-ratio"] = "<h2>CET1 Capital Ratio</h2><p>Common Equity Tier 1 capital divided by risk-weighted assets. The highest quality form of regulatory capital.</p><h3>Requirements</h3><ul><li>Minimum: 4.5%</li><li>Capital Conservation Buffer: +2.5%</li><li>Countercyclical Buffer: 0-2.5% (currently 0%)</li><li>G-SIB Surcharge: 1-4.5% (if applicable)</li><li>Effective minimum for well-capitalized: 6.5%+</li></ul>"
    o["net-interest-margin"] = "<h2>Net Interest Margin (NIM)</h2><p>The primary profitability metric for banks, measuring the spread between interest earned on assets and interest paid on liabilities.</p><h3>Formula</h3><p>(Interest Income - Interest Expense) / Average Earning Assets</p><h3>Industry Benchmarks</h3><ul><li>Community banks: 3.0-4.0%</li><li>Regional banks: 2.5-3.5%</li><li>Large banks: 2.0-3.0%</li></ul>"
    o["aum"] = "<h2>Assets Under Management (AUM)</h2><p>The total market value of investment assets managed by FORTUNA Wealth Management on behalf of clients. AUM is the primary revenue driver for advisory fee income.</p><h3>Revenue Impact</h3><p>Advisory fees are typically 50-150 bps of AUM, billed quarterly. A 1% change in AUM directly impacts fee revenue.</p>"
    o["var"] = "<h2>Value at Risk (VaR)</h2><p>A statistical measure estimating the maximum potential loss on a portfolio over a specified time horizon at a given confidence level.</p><h3>Meridian VaR Parameters</h3><ul><li>99% confidence, 1-day horizon (trading book)</li><li>99% confidence, 10-day horizon (regulatory)</li><li>Methodology: Historical simulation with 2-year lookback</li></ul>"

    for alias, full in [("kyc-abbr", "Know Your Customer"), ("cdd-abbr", "Customer Due Diligence"),
                        ("edd-abbr", "Enhanced Due Diligence"), ("aum-abbr", "Assets Under Management"),
                        ("var-abbr", "Value at Risk"), ("sar-abbr", "Suspicious Activity Report"),
                        ("ctr-abbr", "Currency Transaction Report"), ("nim-abbr", "Net Interest Margin"),
                        ("rwa-abbr", "Risk-Weighted Assets"), ("acl-abbr", "Allowance for Credit Losses"),
                        ("ltv-abbr", "Loan-to-Value Ratio"), ("dti-abbr", "Debt-to-Income Ratio")]:
        o[alias] = f"<p><strong>{alias.replace('-abbr','').upper()}</strong> is a commonly used abbreviation for <em>{full}</em>. See the full term definition for complete details.</p>"

    return o


OVERVIEWS = _build_overviews()

SYNONYM_LINKS = [
    ("kyc-abbr", "kyc"),
    ("cdd-abbr", "cdd"),
    ("edd-abbr", "edd"),
    ("aum-abbr", "aum"),
    ("var-abbr", "var"),
    ("sar-abbr", "sar"),
    ("ctr-abbr", "ctr"),
    ("nim-abbr", "net-interest-margin"),
    ("rwa-abbr", "risk-weighted-assets"),
    ("acl-abbr", "allowance-for-credit-losses"),
    ("ltv-abbr", "ltv-ratio"),
    ("dti-abbr", "dti-ratio"),
]

RELATED_LINKS = [
    ("customer-id", "kyc"),
    ("kyc", "cdd"),
    ("kyc", "edd"),
    ("kyc", "beneficial-owner"),
    ("kyc", "pep"),
    ("kyc", "sar"),
    ("customer-segment", "customer-id"),
    ("checking-account", "account-balance"),
    ("savings-account", "account-balance"),
    ("certificate-of-deposit", "fdic-coverage"),
    ("dormant-account", "account-balance"),
    ("mortgage", "ltv-ratio"),
    ("mortgage", "fico-score"),
    ("fico-score", "dti-ratio"),
    ("delinquency", "risk-rating"),
    ("delinquency", "charge-off"),
    ("risk-rating", "provision-for-credit-losses"),
    ("credit-card", "apr"),
    ("credit-card", "interchange-fee"),
    ("credit-card", "chargeback"),
    ("wire-transfer", "ctr"),
    ("wire-transfer", "ofac-screening"),
    ("ach", "wire-transfer"),
    ("aum", "advisory-fee"),
    ("aum", "portfolio"),
    ("portfolio", "asset-allocation"),
    ("portfolio", "benchmark"),
    ("benchmark", "alpha"),
    ("alpha", "sharpe-ratio"),
    ("financial-advisor", "fiduciary-duty"),
    ("financial-advisor", "advisory-fee"),
    ("cusip", "isin"),
    ("cusip", "ticker-symbol"),
    ("trade-settlement", "order-type"),
    ("var", "market-risk"),
    ("var", "stress-testing"),
    ("credit-risk", "counterparty-risk"),
    ("sar", "bsa"),
    ("sar", "ofac-screening"),
    ("cet1-ratio", "basel-iii"),
    ("cet1-ratio", "risk-weighted-assets"),
    ("cet1-ratio", "dfast"),
    ("dfast", "stress-testing"),
    ("call-report", "general-ledger"),
    ("net-interest-margin", "efficiency-ratio"),
    ("net-interest-margin", "roaa"),
    ("provision-for-credit-losses", "allowance-for-credit-losses"),
    ("general-ledger", "risk-weighted-assets"),
    ("branch", "core-banking-system"),
    ("branch", "digital-channel"),
]


def main():
    cfg = load_config()
    logger.info("Project: %s | Location: %s", cfg["project_id"], cfg["multi_region"])

    if glossary_exists(cfg):
        logger.info("Glossary '%s' already exists — skipping creation, proceeding with terms/links.", GLOSSARY_ID)
    else:
        logger.info("--- Creating glossary ---")
        create_glossary(cfg)
        logger.info("Waiting 15s for glossary propagation...")
        time.sleep(15)

    logger.info("--- Creating L1 categories (%d) ---", len(CATEGORIES))
    for cat in CATEGORIES:
        create_category(cfg, cat["id"], cat["display_name"], cat["description"])
        time.sleep(0.5)

    l2_count = sum(len(c["subs"]) for c in CATEGORIES)
    logger.info("--- Creating L2 sub-categories (%d) ---", l2_count)
    for cat in CATEGORIES:
        for sub_id, sub_name, sub_desc in cat["subs"]:
            create_category(cfg, sub_id, sub_name, sub_desc, parent_category_id=cat["id"])
            time.sleep(0.5)

    logger.info("--- Creating terms (%d) ---", len(TERMS))
    for term_id, display_name, category_id, description in TERMS:
        create_term(cfg, term_id, display_name, description, category_id)
        time.sleep(0.5)

    logger.info("--- Setting term overviews (%d) ---", len(OVERVIEWS))
    for term_id, html in OVERVIEWS.items():
        try:
            set_term_overview(cfg, term_id, html)
        except RuntimeError as e:
            logger.warning("Failed to set overview for %s: %s", term_id, e)
        time.sleep(0.5)

    logger.info("--- Setting term contacts ---")
    for term_id, _, category_id, _ in TERMS:
        contacts = _contacts_for(category_id)
        try:
            set_term_contacts(cfg, term_id, contacts[0], contacts[1], contacts[2], contacts[3])
        except RuntimeError as e:
            logger.warning("Failed to set contacts for %s: %s", term_id, e)
        time.sleep(0.5)

    logger.info("--- Creating synonym links (%d) ---", len(SYNONYM_LINKS))
    for term_a, term_b in SYNONYM_LINKS:
        link_id = f"syn-{term_a}-{term_b}"
        try:
            create_entry_link(cfg, link_id, term_a, term_b, "synonym")
        except RuntimeError as e:
            logger.warning("Failed to create synonym link %s: %s", link_id, e)
        time.sleep(0.5)

    logger.info("--- Creating related links (%d) ---", len(RELATED_LINKS))
    for term_a, term_b in RELATED_LINKS:
        link_id = f"rel-{term_a}-{term_b}"
        try:
            create_entry_link(cfg, link_id, term_a, term_b, "related")
        except RuntimeError as e:
            logger.warning("Failed to create related link %s: %s", link_id, e)
        time.sleep(0.5)

    logger.info("=" * 60)
    logger.info("GLOSSARY CREATION COMPLETE")
    logger.info("  Glossary:       %s", GLOSSARY_ID)
    logger.info("  Categories:     %d (L1) + %d (L2) = %d", len(CATEGORIES), l2_count, len(CATEGORIES) + l2_count)
    logger.info("  Terms:          %d", len(TERMS))
    logger.info("  Overviews:      %d", len(OVERVIEWS))
    logger.info("  Synonym Links:  %d", len(SYNONYM_LINKS))
    logger.info("  Related Links:  %d", len(RELATED_LINKS))
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
