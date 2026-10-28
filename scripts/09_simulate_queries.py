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
Simulates realistic Retail analyst query workload across 5 personas.

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
            "labels": {"persona": persona, "query_name": query_name.replace(" ", "_").lower()[:63], "simulation": "retail_workload"},
        }
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {get_access_token()}"}
    try:
        resp = http_requests.post(url, json=body, headers=headers)
        return resp.status_code in (200, 201)
    except Exception:
        return False


def build_queries(pid):
    S = f"`{pid}.retail_silver"
    G = f"`{pid}.retail_gold"
    queries = []

    # Persona 1: Merchandising Manager (5 queries)
    queries.append(("merchandising_manager", "VIP member GMV", f"SELECT wm_client_id, first_name, last_name, client_tier, total_aum FROM {S}.silver_vip_members` ORDER BY total_aum DESC LIMIT 20"))
    queries.append(("merchandising_manager", "Assortment performance", f"SELECT assortment_name, market_value, ytd_return, avg_sharpe_ratio, avg_alpha FROM {G}.gold_assortment_performance` ORDER BY market_value DESC LIMIT 20"))
    queries.append(("merchandising_manager", "Category manager scorecard", f"SELECT first_name, last_name, total_aum, client_count, avg_assortment_ytd_return, avg_sharpe_ratio FROM {G}.gold_category_manager_scorecard` ORDER BY total_aum DESC LIMIT 10"))
    queries.append(("merchandising_manager", "Inventory allocation mix", f"SELECT asset_class, sector, total_market_value, avg_return_pct FROM {G}.gold_inventory_allocation` ORDER BY total_market_value DESC"))
    queries.append(("merchandising_manager", "Promo margin impact", f"SELECT fee_type, client_tier, total_fees, avg_fee_rate_bps FROM {G}.gold_promo_margin_impact` ORDER BY total_fees DESC"))

    # Persona 2: Store Operations Director (5 queries)
    queries.append(("store_ops_director", "Store performance ranking", f"SELECT store_name, region, total_pos_revenue, total_bnpl_originations, sales_per_associate FROM {G}.gold_store_performance` ORDER BY total_pos_revenue DESC LIMIT 20"))
    queries.append(("store_ops_director", "Omnichannel order patterns", f"SELECT channel, merchant_category, transaction_count, total_amount FROM {G}.gold_order_patterns` WHERE month >= '2024-06-01' ORDER BY total_amount DESC LIMIT 20"))
    queries.append(("store_ops_director", "Gross margin by product", f"SELECT product, balance_type, total_balance, avg_interest_rate FROM {G}.gold_gross_margin_analysis` ORDER BY total_balance DESC"))
    queries.append(("store_ops_director", "Retail financial summary", f"SELECT category, line_item, amount FROM {G}.gold_financial_summary` ORDER BY category, amount DESC"))
    queries.append(("store_ops_director", "Store omnichannel view", f"SELECT store_id, store_name, region, store_pos_sales, vip_digital_gmv, combined_assets FROM `{pid}.retail_dashboards.vw_store_omnichannel_performance` ORDER BY combined_assets DESC LIMIT 20"))

    # Persona 3: Loyalty/CRM Marketer (5 queries)
    queries.append(("loyalty_crm_marketer", "Shopper profile lookup", f"SELECT * FROM {S}.silver_customers` WHERE customer_id = 'CUST-{random.randint(1,20000):08d}'"))
    queries.append(("loyalty_crm_marketer", "Top loyalty members", f"SELECT customer_id, customer_segment, total_loyalty_balance FROM {G}.gold_customer_360` ORDER BY total_loyalty_balance DESC LIMIT 20"))
    queries.append(("loyalty_crm_marketer", "Loyalty account dormancy", f"SELECT account_type, COUNT(*) AS cnt FROM {G}.gold_loyalty_account_summary` WHERE is_dormant GROUP BY 1"))
    queries.append(("loyalty_crm_marketer", "Customer lifetime value tiers", f"SELECT relationship_tier, COUNT(*) AS cnt, SUM(total_relationship_value) AS total_value FROM `{pid}.retail_dashboards.vw_customer_lifetime_value` GROUP BY 1 ORDER BY total_value DESC"))
    queries.append(("loyalty_crm_marketer", "Return risk score bands", f"SELECT CASE WHEN return_risk_score_at_signup >= 800 THEN '800+' WHEN return_risk_score_at_signup >= 740 THEN '740-799' WHEN return_risk_score_at_signup >= 670 THEN '670-739' WHEN return_risk_score_at_signup >= 580 THEN '580-669' ELSE '<580' END AS return_risk_band, COUNT(*) AS cnt FROM {S}.silver_bnpl_plans` GROUP BY 1 ORDER BY 1"))

    # Persona 4: Supply Chain Planner (4 queries)
    queries.append(("supply_chain_planner", "Working capital adequacy", f"SELECT reporting_date, capital_component, capital_ratio, regulatory_minimum, buffer_above_minimum FROM {G}.gold_working_capital_adequacy` ORDER BY reporting_date DESC"))
    queries.append(("supply_chain_planner", "Markdown risk MVaR", f"SELECT asset_class, sector, total_exposure, var_99_1d, var_99_10d FROM {G}.gold_markdown_risk_var` ORDER BY var_99_10d DESC"))
    queries.append(("supply_chain_planner", "BNPL plan assortment", f"SELECT plan_type, risk_rating, plan_count, total_outstanding, delinquency_rate_pct FROM {G}.gold_bnpl_plan_summary` ORDER BY total_outstanding DESC"))
    queries.append(("supply_chain_planner", "B2B commercial trade plans", f"SELECT naics_code, plan_count, total_balance FROM {G}.gold_bnpl_delinquency_analysis` WHERE plan_type = 'COMMERCIAL' ORDER BY total_balance DESC"))

    # Persona 5: Privacy & Compliance Officer (5 queries)
    queries.append(("privacy_compliance_officer", "Return fraud trends", f"SELECT alert_month, alert_type, alert_count, confirmed_fraud_count, false_positive_rate_pct FROM {G}.gold_return_fraud_analytics` ORDER BY alert_month DESC"))
    queries.append(("privacy_compliance_officer", "Promo fraud risk scoring", f"SELECT customer_segment, kyc_risk_rating, customer_count, avg_risk_score, sar_filings FROM {G}.gold_promo_fraud_scoring` ORDER BY avg_risk_score DESC"))
    queries.append(("privacy_compliance_officer", "Privacy consent overdue", f"SELECT due_diligence_level, risk_score_category, COUNT(*) AS total, COUNTIF(review_overdue) AS overdue FROM {S}.silver_privacy_consents` GROUP BY 1, 2"))
    queries.append(("privacy_compliance_officer", "High-value refund logs", f"SELECT wire_type, beneficiary_country, COUNT(*) AS cnt, SUM(amount) AS total FROM {S}.silver_high_value_refunds` WHERE amount >= 10000 GROUP BY 1, 2 ORDER BY total DESC"))
    queries.append(("privacy_compliance_officer", "Privacy & PCI dashboard", f"SELECT metric_category, metric_name, metric_value, threshold, status FROM {G}.gold_compliance_dashboard`"))

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
