#!/usr/bin/env python3
"""Authors scripts/01_create_glossary.py and scripts/12_enrich_glossary.py with rich Northwind Retail Group content."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAPPING_PATH = REPO_ROOT / "tools" / "retail_mapping.json"

# 10 L1 + 18 L2 = 28 categories
RETAIL_CATEGORIES = [
    {
        "old_id": "customer-identity",
        "id": "customer-loyalty-identity",
        "display_name": "Retail — Customer & Loyalty Identity",
        "description": "[Retail] Shopper identification, privacy consent verification, marketing opt-in governance, and household linking.",
        "subs": [
            ("kyc-aml", "privacy-fraud-verification", "Retail — Privacy & Fraud Verification", "[Retail] Shopper identity verification, CCPA/CPRA consent governance, and promo abuse monitoring."),
            ("customer-management", "shopper-profile-management", "Retail — Shopper Profile Management", "[Retail] Customer demographics, omnichannel loyalty tiers, household profiles, and lifetime value segmentation."),
        ],
    },
    {
        "old_id": "deposits-accounts",
        "id": "loyalty-store-credit-accounts",
        "display_name": "Retail — Loyalty & Store Credit Accounts",
        "description": "[Retail] Loyalty program tiers, points balances, VIP cashback wallets, gift registries, and store credit protection.",
        "subs": [
            ("account-types", "loyalty-account-types", "Retail — Loyalty Account Types", "[Retail] Points rewards, VIP cashback, store credit wallets, gift registries, and employee perk accounts."),
            ("account-operations", "loyalty-account-operations", "Retail — Loyalty Account Operations", "[Retail] Points accrual, reward redemption servicing, inactivity dormancy, and balance adjustments."),
        ],
    },
    {
        "old_id": "lending-credit",
        "id": "bnpl-store-financing",
        "display_name": "Retail — BNPL & Store Financing",
        "description": "[Retail] Buy-Now-Pay-Later installment plans, private-label store cards, return-risk scoring, and payment delinquency.",
        "subs": [
            ("loan-products", "bnpl-financing-products", "Retail — BNPL & Financing Products", "[Retail] Extended furniture financing, seasonal installment plans, revolving store credit lines, and B2B trade credit."),
            ("credit-risk", "return-default-risk", "Retail — Return & Default Risk Assessment", "[Retail] Loyalty return-risk scores, basket-to-limit ratios, installment delinquency tracking, and write-offs."),
        ],
    },
    {
        "old_id": "cards-payments",
        "id": "tenders-payment-processing",
        "display_name": "Retail — Tenders & Payment Processing",
        "description": "[Retail] Co-branded store cards, digital wallets, POS tender authorization, processor fees, and chargeback disputes.",
        "subs": [
            ("card-products", "payment-tender-products", "Retail — Payment & Tender Products", "[Retail] Co-branded store credit cards, promotional financing rates, payment network fees, and dispute handling."),
            ("payment-processing", "checkout-settlement", "Retail — Checkout & Settlement Processing", "[Retail] Digital wallet settlements, gift card redemptions, high-value refund logs, and POS batch clearing."),
        ],
    },
    {
        "old_id": "wealth-investments",
        "id": "assortment-clienteling",
        "display_name": "Retail — Assortment & VIP Clienteling",
        "description": "[Retail] Curated product assortments, gross merchandise value (GMV), personal styling services, and category performance.",
        "subs": [
            ("portfolio-management", "assortment-planning", "Retail — Assortment Planning", "[Retail] Category assortments, seasonal collections, inventory mix allocation, and sell-through benchmarks."),
            ("advisory-services", "vip-clienteling-services", "Retail — VIP Clienteling Services", "[Retail] Personal stylists, VIP membership tiers, styling service fees, and brand quality standards."),
        ],
    },
    {
        "old_id": "trading-securities",
        "id": "product-catalog-fulfillment",
        "display_name": "Retail — Product Catalog & Order Fulfillment",
        "description": "[Retail] Master SKU catalog, GTIN-13 barcodes, omnichannel order execution, and carrier fulfillment.",
        "subs": [
            ("security-reference", "sku-master-reference", "Retail — SKU Master Reference Data", "[Retail] GTIN-13 barcodes, internal SKU codes, style codes, and product hierarchy classifications."),
            ("trade-execution", "order-fulfillment-execution", "Retail — Order Fulfillment Execution", "[Retail] Omnichannel fulfillment modes (BOPIS, ship-from-store, parcel) and delivery settlement."),
        ],
    },
    {
        "old_id": "risk-management",
        "id": "retail-risk-loss-prevention",
        "display_name": "Retail — Risk & Loss Prevention",
        "description": "[Retail] Inventory shrinkage, markdown exposure, supply chain disruption, stockout risk, and vendor reliability.",
        "subs": [
            ("market-risk", "demand-markdown-risk", "Retail — Demand & Markdown Risk", "[Retail] Markdown value-at-risk, seasonal demand volatility, stockout exposure, and peak-season stress testing."),
            ("operational-risk", "store-shrinkage-risk", "Retail — Store & Shrinkage Risk", "[Retail] Organized retail crime, fulfillment damages, POS outages, and loss prevention controls."),
        ],
    },
    {
        "old_id": "regulatory-compliance",
        "id": "privacy-pci-compliance",
        "display_name": "Retail — Privacy, Consent & PCI Compliance",
        "description": "[Retail] CCPA/CPRA consumer privacy, PCI-DSS payment security, promo-fraud reporting, and supplier compliance.",
        "subs": [
            ("bsa-aml", "promo-fraud-prevention", "Retail — Promo & Coupon Fraud Prevention", "[Retail] Promotional abuse alerts, organized return fraud reports, and denied-party vendor screening."),
            ("capital-regulation", "pci-privacy-governance", "Retail — PCI-DSS & Privacy Governance", "[Retail] PCI-DSS v4.0 compliance, working capital ratios, peak-season resilience, and annual omnichannel filings."),
        ],
    },
    {
        "old_id": "financial-reporting",
        "id": "retail-financial-reporting",
        "display_name": "Retail — Retail Financial Reporting",
        "description": "[Retail] General ledger, gross margin percentage, store operating expense ratios, ROIC, and markdown reserves.",
        "subs": [
            ("income-statement", "retail-income-statement", "Retail — Store & Channel P&L", "[Retail] Net sales, cost of goods sold (COGS), gross margin, fulfillment expenses, and return allowances."),
            ("balance-sheet", "retail-balance-sheet", "Retail — Inventory & Working Capital", "[Retail] Merchandise inventory valuation, risk-adjusted inventory assets, and markdown reserve allowances."),
        ],
    },
    {
        "old_id": "operations-infrastructure",
        "id": "store-omnichannel-operations",
        "display_name": "Retail — Store & Omnichannel Operations",
        "description": "[Retail] Physical retail stores, POS platforms, e-commerce digital channels, and fulfillment network metrics.",
        "subs": [],
    },
]

# 84 Terms: old_id -> (new_id, display_name, new_cat_id, description)
RETAIL_TERMS = {
    "customer-id": (
        "customer-id",
        "[Retail] Customer ID",
        "shopper-profile-management",
        "[Retail] A unique identifier assigned to each shopper within Northwind Retail Group's core POS and e-commerce systems, linking all loyalty accounts, orders, returns, and privacy preferences.",
    ),
    "kyc": (
        "shopper-verification",
        "[Retail] Shopper Identity Verification (SIV)",
        "privacy-fraud-verification",
        "[Retail] The governance process of verifying a shopper's identity, contact validity, and privacy consent status during loyalty enrollment and high-value omnichannel checkout.",
    ),
    "cdd": (
        "standard-shopper-verification",
        "[Retail] Standard Shopper Verification (SSV)",
        "privacy-fraud-verification",
        "[Retail] The foundational verification level applied to all loyalty members, including email/SMS validation, opt-in consent capture, and basic return-abuse screening.",
    ),
    "edd": (
        "enhanced-fraud-review",
        "[Retail] Enhanced Fraud Review (EFR)",
        "privacy-fraud-verification",
        "[Retail] Additional loss-prevention scrutiny applied to high-velocity resellers, high-value luxury orders, and accounts flagged for multi-account promo stacking.",
    ),
    "beneficial-owner": (
        "household-primary-member",
        "[Retail] Household Primary Member",
        "privacy-fraud-verification",
        "[Retail] The primary adult loyalty account holder who manages linked family or household profiles and authorizes shared points pooling and store credit usage.",
    ),
    "pep": (
        "vip-influencer-flag",
        "[Retail] VIP Influencer & Brand Ambassador (VIP)",
        "privacy-fraud-verification",
        "[Retail] A designation for high-profile influencers, press members, or corporate partners whose orders and comped merchandise require specialized attribution and audit controls.",
    ),
    "customer-segment": (
        "customer-segment",
        "[Retail] Customer Loyalty Segment",
        "shopper-profile-management",
        "[Retail] Classification of shoppers into behavioral and spend tiers (Core Shopper, Insider, Premier, VIP) based on annual net spend, order frequency, and channel engagement.",
    ),
    "tin": (
        "member-tin",
        "[Retail] Member Tax / Identity Number (TIN)",
        "shopper-profile-management",
        "[Retail] Sensitive national or tax identifier collected for private-label store card financing, B2B tax-exempt accounts, or affiliate payouts, subject to strict PII masking.",
    ),
    "checking-account": (
        "points-rewards-account",
        "[Retail] Points Rewards Account",
        "loyalty-account-types",
        "[Retail] The primary everyday Northwind loyalty account that accrues redeemable points on qualifying in-store POS and digital e-commerce purchases.",
    ),
    "savings-account": (
        "vip-cashback-account",
        "[Retail] VIP Cashback Account",
        "loyalty-account-types",
        "[Retail] A tier-upgraded loyalty wallet that earns percentage cashback rewards and exclusive seasonal bonus multipliers for high-spend omnichannel members.",
    ),
    "certificate-of-deposit": (
        "gift-registry-account",
        "[Retail] Gift Registry & Milestone Account",
        "loyalty-account-types",
        "[Retail] A dedicated event-driven retail account (wedding, baby, or housewarming registry) with completion discount milestones and group gifting credits.",
    ),
    "money-market-account": (
        "store-credit-wallet",
        "[Retail] Store Credit Wallet",
        "loyalty-account-types",
        "[Retail] A digital value wallet holding merchandise return credits, price-adjustment credits, and promotional gift balances redeemable across POS and web checkout.",
    ),
    "fdic-coverage": (
        "store-credit-protection",
        "[Retail] Store Credit Balance Protection",
        "loyalty-account-types",
        "[Retail] Consumer protection and state escheatment compliance guaranteeing that gift card and store credit balances do not expire and remain safeguarded against unauthorized use.",
    ),
    "dormant-account": (
        "dormant-loyalty-account",
        "[Retail] Dormant Loyalty Account",
        "loyalty-account-operations",
        "[Retail] A loyalty or store credit account with no qualifying purchase, point accrual, or redemption activity for 12 or more consecutive months.",
    ),
    "account-balance": (
        "loyalty-account-balance",
        "[Retail] Loyalty & Store Credit Balance",
        "loyalty-account-operations",
        "[Retail] The current dollar-equivalent value of accrued loyalty points, cashback rewards, and unredeemed store credit available in a member's account.",
    ),
    "mortgage": (
        "extended-furniture-bnpl",
        "[Retail] Extended Home & Furniture BNPL Plan",
        "bnpl-financing-products",
        "[Retail] Multi-month installment financing originated for high-ticket home furnishings and appliance purchases across Northwind flagship stores and digital channels.",
    ),
    "auto-loan": (
        "seasonal-wardrobe-bnpl",
        "[Retail] Seasonal Apparel Pay-in-4 Plan",
        "bnpl-financing-products",
        "[Retail] Short-term four-installment Buy-Now-Pay-Later financing used for apparel, footwear, and seasonal basket checkouts with zero interest when paid on schedule.",
    ),
    "heloc": (
        "revolving-store-card-line",
        "[Retail] Revolving Store Credit Line",
        "bnpl-financing-products",
        "[Retail] An open-end private-label store credit line allowing approved loyalty members to revolve balances up to their assigned store credit limit.",
    ),
    "commercial-loan": (
        "b2b-corporate-trade-account",
        "[Retail] B2B Corporate & Hospitality Trade Account",
        "bnpl-financing-products",
        "[Retail] Net-30/60 commercial credit facility extended to interior designers, hospitality buyers, and corporate gifting clients purchasing in bulk.",
    ),
    "fico-score": (
        "loyalty-return-risk-score",
        "[Retail] Loyalty & Return-Risk Score",
        "return-default-risk",
        "[Retail] A composite behavioral score ranging from 300 to 850 that evaluates a shopper's payment reliability, return-abuse propensity, and BNPL eligibility.",
    ),
    "ltv-ratio": (
        "basket-to-limit-ratio",
        "[Retail] Basket-to-Credit-Limit Ratio (BLR)",
        "return-default-risk",
        "[Retail] The ratio of a financed BNPL order amount to the shopper's approved store financing limit, used to guard against over-extension at checkout.",
    ),
    "dti-ratio": (
        "installment-to-spend-ratio",
        "[Retail] Installment-to-Spend Ratio (ISR)",
        "return-default-risk",
        "[Retail] The proportion of a member's historical monthly retail spend committed to active BNPL installment obligations.",
    ),
    "delinquency": (
        "installment-delinquency",
        "[Retail] BNPL Installment Delinquency",
        "return-default-risk",
        "[Retail] The status of a BNPL plan or store card account with one or more missed scheduled installment payments, tracked by aging buckets (30, 60, 90+ days past due).",
    ),
    "risk-rating": (
        "shopper-risk-tier",
        "[Retail] Shopper Fraud & Return Risk Tier",
        "return-default-risk",
        "[Retail] An internal classification (Low, Moderate, Elevated, High Risk) reflecting a shopper's combined installment default risk and wardrobing/return-fraud profile.",
    ),
    "charge-off": (
        "bnpl-bad-debt-writeoff",
        "[Retail] BNPL Bad-Debt Write-Off",
        "return-default-risk",
        "[Retail] An uncollectible BNPL installment or store credit balance (typically 120+ days past due) removed from active receivables and recognized as bad-debt expense.",
    ),
    "credit-card": (
        "cobranded-store-card",
        "[Retail] Northwind Co-Branded Store Card",
        "payment-tender-products",
        "[Retail] A payment card issued to loyalty members offering accelerated reward points, exclusive promotional financing, and free expedited shipping.",
    ),
    "apr": (
        "promotional-financing-apr",
        "[Retail] Promotional Financing APR",
        "payment-tender-products",
        "[Retail] The annualized financing rate applied to revolving store card balances or extended BNPL installment plans outside promotional 0% periods.",
    ),
    "interchange-fee": (
        "payment-processing-fee",
        "[Retail] Payment Network Processing Fee",
        "payment-tender-products",
        "[Retail] Transaction fee paid by Northwind Retail Group to card networks and digital wallet providers for authorizing and settling customer checkout tenders.",
    ),
    "chargeback": (
        "order-dispute-chargeback",
        "[Retail] Order Dispute & Chargeback",
        "payment-tender-products",
        "[Retail] A payment reversal initiated by a shopper's card issuer due to claimed non-delivery, unauthorized checkout, or return refund disputes.",
    ),
    "ach": (
        "digital-wallet-settlement",
        "[Retail] Digital Wallet & Direct Pay Settlement",
        "checkout-settlement",
        "[Retail] Electronic batch clearing used for direct account-to-account checkouts, vendor invoice disbursements, and automated BNPL installment drafts.",
    ),
    "wire-transfer": (
        "high-value-refund-payout",
        "[Retail] High-Value Refund & B2B Payout",
        "checkout-settlement",
        "[Retail] Priority electronic settlement used for large B2B trade refunds, commercial vendor settlements, and high-ticket luxury order adjustments.",
    ),
    "ctr": (
        "high-value-cash-refund-log",
        "[Retail] High-Value Cash & Gift Card Log (HCRL)",
        "checkout-settlement",
        "[Retail] Mandatory loss-prevention compliance record generated for high-dollar cash refunds, bulk gift card purchases, or non-receipted merchandise returns.",
    ),
    "aum": (
        "gross-merchandise-value",
        "[Retail] Gross Merchandise Value (GMV)",
        "assortment-planning",
        "[Retail] The total retail dollar value of merchandise sold across store POS and e-commerce channels or managed within curated seasonal assortments prior to returns and discounts.",
    ),
    "portfolio": (
        "merchandise-assortment",
        "[Retail] Merchandise Assortment Collection",
        "assortment-planning",
        "[Retail] A curated grouping of product SKUs managed for a specific season, store format, or digital campaign to achieve target revenue and gross margin goals.",
    ),
    "asset-allocation": (
        "category-inventory-mix",
        "[Retail] Category Inventory Allocation Mix",
        "assortment-planning",
        "[Retail] The strategic distribution of open-to-buy inventory budget across product divisions (Apparel, Footwear, Home, Accessories, Beauty) and fulfillment channels.",
    ),
    "benchmark": (
        "category-comp-benchmark",
        "[Retail] Category Comp-Sales Benchmark",
        "assortment-planning",
        "[Retail] A reference performance index (such as comparable store sales growth or category sell-through target) used to evaluate assortment productivity.",
    ),
    "alpha": (
        "comp-sales-outperformance",
        "[Retail] Comp-Sales Outperformance (Alpha)",
        "assortment-planning",
        "[Retail] The excess sell-through or gross margin rate achieved by a curated assortment relative to its category comp-sales benchmark.",
    ),
    "sharpe-ratio": (
        "gmroi-ratio",
        "[Retail] Gross Margin Return on Inventory Investment (GMROI)",
        "assortment-planning",
        "[Retail] A core retail productivity metric measuring how many gross margin dollars are generated for every dollar invested in average on-hand inventory.",
    ),
    "financial-advisor": (
        "personal-stylist-merchant",
        "[Retail] Personal Stylist & Category Merchant",
        "vip-clienteling-services",
        "[Retail] A dedicated clienteling specialist or category buyer who curates personalized wardrobes and seasonal assortments for VIP loyalty members.",
    ),
    "advisory-fee": (
        "styling-membership-fee",
        "[Retail] VIP Styling & Concierge Fee",
        "vip-clienteling-services",
        "[Retail] Service fee charged for bespoke personal styling boxes, private appointment tailoring, or premium annual membership benefits (often credited toward purchase).",
    ),
    "fiduciary-duty": (
        "brand-quality-standard",
        "[Retail] Brand Quality & Ethical Sourcing Standard",
        "vip-clienteling-services",
        "[Retail] Northwind Retail Group's commitment to product authenticity, transparent pricing, and ethical supplier compliance across all private-label and partner brands.",
    ),
    "accredited-investor": (
        "vip-private-client",
        "[Retail] VIP Private Client Tier",
        "vip-clienteling-services",
        "[Retail] Top-tier omnichannel shoppers exceeding annual spend thresholds who qualify for early collection access, private showroom appointments, and dedicated stylists.",
    ),
    "cusip": (
        "gtin-13",
        "[Retail] GTIN-13 Barcode",
        "sku-master-reference",
        "[Retail] A 13-digit GS1 Global Trade Item Number barcode that uniquely identifies a trade item (product style, color, and size) across POS scanners and warehouse systems.",
    ),
    "isin": (
        "sku-code",
        "[Retail] Master SKU Code",
        "sku-master-reference",
        "[Retail] Northwind Retail Group's standardized internal Stock Keeping Unit identifier (format NW-SKU-NNNNNN) linking catalog attributes, pricing, and inventory positions.",
    ),
    "ticker-symbol": (
        "style-code",
        "[Retail] Vendor Style Code",
        "sku-master-reference",
        "[Retail] A concise alphanumeric designator representing a parent product style across size and color variants in the HELIOS catalog.",
    ),
    "trade-settlement": (
        "order-fulfillment-settlement",
        "[Retail] Order Fulfillment & Carrier Settlement",
        "order-fulfillment-execution",
        "[Retail] The end-to-end completion of an omnichannel customer order, from inventory allocation and pick-pack-ship through carrier delivery confirmation and payment capture.",
    ),
    "order-type": (
        "fulfillment-channel-type",
        "[Retail] Omnichannel Fulfillment Mode",
        "order-fulfillment-execution",
        "[Retail] The fulfillment path selected at checkout, such as In-Store POS, Standard Parcel, Expedited Air, Buy-Online-Pick-Up-In-Store (BOPIS), or Ship-from-Store.",
    ),
    "var": (
        "markdown-value-at-risk",
        "[Retail] Markdown Value at Risk (MVaR)",
        "demand-markdown-risk",
        "[Retail] A statistical estimate of potential gross margin erosion on seasonal inventory over a given holding period under adverse sell-through conditions.",
    ),
    "credit-risk": (
        "return-and-default-risk",
        "[Retail] Return Abuse & BNPL Default Risk",
        "return-default-risk",
        "[Retail] The potential for revenue and margin loss stemming from customer BNPL installment defaults, serial wardrobing, or fraudulent non-receipted returns.",
    ),
    "market-risk": (
        "seasonal-demand-risk",
        "[Retail] Seasonal Demand & Price Elasticity Risk",
        "demand-markdown-risk",
        "[Retail] The risk of margin compression or excess aged inventory resulting from shifts in consumer trends, weather anomalies, or competitor promotional discounting.",
    ),
    "operational-risk": (
        "inventory-shrinkage-risk",
        "[Retail] Inventory Shrinkage & Fulfillment Risk",
        "store-shrinkage-risk",
        "[Retail] The risk of financial loss from store shoplifting, warehouse damage, carrier lost-in-transit parcels, or POS/e-commerce system disruptions.",
    ),
    "liquidity-risk": (
        "stockout-working-capital-risk",
        "[Retail] Stockout & Working Capital Liquidity Risk",
        "demand-markdown-risk",
        "[Retail] The risk that fast-turning SKUs run out of stock in key fulfillment nodes or that slow-moving inventory ties up seasonal open-to-buy working capital.",
    ),
    "counterparty-risk": (
        "supplier-delivery-risk",
        "[Retail] Supplier Lead-Time & Compliance Risk",
        "demand-markdown-risk",
        "[Retail] The risk that a merchandise vendor fails to meet purchase order delivery windows, quality specifications, or ethical sourcing attestations.",
    ),
    "stress-testing": (
        "peak-demand-stress-testing",
        "[Retail] Peak-Season Demand Stress Testing",
        "demand-markdown-risk",
        "[Retail] Simulation of Black Friday / Cyber Monday traffic surges, port delays, and markdown scenarios to verify supply chain capacity and margin resilience.",
    ),
    "sar": (
        "promo-abuse-incident-report",
        "[Retail] Promo & Return Abuse Incident Report (PAIR)",
        "promo-fraud-prevention",
        "[Retail] An internal loss-prevention investigation filing documenting organized return fraud, coupon stacking exploits, or stolen tender rings.",
    ),
    "aml": (
        "promo-fraud-program",
        "[Retail] Anti-Promo & Return Abuse Program (APRA)",
        "promo-fraud-prevention",
        "[Retail] Automated rules, velocity controls, and loss-prevention workflows designed to detect and block coupon abuse, serial wardrobing, and gift card laundering.",
    ),
    "bsa": (
        "retail-loss-prevention-policy",
        "[Retail] Enterprise Loss Prevention & Refund Policy",
        "promo-fraud-prevention",
        "[Retail] Northwind Retail Group's governance framework requiring receipt verification, ID capture on high-value returns, and audit logging of manual price overrides.",
    ),
    "ofac-screening": (
        "denied-party-vendor-screening",
        "[Retail] Denied-Party & Sanctioned Vendor Screening",
        "promo-fraud-prevention",
        "[Retail] Automated compliance screening of international merchandise suppliers, freight forwarders, and cross-border orders against trade restriction lists.",
    ),
    "basel-iii": (
        "pci-dss-v4-framework",
        "[Retail] PCI-DSS v4.0 & Retail Governance Framework",
        "pci-privacy-governance",
        "[Retail] International payment card security and retail working-capital governance standards ensuring tokenization of cardholder data and healthy inventory liquidity buffers.",
    ),
    "cet1-ratio": (
        "core-working-capital-ratio",
        "[Retail] Core Working Capital Ratio (CWCR)",
        "pci-privacy-governance",
        "[Retail] Northwind Retail Group's primary liquidity adequacy metric, comparing liquid cash and core fast-turning inventory against risk-adjusted inventory and lease commitments.",
    ),
    "dfast": (
        "holiday-peak-readiness-test",
        "[Retail] Holiday Peak Readiness Stress Test (HPRST)",
        "pci-privacy-governance",
        "[Retail] Annual enterprise simulation testing omnichannel fulfillment throughput, inventory working capital, and payment gateway stability under peak Q4 holiday loads.",
    ),
    "call-report": (
        "pci-aoc-compliance-filing",
        "[Retail] Quarterly PCI-DSS AOC & Privacy Filing",
        "pci-privacy-governance",
        "[Retail] Formal quarterly compliance attestation summarizing payment card tokenization coverage, CCPA/CPRA DSAR fulfillment SLAs, and channel revenue reconciliation.",
    ),
    "net-interest-margin": (
        "gross-margin-percentage",
        "[Retail] Gross Margin Percentage (GM%)",
        "retail-income-statement",
        "[Retail] Net merchandise sales minus cost of goods sold (COGS) and freight, expressed as a percentage of net sales across stores and digital channels.",
    ),
    "efficiency-ratio": (
        "store-opex-efficiency-ratio",
        "[Retail] Store Operating Expense Ratio",
        "retail-income-statement",
        "[Retail] Store payroll, occupancy, and fulfillment operating expenses divided by net omnichannel revenue, measuring operational cost discipline (lower is better).",
    ),
    "roaa": (
        "return-on-invested-capital",
        "[Retail] Return on Retail Assets (RORA)",
        "retail-income-statement",
        "[Retail] Net retail operating income divided by average store leasehold, fulfillment technology, and merchandise inventory assets.",
    ),
    "provision-for-credit-losses": (
        "return-and-markdown-allowance",
        "[Retail] Provision for Returns & Markdowns",
        "retail-income-statement",
        "[Retail] Income statement reserve expense set aside for anticipated post-holiday customer returns, BNPL bad debt, and end-of-season clearance markdowns.",
    ),
    "general-ledger": (
        "general-ledger",
        "[Retail] Retail General Ledger (SAP HELIOS GL)",
        "retail-balance-sheet",
        "[Retail] The master accounting system of record in SAP S/4HANA Retail (HELIOS) capturing all store POS sales, e-commerce settlements, inventory receipts, and operating expenses.",
    ),
    "risk-weighted-assets": (
        "risk-adjusted-inventory-assets",
        "[Retail] Risk-Adjusted Inventory Assets (RAIA)",
        "retail-balance-sheet",
        "[Retail] Total on-hand and in-transit merchandise inventory weighted by seasonal obsolescence, markdown velocity, and shrinkage risk factors.",
    ),
    "allowance-for-credit-losses": (
        "inventory-obsolescence-reserve",
        "[Retail] Inventory Obsolescence & Return Reserve (IOR)",
        "retail-balance-sheet",
        "[Retail] Contra-asset balance sheet valuation reserve estimating future inventory shrinkage, clearance write-downs, and uncollectible BNPL receivables.",
    ),
    "branch": (
        "retail-store-location",
        "[Retail] Retail Store Location",
        "store-omnichannel-operations",
        "[Retail] A physical Northwind specialty retail storefront (Flagship, Mall, Lifestyle Center, or Outlet) equipped with ORION POS terminals and BOPIS/Ship-from-Store fulfillment.",
    ),
    "core-banking-system": (
        "core-pos-commerce-platform",
        "[Retail] Core POS & Omnichannel Commerce Platform",
        "store-omnichannel-operations",
        "[Retail] The mission-critical transaction engines powering Northwind Retail Group: ORION (in-store NCR POS), LUMEN (Salesforce Commerce Cloud), and HELIOS (SAP S/4HANA Retail ERP).",
    ),
    "digital-channel": (
        "digital-commerce-channel",
        "[Retail] Digital & Mobile Commerce Channel",
        "store-omnichannel-operations",
        "[Retail] Northwind's e-commerce website, iOS/Android mobile shopping app, and in-store endless-aisle kiosks enabling 24/7 browsing, checkout, and loyalty management.",
    ),
    "kyc-abbr": (
        "siv-abbr",
        "[Retail] SIV",
        "privacy-fraud-verification",
        "[Retail] Abbreviation for Shopper Identity Verification, the process of validating customer identity and privacy consent status.",
    ),
    "cdd-abbr": (
        "ssv-abbr",
        "[Retail] SSV",
        "privacy-fraud-verification",
        "[Retail] Abbreviation for Standard Shopper Verification, the initial contact and consent check performed at loyalty enrollment.",
    ),
    "edd-abbr": (
        "efr-abbr",
        "[Retail] EFR",
        "privacy-fraud-verification",
        "[Retail] Abbreviation for Enhanced Fraud Review, the elevated loss-prevention review applied to high-risk orders and bulk resellers.",
    ),
    "aum-abbr": (
        "gmv-abbr",
        "[Retail] GMV",
        "assortment-planning",
        "[Retail] Abbreviation for Gross Merchandise Value, the total retail dollar value of merchandise sold across omnichannel touchpoints.",
    ),
    "var-abbr": (
        "mvar-abbr",
        "[Retail] MVaR",
        "demand-markdown-risk",
        "[Retail] Abbreviation for Markdown Value at Risk, the statistical measure of potential seasonal margin erosion.",
    ),
    "sar-abbr": (
        "pair-abbr",
        "[Retail] PAIR",
        "promo-fraud-prevention",
        "[Retail] Abbreviation for Promo & Return Abuse Incident Report, an internal loss-prevention filing for organized retail fraud.",
    ),
    "ctr-abbr": (
        "hcrl-abbr",
        "[Retail] HCRL",
        "checkout-settlement",
        "[Retail] Abbreviation for High-Value Cash & Gift Card Log, a mandatory audit log for large cash refunds or bulk gift card activity.",
    ),
    "nim-abbr": (
        "gm-abbr",
        "[Retail] GM%",
        "retail-income-statement",
        "[Retail] Abbreviation for Gross Margin Percentage, measuring net sales minus cost of goods sold divided by net sales.",
    ),
    "rwa-abbr": (
        "raia-abbr",
        "[Retail] RAIA",
        "retail-balance-sheet",
        "[Retail] Abbreviation for Risk-Adjusted Inventory Assets, weighting inventory balances by obsolescence and markdown risk.",
    ),
    "acl-abbr": (
        "ior-abbr",
        "[Retail] IOR",
        "retail-balance-sheet",
        "[Retail] Abbreviation for Inventory Obsolescence & Return Reserve, the balance sheet contra-asset reserve for shrinkage and markdowns.",
    ),
    "ltv-abbr": (
        "blr-abbr",
        "[Retail] BLR",
        "return-default-risk",
        "[Retail] Abbreviation for Basket-to-Credit-Limit Ratio, comparing a financed order total against the member's BNPL credit limit.",
    ),
    "dti-abbr": (
        "isr-abbr",
        "[Retail] ISR",
        "return-default-risk",
        "[Retail] Abbreviation for Installment-to-Spend Ratio, measuring active BNPL installment commitments relative to monthly retail spend.",
    ),
}

RETAIL_CONTACTS = {
    "customer-loyalty-identity": ("Privacy & Consent Data Steward", "privacy-steward@northwindretail.com", "Chief Privacy Officer", "cpo@northwindretail.com"),
    "loyalty-store-credit-accounts": ("Loyalty Operations Steward", "loyalty-ops@northwindretail.com", "VP of Loyalty & CRM", "vp-loyalty@northwindretail.com"),
    "bnpl-store-financing": ("Store Financing Data Steward", "bnpl-data@northwindretail.com", "VP of Customer Financing", "vp-financing@northwindretail.com"),
    "tenders-payment-processing": ("POS & Payments Steward", "payments-ops@northwindretail.com", "Head of Omnichannel Checkout", "checkout-head@northwindretail.com"),
    "assortment-clienteling": ("Assortment Data Steward", "assortment-data@northwindretail.com", "Chief Merchant Officer", "cmo-merch@northwindretail.com"),
    "product-catalog-fulfillment": ("Catalog & SKU Master Steward", "catalog-steward@northwindretail.com", "VP of Supply Chain & Fulfillment", "vp-supplychain@northwindretail.com"),
    "retail-risk-loss-prevention": ("Loss Prevention Data Steward", "lp-data@northwindretail.com", "VP of Asset Protection", "vp-assetprotection@northwindretail.com"),
    "privacy-pci-compliance": ("Compliance & PCI Steward", "pci-compliance@northwindretail.com", "Chief Compliance Officer", "cco@northwindretail.com"),
    "retail-financial-reporting": ("Retail Finance Data Steward", "finance-data@northwindretail.com", "Chief Financial Officer", "cfo@northwindretail.com"),
    "store-omnichannel-operations": ("Store Operations Data Steward", "store-ops@northwindretail.com", "Chief Stores Officer", "cso@northwindretail.com"),
}


def build_rich_overview(term_id: str, display_name: str, cat_id: str, short_desc: str) -> str:
    clean_title = display_name.replace("[Retail] ", "")
    clean_desc = short_desc.replace("[Retail] ", "")
    if term_id.endswith("-abbr"):
        return (
            f"<p><strong>[Retail] {clean_title}</strong>: {clean_desc}</p>"
            f"<p>Used across Northwind Retail Group's ORION (Store POS), LUMEN (Digital Commerce), "
            f"and HELIOS (SAP S/4HANA Retail ERP) reporting layers and governed in Google Cloud Knowledge Catalog.</p>"
        )
    return f"""<h3>[Retail] Business Definition</h3>
<p>{clean_desc}</p>

<h3>Northwind Retail Group Operational Context</h3>
<p>At Northwind Retail Group (~1,200 specialty stores and e-commerce across North America), <strong>{clean_title}</strong> is a core governed business concept within the <em>{cat_id}</em> domain. Data for this concept is captured across our omnichannel estate—<strong>ORION</strong> (NCR POS on IBM i), <strong>LUMEN</strong> (Salesforce Commerce Cloud), and <strong>HELIOS</strong> (SAP S/4HANA Retail)—and standardized through the BigQuery medallion architecture (<code>retail_bronze</code> &rarr; <code>retail_silver</code> &rarr; <code>retail_gold</code>).</p>

<h3>Data Governance &amp; Quality Standards</h3>
<ul>
  <li><strong>System of Record:</strong> Validated during silver-layer standardization with automated Dataplex Data Quality scans.</li>
  <li><strong>Catalog Lineage:</strong> Linked directly to physical BigQuery columns via Knowledge Catalog definition links and governed under Northwind Retail Group's data stewardship policies.</li>
  <li><strong>Compliance &amp; Privacy:</strong> Subject to Northwind's PCI-DSS v4.0, CCPA/CPRA, and GDPR data classification and retention controls where applicable.</li>
</ul>"""


def main() -> None:
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    # Update mapping json with the exact category and term ID maps
    cat_map = {}
    for c in RETAIL_CATEGORIES:
        cat_map[c["old_id"]] = c["id"]
        for old_sub, new_sub, _, _ in c["subs"]:
            cat_map[old_sub] = new_sub
    term_map = {old_k: v[0] for old_k, v in RETAIL_TERMS.items()}
    mapping["glossary_categories"] = cat_map
    mapping["glossary_terms"] = term_map
    MAPPING_PATH.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")

    # Parse original HEAD:scripts/01_create_glossary.py to extract SYNONYM_LINKS, RELATED_LINKS, DEFINITION_LINKS
    orig_01 = subprocess.check_output(["git", "show", "HEAD:scripts/01_create_glossary.py"], text=True)
    tree = ast.parse(orig_01)
    orig_syn, orig_rel, orig_def = [], [], []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            name = getattr(node.targets[0], "id", "")
            if name == "SYNONYM_LINKS":
                orig_syn = ast.literal_eval(node.value)
            elif name == "RELATED_LINKS":
                orig_rel = ast.literal_eval(node.value)
            elif name == "DEFINITION_LINKS":
                orig_def = ast.literal_eval(node.value)

    new_syn = [(term_map.get(a, "promo-fraud-program"), term_map.get(b, "promo-fraud-program")) for a, b in orig_syn]
    new_rel = [(term_map[a], term_map[b]) for a, b in orig_rel]

    ds_map = mapping["datasets"]
    tbl_map = mapping["tables"]
    col_map = mapping["columns"]

    new_def = []
    for old_term, old_ds, old_tbl, old_col in orig_def:
        nt = term_map[old_term]
        nds = ds_map.get(old_ds, old_ds)
        ntbl = tbl_map.get(old_tbl, old_tbl)
        ncol = col_map.get(old_col, old_col) if old_col else None
        new_def.append((nt, nds, ntbl, ncol))

    # Build CATEGORIES structure for 01_create_glossary.py
    cats_out = []
    for c in RETAIL_CATEGORIES:
        cats_out.append({
            "id": c["id"],
            "display_name": c["display_name"],
            "description": c["description"],
            "subs": [(s_id, s_disp, s_desc) for _, s_id, s_disp, s_desc in c["subs"]],
        })

    terms_out = [RETAIL_TERMS[k] for k in RETAIL_TERMS]
    overviews_out = {
        t_id: build_rich_overview(t_id, disp, cat_id, desc)
        for t_id, disp, cat_id, desc in terms_out
    }

    # Read current 01_create_glossary.py header/functions up to '# Data definitions' and footer from 'def create_definition_link'
    cur_01 = (REPO_ROOT / "scripts" / "01_create_glossary.py").read_text(encoding="utf-8")
    header_split = "# Data definitions\n# ---------------------------------------------------------------------------"
    footer_split = "def create_definition_link("
    header_part = cur_01.split(header_split)[0] + header_split + "\n\n"
    footer_part = "def create_definition_link(" + cur_01.split(footer_split)[1]

    # Fix description in create_glossary in header_part
    header_part = header_part.replace(
        '"Comprehensive business glossary for Northwind Retail Group covering "\n            "retail retail, loyalty management, lending, risk, compliance, and financial reporting."',
        '"[Retail] Comprehensive business glossary for Northwind Retail Group covering "\n            "omnichannel store operations, loyalty & CRM, BNPL financing, merchandising, supply chain, and privacy/PCI compliance."',
    )

    body_01 = (
        f"CATEGORIES = {json.dumps(cats_out, indent=4)}\n\n"
        f"CONTACTS = {repr(RETAIL_CONTACTS)}\n\n"
        "_L2_TO_L1 = {}\n"
        "for cat in CATEGORIES:\n"
        "    for sub_id, _, _ in cat['subs']:\n"
        "        _L2_TO_L1[sub_id] = cat['id']\n"
        "    _L2_TO_L1[cat['id']] = cat['id']\n\n"
        "def _contacts_for(category_id):\n"
        "    l1 = _L2_TO_L1.get(category_id, category_id)\n"
        "    return CONTACTS[l1]\n\n"
        f"TERMS = {repr(terms_out)}\n\n"
        f"OVERVIEWS = {repr(overviews_out)}\n\n"
        f"SYNONYM_LINKS = {repr(new_syn)}\n\n"
        f"RELATED_LINKS = {repr(new_rel)}\n\n"
        f"DEFINITION_LINKS = {repr(new_def)}\n\n\n"
    )

    (REPO_ROOT / "scripts" / "01_create_glossary.py").write_text(header_part + body_01 + footer_part, encoding="utf-8")

    # Now write scripts/12_enrich_glossary.py
    enrich_code = f'''#!/usr/bin/env python3
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
Enriches ALL 84 glossary term overviews with rich, detailed HTML content for Northwind Retail Group.

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
        f"projects/{{pn}}/locations/{{loc}}/entryGroups/@dataplex/entries/"
        f"projects/{{pn}}/locations/{{loc}}/glossaries/{{GLOSSARY_ID}}/terms/{{term_id}}"
    )


def set_term_overview(cfg, term_id, html):
    entry = _entry_path(cfg, term_id)
    url = (
        f"{{BASE_URL}}/{{entry}}"
        "?updateMask=aspects&deleteMissingAspects=false"
        "&aspect_keys=dataplex-types.global.overview"
    )
    body = {{
        "aspects": {{
            "dataplex-types.global.overview": {{
                "aspectType": "projects/dataplex-types/locations/global/aspectTypes/overview",
                "data": {{"content": html}},
            }}
        }}
    }}
    api_call(url, "PATCH", body)


OVERVIEWS = {repr(overviews_out)}


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
        time.sleep(6)

    logger.info("=" * 60)
    logger.info("GLOSSARY ENRICHMENT COMPLETE")
    logger.info("  Total terms:    %d", len(OVERVIEWS))
    logger.info("  Succeeded:      %d", success)
    logger.info("  Failed:         %d", failed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
'''
    (REPO_ROOT / "scripts" / "12_enrich_glossary.py").write_text(enrich_code, encoding="utf-8")
    print(f"Generated 01_create_glossary.py ({len(cats_out)} L1, {len(terms_out)} terms, {len(new_def)} def links) and 12_enrich_glossary.py ({len(overviews_out)} overviews).")


if __name__ == "__main__":
    main()
