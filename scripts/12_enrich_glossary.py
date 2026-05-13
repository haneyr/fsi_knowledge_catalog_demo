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
Enriches ALL 83 glossary term overviews with rich, detailed HTML content.

Generates comprehensive overviews including business definitions, Meridian
National Bank context, data quality rule descriptions, regulatory context,
and cross-references to related terms.

Usage: python3 12_enrich_glossary.py
"""

import logging
import time

from common import load_config, api_call, DATAPLEX_URL as BASE_URL, GLOSSARY_ID

logger = logging.getLogger(__name__)


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


# ---------------------------------------------------------------------------
# Rich HTML overviews for all 83 terms
# ---------------------------------------------------------------------------

OVERVIEWS = {}

# ==========================================================================
# CUSTOMER & IDENTITY
# ==========================================================================

OVERVIEWS["customer-id"] = """
<h2>Customer ID</h2>
<p>A Customer ID is the unique, system-generated identifier assigned to each customer
within Meridian National Bank's core banking platform (ATLAS). The format follows the
pattern <strong>CUST-NNNNNNNN</strong>, where N represents a numeric digit. This
identifier serves as the primary key linking all accounts, loans, credit cards, KYC
records, and interaction history for a single customer relationship.</p>

<p>At Meridian National Bank, the Customer ID is established at the point of onboarding
and persists for the lifetime of the customer relationship. Even if all accounts are
closed, the Customer ID is retained for regulatory record-keeping purposes (minimum
5 years post-relationship under BSA requirements). The ATLAS system ensures uniqueness
across all branches and channels.</p>

<h3>Cross-System Mapping</h3>
<p>Retail banking customers who also have a wealth management relationship are assigned
a separate FORTUNA Wealth Management ID (format: <strong>WMC-NNNNNNN</strong>). The
<em>gold_customer_360</em> table in the analytics layer joins both identifiers to
provide a unified, enterprise-wide view of each customer's total relationship value,
product holdings, and risk profile.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Know Your Customer (KYC)</strong> &mdash; KYC verification is performed using the Customer ID as the anchor</li>
<li><strong>Customer Segment</strong> &mdash; Segmentation models reference Customer ID to assign tier classifications</li>
<li><strong>Tax Identification Number (TIN)</strong> &mdash; TIN is linked to the Customer ID for tax reporting</li>
</ul>
"""

OVERVIEWS["kyc"] = """
<h2>Know Your Customer (KYC)</h2>
<p>Know Your Customer (KYC) is the regulatory process mandated by the Bank Secrecy Act
(BSA) and USA PATRIOT Act requiring financial institutions to verify the identity of
their customers, assess their risk profiles, and monitor their transactions on an
ongoing basis. KYC is the foundation of Meridian National Bank's anti-money laundering
(AML) compliance program.</p>

<p>The KYC process at Meridian encompasses three tiers of due diligence, each applied
based on the customer's assessed risk level. All new customers undergo standard Customer
Due Diligence (CDD) at account opening. Customers identified as higher risk &mdash;
including Politically Exposed Persons (PEPs), those operating in high-risk jurisdictions,
or those with complex corporate structures &mdash; are escalated to Enhanced Due
Diligence (EDD).</p>

<h3>KYC Tiers at Meridian National Bank</h3>
<ul>
<li><strong>SDD (Simplified Due Diligence):</strong> Applied to low-risk, well-known customer
types such as publicly listed companies and government entities</li>
<li><strong>CDD (Customer Due Diligence):</strong> Standard verification applied to all
customers at onboarding, including identity verification, risk assessment, and
beneficial ownership identification for legal entities</li>
<li><strong>EDD (Enhanced Due Diligence):</strong> Intensified scrutiny for PEPs,
foreign correspondents, customers in FATF high-risk jurisdictions, and those with
complex or opaque ownership structures</li>
</ul>

<h3>Regulatory Context</h3>
<p>KYC requirements are enforced under 31 CFR Chapter X (FinCEN regulations), the
BSA/AML framework, and the CDD Final Rule (31 CFR 1010.230). Failure to maintain
adequate KYC programs can result in significant civil money penalties, enforcement
actions, and reputational damage. Meridian's KYC program is examined annually by the
OCC as part of the BSA/AML examination.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Customer Due Diligence (CDD)</strong> &mdash; The standard KYC tier</li>
<li><strong>Enhanced Due Diligence (EDD)</strong> &mdash; The elevated KYC tier for high-risk customers</li>
<li><strong>Beneficial Owner</strong> &mdash; Must be identified as part of the CDD process</li>
<li><strong>Politically Exposed Person (PEP)</strong> &mdash; A key risk indicator triggering EDD</li>
<li><strong>Suspicious Activity Report (SAR)</strong> &mdash; Filed when KYC monitoring detects suspicious patterns</li>
</ul>
"""

OVERVIEWS["cdd"] = """
<h2>Customer Due Diligence (CDD)</h2>
<p>Customer Due Diligence is the standard level of KYC review that Meridian National
Bank applies to every customer at the time of account opening and throughout the
banking relationship. CDD encompasses identity verification, risk assessment, and
the collection of information necessary to understand the nature and purpose of
the customer relationship.</p>

<p>Under the FinCEN CDD Final Rule (effective May 2018), Meridian is required to
establish and maintain written procedures for: (1) identifying and verifying the
identity of customers, (2) identifying and verifying the identity of beneficial
owners of legal entity customers, (3) understanding the nature and purpose of
customer relationships, and (4) conducting ongoing monitoring to identify and
report suspicious transactions and maintain/update customer information.</p>

<h3>CDD at Meridian National Bank</h3>
<p>The ATLAS core banking system captures CDD data at onboarding and stores it in
the <em>bronze_kyc_records</em> table. CDD reviews are triggered by risk-based
schedules: annually for high-risk customers, every two years for medium-risk, and
every three years for low-risk. The <em>gold_aml_risk_scoring</em> table
aggregates CDD data with transaction patterns for ongoing risk assessment.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Know Your Customer (KYC)</strong> &mdash; The overarching regulatory framework</li>
<li><strong>Enhanced Due Diligence (EDD)</strong> &mdash; Elevated review for high-risk customers</li>
<li><strong>Beneficial Owner</strong> &mdash; Must be identified under the CDD Rule</li>
</ul>
"""

OVERVIEWS["edd"] = """
<h2>Enhanced Due Diligence (EDD)</h2>
<p>Enhanced Due Diligence is the heightened level of scrutiny applied to customers
presenting elevated money laundering, terrorist financing, or sanctions risk. EDD
goes beyond standard CDD by requiring more extensive information gathering, deeper
investigation of the source of funds and wealth, and more frequent ongoing monitoring.</p>

<p>At Meridian National Bank, EDD is triggered when a customer is identified as a
Politically Exposed Person (PEP), operates in or transacts with parties in FATF
high-risk jurisdictions, maintains complex multi-layered corporate structures, or
is otherwise assessed as high-risk by the bank's AML risk scoring model. EDD cases
are reviewed by the BSA/AML compliance team and require senior management approval
for relationship continuation.</p>

<h3>EDD Triggers</h3>
<ul>
<li><strong>PEP status:</strong> Current or former senior government officials, their family members, and close associates</li>
<li><strong>High-risk jurisdictions:</strong> Countries identified by FATF as having strategic AML/CFT deficiencies</li>
<li><strong>Complex structures:</strong> Multi-layered entities, trusts, or nominee arrangements that obscure beneficial ownership</li>
<li><strong>Unusual transaction patterns:</strong> Activity inconsistent with the customer's stated business or risk profile</li>
<li><strong>Adverse media:</strong> Negative news findings related to financial crime, corruption, or sanctions</li>
</ul>

<h3>Regulatory Context</h3>
<p>EDD requirements are rooted in the BSA/AML framework, FFIEC BSA/AML Examination
Manual, and FinCEN advisories. The OCC expects banks to apply risk-based EDD procedures
proportionate to the risks posed by higher-risk customers.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Know Your Customer (KYC)</strong> &mdash; The overarching framework</li>
<li><strong>Customer Due Diligence (CDD)</strong> &mdash; The standard level of review</li>
<li><strong>Politically Exposed Person (PEP)</strong> &mdash; A primary trigger for EDD</li>
</ul>
"""

OVERVIEWS["beneficial-owner"] = """
<h2>Beneficial Owner</h2>
<p>A Beneficial Owner is any natural person who, directly or indirectly, owns 25% or
more of the equity interests of a legal entity customer, or who exercises significant
managerial control over the entity. Under FinCEN's Customer Due Diligence (CDD) Rule,
Meridian National Bank must identify and verify the identity of all beneficial owners
at the time of account opening for legal entity customers.</p>

<p>The CDD Rule (31 CFR 1010.230) requires collection of the following for each
beneficial owner: full legal name, date of birth, address, and an identification number
(SSN or passport number for non-US persons). Meridian uses the FinCEN Beneficial
Ownership Certification Form to collect this information and stores it in the KYC
records system for ongoing monitoring and regulatory examination.</p>

<h3>Beneficial Ownership at Meridian</h3>
<p>Beneficial ownership data is captured in <em>bronze_kyc_records</em> and linked to
the legal entity customer record. The compliance team conducts periodic reviews to
ensure ownership information remains current, particularly when triggered by
significant changes in account activity or entity structure. Changes in beneficial
ownership require re-verification within a reasonable timeframe.</p>

<h3>Regulatory Context</h3>
<p>The Corporate Transparency Act (CTA) further strengthened beneficial ownership
requirements, mandating that companies report their beneficial owners directly to
FinCEN. Banks must still collect this information under the CDD Rule and may use
the FinCEN registry as a supplementary verification source.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Customer Due Diligence (CDD)</strong> &mdash; Beneficial ownership identification is a core CDD requirement</li>
<li><strong>Know Your Customer (KYC)</strong> &mdash; The overarching regulatory process</li>
<li><strong>Enhanced Due Diligence (EDD)</strong> &mdash; Complex ownership structures may trigger EDD</li>
</ul>
"""

OVERVIEWS["pep"] = """
<h2>Politically Exposed Person (PEP)</h2>
<p>A Politically Exposed Person is an individual who holds or has recently held a
prominent public function, including heads of state, senior government officials,
judicial or military leaders, senior executives of state-owned enterprises, and
senior political party officials. The definition extends to their immediate family
members and close associates, who may be conduits for illicit financial flows.</p>

<p>PEPs present heightened risk for potential involvement in bribery, corruption,
and money laundering due to their positions of influence and access to public funds.
At Meridian National Bank, PEP screening is conducted at customer onboarding and
periodically throughout the relationship using specialized screening databases that
cover domestic and foreign PEP lists.</p>

<h3>PEP Management at Meridian</h3>
<p>When a customer is identified as a PEP, Meridian's BSA/AML compliance team
initiates Enhanced Due Diligence (EDD) procedures, including investigation of the
source of funds and wealth, senior management approval for the relationship, and
enhanced transaction monitoring with lower alert thresholds. PEP status is recorded
in the KYC system and reviewed at least annually.</p>

<h3>Regulatory Context</h3>
<p>While US regulations do not explicitly define "PEP," the FFIEC BSA/AML Examination
Manual and FinCEN guidance expect banks to identify and apply enhanced scrutiny to
PEP relationships. The FATF Recommendations (12 and 22) provide the international
standard for PEP due diligence.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Enhanced Due Diligence (EDD)</strong> &mdash; Required for all PEP relationships</li>
<li><strong>Know Your Customer (KYC)</strong> &mdash; PEP screening is a component of KYC</li>
<li><strong>OFAC Screening</strong> &mdash; PEPs may also appear on sanctions lists</li>
</ul>
"""

OVERVIEWS["customer-segment"] = """
<h2>Customer Segment</h2>
<p>Customer Segment refers to the classification of banking customers into distinct
groups based on their total relationship value, product usage patterns, service
requirements, and revenue potential. Segmentation enables Meridian National Bank to
tailor product offerings, service levels, pricing, and communication strategies to
each customer tier.</p>

<p>Meridian employs a four-tier segmentation model for retail customers:
<strong>Standard</strong> (basic banking relationships), <strong>Preferred</strong>
(mid-tier with multiple products), <strong>Premier</strong> (high-value relationships
with dedicated service), and <strong>Private Banking</strong> (ultra-high-net-worth
individuals requiring bespoke financial solutions). Commercial customers are segmented
separately by revenue size and industry classification.</p>

<h3>Segmentation at Meridian</h3>
<p>Customer segments are calculated monthly using the <em>gold_customer_360</em>
analytics table, which aggregates deposit balances, loan outstanding, investment AUM,
fee revenue, and transaction volume across all products. Segment assignments drive
fee waivers, interest rate pricing, priority service routing, and advisor assignment
in the wealth management division.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Customer ID</strong> &mdash; The unique identifier used to calculate segment membership</li>
<li><strong>Assets Under Management (AUM)</strong> &mdash; A key input for Premier and Private Banking segmentation</li>
<li><strong>Financial Advisor</strong> &mdash; Premier and Private Banking clients are assigned dedicated advisors</li>
</ul>
"""

OVERVIEWS["tin"] = """
<h2>Tax Identification Number (TIN)</h2>
<p>A Tax Identification Number is a nine-digit identifier used by the Internal Revenue
Service (IRS) and financial institutions for tax reporting and regulatory compliance
purposes. For individual customers, the TIN is their Social Security Number (SSN);
for business entities, it is the Employer Identification Number (EIN). The TIN is
classified as Personally Identifiable Information (PII) and is subject to strict
data protection and access controls.</p>

<p>At Meridian National Bank, TIN collection is mandatory at account opening under
IRS regulations (26 CFR 301.6109). The TIN is required for filing Forms 1099 (interest
income), 1098 (mortgage interest), and Currency Transaction Reports (CTRs). Customers
who fail to provide a valid TIN are subject to backup withholding at 24% on
reportable payments.</p>

<h3>Data Quality Controls</h3>
<p>TINs stored in Meridian's data systems are masked in the format <strong>XXX-XX-NNNN</strong>
to protect customer privacy while preserving the last four digits for verification
purposes. Data quality rules validate that all stored TIN values conform to this
masking pattern. Records that do not match the expected format are flagged for
review by the data stewardship team to ensure compliance with PII protection
policies and prevent accidental exposure of unmasked sensitive data.</p>

<h3>Regulatory Context</h3>
<p>TIN requirements are governed by the IRS (26 USC 6109), BSA/AML regulations
(customer identification program), and GLBA (data privacy). Meridian performs
TIN verification through the IRS TIN Matching Program to ensure accuracy of
tax reporting.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Customer ID</strong> &mdash; TIN is linked to the Customer ID for tax reporting</li>
<li><strong>Know Your Customer (KYC)</strong> &mdash; TIN verification is part of the CIP/KYC process</li>
<li><strong>Currency Transaction Report (CTR)</strong> &mdash; TIN is required on CTR filings</li>
</ul>
"""

# ==========================================================================
# DEPOSITS & ACCOUNTS
# ==========================================================================

OVERVIEWS["checking-account"] = """
<h2>Checking Account</h2>
<p>A Checking Account, formally known as a Demand Deposit Account (DDA), is a
transactional bank account that allows the account holder to deposit and withdraw
funds without restriction. Unlike savings accounts or certificates of deposit,
checking accounts provide immediate access to funds through checks, debit cards,
ACH transfers, wire transfers, and ATM withdrawals.</p>

<p>Meridian National Bank offers several checking account tiers: <strong>Essential
Checking</strong> (no minimum balance, modest monthly fee), <strong>Preferred
Checking</strong> (fee waived with $5,000 combined balance), and <strong>Premier
Checking</strong> (premium features including higher ATM reimbursement and dedicated
service). All checking accounts are FDIC-insured up to $250,000 per depositor per
ownership category.</p>

<h3>Regulatory Reporting</h3>
<p>Checking account balances are reported on the Call Report (FFIEC 031/041)
Schedule RC-E as domestic office deposits in transaction accounts. Meridian tracks
these balances daily in the <em>bronze_accounts</em> table and aggregates them
in <em>gold_account_summary</em> for reporting.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Account Balance</strong> &mdash; The current value held in the checking account</li>
<li><strong>FDIC Insurance Coverage</strong> &mdash; Protection for deposited funds</li>
<li><strong>Dormant Account</strong> &mdash; Checking accounts may become dormant after prolonged inactivity</li>
<li><strong>ACH Transfer</strong> &mdash; Common payment method used with checking accounts</li>
</ul>
"""

OVERVIEWS["savings-account"] = """
<h2>Savings Account</h2>
<p>A Savings Account is an interest-bearing deposit account designed for the
accumulation and preservation of funds. Historically subject to Federal Reserve
Regulation D, which limited certain types of withdrawals and transfers to six per
month, this restriction was suspended in April 2020 and has not been reinstated.
Despite this, savings accounts remain distinct from checking accounts in their
purpose and interest-bearing characteristics.</p>

<p>Meridian National Bank offers tiered savings products including <strong>Standard
Savings</strong>, <strong>High-Yield Savings</strong> (with a higher APY for balances
above $10,000), and <strong>Youth Savings</strong> (for customers under 18 with no
minimum balance requirement). Interest is accrued daily and credited monthly, with
rates set by the Asset-Liability Committee (ALCO) based on market conditions and
the bank's funding needs.</p>

<h3>Regulatory Reporting</h3>
<p>Savings account balances are reported on the Call Report Schedule RC-E as
nontransaction accounts. Interest paid on savings is reported to customers via
Form 1099-INT and impacts the bank's net interest margin calculation.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Account Balance</strong> &mdash; The current value held in the savings account</li>
<li><strong>FDIC Insurance Coverage</strong> &mdash; Deposit protection up to statutory limits</li>
<li><strong>Net Interest Margin (NIM)</strong> &mdash; Interest paid on savings is a component of interest expense</li>
</ul>
"""

OVERVIEWS["certificate-of-deposit"] = """
<h2>Certificate of Deposit (CD)</h2>
<p>A Certificate of Deposit is a time deposit product with a fixed term (typically
ranging from 3 months to 5 years) and a fixed or variable interest rate. CDs offer
higher yields than savings accounts in exchange for the customer's agreement to leave
funds on deposit for the specified term. Early withdrawal prior to maturity incurs a
penalty, typically calculated as a portion of the interest earned.</p>

<p>Meridian National Bank offers standard CDs, jumbo CDs (minimum $100,000), and
brokered CDs distributed through the bank's wealth management division. CD rates
are set by ALCO and are influenced by the prevailing federal funds rate, Treasury
yields, and competitive market conditions. CDs are a key component of Meridian's
stable funding base.</p>

<h3>Regulatory Reporting</h3>
<p>CDs are reported on Call Report Schedule RC-E as time deposits. CDs of $250,000
or more are reported separately on Schedule RC-E, Memoranda item 1. The maturity
distribution of CDs is critical for asset-liability management and liquidity
reporting under the Liquidity Coverage Ratio (LCR).</p>

<h3>Related Terms</h3>
<ul>
<li><strong>FDIC Insurance Coverage</strong> &mdash; CDs are insured up to $250,000 per depositor</li>
<li><strong>Net Interest Margin (NIM)</strong> &mdash; CD interest expense impacts NIM</li>
<li><strong>Liquidity Risk</strong> &mdash; CD maturity laddering is a tool for managing liquidity</li>
</ul>
"""

OVERVIEWS["money-market-account"] = """
<h2>Money Market Account</h2>
<p>A Money Market Account (MMA) is a higher-yield deposit account that combines
features of both savings and checking accounts. MMAs typically offer tiered interest
rates that increase with the account balance, along with limited check-writing
privileges and debit card access. They are designed for customers seeking higher
returns on liquid funds while maintaining some transactional flexibility.</p>

<p>At Meridian National Bank, Money Market Accounts are offered in two tiers:
<strong>MMA Select</strong> (minimum $2,500 opening deposit) and <strong>MMA
Premier</strong> (minimum $25,000 with higher APY tiers). MMA rates are set
competitively by ALCO, typically above standard savings but below CD rates for
equivalent term structures.</p>

<h3>Regulatory Treatment</h3>
<p>Money Market Accounts are classified as savings deposits (nontransaction
accounts) on Call Report Schedule RC-E. They should not be confused with Money
Market Funds (MMFs), which are investment products regulated by the SEC under
Rule 2a-7 and are not FDIC-insured.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Savings Account</strong> &mdash; Similar product with typically lower yields</li>
<li><strong>FDIC Insurance Coverage</strong> &mdash; MMAs are FDIC-insured deposit accounts</li>
<li><strong>Account Balance</strong> &mdash; MMA balances contribute to total deposit base</li>
</ul>
"""

OVERVIEWS["fdic-coverage"] = """
<h2>FDIC Insurance Coverage</h2>
<p>The Federal Deposit Insurance Corporation (FDIC) provides insurance coverage to
depositors of insured banks, protecting deposits up to <strong>$250,000 per depositor,
per insured bank, per ownership category</strong>. This coverage is automatic for all
deposit products at FDIC-insured institutions and is funded by premiums paid by
member banks, not by taxpayer funds.</p>

<p>Meridian National Bank is an FDIC-insured institution (Certificate Number assigned
at charter). All deposit products &mdash; checking, savings, money market accounts,
and certificates of deposit &mdash; are covered up to the standard maximum deposit
insurance amount (SMDIA). Coverage is calculated separately for each ownership
category, including single accounts, joint accounts, certain retirement accounts
(IRAs), revocable trust accounts, and business accounts.</p>

<h3>Deposit Insurance Implications</h3>
<p>Meridian's operations team monitors large depositor concentrations to ensure
customers understand their coverage limits. For customers with balances approaching
or exceeding FDIC limits, Meridian offers the IntraFi Network Deposits program
(formerly CDARS/ICS), which distributes deposits across multiple FDIC-insured
institutions to provide full coverage on larger balances.</p>

<h3>Regulatory Context</h3>
<p>FDIC insurance is governed by the Federal Deposit Insurance Act (12 USC 1811-1835a).
Meridian reports insured and uninsured deposit estimates on Call Report Schedule RC-O.
Assessment rates are determined by the FDIC based on the bank's risk profile and
capital levels.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Certificate of Deposit (CD)</strong> &mdash; A covered deposit product</li>
<li><strong>Checking Account</strong> &mdash; A covered deposit product</li>
<li><strong>Savings Account</strong> &mdash; A covered deposit product</li>
</ul>
"""

OVERVIEWS["dormant-account"] = """
<h2>Dormant Account</h2>
<p>A Dormant Account (also called an inactive account) is a bank account that has had
no customer-initiated activity &mdash; deposits, withdrawals, transfers, or other
transactions &mdash; for a specified period, typically 12 consecutive months at
Meridian National Bank. Dormancy status triggers special handling procedures to
protect both the customer and the bank.</p>

<p>When an account is classified as dormant, Meridian restricts certain activities
(such as ATM and debit card access) to prevent unauthorized use, and initiates
customer outreach to confirm the account holder's intent. If the account remains
inactive beyond the period specified by applicable state unclaimed property laws
(escheatment period), the bank is required to remit the funds to the state as
unclaimed property.</p>

<h3>Escheatment and Regulatory Requirements</h3>
<p>State unclaimed property laws vary but typically require escheatment after 3-5 years
of dormancy. Meridian's operations team tracks dormancy status in the
<em>bronze_accounts</em> table and runs quarterly escheatment reporting. The bank must
perform due diligence mailings (typically 60-90 days before escheatment) as required
by state law.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Account Balance</strong> &mdash; Dormant accounts may still carry a balance subject to escheatment</li>
<li><strong>Checking Account</strong> &mdash; A common account type subject to dormancy rules</li>
<li><strong>Savings Account</strong> &mdash; Also subject to dormancy classification</li>
</ul>
"""

OVERVIEWS["account-balance"] = """
<h2>Account Balance</h2>
<p>Account Balance represents the current monetary value held in a bank account at a
given point in time. Financial institutions track multiple balance types for each
account: the <strong>ledger balance</strong> (reflecting all posted transactions
including pending holds), the <strong>available balance</strong> (funds currently
available for withdrawal or use), and the <strong>collected balance</strong> (funds
from deposited items that have cleared). These distinctions are critical for
regulatory reporting, interest calculations, and customer-facing disclosures.</p>

<p>At Meridian National Bank, account balances are maintained in real-time by the ATLAS
core banking system and captured in the <em>bronze_accounts</em> table. The
<em>gold_account_summary</em> analytics table aggregates balances across all account
types to support enterprise-level reporting, liquidity management, and FDIC insurance
calculations. Monthly balance snapshots are preserved in <em>snapshot_monthly_balances</em>
for trend analysis and regulatory reporting.</p>

<h3>Data Quality Controls</h3>
<p>Account balances are subject to automated data quality validation to ensure
accuracy and consistency across systems. Balances are validated to ensure they are
non-negative for deposit accounts, as a negative deposit balance would indicate a
data integrity issue or an unprocessed overdraft. Records with negative balances
are flagged for immediate investigation by the operations team.</p>

<h3>Regulatory Context</h3>
<p>Account balances are reported on Call Report Schedule RC (Balance Sheet) and
Schedule RC-E (Deposit Liabilities). Accurate balance reporting is essential for
FDIC insurance assessments, reserve requirements, and liquidity coverage ratio
(LCR) calculations under Basel III.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Checking Account</strong> &mdash; A demand deposit account type with balance tracking</li>
<li><strong>Savings Account</strong> &mdash; An interest-bearing account with balance tracking</li>
<li><strong>Dormant Account</strong> &mdash; Dormancy is determined by activity against the balance</li>
<li><strong>FDIC Insurance Coverage</strong> &mdash; Balance levels determine insurance coverage</li>
</ul>
"""

# ==========================================================================
# LENDING & CREDIT
# ==========================================================================

OVERVIEWS["mortgage"] = """
<h2>Mortgage Loan</h2>
<p>A Mortgage Loan is a secured lending product where the borrower pledges residential
real property as collateral for the loan. Mortgages are typically the largest single
loan category for community and regional banks, representing a significant portion of
both the asset base and interest income. At Meridian National Bank, mortgage products
include fixed-rate (15-year and 30-year), adjustable-rate (5/1 and 7/1 ARM), and
jumbo mortgages for loan amounts exceeding conforming limits.</p>

<p>The mortgage underwriting process at Meridian evaluates the borrower's FICO score,
debt-to-income ratio (DTI), loan-to-value ratio (LTV), employment history, and
property appraisal. Loans are originated through both branch and digital channels and
processed through the ATLAS lending module. Qualifying mortgages may be sold to
Fannie Mae or Freddie Mac on the secondary market, with Meridian retaining servicing
rights.</p>

<h3>Regulatory Reporting</h3>
<p>Mortgage loans are reported on Call Report Schedule RC-C, Line 1 (Loans secured by
real estate). HMDA (Home Mortgage Disclosure Act) data is collected and reported
annually for fair lending analysis. Meridian also complies with TILA-RESPA Integrated
Disclosure (TRID) rules for mortgage disclosures.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>FICO Score</strong> &mdash; Primary credit score used in mortgage underwriting</li>
<li><strong>Loan-to-Value Ratio (LTV)</strong> &mdash; Key collateral metric for mortgage lending</li>
<li><strong>Debt-to-Income Ratio (DTI)</strong> &mdash; Measures the borrower's repayment capacity</li>
<li><strong>Delinquency</strong> &mdash; Tracks past-due status of mortgage payments</li>
</ul>
"""

OVERVIEWS["auto-loan"] = """
<h2>Auto Loan</h2>
<p>An Auto Loan is a secured installment loan used to finance the purchase of a motor
vehicle, with the vehicle itself serving as collateral. The loan is fully amortizing
over a fixed term, typically 36 to 72 months, with fixed monthly payments. Auto
lending is a significant consumer loan category for Meridian National Bank, offered
through both direct (branch/online) and indirect (dealer partnership) channels.</p>

<p>Meridian's auto loan underwriting considers the borrower's FICO score, DTI ratio,
the loan-to-value of the vehicle (based on NADA or Kelley Blue Book values), and
the vehicle age and mileage. New vehicle loans typically receive more favorable rates
than used vehicle loans due to lower depreciation risk. The bank's auto loan portfolio
is tracked in <em>bronze_loans</em> with loan type classification.</p>

<h3>Regulatory Context</h3>
<p>Auto loans are reported on Call Report Schedule RC-C, Line 6 (Other consumer loans).
Meridian complies with ECOA (Equal Credit Opportunity Act) and fair lending regulations
in auto lending, including monitoring for disparate impact in dealer markup pricing.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>FICO Score</strong> &mdash; Used in auto loan credit decisions</li>
<li><strong>Delinquency</strong> &mdash; Tracks payment status</li>
<li><strong>Charge-Off</strong> &mdash; Applied when auto loans become uncollectible</li>
</ul>
"""

OVERVIEWS["heloc"] = """
<h2>Home Equity Line of Credit (HELOC)</h2>
<p>A Home Equity Line of Credit is a revolving credit facility secured by the
borrower's residential real estate, specifically the equity in the property (market
value minus outstanding mortgage balance). HELOCs provide flexible access to funds
during a draw period (typically 10 years), followed by a repayment period (typically
10-20 years) during which the outstanding balance is amortized.</p>

<p>At Meridian National Bank, HELOCs are underwritten based on the combined
loan-to-value ratio (CLTV) of the first mortgage plus the HELOC line, the borrower's
FICO score, and DTI ratio. Interest rates are typically variable, indexed to the
prime rate plus a margin determined by the borrower's creditworthiness. The maximum
CLTV for Meridian HELOCs is 85%.</p>

<h3>Regulatory Context</h3>
<p>HELOCs are subject to TILA (Truth in Lending Act) requirements, including the
right to rescind within three business days of account opening. Periodic statements
must comply with Regulation Z disclosure requirements. HELOC balances are reported
on Call Report Schedule RC-C as revolving, open-end loans secured by 1-4 family
residential properties.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Mortgage Loan</strong> &mdash; The first lien that precedes the HELOC</li>
<li><strong>Loan-to-Value Ratio (LTV)</strong> &mdash; Combined LTV is key for HELOC underwriting</li>
<li><strong>FICO Score</strong> &mdash; Credit score used in underwriting decisions</li>
</ul>
"""

OVERVIEWS["commercial-loan"] = """
<h2>Commercial Loan (C&I)</h2>
<p>A Commercial and Industrial (C&I) loan is a loan made to a business entity for
working capital, equipment acquisition, inventory financing, or business expansion.
C&I loans may be structured as revolving lines of credit, term loans, or a combination,
and are typically secured by business assets (accounts receivable, inventory, equipment)
or guaranteed by the business owner.</p>

<p>Meridian National Bank's commercial lending team underwrites C&I loans based on
the business's financial statements, cash flow projections, industry risk, management
quality, and collateral coverage. Each commercial loan is assigned an internal risk
rating (Pass, Special Mention, Substandard, Doubtful, or Loss) that is reviewed at
least annually or when material changes occur. The commercial loan portfolio is
managed through the ATLAS lending module.</p>

<h3>Regulatory Reporting</h3>
<p>C&I loans are reported on Call Report Schedule RC-C, Line 4 (Commercial and
industrial loans). Concentration risk in C&I lending is monitored against regulatory
guidance (OCC Bulletin 2013-29) and internal concentration limits established by
Meridian's board of directors.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Risk Rating</strong> &mdash; Internal credit quality classification for commercial loans</li>
<li><strong>Delinquency</strong> &mdash; Payment status tracking for the commercial portfolio</li>
<li><strong>Provision for Credit Losses</strong> &mdash; Reserve estimation includes C&I loss expectations</li>
</ul>
"""

OVERVIEWS["fico-score"] = """
<h2>FICO Score</h2>
<p>A FICO Score is a credit score developed by the Fair Isaac Corporation, ranging from
<strong>300 to 850</strong>, that quantifies an individual's creditworthiness based on
their credit history. It is the primary credit scoring model used by US banks,
including Meridian National Bank, for consumer lending decisions across mortgages,
auto loans, HELOCs, personal loans, and credit cards. The score is derived from five
weighted factors: payment history (35%), amounts owed (30%), length of credit history
(15%), new credit (10%), and credit mix (10%).</p>

<p>At Meridian, FICO scores are captured at loan origination from one or more of the
three major credit bureaus (Equifax, Experian, TransUnion) and are refreshed quarterly
for the existing loan portfolio as part of ongoing credit monitoring. The score is a
critical input to the bank's credit risk models, pricing tiers, and regulatory
capital calculations under Basel III.</p>

<h3>Score Ranges</h3>
<ul>
<li><strong>Exceptional:</strong> 800&ndash;850 &mdash; Best rates and terms</li>
<li><strong>Very Good:</strong> 740&ndash;799 &mdash; Favorable pricing</li>
<li><strong>Good:</strong> 670&ndash;739 &mdash; Standard terms</li>
<li><strong>Fair:</strong> 580&ndash;669 &mdash; Higher rates, additional review</li>
<li><strong>Poor:</strong> 300&ndash;579 &mdash; May require collateral or co-signer</li>
</ul>

<h3>Data Quality Controls</h3>
<p>FICO scores are validated through automated data quality rules to ensure they
fall within the standard <strong>300 to 850</strong> range. Any record with a score
below 300 or above 850 is flagged as invalid, as these values fall outside the
defined scoring model. Flagged records are routed to the credit data stewardship
team for investigation, which may indicate a data entry error, system integration
issue, or corrupted bureau feed. This validation is critical because incorrect
FICO data could lead to inappropriate lending decisions, mispriced risk, or
inaccurate regulatory capital calculations.</p>

<h3>Regulatory Context</h3>
<p>Use of credit scores in lending is governed by the Fair Credit Reporting Act (FCRA),
Equal Credit Opportunity Act (ECOA), and Regulation B. Meridian provides adverse action
notices to applicants when a credit score materially impacts the lending decision, as
required under the Risk-Based Pricing Rule.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Mortgage Loan</strong> &mdash; FICO is a primary underwriting factor</li>
<li><strong>Debt-to-Income Ratio (DTI)</strong> &mdash; Evaluated alongside FICO in credit decisions</li>
<li><strong>Risk Rating</strong> &mdash; FICO influences the internal risk rating for consumer loans</li>
<li><strong>Credit Risk</strong> &mdash; FICO is a key measure of individual credit risk</li>
</ul>
"""

OVERVIEWS["ltv-ratio"] = """
<h2>Loan-to-Value Ratio (LTV)</h2>
<p>The Loan-to-Value Ratio is a financial metric expressing the ratio of a loan amount
to the appraised value of the underlying collateral, most commonly real property. It
is calculated as: <strong>LTV = Loan Amount / Appraised Property Value</strong>. LTV
is one of the most critical underwriting metrics in mortgage and real estate lending,
as it directly measures the degree of collateral coverage protecting the lender.</p>

<p>At Meridian National Bank, LTV requirements vary by product type. Conventional
mortgages typically require an LTV of 80% or less to avoid private mortgage insurance
(PMI). HELOCs use a combined LTV (CLTV) calculation that includes both the first
mortgage and the HELOC line. Commercial real estate loans generally require LTVs
at or below regulatory guidelines established by the OCC and other banking agencies.</p>

<h3>Regulatory Guidelines</h3>
<p>Federal banking regulators (OCC, FDIC, Fed) have established supervisory LTV limits
in the Interagency Guidelines for Real Estate Lending (12 CFR 34, Appendix A):
raw land (65%), land development (75%), commercial construction (80%), improved
property (85%), and 1-4 family residential (no supervisory limit but monitored).
Loans exceeding these limits are counted against the bank's exception-to-policy
concentration.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Mortgage Loan</strong> &mdash; LTV is a primary underwriting metric for mortgages</li>
<li><strong>Home Equity Line of Credit (HELOC)</strong> &mdash; Combined LTV applies</li>
<li><strong>FICO Score</strong> &mdash; Evaluated together with LTV in lending decisions</li>
</ul>
"""

OVERVIEWS["dti-ratio"] = """
<h2>Debt-to-Income Ratio (DTI)</h2>
<p>The Debt-to-Income Ratio is a financial metric representing the percentage of a
borrower's gross monthly income that is consumed by monthly debt payments. It is
calculated as: <strong>DTI = Total Monthly Debt Payments / Gross Monthly Income</strong>.
DTI is a key measure of a borrower's ability to manage monthly payments and repay debts,
and it is used extensively in consumer lending decisions.</p>

<p>Meridian National Bank evaluates two types of DTI in mortgage underwriting:
<strong>front-end DTI</strong> (housing expenses only, including PITI &mdash; principal,
interest, taxes, and insurance) and <strong>back-end DTI</strong> (all monthly debt
obligations including housing, auto loans, student loans, credit card minimums, and
other installment debt). The Qualified Mortgage (QM) rule under CFPB regulations
requires that back-end DTI not exceed 43% for QM designation.</p>

<h3>DTI Limits at Meridian</h3>
<ul>
<li><strong>Conventional mortgage:</strong> Front-end 28% / Back-end 36% (standard); up to 43% with compensating factors</li>
<li><strong>Auto loan:</strong> Back-end DTI generally under 50%</li>
<li><strong>HELOC:</strong> Combined DTI evaluated with existing mortgage obligation</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>FICO Score</strong> &mdash; Evaluated alongside DTI in credit decisions</li>
<li><strong>Loan-to-Value Ratio (LTV)</strong> &mdash; Complementary underwriting metric</li>
<li><strong>Mortgage Loan</strong> &mdash; DTI is a key factor in mortgage qualification</li>
</ul>
"""

OVERVIEWS["delinquency"] = """
<h2>Delinquency</h2>
<p>Delinquency refers to the status of a loan where the borrower has failed to make
one or more scheduled payments by the due date. Delinquency is categorized by the
number of days past due: <strong>30 days</strong> (early-stage), <strong>60 days</strong>,
<strong>90 days</strong> (serious delinquency), and <strong>120+ days</strong>
(severe/pre-charge-off). Each stage triggers escalating collection activities,
reporting obligations, and reserve adjustments.</p>

<p>At Meridian National Bank, delinquency tracking begins on the day after a payment
due date is missed. The ATLAS core banking system automatically moves loans through
delinquency buckets and triggers notifications to the collections team, relationship
managers, and credit risk officers. Delinquency status is a key input to the
allowance for credit losses (ACL) calculation under CECL methodology and directly
impacts the bank's asset quality ratios reported to regulators.</p>

<h3>Delinquency Management</h3>
<p>Meridian's early intervention program contacts borrowers within 15 days of a missed
payment. At 90 days past due, loans are placed on nonaccrual status (interest income
is no longer recognized). The <em>gold_delinquency_analysis</em> table provides
portfolio-level delinquency trends by product type, vintage, and geography for
management and board reporting.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Risk Rating</strong> &mdash; Delinquency status influences internal risk ratings</li>
<li><strong>Charge-Off</strong> &mdash; Severely delinquent loans may be charged off</li>
<li><strong>Provision for Credit Losses</strong> &mdash; Delinquency levels drive provision expense</li>
<li><strong>Allowance for Credit Losses (ACL)</strong> &mdash; Reserve calculation incorporates delinquency data</li>
</ul>
"""

OVERVIEWS["risk-rating"] = """
<h2>Risk Rating</h2>
<p>A Risk Rating is an internal credit quality classification assigned to each loan in
the bank's portfolio. The rating system follows the regulatory framework established
by the OCC and other federal banking agencies, using five categories:
<strong>Pass</strong> (acceptable quality), <strong>Special Mention</strong> (potential
weakness), <strong>Substandard</strong> (well-defined weakness), <strong>Doubtful</strong>
(full collection is improbable), and <strong>Loss</strong> (uncollectible). Risk
ratings are required for regulatory reporting and are a key input to the bank's
credit risk management framework.</p>

<p>At Meridian National Bank, all commercial loans are individually risk-rated at
origination and reviewed at least annually. Consumer loans are pool-rated based on
product type and delinquency status. Risk rating changes trigger notifications to
credit officers and may require action such as increased monitoring, collateral
re-evaluation, or loan restructuring. The risk rating distribution is a standing
agenda item for Meridian's Loan Committee and Board Risk Committee.</p>

<h3>Regulatory Context</h3>
<p>Risk ratings must comply with the Uniform Financial Institutions Rating System
and the OCC's Rating Credit Risk handbook (OCC 2001-37). Adversely classified assets
(Substandard, Doubtful, Loss) are reported on Call Report Schedule RC-N and examined
closely during regulatory examinations.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Delinquency</strong> &mdash; Payment status is a factor in risk rating assignment</li>
<li><strong>Charge-Off</strong> &mdash; Loans rated Loss are fully charged off</li>
<li><strong>Provision for Credit Losses</strong> &mdash; Risk ratings drive reserve levels</li>
<li><strong>Commercial Loan (C&I)</strong> &mdash; Individually rated loan type</li>
</ul>
"""

OVERVIEWS["charge-off"] = """
<h2>Charge-Off</h2>
<p>A Charge-Off is the accounting action of writing off a loan balance as uncollectible
when the bank determines that the borrower is unlikely to repay the obligation. For
consumer loans, regulatory guidance (FFIEC Uniform Retail Credit Classification Policy)
requires charge-off at specific delinquency thresholds: closed-end loans at 120 days
past due and open-end (credit card) loans at 180 days past due. Commercial loan
charge-offs are based on the individual credit review and loss confirmation.</p>

<p>At Meridian National Bank, charge-offs are recorded as a reduction in the gross
loan portfolio and a corresponding reduction in the allowance for credit losses (ACL).
Net charge-offs (gross charge-offs minus recoveries) are a key asset quality metric
tracked monthly by the Credit Risk department and reported quarterly on Call Report
Schedule RI-B. Charge-off rates by product segment are compared against peer
benchmarks and internal targets.</p>

<h3>Post-Charge-Off Recovery</h3>
<p>Even after a loan is charged off, Meridian continues collection efforts through
internal recovery specialists and third-party collection agencies. Recovered amounts
are credited back against net charge-offs, improving the bank's net loss experience.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Delinquency</strong> &mdash; Charge-off typically follows sustained delinquency</li>
<li><strong>Allowance for Credit Losses (ACL)</strong> &mdash; Charge-offs reduce the ACL balance</li>
<li><strong>Provision for Credit Losses</strong> &mdash; Provisions replenish the ACL after charge-offs</li>
<li><strong>Risk Rating</strong> &mdash; Loans rated Loss are candidates for charge-off</li>
</ul>
"""

# ==========================================================================
# CARDS & PAYMENTS
# ==========================================================================

OVERVIEWS["credit-card"] = """
<h2>Credit Card</h2>
<p>A Credit Card is a revolving credit product issued under the Visa or Mastercard
network that allows the cardholder to make purchases and cash advances up to an
approved credit limit. Unlike installment loans, credit cards have no fixed repayment
schedule &mdash; cardholders may pay the full balance, a minimum payment, or any
amount in between. Outstanding balances accrue interest at the applicable Annual
Percentage Rate (APR).</p>

<p>Meridian National Bank issues credit cards across multiple tiers: <strong>Essential
Card</strong> (no annual fee, standard rewards), <strong>Preferred Rewards Card</strong>
(tiered cash-back rewards), and <strong>Premier Card</strong> (premium travel rewards,
concierge service). Credit card underwriting uses FICO scores, income verification,
and existing credit utilization to determine approval, credit limit, and pricing tier.</p>

<h3>Revenue Components</h3>
<p>Credit card revenue at Meridian comes from three primary sources: <strong>interest
income</strong> on revolving balances, <strong>interchange fees</strong> earned on each
purchase transaction, and <strong>annual/service fees</strong>. Credit card interest
income is reported on Call Report Schedule RI as interest on credit card loans.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Annual Percentage Rate (APR)</strong> &mdash; The interest rate charged on balances</li>
<li><strong>Interchange Fee</strong> &mdash; Revenue earned on each transaction</li>
<li><strong>Chargeback</strong> &mdash; Forced transaction reversals</li>
<li><strong>FICO Score</strong> &mdash; Used in credit card underwriting</li>
</ul>
"""

OVERVIEWS["apr"] = """
<h2>Annual Percentage Rate (APR)</h2>
<p>The Annual Percentage Rate is the annualized cost of credit expressed as a percentage,
representing the interest rate charged on outstanding credit card and loan balances.
For credit cards, the APR may include a variable base rate (typically the US Prime Rate)
plus a margin determined by the cardholder's creditworthiness. Different APRs may apply
to purchases, balance transfers, cash advances, and penalty situations.</p>

<p>At Meridian National Bank, credit card APRs are set based on the customer's credit
profile at the time of application and are disclosed in the Schumer Box as required
by TILA. The current APR range for Meridian credit cards is Prime + 8.99% to
Prime + 21.99%. A penalty APR of up to 29.99% may be applied after 60+ days of
delinquency, as permitted under the CARD Act.</p>

<h3>Regulatory Context</h3>
<p>APR disclosures are governed by the Truth in Lending Act (TILA) and Regulation Z.
The CARD Act of 2009 restricts rate increases on existing balances, requires 45-day
advance notice of APR changes, and prohibits retroactive rate increases on existing
balances (with limited exceptions).</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Credit Card</strong> &mdash; The product subject to APR charges</li>
<li><strong>Net Interest Margin (NIM)</strong> &mdash; Credit card interest income contributes to NIM</li>
</ul>
"""

OVERVIEWS["interchange-fee"] = """
<h2>Interchange Fee</h2>
<p>An Interchange Fee is the fee paid by the merchant's acquiring bank to the
card-issuing bank (Meridian National Bank) each time a cardholder makes a purchase
using a credit or debit card. Interchange fees are set by the card networks (Visa,
Mastercard) and vary based on the merchant's industry, transaction type (card-present
vs. card-not-present), and card product tier. Interchange is a significant source of
noninterest income for banks with large card portfolios.</p>

<p>For debit card transactions, interchange fees are regulated under the Durbin
Amendment (Section 1075 of the Dodd-Frank Act), which caps debit interchange for
banks with over $10 billion in assets. As a community/regional bank, Meridian is
currently exempt from Durbin Amendment interchange caps, allowing the bank to earn
market-rate interchange on debit card transactions.</p>

<h3>Interchange at Meridian</h3>
<p>Interchange revenue is tracked in the <em>bronze_card_transactions</em> table and
reported as noninterest income on Call Report Schedule RI. The <em>gold_fee_revenue</em>
analytics table aggregates interchange revenue by card type, merchant category, and
transaction channel.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Credit Card</strong> &mdash; The product generating interchange revenue</li>
<li><strong>Chargeback</strong> &mdash; Chargebacks may result in reversal of interchange</li>
</ul>
"""

OVERVIEWS["chargeback"] = """
<h2>Chargeback</h2>
<p>A Chargeback is a forced reversal of a credit or debit card transaction, initiated
by the cardholder's issuing bank when the cardholder disputes a charge. Chargebacks
may arise from unauthorized transactions (fraud), merchant service failures (goods
not received, not as described), processing errors (duplicate charges, incorrect
amounts), or billing disputes. The chargeback process is governed by card network
rules (Visa Claims Resolution, Mastercard Chargeback Guide).</p>

<p>At Meridian National Bank, chargebacks are managed by the Card Disputes team within
Card Operations. When a cardholder disputes a transaction, Meridian issues a
provisional credit to the cardholder and initiates the dispute process with the
acquiring bank. The <em>bronze_card_transactions</em> table tracks chargeback status,
and the <em>gold_fraud_analytics</em> table identifies patterns that may indicate
organized fraud rings or merchant compromise.</p>

<h3>Regulatory Context</h3>
<p>Chargeback rights for consumers are protected under Regulation E (debit cards) and
Regulation Z (credit cards). Under Reg Z, cardholders are limited to $50 in liability
for unauthorized credit card use (most banks, including Meridian, offer $0 liability
as a competitive benefit).</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Credit Card</strong> &mdash; The product subject to chargebacks</li>
<li><strong>Interchange Fee</strong> &mdash; May be reversed upon chargeback</li>
</ul>
"""

OVERVIEWS["ach"] = """
<h2>ACH Transfer</h2>
<p>An ACH (Automated Clearing House) Transfer is an electronic funds transfer processed
through the ACH network, a nationwide batch-processing system operated by the Federal
Reserve (FedACH) and The Clearing House (EPN). ACH is the backbone of electronic
payments in the United States, handling direct deposits (payroll, Social Security),
bill payments, person-to-person (P2P) transfers, and business-to-business payments.
The ACH network is governed by NACHA (National Automated Clearing House Association)
Operating Rules.</p>

<p>Meridian National Bank acts as both an Originating Depository Financial Institution
(ODFI) and a Receiving Depository Financial Institution (RDFI) in the ACH network.
The bank processes ACH transactions through the ATLAS core system, with same-day
ACH capabilities for eligible transactions. ACH volumes and values are tracked in
<em>bronze_ach_transfers</em> and aggregated in analytics tables for operational
and compliance monitoring.</p>

<h3>Regulatory Context</h3>
<p>ACH transactions exceeding $10,000 (cash equivalent) may trigger BSA/AML monitoring
obligations. Meridian's transaction monitoring system screens ACH activity against OFAC
sanctions lists and internal suspicious activity thresholds.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Wire Transfer</strong> &mdash; An alternative electronic payment method for same-day settlement</li>
<li><strong>Currency Transaction Report (CTR)</strong> &mdash; May be required for large cash-related ACH activity</li>
<li><strong>OFAC Screening</strong> &mdash; All ACH transactions are screened against sanctions lists</li>
</ul>
"""

OVERVIEWS["wire-transfer"] = """
<h2>Wire Transfer</h2>
<p>A Wire Transfer is a same-day electronic funds transfer between financial institutions,
processed through either the Fedwire Funds Service (domestic, operated by the Federal
Reserve) or the SWIFT network (international, Society for Worldwide Interbank Financial
Telecommunication). Wire transfers provide immediate, irrevocable settlement and are
used for large-value, time-sensitive payments including real estate closings, investment
transactions, and international trade settlements.</p>

<p>At Meridian National Bank, wire transfers are initiated through branches, the
commercial banking portal, or the treasury management platform. All wire transfers
undergo real-time OFAC sanctions screening before release. International wires require
additional compliance review, including validation of the beneficiary's country against
sanctioned jurisdictions and travel rule information for transfers exceeding $3,000.</p>

<h3>BSA/AML Monitoring</h3>
<p>Wire transfers are among the highest-risk transaction types for money laundering
and are subject to intensive BSA/AML monitoring. Meridian's transaction monitoring
system applies enhanced rules to wire activity, including same-day aggregate monitoring,
geographic risk scoring, and pattern detection for structuring. Wire transfer data is
maintained in <em>bronze_wire_transfers</em>.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>ACH Transfer</strong> &mdash; Lower-cost alternative for non-urgent payments</li>
<li><strong>Currency Transaction Report (CTR)</strong> &mdash; Required for cash-funded wires over $10,000</li>
<li><strong>OFAC Screening</strong> &mdash; Mandatory for all wire transfers</li>
<li><strong>Suspicious Activity Report (SAR)</strong> &mdash; Filed when wire patterns suggest illicit activity</li>
</ul>
"""

OVERVIEWS["ctr"] = """
<h2>Currency Transaction Report (CTR)</h2>
<p>A Currency Transaction Report is a regulatory filing required by the Bank Secrecy Act
(BSA), submitted to the Financial Crimes Enforcement Network (FinCEN) on Form 112 for
any cash transaction (or series of related cash transactions) exceeding <strong>$10,000
in a single business day</strong>. CTRs capture both deposits and withdrawals of
physical currency and are a cornerstone of the US anti-money laundering framework.</p>

<p>Meridian National Bank files CTRs electronically through the BSA E-Filing System.
The ATLAS core banking system automatically aggregates cash transactions by customer
across all branches and channels within a business day. When the aggregate exceeds
$10,000, the system generates a CTR pre-filing alert for the BSA team to review and
submit. CTRs must be filed within 15 calendar days of the transaction date.</p>

<h3>Regulatory Context</h3>
<p>CTR requirements are codified at 31 CFR 1010.311. Failure to file CTRs can result
in civil money penalties up to $100,000 per violation. Structuring &mdash; the act of
breaking transactions into smaller amounts to evade CTR filing &mdash; is a federal
crime (31 USC 5324). Meridian's monitoring system includes specific structuring
detection rules.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Bank Secrecy Act (BSA)</strong> &mdash; The legislative foundation for CTR requirements</li>
<li><strong>Suspicious Activity Report (SAR)</strong> &mdash; Filed when structuring or other suspicious cash patterns are detected</li>
<li><strong>Wire Transfer</strong> &mdash; Cash-funded wires count toward CTR aggregation</li>
<li><strong>OFAC Screening</strong> &mdash; Cash transactions are screened alongside CTR filing</li>
</ul>
"""

# ==========================================================================
# WEALTH & INVESTMENTS
# ==========================================================================

OVERVIEWS["aum"] = """
<h2>Assets Under Management (AUM)</h2>
<p>Assets Under Management represents the total market value of all investment assets
that Meridian National Bank's FORTUNA Wealth Management division manages on behalf
of its clients. AUM is the primary revenue driver for the advisory business, as
management fees are typically calculated as a percentage of AUM. AUM fluctuates based
on market performance, net client flows (new assets minus withdrawals), and investment
returns.</p>

<p>AUM at Meridian is tracked at multiple levels: individual account, household,
financial advisor book, branch, and enterprise. The <em>gold_portfolio_performance</em>
and <em>gold_client_revenue</em> analytics tables aggregate AUM data for management
reporting, advisor compensation, and regulatory filings. Changes in AUM are decomposed
into market effect, net flows, and fee deductions for performance attribution.</p>

<h3>Revenue Impact</h3>
<p>Advisory fees are typically charged at 50-150 basis points (bps) of AUM annually,
billed quarterly in arrears. A 1% change in AUM directly impacts fee revenue by a
corresponding amount. Meridian's <em>gold_fee_revenue</em> table tracks fee income
by product type and fee tier.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Advisory Fee</strong> &mdash; Fees calculated as a percentage of AUM</li>
<li><strong>Investment Portfolio</strong> &mdash; Individual portfolios that comprise total AUM</li>
<li><strong>Financial Advisor</strong> &mdash; Advisors manage and grow AUM for their clients</li>
<li><strong>Benchmark Index</strong> &mdash; AUM performance is measured against benchmarks</li>
</ul>
"""

OVERVIEWS["portfolio"] = """
<h2>Investment Portfolio</h2>
<p>An Investment Portfolio is a collection of financial assets (equities, fixed income
securities, mutual funds, ETFs, alternative investments, and cash equivalents) managed
under a single account and aligned to a client's investment objective, risk tolerance,
and time horizon. Each portfolio is constructed according to a target asset allocation
model selected based on the client's Investment Policy Statement (IPS).</p>

<p>In Meridian National Bank's FORTUNA Wealth Management division, portfolios are
established during the client onboarding process and are managed on a discretionary
or non-discretionary basis depending on the advisory agreement. Portfolio data is
maintained in <em>bronze_portfolios</em> and <em>bronze_holdings</em>, with
performance metrics calculated in <em>gold_portfolio_performance</em>.</p>

<h3>Portfolio Management Process</h3>
<p>Meridian's Investment Committee sets model portfolios and approved security lists.
Financial advisors implement these models for individual clients with customizations
based on tax considerations, concentration limits, and client preferences. Portfolios
are rebalanced quarterly or when drift exceeds threshold bands (typically +/- 5% from
target allocation).</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Asset Allocation</strong> &mdash; The strategic distribution of portfolio assets</li>
<li><strong>Benchmark Index</strong> &mdash; Used to evaluate portfolio performance</li>
<li><strong>Assets Under Management (AUM)</strong> &mdash; Total value of all managed portfolios</li>
<li><strong>Financial Advisor</strong> &mdash; Manages the portfolio on behalf of the client</li>
</ul>
"""

OVERVIEWS["asset-allocation"] = """
<h2>Asset Allocation</h2>
<p>Asset Allocation is the strategic distribution of investment portfolio assets across
major asset classes &mdash; equities, fixed income, alternatives (real estate, hedge
funds, private equity), and cash equivalents &mdash; to optimize the risk-return
profile based on the client's investment objectives, risk tolerance, and time horizon.
Asset allocation is widely regarded as the primary driver of long-term portfolio
performance, accounting for approximately 90% of return variability according to
academic research.</p>

<p>At Meridian National Bank's FORTUNA Wealth Management division, asset allocation
models are designed by the Chief Investment Officer and Investment Committee. Five
standard models are offered: Conservative, Moderately Conservative, Moderate,
Moderately Aggressive, and Aggressive, each with defined target allocations and
rebalancing bands. Custom allocations are available for Private Banking clients.</p>

<h3>Rebalancing</h3>
<p>The <em>gold_asset_allocation</em> analytics table monitors actual vs. target
allocations across all client portfolios. When allocation drift exceeds +/- 5% in
any asset class, automated alerts trigger rebalancing activity. Tax-loss harvesting
opportunities are evaluated as part of the rebalancing process.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Investment Portfolio</strong> &mdash; The portfolio being allocated</li>
<li><strong>Benchmark Index</strong> &mdash; Each asset class has a corresponding benchmark</li>
<li><strong>Sharpe Ratio</strong> &mdash; Measures risk-adjusted performance of the allocation</li>
</ul>
"""

OVERVIEWS["benchmark"] = """
<h2>Benchmark Index</h2>
<p>A Benchmark Index is a market index used as a standard of comparison for evaluating
the performance of an investment portfolio. By comparing portfolio returns to an
appropriate benchmark, advisors and clients can assess whether active management is
adding value (generating positive alpha) or underperforming passive alternatives.
Common benchmarks include the S&P 500 (US large-cap equities), Bloomberg US Aggregate
Bond Index (US investment-grade fixed income), and MSCI EAFE (international developed
markets).</p>

<p>Meridian National Bank's FORTUNA Wealth Management division assigns a blended
benchmark to each portfolio based on its target asset allocation. For example, a
moderate portfolio with 60% equity / 40% fixed income would be benchmarked against
60% S&P 500 + 40% Bloomberg US Aggregate. Benchmark data is maintained in
<em>bronze_benchmarks</em> and performance comparisons are calculated in
<em>gold_portfolio_performance</em>.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Alpha</strong> &mdash; The excess return above the benchmark</li>
<li><strong>Sharpe Ratio</strong> &mdash; Risk-adjusted performance relative to the risk-free rate</li>
<li><strong>Investment Portfolio</strong> &mdash; The portfolio being evaluated against the benchmark</li>
<li><strong>Asset Allocation</strong> &mdash; Determines the appropriate benchmark blend</li>
</ul>
"""

OVERVIEWS["alpha"] = """
<h2>Alpha</h2>
<p>Alpha is a financial metric representing the excess return of an investment portfolio
relative to its designated benchmark index. A positive alpha indicates that the portfolio
manager (or financial advisor) has generated returns above what the benchmark delivered,
after adjusting for market movements. Alpha is one of the most important measures of
active management skill and is a key component of performance reporting to wealth
management clients.</p>

<p>At Meridian National Bank, alpha is calculated monthly and reported quarterly to
clients as part of the portfolio performance report. Advisor-level alpha is also
tracked in the <em>gold_advisor_scorecard</em> table, where it influences advisor
performance evaluations and compensation. Consistent positive alpha supports the
value proposition for Meridian's advisory fees.</p>

<h3>Alpha Calculation</h3>
<p>Alpha = Portfolio Return - Benchmark Return (simple alpha) or the intercept of a
regression of portfolio excess returns on benchmark excess returns (Jensen's alpha).
Meridian uses time-weighted returns (GIPS-compliant) for alpha calculations.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Benchmark Index</strong> &mdash; The reference point for calculating alpha</li>
<li><strong>Sharpe Ratio</strong> &mdash; Another risk-adjusted performance metric</li>
<li><strong>Financial Advisor</strong> &mdash; The advisor responsible for generating alpha</li>
<li><strong>Advisory Fee</strong> &mdash; Fees justified by positive alpha generation</li>
</ul>
"""

OVERVIEWS["sharpe-ratio"] = """
<h2>Sharpe Ratio</h2>
<p>The Sharpe Ratio is a risk-adjusted return metric that measures how much excess
return (above the risk-free rate) a portfolio generates per unit of total risk
(standard deviation). It is calculated as: <strong>Sharpe Ratio = (Portfolio Return -
Risk-Free Rate) / Portfolio Standard Deviation</strong>. A higher Sharpe Ratio
indicates better risk-adjusted performance, meaning the portfolio is being compensated
more effectively for the risk taken.</p>

<p>At Meridian National Bank, the Sharpe Ratio is calculated quarterly for all
managed portfolios using the 90-day Treasury bill rate as the risk-free proxy.
The metric is reported to clients in performance reviews and used internally by the
Investment Committee to evaluate model portfolio efficiency. Advisors whose client
portfolios consistently achieve below-median Sharpe Ratios are flagged for additional
review and coaching.</p>

<h3>Interpretation</h3>
<ul>
<li><strong>&gt; 1.0:</strong> Good &mdash; portfolio is well-compensated for risk</li>
<li><strong>&gt; 2.0:</strong> Very good &mdash; strong risk-adjusted performance</li>
<li><strong>&gt; 3.0:</strong> Excellent &mdash; exceptional risk management and returns</li>
<li><strong>&lt; 1.0:</strong> Subpar &mdash; risk not adequately compensated</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>Alpha</strong> &mdash; Another measure of investment performance</li>
<li><strong>Benchmark Index</strong> &mdash; Sharpe Ratios are compared across portfolios and benchmarks</li>
<li><strong>Investment Portfolio</strong> &mdash; The portfolio being measured</li>
</ul>
"""

OVERVIEWS["financial-advisor"] = """
<h2>Financial Advisor</h2>
<p>A Financial Advisor is a FINRA-registered representative (Series 7, Series 66 or
equivalent) who provides personalized investment advice, financial planning, and
portfolio management services to clients. Advisors at Meridian National Bank's FORTUNA
Wealth Management division serve as the primary relationship manager for wealth clients,
responsible for understanding client goals, recommending investment strategies, and
executing portfolio changes in alignment with the client's Investment Policy Statement.</p>

<p>Meridian's financial advisors operate under either a suitability standard (for
brokerage accounts) or a fiduciary standard (for advisory/managed accounts), depending
on the account type and applicable regulations. Advisor performance is tracked in the
<em>gold_advisor_scorecard</em> analytics table, measuring AUM growth, client
retention, revenue generation, alpha delivery, and compliance record.</p>

<h3>Regulatory Context</h3>
<p>Financial advisors are subject to FINRA supervision, SEC Regulation Best Interest
(Reg BI) for brokerage recommendations, and the Investment Advisers Act of 1940 for
advisory accounts. Meridian's compliance team monitors advisor activity for suitability,
excessive trading (churning), and unauthorized transactions.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Fiduciary Duty</strong> &mdash; The legal standard for advisory accounts</li>
<li><strong>Advisory Fee</strong> &mdash; Revenue generated by advisor relationships</li>
<li><strong>Assets Under Management (AUM)</strong> &mdash; The assets managed by the advisor</li>
<li><strong>Accredited Investor</strong> &mdash; Client qualification for certain investment products</li>
</ul>
"""

OVERVIEWS["advisory-fee"] = """
<h2>Advisory Fee</h2>
<p>An Advisory Fee is the fee charged by Meridian National Bank's FORTUNA Wealth
Management division for investment advisory services, including portfolio management,
financial planning, and ongoing investment monitoring. Advisory fees are typically
expressed in basis points (bps) of Assets Under Management (AUM) and billed quarterly
in arrears based on the average daily or quarter-end account value.</p>

<p>Meridian's fee schedule is tiered by AUM level: larger accounts receive lower fee
rates, reflecting economies of scale. The standard fee schedule ranges from 100 bps
(1.0%) on the first $500,000 to 50 bps (0.5%) on amounts above $5 million. Fee
schedules are maintained in <em>bronze_fee_schedules</em> and revenue tracking is
aggregated in <em>gold_fee_revenue</em>.</p>

<h3>Regulatory Context</h3>
<p>Advisory fee disclosures are required under the Investment Advisers Act of 1940
and are documented in Form ADV Part 2A (the firm brochure). Fees must be reasonable
and clearly disclosed to clients. The SEC examines advisory fees as part of its
assessment of the firm's fiduciary obligations.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Assets Under Management (AUM)</strong> &mdash; The base for fee calculation</li>
<li><strong>Financial Advisor</strong> &mdash; The advisor whose services are compensated</li>
<li><strong>Fiduciary Duty</strong> &mdash; Fee reasonableness is a fiduciary obligation</li>
</ul>
"""

OVERVIEWS["fiduciary-duty"] = """
<h2>Fiduciary Duty</h2>
<p>Fiduciary Duty is the legal obligation of an investment advisor to act in the best
interest of the client, placing the client's interests ahead of the advisor's own or
the firm's interests. This duty, established under the Investment Advisers Act of 1940,
encompasses two core components: the duty of care (providing advice that is in the
client's best interest based on thorough analysis) and the duty of loyalty (disclosing
and managing conflicts of interest).</p>

<p>At Meridian National Bank, fiduciary duty applies to all advisory (managed) accounts
in the FORTUNA Wealth Management division. Advisors must document the rationale for
investment recommendations, ensure suitability for the client's stated objectives and
risk tolerance, and disclose all material conflicts of interest including compensation
arrangements, proprietary products, and revenue-sharing agreements.</p>

<h3>Regulatory Context</h3>
<p>The fiduciary standard is distinct from the suitability standard (which applies to
brokerage accounts under FINRA rules) and the enhanced standard under SEC Regulation
Best Interest (Reg BI). Meridian maintains compliance monitoring programs to ensure
adherence to the applicable standard for each account type.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Financial Advisor</strong> &mdash; The individual bound by fiduciary duty</li>
<li><strong>Advisory Fee</strong> &mdash; Must be reasonable under fiduciary standards</li>
<li><strong>Accredited Investor</strong> &mdash; Fiduciary duty applies regardless of investor sophistication</li>
</ul>
"""

OVERVIEWS["accredited-investor"] = """
<h2>Accredited Investor</h2>
<p>An Accredited Investor is an individual or entity that meets specific financial
thresholds established by the Securities and Exchange Commission (SEC), qualifying
them to invest in securities offerings that are exempt from SEC registration, such
as private placements, hedge funds, private equity funds, and venture capital funds.
These investments carry higher risk and complexity, and the SEC's accredited investor
framework presumes that individuals meeting the financial thresholds possess the
sophistication to evaluate such risks.</p>

<p>At Meridian National Bank, accredited investor status is verified for wealth
management clients seeking access to alternative investments and private offerings.
The verification process is documented in the client's profile and reviewed annually.
FORTUNA advisors may only recommend non-registered securities to clients who meet
the accredited investor definition.</p>

<h3>Qualification Thresholds (SEC Rule 501)</h3>
<ul>
<li><strong>Income test:</strong> $200,000 individual income (or $300,000 joint) in each of the last two years with expectation of the same</li>
<li><strong>Net worth test:</strong> $1 million in net worth (excluding primary residence), individually or jointly</li>
<li><strong>Professional certifications:</strong> Holders of Series 7, Series 65, or Series 82 licenses</li>
<li><strong>Entity test:</strong> Entities with $5 million in assets, or entities owned entirely by accredited investors</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>Financial Advisor</strong> &mdash; Verifies accredited investor status</li>
<li><strong>Fiduciary Duty</strong> &mdash; Applies to recommendations of alternative investments</li>
<li><strong>Investment Portfolio</strong> &mdash; Alternative investments may be included in eligible portfolios</li>
</ul>
"""

# ==========================================================================
# TRADING & SECURITIES
# ==========================================================================

OVERVIEWS["cusip"] = """
<h2>CUSIP</h2>
<p>CUSIP (Committee on Uniform Securities Identification Procedures) is a standardized
<strong>9-character alphanumeric code</strong> that uniquely identifies a financial
security in North America. The first six characters identify the issuer, the next two
identify the specific issue (e.g., common stock, preferred stock, specific bond series),
and the ninth character is a check digit calculated using a modulus-10 algorithm. CUSIPs
are assigned and maintained by CUSIP Global Services, a joint venture of the American
Bankers Association and S&P Global Market Intelligence.</p>

<p>At Meridian National Bank, CUSIPs are the primary security identifier used in the
FORTUNA Wealth Management and trading systems. The <em>ref_cusip_master</em> reference
table maintains a comprehensive mapping of CUSIPs to security names, types, and
attributes. CUSIPs are used for trade execution, settlement, position keeping,
regulatory reporting, and client portfolio statements.</p>

<h3>Data Quality Controls</h3>
<p>CUSIP identifiers are validated through automated data quality rules to ensure
they conform to the standard <strong>9-character alphanumeric format</strong>. Any
security record with a CUSIP that does not match the expected pattern (exactly 9
characters, each being an uppercase letter A-Z or digit 0-9) is flagged for
investigation. Invalid CUSIPs can cause trade settlement failures, incorrect
position reporting, and regulatory filing errors.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>ISIN</strong> &mdash; The international equivalent; a CUSIP is embedded within the ISIN</li>
<li><strong>Ticker Symbol</strong> &mdash; The exchange trading identifier (distinct from CUSIP)</li>
<li><strong>Trade Settlement</strong> &mdash; CUSIPs are used to identify securities in settlement</li>
</ul>
"""

OVERVIEWS["isin"] = """
<h2>ISIN</h2>
<p>An International Securities Identification Number (ISIN) is a <strong>12-character
alphanumeric code</strong> that uniquely identifies a financial security globally. The
ISIN format consists of a 2-letter ISO 3166-1 country code, followed by a 9-character
national security identifier (which is the CUSIP for US and Canadian securities), and
a single check digit calculated using the Luhn algorithm. ISINs are assigned by
National Numbering Agencies (NNAs) &mdash; in the US, this is CUSIP Global Services.</p>

<p>At Meridian National Bank, ISINs are used primarily for international securities held
in client portfolios through the FORTUNA Wealth Management division. The
<em>ref_isin_mapping</em> reference table maintains the mapping between ISINs and CUSIPs,
enabling seamless identification of securities across domestic and international systems.
ISINs are required for regulatory reporting of foreign securities and for settlement
through international central securities depositories (Euroclear, Clearstream).</p>

<h3>Data Quality Controls</h3>
<p>ISIN identifiers are validated through automated data quality rules to ensure they
conform to the standard <strong>12-character format</strong>: exactly 2 uppercase
letters followed by 9 alphanumeric characters and 1 check digit. Records with ISINs
that do not match this pattern are flagged for review, as invalid ISINs can cause
failures in international trade settlement and cross-border regulatory reporting.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>CUSIP</strong> &mdash; The North American identifier embedded within the ISIN</li>
<li><strong>Ticker Symbol</strong> &mdash; The exchange trading code, distinct from the ISIN</li>
<li><strong>Trade Settlement</strong> &mdash; ISINs are used in international settlement</li>
</ul>
"""

OVERVIEWS["ticker-symbol"] = """
<h2>Ticker Symbol</h2>
<p>A Ticker Symbol (also called a stock symbol or trading symbol) is a short
alphabetic code assigned to a publicly traded security for identification on stock
exchanges and electronic trading platforms. Ticker symbols are exchange-specific:
NYSE-listed securities typically have 1-3 character symbols, while NASDAQ-listed
securities use 4-character symbols. The ticker is the most commonly recognized
identifier for publicly traded securities among investors and the financial media.</p>

<p>At Meridian National Bank, ticker symbols are used alongside CUSIPs and ISINs in
the FORTUNA trading platform. While CUSIPs serve as the system of record for security
identification, ticker symbols are used in client-facing reports, trade confirmations,
and the wealth management portal for ease of recognition. The <em>bronze_securities</em>
table maintains the mapping between tickers, CUSIPs, and ISINs.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>CUSIP</strong> &mdash; The authoritative security identifier in internal systems</li>
<li><strong>ISIN</strong> &mdash; The global security identifier</li>
<li><strong>Trade Settlement</strong> &mdash; Tickers are used for order entry, CUSIPs for settlement</li>
</ul>
"""

OVERVIEWS["trade-settlement"] = """
<h2>Trade Settlement</h2>
<p>Trade Settlement is the process of completing a securities transaction by
transferring the purchased securities to the buyer and the sale proceeds to the seller.
In the United States, most equity transactions settle on a <strong>T+1 basis</strong>
(one business day after the trade date), following the SEC's move from T+2 to T+1 in
May 2024. Fixed income, options, and certain other instruments may follow different
settlement cycles. Settlement is facilitated by the Depository Trust & Clearing
Corporation (DTCC) through its subsidiaries NSCC and DTC.</p>

<p>At Meridian National Bank, trade settlement is managed by the Operations team in
coordination with the bank's custodian. The <em>bronze_trades</em> table captures
trade details at execution, and settlement status is updated through custodian feeds
in <em>bronze_custodian_feeds</em>. Failed settlements (where securities or funds are
not delivered by the settlement date) are tracked and escalated, as they can result in
regulatory penalties and increased counterparty risk.</p>

<h3>Regulatory Context</h3>
<p>Settlement cycles are governed by SEC Rule 15c6-1. The move to T+1 settlement
reduced counterparty risk and margin requirements. Meridian's compliance team monitors
settlement failures against the SEC's close-out requirements (Regulation SHO for
equity shorts).</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Order Type</strong> &mdash; Trade execution that precedes settlement</li>
<li><strong>CUSIP</strong> &mdash; Security identifier used in settlement instructions</li>
<li><strong>Counterparty Risk</strong> &mdash; Settlement failures create counterparty exposure</li>
</ul>
"""

OVERVIEWS["order-type"] = """
<h2>Order Type</h2>
<p>An Order Type specifies the conditions under which a securities trade should be
executed. The three primary order types are: <strong>Market Order</strong> (execute
immediately at the best available price), <strong>Limit Order</strong> (execute at
a specified price or better), and <strong>Stop Order</strong> (triggered when the
security reaches a specified price, then executed as a market order). Additional
order types include Stop-Limit, Trailing Stop, and Immediate-or-Cancel (IOC).</p>

<p>At Meridian National Bank, order types are selected by financial advisors on behalf
of clients or by clients directly through the self-directed trading platform. The
FORTUNA trading system validates order parameters, checks buying power or share
availability, and routes orders to the appropriate execution venue. Order details
including type, status, and fill information are captured in <em>bronze_trades</em>.</p>

<h3>Regulatory Context</h3>
<p>Order handling and execution quality are governed by SEC Regulation NMS (National
Market System) and FINRA rules on best execution. Meridian is required to disclose
its order routing practices under SEC Rule 606 and evaluate execution quality
periodically.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Trade Settlement</strong> &mdash; Settlement follows order execution</li>
<li><strong>CUSIP</strong> &mdash; The security identifier in the order</li>
<li><strong>Financial Advisor</strong> &mdash; May place orders on behalf of clients</li>
</ul>
"""

# ==========================================================================
# RISK MANAGEMENT
# ==========================================================================

OVERVIEWS["var"] = """
<h2>Value at Risk (VaR)</h2>
<p>Value at Risk is a statistical measure that estimates the maximum potential loss on
a portfolio or position over a specified time horizon at a given confidence level. For
example, a 99% 1-day VaR of $1 million means there is a 99% probability that the
portfolio will not lose more than $1 million in a single trading day. VaR is the most
widely used market risk metric in banking and is a cornerstone of both internal risk
management and regulatory capital calculations.</p>

<p>Meridian National Bank calculates VaR for its trading book and available-for-sale
investment portfolio using historical simulation with a 2-year lookback period. The
bank reports VaR at both 99% confidence / 1-day horizon (internal risk limits) and
99% confidence / 10-day horizon (regulatory capital calculation). VaR results are
produced daily by the ARGUS risk engine and reviewed by the Market Risk team.</p>

<h3>VaR Methodology at Meridian</h3>
<ul>
<li><strong>Model:</strong> Historical simulation with full revaluation</li>
<li><strong>Lookback period:</strong> 500 trading days (approximately 2 years)</li>
<li><strong>Confidence level:</strong> 99% (1-day) and 99% (10-day)</li>
<li><strong>Risk factors:</strong> Interest rates, equity prices, FX rates, credit spreads</li>
</ul>

<h3>Limitations</h3>
<p>VaR has well-known limitations: it does not capture tail risk beyond the confidence
level, assumes normal market conditions, and may underestimate risk during periods of
market stress. Meridian supplements VaR with stress testing and expected shortfall (ES)
analysis.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Market Risk</strong> &mdash; VaR is the primary market risk metric</li>
<li><strong>Stress Testing</strong> &mdash; Supplements VaR for extreme scenarios</li>
<li><strong>Liquidity Risk</strong> &mdash; Illiquid positions may have understated VaR</li>
</ul>
"""

OVERVIEWS["credit-risk"] = """
<h2>Credit Risk</h2>
<p>Credit Risk is the risk of financial loss arising from a borrower's or counterparty's
failure to meet their contractual obligations, including principal and interest payments
on loans, settlement obligations on securities transactions, or performance under
derivative contracts. Credit risk is the single largest risk category for most banks,
and managing it effectively is fundamental to the safety and soundness of the
institution.</p>

<p>At Meridian National Bank, credit risk management encompasses the entire credit
lifecycle: origination (underwriting standards, credit approval authorities), ongoing
monitoring (risk rating reviews, covenant compliance, early warning indicators),
workout and recovery (troubled debt restructuring, charge-offs), and portfolio
management (concentration limits, stress testing, CECL provisioning). The Credit
Risk department reports to the Chief Risk Officer and provides regular reporting to
the Board Risk Committee.</p>

<h3>Regulatory Context</h3>
<p>Credit risk management is governed by extensive regulatory guidance including the
OCC's Comptroller's Handbook on Credit Risk, Basel III standardized and advanced
approaches for credit risk capital, and CECL (ASC 326) for loss provisioning. The
<em>gold_aml_risk_scoring</em> and risk-related analytics tables support credit
risk reporting.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Counterparty Risk</strong> &mdash; A specific form of credit risk</li>
<li><strong>Risk Rating</strong> &mdash; Internal classification of credit quality</li>
<li><strong>FICO Score</strong> &mdash; A measure of individual consumer credit risk</li>
<li><strong>Allowance for Credit Losses (ACL)</strong> &mdash; The reserve for expected credit losses</li>
</ul>
"""

OVERVIEWS["market-risk"] = """
<h2>Market Risk</h2>
<p>Market Risk is the risk of financial losses arising from adverse movements in market
prices and rates, including interest rates, equity prices, foreign exchange rates,
commodity prices, and credit spreads. Market risk affects both on-balance-sheet
positions (investment securities, trading book) and off-balance-sheet positions
(derivatives, commitments). For most banks, interest rate risk in the banking book
(IRRBB) is the most significant component of market risk.</p>

<p>Meridian National Bank manages market risk through its Asset-Liability Management
Committee (ALCO), which meets monthly to review the bank's interest rate risk position,
investment portfolio duration, and funding mix. The ARGUS risk engine produces daily
VaR calculations, interest rate sensitivity analyses (EVE and NII shocks), and
duration gap reports. Market risk data is maintained in <em>bronze_market_data</em>
and analyzed in <em>gold_market_risk_var</em>.</p>

<h3>Regulatory Context</h3>
<p>Market risk capital requirements are governed by Basel III/IV, specifically the
Fundamental Review of the Trading Book (FRTB) for trading positions and the standardized
approach for banking book interest rate risk. The OCC examines market risk management
as part of its annual supervisory cycle.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Value at Risk (VaR)</strong> &mdash; The primary quantitative market risk measure</li>
<li><strong>Stress Testing</strong> &mdash; Evaluates market risk under extreme scenarios</li>
<li><strong>Liquidity Risk</strong> &mdash; Market illiquidity amplifies market risk</li>
<li><strong>Net Interest Margin (NIM)</strong> &mdash; NIM is sensitive to market interest rate changes</li>
</ul>
"""

OVERVIEWS["operational-risk"] = """
<h2>Operational Risk</h2>
<p>Operational Risk is the risk of loss resulting from inadequate or failed internal
processes, people, and systems, or from external events. This broad category encompasses
fraud (both internal and external), technology failures, cyber attacks, human errors,
legal and compliance breaches, business disruption, and third-party/vendor risk.
Operational risk is distinct from credit and market risk in that it arises from the
bank's operations rather than from financial market positions.</p>

<p>At Meridian National Bank, operational risk is managed through a comprehensive
framework that includes risk and control self-assessments (RCSAs), key risk indicators
(KRIs), incident and loss event tracking, scenario analysis, and business continuity
planning. The Operational Risk team reports to the Chief Risk Officer and provides
quarterly reporting to the Board Risk Committee. Operational events are tracked in
<em>bronze_audit_events</em> and analyzed in <em>gold_operational_risk</em>.</p>

<h3>Regulatory Context</h3>
<p>Under Basel III, operational risk capital is calculated using the Standardized
Measurement Approach (SMA), which replaced the previous Basic Indicator, Standardized,
and Advanced Measurement approaches. The OCC's Heightened Standards (12 CFR 30,
Appendix D) require banks to maintain robust operational risk governance frameworks.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Credit Risk</strong> &mdash; Distinguished from operational risk by its financial market origin</li>
<li><strong>Market Risk</strong> &mdash; Another primary risk category</li>
<li><strong>Stress Testing</strong> &mdash; Includes operational risk scenarios</li>
</ul>
"""

OVERVIEWS["liquidity-risk"] = """
<h2>Liquidity Risk</h2>
<p>Liquidity Risk is the risk that a bank cannot meet its financial obligations as they
come due without incurring unacceptable losses. This includes both <strong>funding
liquidity risk</strong> (the risk of being unable to raise funds at reasonable cost)
and <strong>market liquidity risk</strong> (the risk of being unable to sell assets
at fair value in a timely manner). Effective liquidity risk management is critical
for bank survival, as liquidity crises can escalate rapidly and become existential.</p>

<p>Meridian National Bank manages liquidity risk through a Contingency Funding Plan
(CFP), diversified funding sources, maintenance of a liquid asset buffer, and ongoing
cash flow forecasting. The bank monitors liquidity daily using internal metrics and
regulatory ratios. Liquidity data is analyzed in <em>gold_liquidity_coverage</em>
for management and regulatory reporting.</p>

<h3>Regulatory Requirements</h3>
<p>Under Basel III, banks must maintain a Liquidity Coverage Ratio (LCR) &mdash; high
quality liquid assets sufficient to cover 30 days of net cash outflows in a stress
scenario &mdash; and a Net Stable Funding Ratio (NSFR) &mdash; stable funding
sufficient to cover required stable funding over a one-year horizon. Meridian reports
liquidity metrics on Call Report Schedule RC-O and the Complex Institution Liquidity
Monitoring Report (FR 2052a, if applicable).</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Basel III</strong> &mdash; The regulatory framework for liquidity standards</li>
<li><strong>Stress Testing</strong> &mdash; Liquidity stress scenarios are a key component</li>
<li><strong>Market Risk</strong> &mdash; Illiquidity amplifies market risk</li>
</ul>
"""

OVERVIEWS["counterparty-risk"] = """
<h2>Counterparty Risk</h2>
<p>Counterparty Risk is the risk that the other party in a financial transaction will
default on its contractual obligation before the final settlement of the transaction's
cash flows. This risk is particularly relevant for over-the-counter (OTC) derivatives,
securities lending, repurchase agreements (repos), and unsettled securities trades.
Counterparty risk differs from general credit risk in that the exposure is bilateral
and changes with market movements.</p>

<p>At Meridian National Bank, counterparty risk arises primarily from the bank's
derivative hedging activities (interest rate swaps used for IRRBB management),
interbank lending, and securities settlement. Counterparty data is maintained in
<em>bronze_counterparties</em>, including credit ratings, exposure limits, and
netting agreements. The <em>gold_market_risk_var</em> table incorporates
counterparty credit valuation adjustments (CVA).</p>

<h3>Risk Mitigation</h3>
<p>Meridian mitigates counterparty risk through master netting agreements (ISDA),
collateral requirements (CSA), central clearing of eligible derivatives, counterparty
credit limits, and ongoing monitoring of counterparty creditworthiness.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Credit Risk</strong> &mdash; Counterparty risk is a specific form of credit risk</li>
<li><strong>Trade Settlement</strong> &mdash; Settlement failure creates counterparty exposure</li>
<li><strong>Value at Risk (VaR)</strong> &mdash; Counterparty exposure affects portfolio VaR</li>
</ul>
"""

OVERVIEWS["stress-testing"] = """
<h2>Stress Testing</h2>
<p>Stress Testing is a forward-looking analytical exercise that evaluates the potential
impact of hypothetical adverse economic and financial scenarios on a bank's capital
adequacy, earnings, asset quality, and liquidity position. Stress tests help identify
vulnerabilities, assess the sufficiency of capital buffers, and inform strategic and
capital planning decisions. They are a fundamental component of sound risk management
and a regulatory requirement for banks above certain asset thresholds.</p>

<p>Meridian National Bank conducts both regulatory and internal stress tests. Internal
stress tests are run quarterly by the ARGUS risk engine using scenarios developed by
the Risk Management team and approved by the Board Risk Committee. Scenarios include
baseline, adverse, and severely adverse economic conditions with impacts modeled
across credit losses, market risk, interest rates, and operational disruptions.
Results are stored in <em>bronze_stress_tests</em> and reported in
<em>gold_regulatory_dashboard</em>.</p>

<h3>Regulatory Context</h3>
<p>For banks with over $100 billion in assets, the Dodd-Frank Act Stress Test (DFAST)
is required annually. While Meridian may fall below this threshold, the OCC expects
all national banks to conduct stress testing proportionate to their size, complexity,
and risk profile (OCC Bulletin 2012-33).</p>

<h3>Related Terms</h3>
<ul>
<li><strong>DFAST (Dodd-Frank Act Stress Test)</strong> &mdash; The formal regulatory stress test</li>
<li><strong>Value at Risk (VaR)</strong> &mdash; Stress tests complement VaR analysis</li>
<li><strong>CET1 Capital Ratio</strong> &mdash; Stress-tested to ensure adequacy under adverse conditions</li>
<li><strong>Basel III</strong> &mdash; Stress testing is a Pillar 2 requirement</li>
</ul>
"""

# ==========================================================================
# REGULATORY & COMPLIANCE
# ==========================================================================

OVERVIEWS["sar"] = """
<h2>Suspicious Activity Report (SAR)</h2>
<p>A Suspicious Activity Report is a regulatory filing submitted to the Financial Crimes
Enforcement Network (FinCEN) on Form 111 when a bank detects known or suspected
violations of federal law, transactions involving funds derived from illegal activity,
attempts to evade BSA reporting requirements (structuring), or transactions with no
apparent lawful purpose that the bank cannot reasonably explain after examining
available facts.</p>

<p>At Meridian National Bank, SAR filings are the responsibility of the BSA/AML
Compliance team, led by the BSA Officer. The bank's transaction monitoring system
generates alerts based on rule-based and behavioral analytics models. Alerts are
investigated by the Financial Intelligence Unit (FIU), and if suspicious activity is
confirmed, a SAR is filed. The <em>gold_aml_risk_scoring</em> table provides risk
scores used to prioritize alert investigation.</p>

<h3>Filing Requirements</h3>
<ul>
<li><strong>Timing:</strong> Must be filed within 30 calendar days of initial detection (60 days if no suspect is identified)</li>
<li><strong>No dollar threshold:</strong> Any suspicious activity must be evaluated, though most banks use $5,000 as a practical threshold for investigation</li>
<li><strong>Confidentiality:</strong> SAR existence and content cannot be disclosed to the subject of the report (31 USC 5318(g)(2))</li>
<li><strong>Retention:</strong> SARs and supporting documentation must be retained for 5 years from filing date</li>
<li><strong>Continuing activity:</strong> SARs for ongoing activity must be updated every 90 days</li>
</ul>

<h3>Regulatory Context</h3>
<p>SAR requirements are codified at 31 CFR 1020.320 for banks. Failure to file SARs
is one of the most common and consequential BSA/AML violations, frequently resulting
in enforcement actions, civil money penalties, and cease-and-desist orders.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Bank Secrecy Act (BSA)</strong> &mdash; The legislative foundation for SAR requirements</li>
<li><strong>OFAC Screening</strong> &mdash; OFAC matches may trigger SAR filings</li>
<li><strong>Currency Transaction Report (CTR)</strong> &mdash; CTR structuring patterns may lead to SARs</li>
</ul>
"""

OVERVIEWS["bsa"] = """
<h2>Bank Secrecy Act (BSA)</h2>
<p>The Bank Secrecy Act (formally the Currency and Foreign Transactions Reporting Act
of 1970) is federal legislation requiring financial institutions to maintain records
and file reports that are useful in detecting and preventing money laundering, terrorist
financing, and other financial crimes. The BSA is the foundation of the US anti-money
laundering (AML) regulatory framework and is administered by the Financial Crimes
Enforcement Network (FinCEN), a bureau of the US Department of the Treasury.</p>

<p>Meridian National Bank maintains a comprehensive BSA/AML compliance program as
required by the BSA and its implementing regulations. The program includes five pillars:
(1) internal policies, procedures, and controls; (2) designation of a BSA compliance
officer; (3) an ongoing employee training program; (4) an independent audit function;
and (5) customer due diligence and beneficial ownership identification (added by the
2016 CDD Rule).</p>

<h3>Key BSA Filing Obligations</h3>
<ul>
<li><strong>CTR (Currency Transaction Report):</strong> Filed for cash transactions over $10,000</li>
<li><strong>SAR (Suspicious Activity Report):</strong> Filed for suspected criminal activity</li>
<li><strong>CMIR (Report of International Transportation of Currency):</strong> Physical transport of currency over $10,000</li>
<li><strong>FBAR (Foreign Bank Account Report):</strong> Reported by customers with foreign accounts over $10,000</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>Suspicious Activity Report (SAR)</strong> &mdash; A core BSA filing</li>
<li><strong>Currency Transaction Report (CTR)</strong> &mdash; A core BSA filing</li>
<li><strong>Know Your Customer (KYC)</strong> &mdash; The CDD component of the BSA program</li>
<li><strong>OFAC Screening</strong> &mdash; Conducted alongside BSA compliance</li>
</ul>
"""

OVERVIEWS["ofac-screening"] = """
<h2>OFAC Screening</h2>
<p>OFAC Screening is the process of checking customers, counterparties, and transactions
against the sanctions lists maintained by the Office of Foreign Assets Control (OFAC),
a bureau of the US Department of the Treasury. OFAC administers and enforces US
economic sanctions programs targeting specific countries, regimes, entities, and
individuals. The primary screening lists include the Specially Designated Nationals
(SDN) list, the Sectoral Sanctions Identifications (SSI) list, and the Non-SDN
Consolidated Sanctions list.</p>

<p>Meridian National Bank performs OFAC screening at multiple touchpoints: customer
onboarding, wire transfer processing (both domestic and international), ACH
transactions, loan origination, and periodic batch screening of the entire customer
base. The bank uses an automated screening platform with fuzzy matching logic to
catch name variations, transliterations, and aliases. All potential matches are
investigated by the BSA/AML Compliance team, and confirmed matches are blocked
and reported.</p>

<h3>Regulatory Context</h3>
<p>OFAC compliance is a strict liability regime &mdash; violations can result in
civil penalties regardless of whether the bank knew it was dealing with a sanctioned
party. Penalties can reach $250,000 or twice the transaction amount per violation.
Willful violations carry criminal penalties including imprisonment. OFAC compliance
is examined jointly with BSA/AML programs.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Wire Transfer</strong> &mdash; All wires are screened against OFAC lists</li>
<li><strong>Suspicious Activity Report (SAR)</strong> &mdash; OFAC matches may trigger SAR filings</li>
<li><strong>Bank Secrecy Act (BSA)</strong> &mdash; OFAC screening is part of the broader BSA compliance framework</li>
</ul>
"""

OVERVIEWS["basel-iii"] = """
<h2>Basel III</h2>
<p>Basel III is the international regulatory framework for banks, developed by the
Basel Committee on Banking Supervision (BCBS) in response to the 2008 global
financial crisis. It establishes strengthened minimum capital requirements, introduces
new liquidity standards, and adds a leverage ratio requirement. Basel III aims to
improve the banking sector's ability to absorb shocks, reduce risk of spillover to
the real economy, and enhance risk management and governance.</p>

<p>At Meridian National Bank, Basel III requirements are implemented through US federal
banking agency rules. The bank calculates and reports capital ratios (CET1, Tier 1,
Total Capital) and risk-weighted assets quarterly on Call Report Schedule RC-R.
Liquidity ratios are monitored daily and reported on Call Report Schedule RC-O.
The ARGUS risk engine calculates risk-weighted assets, and the Finance team manages
capital planning in alignment with Basel III requirements.</p>

<h3>Key Basel III Components</h3>
<ul>
<li><strong>Capital:</strong> CET1 minimum 4.5% + conservation buffer 2.5% = 7.0% effective minimum</li>
<li><strong>Leverage:</strong> Minimum 4% Tier 1 leverage ratio (5% for well-capitalized)</li>
<li><strong>Liquidity:</strong> LCR (30-day stress), NSFR (1-year structural), both at 100% minimum</li>
<li><strong>Counterparty credit risk:</strong> CVA capital charge for OTC derivatives</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>CET1 Capital Ratio</strong> &mdash; The most stringent Basel III capital metric</li>
<li><strong>Risk-Weighted Assets (RWA)</strong> &mdash; The denominator for capital ratios</li>
<li><strong>Liquidity Risk</strong> &mdash; Addressed by LCR and NSFR requirements</li>
<li><strong>DFAST</strong> &mdash; US stress testing requirement that complements Basel capital standards</li>
</ul>
"""

OVERVIEWS["cet1-ratio"] = """
<h2>CET1 Capital Ratio</h2>
<p>The Common Equity Tier 1 (CET1) Capital Ratio is the most stringent and important
measure of bank capital adequacy under Basel III. It is calculated as CET1 capital
divided by total risk-weighted assets (RWA). CET1 capital consists of the highest
quality capital instruments: common stock, retained earnings, accumulated other
comprehensive income (AOCI), and qualifying minority interests, less required
regulatory deductions (goodwill, intangible assets, deferred tax assets above
threshold deductions).</p>

<p>Meridian National Bank monitors its CET1 ratio daily and reports it quarterly on
Call Report Schedule RC-R. The Finance team manages capital planning to maintain CET1
above both regulatory minimums and the bank's internal target (which includes a
management buffer above regulatory requirements). Capital adequacy data is analyzed
in <em>gold_capital_adequacy</em>.</p>

<h3>Regulatory Requirements</h3>
<ul>
<li><strong>Minimum CET1:</strong> 4.5% of RWA</li>
<li><strong>Capital Conservation Buffer:</strong> +2.5% (restricts distributions if breached)</li>
<li><strong>Countercyclical Buffer:</strong> 0-2.5% (set by regulators, currently 0%)</li>
<li><strong>G-SIB Surcharge:</strong> 1.0-4.5% (for globally systemically important banks)</li>
<li><strong>Well-capitalized threshold:</strong> 6.5% CET1 (for prompt corrective action)</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>Basel III</strong> &mdash; The regulatory framework establishing CET1 requirements</li>
<li><strong>Risk-Weighted Assets (RWA)</strong> &mdash; The denominator of the CET1 ratio</li>
<li><strong>DFAST</strong> &mdash; Stress tests project CET1 ratios under adverse scenarios</li>
<li><strong>Call Report</strong> &mdash; Quarterly filing where CET1 is reported</li>
</ul>
"""

OVERVIEWS["dfast"] = """
<h2>DFAST (Dodd-Frank Act Stress Test)</h2>
<p>The Dodd-Frank Act Stress Test is an annual supervisory exercise required for
banking organizations with over $100 billion in total consolidated assets. DFAST
evaluates the resilience of a bank's capital position under hypothetical adverse
economic scenarios, projecting revenues, losses, reserves, and capital ratios over
a nine-quarter planning horizon. The scenarios (baseline, adverse, severely adverse)
are prescribed annually by the Federal Reserve Board.</p>

<p>While Meridian National Bank may fall below the $100 billion threshold for mandatory
DFAST participation, the bank conducts internal stress tests modeled on the DFAST
framework as a risk management best practice. These internal stress tests are performed
quarterly using scenarios developed by the Risk Management team and approved by the
Board Risk Committee. Results inform capital planning, dividend decisions, and risk
appetite calibration. Stress test data is managed in <em>bronze_stress_tests</em>
and reported via <em>gold_regulatory_dashboard</em>.</p>

<h3>DFAST Process</h3>
<ul>
<li><strong>Scenario design:</strong> Macroeconomic variables including GDP, unemployment, interest rates, housing prices</li>
<li><strong>Loss modeling:</strong> Credit losses by portfolio segment, market losses, operational losses</li>
<li><strong>Revenue projection:</strong> Net interest income, noninterest income under stress</li>
<li><strong>Capital impact:</strong> Pre-provision net revenue minus losses, post-tax capital impact</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>Stress Testing</strong> &mdash; The broader risk management discipline</li>
<li><strong>CET1 Capital Ratio</strong> &mdash; A key output metric of stress tests</li>
<li><strong>Basel III</strong> &mdash; The capital framework that DFAST tests against</li>
</ul>
"""

OVERVIEWS["call-report"] = """
<h2>Call Report (FFIEC 031/041)</h2>
<p>The Call Report (formally the Consolidated Reports of Condition and Income) is a
quarterly regulatory filing submitted by all FDIC-insured commercial banks to the
Federal Financial Institutions Examination Council (FFIEC). Banks with domestic offices
only file FFIEC 041; banks with domestic and foreign offices file FFIEC 031. The Call
Report is the most comprehensive and important recurring regulatory filing for US
banks, providing detailed financial data used by regulators, analysts, and the public.</p>

<p>At Meridian National Bank, Call Report preparation is led by the Finance team with
input from the Credit Risk, Treasury, and Compliance departments. Data is sourced from
the <em>general-ledger</em> (GL) and supplemented by subsidiary ledger detail. The
ARGUS financial reporting module maps GL accounts to Call Report line items. Meridian
targets submission within 30 calendar days of quarter-end (regulatory deadline). The
<em>gold_regulatory_dashboard</em> provides a pre-filing summary for management review.</p>

<h3>Key Call Report Schedules</h3>
<ul>
<li><strong>RC (Balance Sheet):</strong> Assets, liabilities, and equity</li>
<li><strong>RI (Income Statement):</strong> Interest and noninterest income and expense</li>
<li><strong>RC-C (Loans):</strong> Loan portfolio by type and collateral</li>
<li><strong>RC-E (Deposits):</strong> Deposit balances by type and insurance status</li>
<li><strong>RC-N (Past Due Loans):</strong> Delinquent and nonaccrual loans</li>
<li><strong>RC-R (Capital):</strong> Risk-based capital ratios</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>General Ledger (GL)</strong> &mdash; Primary data source for the Call Report</li>
<li><strong>CET1 Capital Ratio</strong> &mdash; Reported on Schedule RC-R</li>
<li><strong>Risk-Weighted Assets (RWA)</strong> &mdash; Reported on Schedule RC-R</li>
</ul>
"""

# ==========================================================================
# FINANCIAL REPORTING
# ==========================================================================

OVERVIEWS["net-interest-margin"] = """
<h2>Net Interest Margin (NIM)</h2>
<p>Net Interest Margin is the primary profitability metric for banks, measuring the
spread between interest income earned on interest-bearing assets (loans, securities,
Fed funds sold) and interest expense paid on interest-bearing liabilities (deposits,
borrowings, subordinated debt), expressed as a percentage of average earning assets.
NIM reflects the bank's ability to earn a favorable spread in the prevailing interest
rate environment and is the single largest driver of bank revenue.</p>

<p>At Meridian National Bank, NIM is calculated daily by the Finance team and reviewed
monthly by ALCO. The <em>gold_net_interest_margin</em> analytics table provides trend
analysis, peer comparison, and decomposition of NIM drivers (asset yield, cost of
funds, asset mix, funding mix). NIM is also a key input to interest rate sensitivity
analysis and earnings-at-risk modeling.</p>

<h3>Formula</h3>
<p><strong>NIM = (Interest Income - Interest Expense) / Average Earning Assets</strong></p>

<h3>Industry Benchmarks</h3>
<ul>
<li><strong>Community banks (&lt;$1B assets):</strong> 3.0-4.0%</li>
<li><strong>Regional banks ($1B-$100B):</strong> 2.5-3.5%</li>
<li><strong>Large banks (&gt;$100B):</strong> 2.0-3.0%</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>Efficiency Ratio</strong> &mdash; Another key profitability metric</li>
<li><strong>Return on Average Assets (ROAA)</strong> &mdash; NIM is a major driver of ROAA</li>
<li><strong>General Ledger (GL)</strong> &mdash; Source of interest income and expense data</li>
<li><strong>Market Risk</strong> &mdash; NIM is sensitive to interest rate movements</li>
</ul>
"""

OVERVIEWS["efficiency-ratio"] = """
<h2>Efficiency Ratio</h2>
<p>The Efficiency Ratio is a key banking profitability metric that measures how much it
costs the bank to generate one dollar of revenue. It is calculated as: <strong>Noninterest
Expense / (Net Interest Income + Noninterest Income)</strong>. A lower efficiency ratio
indicates better cost management &mdash; the bank is spending less to produce each
dollar of revenue. Top-performing banks typically achieve efficiency ratios below 55%.</p>

<p>At Meridian National Bank, the efficiency ratio is tracked monthly in the
<em>gold_balance_sheet_summary</em> analytics table and reported to the Board Finance
Committee quarterly. Key drivers of the efficiency ratio include compensation costs
(the largest noninterest expense), technology investments, branch network costs, and
regulatory compliance expenses. Management targets are set annually as part of the
strategic planning process.</p>

<h3>Industry Benchmarks</h3>
<ul>
<li><strong>Top quartile:</strong> Below 55%</li>
<li><strong>Median:</strong> 58-65%</li>
<li><strong>Below average:</strong> Above 70%</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>Net Interest Margin (NIM)</strong> &mdash; A key component of total revenue in the denominator</li>
<li><strong>Return on Average Assets (ROAA)</strong> &mdash; Complementary profitability metric</li>
<li><strong>Branch</strong> &mdash; Branch costs are a significant driver of the efficiency ratio</li>
</ul>
"""

OVERVIEWS["roaa"] = """
<h2>Return on Average Assets (ROAA)</h2>
<p>Return on Average Assets is a profitability ratio that measures how effectively a
bank uses its total asset base to generate earnings. It is calculated as:
<strong>Net Income / Average Total Assets</strong>. ROAA normalizes earnings by asset
size, making it useful for comparing profitability across banks of different sizes.
It is one of the primary metrics used by regulators, analysts, and investors to
assess bank performance.</p>

<p>At Meridian National Bank, ROAA is calculated quarterly using annualized net income
divided by the quarterly average of total assets. The Finance team reports ROAA
alongside Return on Average Equity (ROAE) and the efficiency ratio as part of the
comprehensive profitability dashboard. ROAA trends are analyzed in the
<em>gold_balance_sheet_summary</em> table.</p>

<h3>Industry Benchmarks</h3>
<ul>
<li><strong>Strong performance:</strong> ROAA &gt; 1.25%</li>
<li><strong>Satisfactory:</strong> ROAA 0.75-1.25%</li>
<li><strong>Underperforming:</strong> ROAA &lt; 0.75%</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>Net Interest Margin (NIM)</strong> &mdash; The primary revenue driver affecting ROAA</li>
<li><strong>Efficiency Ratio</strong> &mdash; Expense management directly impacts ROAA</li>
<li><strong>Provision for Credit Losses</strong> &mdash; Higher provisions reduce net income and ROAA</li>
</ul>
"""

OVERVIEWS["provision-for-credit-losses"] = """
<h2>Provision for Credit Losses</h2>
<p>The Provision for Credit Losses is the expense recognized on the income statement to
establish and maintain the Allowance for Credit Losses (ACL) at a level sufficient to
cover expected lifetime credit losses on the bank's loan portfolio and other financial
assets held at amortized cost. Under the Current Expected Credit Losses (CECL)
methodology (ASC 326), the provision reflects management's estimate of expected losses
considering historical experience, current conditions, and reasonable and supportable
forecasts.</p>

<p>At Meridian National Bank, the provision is calculated quarterly by the Credit Risk
department in collaboration with Finance. The CECL model incorporates probability of
default (PD), loss given default (LGD), and exposure at default (EAD) across loan
segments, adjusted for macroeconomic forecasts. Provision adequacy is reviewed by
external auditors, the Audit Committee, and banking examiners. Provision expense is
reported on Call Report Schedule RI, Line 4.</p>

<h3>Drivers of Provision Expense</h3>
<ul>
<li>Net loan growth (new originations requiring reserves)</li>
<li>Changes in loan portfolio composition and risk mix</li>
<li>Deterioration or improvement in credit quality metrics</li>
<li>Changes in macroeconomic forecasts (unemployment, GDP, housing)</li>
<li>Net charge-offs (provisions replenish the ACL after charge-offs)</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>Allowance for Credit Losses (ACL)</strong> &mdash; The balance sheet reserve funded by provision expense</li>
<li><strong>Charge-Off</strong> &mdash; Charge-offs reduce the ACL, requiring additional provisions</li>
<li><strong>Risk Rating</strong> &mdash; Risk ratings are a key input to the CECL model</li>
<li><strong>Return on Average Assets (ROAA)</strong> &mdash; Provision expense reduces net income</li>
</ul>
"""

OVERVIEWS["general-ledger"] = """
<h2>General Ledger (GL)</h2>
<p>The General Ledger is the master accounting record of Meridian National Bank,
containing all financial transactions organized by account in a structured chart of
accounts. The GL is the authoritative source for financial statement preparation,
regulatory reporting, management reporting, and external audit. Every financial
transaction &mdash; deposits, loans, payments, interest accruals, fee postings,
operational expenses &mdash; is recorded in the GL through journal entries.</p>

<p>Meridian's GL is maintained in the ARGUS financial reporting system, with automated
feeds from the ATLAS core banking system and FORTUNA wealth management platform. The
GL chart of accounts is organized hierarchically: division, department, account class
(asset, liability, equity, revenue, expense), and detailed account number. GL data is
captured in <em>bronze_gl_entries</em> and <em>bronze_gl_accounts</em>, with the
account hierarchy maintained in <em>ref_gl_account_hierarchy</em>.</p>

<h3>GL and Regulatory Reporting</h3>
<p>The GL serves as the primary source for Call Report preparation, with GL account
balances mapped to specific Call Report line items. The <em>gold_balance_sheet_summary</em>
table aggregates GL data for management and regulatory reporting. Reconciliation
between the GL and subsidiary ledgers (loan system, deposit system, investment system)
is performed daily to ensure data integrity.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Call Report</strong> &mdash; Regulatory filing sourced primarily from GL data</li>
<li><strong>Risk-Weighted Assets (RWA)</strong> &mdash; GL account balances feed RWA calculations</li>
<li><strong>Net Interest Margin (NIM)</strong> &mdash; Interest income/expense from GL accounts</li>
</ul>
"""

OVERVIEWS["risk-weighted-assets"] = """
<h2>Risk-Weighted Assets (RWA)</h2>
<p>Risk-Weighted Assets represent total on-balance-sheet assets and off-balance-sheet
exposures adjusted by risk weight factors prescribed by Basel III. Each asset category
is assigned a risk weight reflecting its relative credit risk: cash and government
securities at 0%, GSE securities at 20%, residential mortgages at 50%, commercial
loans at 100%, and certain high-risk assets at 150%. RWA is the denominator in all
Basel III capital ratio calculations (CET1, Tier 1, Total Capital).</p>

<p>At Meridian National Bank, RWA is calculated quarterly by the Finance team using the
Basel III standardized approach. The ARGUS risk engine maps each GL account and loan
to the appropriate risk weight category and computes aggregate RWA. Off-balance-sheet
items (loan commitments, letters of credit, derivatives) are converted to credit
equivalent amounts before applying risk weights. RWA is reported on Call Report
Schedule RC-R.</p>

<h3>Risk Weight Categories</h3>
<ul>
<li><strong>0%:</strong> Cash, US government securities, Fed deposits</li>
<li><strong>20%:</strong> GSE securities, interbank deposits, general obligation municipal bonds</li>
<li><strong>50%:</strong> 1-4 family residential mortgages (prudently underwritten)</li>
<li><strong>100%:</strong> Commercial loans, consumer loans, most other assets</li>
<li><strong>150%:</strong> Past-due loans (90+ days), high-volatility commercial real estate</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>CET1 Capital Ratio</strong> &mdash; CET1 capital / RWA</li>
<li><strong>Basel III</strong> &mdash; The framework prescribing risk weight factors</li>
<li><strong>General Ledger (GL)</strong> &mdash; Asset balances sourced from the GL</li>
</ul>
"""

OVERVIEWS["allowance-for-credit-losses"] = """
<h2>Allowance for Credit Losses (ACL)</h2>
<p>The Allowance for Credit Losses (formerly the Allowance for Loan and Lease Losses,
or ALLL) is a contra-asset account on the bank's balance sheet representing
management's estimate of expected lifetime credit losses on the loan portfolio and
other financial assets measured at amortized cost. Under the Current Expected Credit
Losses (CECL) methodology (ASC 326, effective for most banks in 2023), the ACL must
reflect all expected credit losses over the remaining contractual life of the financial
asset, adjusted for expected prepayments.</p>

<p>At Meridian National Bank, the ACL is calculated quarterly using a combination of
quantitative models (probability of default, loss given default, discounted cash flow)
and qualitative adjustments for factors not fully captured by the models (economic
uncertainty, emerging risks, portfolio concentrations). The ACL is reviewed by the
Chief Credit Officer, external auditors, and banking examiners. ACL adequacy is
reported on Call Report Schedule RC (line 4d) and Schedule RI-B.</p>

<h3>ACL Components</h3>
<ul>
<li><strong>Quantitative reserve:</strong> Model-driven estimate based on historical loss experience, current conditions, and forecasts</li>
<li><strong>Qualitative adjustments:</strong> Management overlays for emerging risks, model limitations, and portfolio-specific factors</li>
<li><strong>Individually assessed:</strong> Specific reserves for large nonperforming loans</li>
</ul>

<h3>Related Terms</h3>
<ul>
<li><strong>Provision for Credit Losses</strong> &mdash; The income statement expense that funds the ACL</li>
<li><strong>Charge-Off</strong> &mdash; Charged-off loans reduce the ACL balance</li>
<li><strong>Risk Rating</strong> &mdash; A key input to ACL calculation models</li>
<li><strong>Delinquency</strong> &mdash; Delinquency status affects expected loss estimates</li>
</ul>
"""

# ==========================================================================
# OPERATIONS & INFRASTRUCTURE
# ==========================================================================

OVERVIEWS["branch"] = """
<h2>Branch</h2>
<p>A Branch is a physical bank location offering in-person deposit, lending, advisory,
and customer service capabilities. Each branch operates as a cost center within
Meridian National Bank's organizational structure, with performance measured by
deposit growth, loan production, customer acquisition, cross-sell ratios, and
operating efficiency. Branches also serve as the primary venue for complex
transactions requiring identity verification, notarization, or advisory
consultation.</p>

<p>Meridian National Bank operates a network of branches across its footprint, each
staffed with tellers, personal bankers, and (at larger locations) business bankers
and mortgage loan officers. Branch data is maintained in <em>bronze_branches</em>
and <em>bronze_employees</em>, with performance metrics aggregated in
<em>gold_branch_performance</em>. The <em>vw_branch_retail_wealth</em> dashboard
view provides an integrated view of retail and wealth management activity by branch.</p>

<h3>Regulatory Context</h3>
<p>Branch openings and closings require regulatory notification (OCC/FDIC). Under the
Community Reinvestment Act (CRA), branch distribution and services are evaluated as
part of the bank's CRA performance assessment. BSA/AML compliance activities
(CTR filing, SAR awareness) are conducted at the branch level.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Core Banking System</strong> &mdash; Branches access ATLAS for real-time transaction processing</li>
<li><strong>Digital Channel</strong> &mdash; Complements branch services for self-service banking</li>
<li><strong>Customer Segment</strong> &mdash; Branch staffing models align with customer segments served</li>
</ul>
"""

OVERVIEWS["core-banking-system"] = """
<h2>Core Banking System</h2>
<p>The Core Banking System is the central technology platform that processes and records
the bank's primary financial transactions, including deposits, withdrawals, loan
payments, interest calculations, and account maintenance. At Meridian National Bank,
the core banking system is called <strong>ATLAS</strong>, which handles retail banking,
commercial banking, and lending operations in real-time across all branches and digital
channels.</p>

<p>ATLAS serves as the system of record for customer accounts, loan portfolios, and
transaction history. It feeds data downstream to the analytics platform (bronze/silver/gold
data layers), the FORTUNA wealth management system, the ARGUS financial reporting and
risk engine, and various regulatory reporting systems. Integration between ATLAS and
downstream systems is managed through real-time feeds and nightly batch processes,
captured in <em>bronze_*</em> tables.</p>

<h3>System Architecture</h3>
<p>ATLAS processes millions of transactions daily across deposit, lending, and payment
channels. Key capabilities include real-time account balance updates, automated interest
accrual, fee assessment, overdraft processing, hold management, and regulatory
compliance checks (OFAC screening, BSA monitoring). System availability targets
exceed 99.95% uptime.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Branch</strong> &mdash; Branches access ATLAS for customer transactions</li>
<li><strong>Digital Channel</strong> &mdash; Online and mobile channels connect through ATLAS APIs</li>
<li><strong>General Ledger (GL)</strong> &mdash; ATLAS posts transactions to the ARGUS GL</li>
</ul>
"""

OVERVIEWS["digital-channel"] = """
<h2>Digital Channel</h2>
<p>Digital Channel encompasses all electronic self-service banking platforms that enable
customers to conduct financial transactions and access banking services outside of
traditional branch hours and locations. At Meridian National Bank, digital channels
include online banking (web), mobile banking (iOS/Android apps), ATM network, and
interactive voice response (IVR) telephone banking.</p>

<p>Digital adoption is a strategic priority for Meridian, as digital transactions
are significantly lower-cost than branch transactions. The bank tracks digital
channel usage metrics including adoption rates, feature utilization, mobile deposit
volumes, and digital-to-branch transaction ratios. Digital channel data feeds into
<em>bronze_atm_transactions</em> and is analyzed in <em>gold_branch_performance</em>
(which includes digital vs. branch comparisons) for strategic planning.</p>

<h3>Regulatory Considerations</h3>
<p>Digital channels must comply with Regulation E (electronic fund transfers),
GLBA (data privacy), ADA accessibility requirements, and the bank's information
security program. Multi-factor authentication (MFA) is required for all digital
banking sessions. Mobile deposit capture is subject to Regulation CC hold policies
and the bank's funds availability policy.</p>

<h3>Related Terms</h3>
<ul>
<li><strong>Core Banking System</strong> &mdash; Digital channels connect to ATLAS for transaction processing</li>
<li><strong>Branch</strong> &mdash; Physical alternative to digital self-service</li>
<li><strong>ACH Transfer</strong> &mdash; Commonly initiated through digital channels</li>
</ul>
"""

# ==========================================================================
# ABBREVIATION ALIASES
# ==========================================================================

OVERVIEWS["kyc-abbr"] = """<p><strong>KYC</strong> is a commonly used abbreviation for <em>Know Your Customer</em>, the regulatory process mandated by the BSA/AML framework requiring banks to verify customer identity and assess risk. At Meridian National Bank, KYC encompasses CDD, EDD, and ongoing monitoring. See the full <strong>Know Your Customer (KYC)</strong> term for complete details.</p>"""

OVERVIEWS["cdd-abbr"] = """<p><strong>CDD</strong> is a commonly used abbreviation for <em>Customer Due Diligence</em>, the standard level of identity verification and risk assessment applied to all customers at account opening. Required by the FinCEN CDD Final Rule. See the full <strong>Customer Due Diligence (CDD)</strong> term for complete details.</p>"""

OVERVIEWS["edd-abbr"] = """<p><strong>EDD</strong> is a commonly used abbreviation for <em>Enhanced Due Diligence</em>, the elevated level of scrutiny applied to high-risk customers including PEPs and those in high-risk jurisdictions. See the full <strong>Enhanced Due Diligence (EDD)</strong> term for complete details.</p>"""

OVERVIEWS["aum-abbr"] = """<p><strong>AUM</strong> is a commonly used abbreviation for <em>Assets Under Management</em>, representing the total market value of investment assets managed by FORTUNA Wealth Management. AUM is the primary driver of advisory fee revenue. See the full <strong>Assets Under Management (AUM)</strong> term for complete details.</p>"""

OVERVIEWS["var-abbr"] = """<p><strong>VaR</strong> is a commonly used abbreviation for <em>Value at Risk</em>, a statistical measure of the maximum expected loss on a portfolio at a given confidence level and time horizon. Meridian uses historical simulation with 99% confidence. See the full <strong>Value at Risk (VaR)</strong> term for complete details.</p>"""

OVERVIEWS["sar-abbr"] = """<p><strong>SAR</strong> is a commonly used abbreviation for <em>Suspicious Activity Report</em>, a FinCEN filing (Form 111) required when the bank detects suspected financial crime. SAR filings are confidential and must be submitted within 30 days of detection. See the full <strong>Suspicious Activity Report (SAR)</strong> term for complete details.</p>"""

OVERVIEWS["ctr-abbr"] = """<p><strong>CTR</strong> is a commonly used abbreviation for <em>Currency Transaction Report</em>, a FinCEN filing (Form 112) required for cash transactions exceeding $10,000 in a single business day. See the full <strong>Currency Transaction Report (CTR)</strong> term for complete details.</p>"""

OVERVIEWS["nim-abbr"] = """<p><strong>NIM</strong> is a commonly used abbreviation for <em>Net Interest Margin</em>, the primary profitability metric for banks measuring the interest spread as a percentage of earning assets. See the full <strong>Net Interest Margin (NIM)</strong> term for complete details.</p>"""

OVERVIEWS["rwa-abbr"] = """<p><strong>RWA</strong> is a commonly used abbreviation for <em>Risk-Weighted Assets</em>, total assets adjusted by Basel III risk weight factors. RWA is the denominator for all capital ratio calculations. See the full <strong>Risk-Weighted Assets (RWA)</strong> term for complete details.</p>"""

OVERVIEWS["acl-abbr"] = """<p><strong>ACL</strong> is a commonly used abbreviation for <em>Allowance for Credit Losses</em>, the balance sheet reserve for expected lifetime credit losses under CECL methodology (ASC 326). See the full <strong>Allowance for Credit Losses (ACL)</strong> term for complete details.</p>"""

OVERVIEWS["ltv-abbr"] = """<p><strong>LTV</strong> is a commonly used abbreviation for <em>Loan-to-Value Ratio</em>, the ratio of loan amount to collateral value. A key underwriting metric for mortgage and real estate lending. See the full <strong>Loan-to-Value Ratio (LTV)</strong> term for complete details.</p>"""

OVERVIEWS["dti-abbr"] = """<p><strong>DTI</strong> is a commonly used abbreviation for <em>Debt-to-Income Ratio</em>, the percentage of gross monthly income consumed by debt payments. A key measure of borrower repayment capacity. See the full <strong>Debt-to-Income Ratio (DTI)</strong> term for complete details.</p>"""


def main():
    cfg = load_config()
    logger.info("Project: %s | Location: %s", cfg["project_id"], cfg["multi_region"])
    logger.info("Total overviews to enrich: %d", len(OVERVIEWS))

    success = 0
    failed = 0

    for i, (term_id, html) in enumerate(OVERVIEWS.items(), 1):
        clean_html = html.strip()
        try:
            set_term_overview(cfg, term_id, clean_html)
            logger.info("  [%d/%d] Updated: %s", i, len(OVERVIEWS), term_id)
            success += 1
        except RuntimeError as e:
            logger.warning("  [%d/%d] FAILED: %s - %s", i, len(OVERVIEWS), term_id, str(e)[:120])
            failed += 1
        # Dataplex API rate limits at ~10 writes/min for catalog resources
        # 6 seconds between calls = 10 calls/min, staying within limits
        time.sleep(6)

    logger.info("=" * 60)
    logger.info("GLOSSARY ENRICHMENT COMPLETE")
    logger.info("  Total terms:    %d", len(OVERVIEWS))
    logger.info("  Succeeded:      %d", success)
    logger.info("  Failed:         %d", failed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
