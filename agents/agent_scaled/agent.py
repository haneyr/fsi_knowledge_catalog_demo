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

"""
FSI Scaled Agent — Exposed to all 150+ tables with no Knowledge Catalog guidance.

Demonstrates that the same agent architecture breaks down when exposed to
enterprise-scale data complexity. The agent struggles with table selection,
ambiguous column names, and cross-domain queries.

Deploy to Vertex AI Agent Engine or run locally:
    export GOOGLE_CLOUD_PROJECT=your-project-id
    python3 agent.py
"""

import asyncio
import os
import sys

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.cloud import bigquery

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")

SYSTEM_INSTRUCTION = f"""You are a financial data analyst for Meridian National Bank.
You have access to BigQuery and can run SQL queries against the bank's data warehouse.

Your project is: {PROJECT_ID}

## Available Datasets and Tables

### fsi_bronze (40 raw tables from 3 source systems)
bronze_customers, bronze_accounts, bronze_transactions, bronze_loans,
bronze_loan_payments, bronze_credit_cards, bronze_card_transactions,
bronze_fraud_alerts, bronze_kyc_records, bronze_branches, bronze_employees,
bronze_wire_transfers, bronze_ach_transfers, bronze_atm_transactions,
bronze_wm_clients, bronze_portfolios, bronze_holdings, bronze_trades,
bronze_securities, bronze_advisors, bronze_performance, bronze_fee_schedules,
bronze_benchmarks, bronze_client_goals, bronze_risk_profiles,
bronze_distributions, bronze_custodian_feeds, bronze_gl_entries,
bronze_gl_accounts, bronze_cost_centers, bronze_regulatory_capital,
bronze_risk_exposures, bronze_counterparties, bronze_market_data,
bronze_stress_tests, bronze_audit_events, bronze_regulatory_filings,
bronze_interest_rates, bronze_fx_rates, bronze_compliance_cases

### fsi_silver (40 cleansed tables)
silver_customers, silver_accounts, silver_transactions, silver_loans,
silver_loan_payments, silver_credit_cards, silver_card_transactions,
silver_fraud_alerts, silver_kyc_records, silver_branches, silver_employees,
silver_wire_transfers, silver_ach_transfers, silver_atm_transactions,
silver_wm_clients, silver_portfolios, silver_holdings, silver_trades,
silver_securities, silver_advisors, silver_performance, silver_fee_schedules,
silver_benchmarks, silver_client_goals, silver_risk_profiles,
silver_distributions, silver_custodian_feeds, silver_gl_entries,
silver_gl_accounts, silver_cost_centers, silver_regulatory_capital,
silver_risk_exposures, silver_counterparties, silver_market_data,
silver_stress_tests, silver_audit_events, silver_regulatory_filings,
silver_interest_rates, silver_fx_rates, silver_compliance_cases

### fsi_gold (20 analytics tables)
gold_customer_360, gold_account_summary, gold_transaction_patterns,
gold_loan_portfolio_summary, gold_delinquency_analysis, gold_fraud_analytics,
gold_aml_risk_scoring, gold_branch_performance, gold_portfolio_performance,
gold_client_revenue, gold_asset_allocation, gold_advisor_scorecard,
gold_fee_revenue, gold_net_interest_margin, gold_capital_adequacy,
gold_liquidity_coverage, gold_market_risk_var, gold_operational_risk,
gold_regulatory_dashboard, gold_balance_sheet_summary

### fsi_reference (10 reference tables)
ref_naics_codes, ref_country_codes, ref_currency_codes, ref_cusip_master,
ref_isin_mapping, ref_lei_registry, ref_fed_district_codes,
ref_product_catalog, ref_fee_tiers, ref_gl_account_hierarchy

### fsi_dashboards (8 views)
vw_dq_scorecard, vw_dq_by_dimension, vw_dq_failed_rules, vw_dq_rule_detail,
vw_profile_summary, vw_customer_total_relationship, vw_branch_retail_wealth,
vw_regulatory_summary

### fsi_staging (5 staging tables)
staging_call_report_rc, staging_call_report_ri, staging_call_report_rc_r,
staging_call_report_rc_c, staging_fr_y9c

### fsi_snapshots (3 snapshot tables)
snapshot_monthly_balances, snapshot_quarterly_positions, snapshot_daily_market_data

### fsi_audit (2 audit tables)
audit_data_access_log, audit_model_decisions

## Rules
- Use fully qualified table names: `{PROJECT_ID}.dataset.table`
- The BigQuery location is 'us' multi-region
- Try to use gold tables when possible, silver for detailed queries
"""


@FunctionTool
def run_sql(sql: str) -> str:
    """Execute a SQL query against BigQuery and return results."""
    try:
        client = bigquery.Client(project=PROJECT_ID)
        query_job = client.query(sql)
        results = query_job.result()

        rows = []
        for row in results:
            rows.append(dict(row))
            if len(rows) >= 50:
                break

        if not rows:
            return "Query returned 0 rows."

        header = " | ".join(rows[0].keys())
        lines = [header, "-" * len(header)]
        for row in rows:
            lines.append(" | ".join(str(v) for v in row.values()))

        return f"Query returned {results.total_rows} rows (showing first {len(rows)}):\n\n" + "\n".join(lines)
    except Exception as e:
        return f"SQL Error: {str(e)}"


agent = Agent(
    name="fsi_scaled_agent",
    model="gemini-2.5-flash",
    instruction=SYSTEM_INSTRUCTION,
    tools=[run_sql],
)


async def run_interactive():
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="fsi_scaled_agent", session_service=session_service)
    session = await session_service.create_session(app_name="fsi_scaled_agent", user_id="demo_user")

    print("\n" + "=" * 60)
    print("FSI Scaled Agent (150+ tables, NO Knowledge Catalog)")
    print("=" * 60)
    print('\nType "quit" to exit.\n')

    from google.genai import types

    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break

            content = types.Content(role="user", parts=[types.Part(text=user_input)])
            print("\nAgent: ", end="", flush=True)
            async for event in runner.run_async(user_id="demo_user", session_id=session.id, new_message=content):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(part.text, end="", flush=True)
            print("\n")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    asyncio.run(run_interactive())
