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
Simulates realistic FSI analyst query workload across 5 personas.

Usage:
    python3 09_simulate_queries.py                    # 1 iteration
    python3 09_simulate_queries.py --iterations 100   # 100 iterations
"""

import argparse
import logging
import random
import time

from common import load_config, get_access_token, BQ_URL
import requests as http_requests

logger = logging.getLogger(__name__)


def run_query(cfg, sql, persona, query_name):
    url = f"{BQ_URL}/projects/{cfg['project_id']}/jobs"
    body = {
        "configuration": {
            "query": {"query": sql, "useLegacySql": False},
            "labels": {"persona": persona, "query_name": query_name.replace(" ", "_").lower()[:63], "simulation": "fsi_workload"},
        }
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {get_access_token()}"}
    try:
        resp = http_requests.post(url, json=body, headers=headers)
        return resp.status_code in (200, 201)
    except Exception:
        return False


def build_queries(pid):
    S = f"`{pid}.fsi_silver"
    G = f"`{pid}.fsi_gold"
    queries = []

    # Retail Analyst
    queries.append(("retail_analyst", "Customer lookup", f"SELECT * FROM {S}.silver_customers` WHERE customer_id = 'CUST-{random.randint(1,20000):08d}'"))
    queries.append(("retail_analyst", "Top depositors", f"SELECT customer_id, customer_segment, total_deposit_balance FROM {G}.gold_customer_360` ORDER BY total_deposit_balance DESC LIMIT 20"))
    queries.append(("retail_analyst", "Account dormancy", f"SELECT account_type, COUNT(*) AS cnt FROM {G}.gold_account_summary` WHERE is_dormant GROUP BY 1"))
    queries.append(("retail_analyst", "Branch performance", f"SELECT branch_name, region, total_deposits, total_loans, deposits_per_employee FROM {G}.gold_branch_performance` ORDER BY total_deposits DESC LIMIT 20"))
    queries.append(("retail_analyst", "Transaction patterns", f"SELECT channel, merchant_category, transaction_count, total_amount FROM {G}.gold_transaction_patterns` WHERE month >= '2024-06-01' ORDER BY total_amount DESC LIMIT 20"))

    # Credit Risk
    queries.append(("credit_risk", "Loan portfolio", f"SELECT loan_type, risk_rating, loan_count, total_outstanding, delinquency_rate_pct FROM {G}.gold_loan_portfolio_summary` ORDER BY total_outstanding DESC"))
    queries.append(("credit_risk", "Delinquency by type", f"SELECT loan_type, delinquency_status, loan_count, total_balance FROM {G}.gold_delinquency_analysis` ORDER BY total_balance DESC"))
    queries.append(("credit_risk", "FICO distribution", f"SELECT CASE WHEN fico_score_at_origination >= 800 THEN '800+' WHEN fico_score_at_origination >= 740 THEN '740-799' WHEN fico_score_at_origination >= 670 THEN '670-739' WHEN fico_score_at_origination >= 580 THEN '580-669' ELSE '<580' END AS fico_band, COUNT(*) AS cnt FROM {S}.silver_loans` GROUP BY 1 ORDER BY 1"))
    queries.append(("credit_risk", "CRE concentration", f"SELECT naics_code, loan_count, total_balance FROM {G}.gold_delinquency_analysis` WHERE loan_type = 'COMMERCIAL' ORDER BY total_balance DESC"))

    # Wealth Advisor
    queries.append(("wealth_advisor", "Client AUM", f"SELECT wm_client_id, first_name, last_name, client_tier, total_aum FROM {S}.silver_wm_clients` ORDER BY total_aum DESC LIMIT 20"))
    queries.append(("wealth_advisor", "Portfolio performance", f"SELECT portfolio_name, market_value, ytd_return, avg_sharpe_ratio, avg_alpha FROM {G}.gold_portfolio_performance` ORDER BY market_value DESC LIMIT 20"))
    queries.append(("wealth_advisor", "Advisor scorecard", f"SELECT first_name, last_name, total_aum, client_count, avg_portfolio_ytd_return, avg_sharpe_ratio FROM {G}.gold_advisor_scorecard` ORDER BY total_aum DESC LIMIT 10"))
    queries.append(("wealth_advisor", "Asset allocation", f"SELECT asset_class, sector, total_market_value, avg_return_pct FROM {G}.gold_asset_allocation` ORDER BY total_market_value DESC"))
    queries.append(("wealth_advisor", "Fee revenue", f"SELECT fee_type, client_tier, total_fees, avg_fee_rate_bps FROM {G}.gold_fee_revenue` ORDER BY total_fees DESC"))

    # Compliance Officer
    queries.append(("compliance_officer", "Fraud trends", f"SELECT alert_month, alert_type, alert_count, confirmed_fraud_count, false_positive_rate_pct FROM {G}.gold_fraud_analytics` ORDER BY alert_month DESC"))
    queries.append(("compliance_officer", "AML risk", f"SELECT customer_segment, kyc_risk_rating, customer_count, avg_risk_score, sar_filings FROM {G}.gold_aml_risk_scoring` ORDER BY avg_risk_score DESC"))
    queries.append(("compliance_officer", "KYC overdue", f"SELECT due_diligence_level, risk_score_category, COUNT(*) AS total, COUNTIF(review_overdue) AS overdue FROM {S}.silver_kyc_records` GROUP BY 1, 2"))
    queries.append(("compliance_officer", "Large wires", f"SELECT wire_type, beneficiary_country, COUNT(*) AS cnt, SUM(amount) AS total FROM {S}.silver_wire_transfers` WHERE amount >= 10000 GROUP BY 1, 2 ORDER BY total DESC"))
    queries.append(("compliance_officer", "Regulatory dashboard", f"SELECT metric_category, metric_name, metric_value, threshold, status FROM {G}.gold_regulatory_dashboard`"))

    # CFO
    queries.append(("cfo", "NIM by product", f"SELECT product, balance_type, total_balance, avg_interest_rate FROM {G}.gold_net_interest_margin` ORDER BY total_balance DESC"))
    queries.append(("cfo", "Capital adequacy", f"SELECT reporting_date, capital_component, capital_ratio, regulatory_minimum, buffer_above_minimum FROM {G}.gold_capital_adequacy` ORDER BY reporting_date DESC"))
    queries.append(("cfo", "Balance sheet", f"SELECT category, line_item, amount FROM {G}.gold_balance_sheet_summary` ORDER BY category, amount DESC"))
    queries.append(("cfo", "Market risk VaR", f"SELECT asset_class, sector, total_exposure, var_99_1d, var_99_10d FROM {G}.gold_market_risk_var` ORDER BY var_99_10d DESC"))
    queries.append(("cfo", "Total relationship", f"SELECT relationship_tier, COUNT(*) AS cnt, SUM(total_relationship_value) AS total_value FROM `{pid}.fsi_dashboards.vw_customer_total_relationship` GROUP BY 1 ORDER BY total_value DESC"))

    return queries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1)
    args = parser.parse_args()

    cfg = load_config()
    logger.info("Project: %s | Iterations: %d", cfg["project_id"], args.iterations)

    total_ok = 0
    total_fail = 0
    for i in range(1, args.iterations + 1):
        queries = build_queries(cfg["project_id"])
        random.shuffle(queries)
        ok = sum(1 for p, n, s in queries if run_query(cfg, s, p, n))
        fail = len(queries) - ok
        total_ok += ok
        total_fail += fail
        if args.iterations > 1:
            logger.info("Iteration %d/%d: %d ok, %d fail", i, args.iterations, ok, fail)
        time.sleep(0.5)

    logger.info("Query simulation complete: %d succeeded, %d failed", total_ok, total_fail)


if __name__ == "__main__":
    main()
