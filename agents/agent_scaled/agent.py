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
from google.adk.apps import App
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.adk.plugins.bigquery_agent_analytics_plugin import BigQueryAgentAnalyticsPlugin
from google.cloud import bigquery

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
BQ_ANALYTICS_DATASET = os.environ.get("BQ_ANALYTICS_DATASET", "agent_analytics")

_bq_client = None


def _get_bq_client():
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=PROJECT_ID)
    return _bq_client

SYSTEM_INSTRUCTION = f"""You are a financial data analyst for Meridian National Bank.
You have access to BigQuery and can run SQL queries against the bank's data warehouse.

Your project is: {PROJECT_ID}

## Available Tables

The following tables are available across multiple datasets. You must figure out which
tables are relevant to each question. Table names follow a naming convention but you
do not have descriptions, column details, or metadata for any of them.

{PROJECT_ID}.fsi_bronze.bronze_customers, {PROJECT_ID}.fsi_bronze.bronze_accounts,
{PROJECT_ID}.fsi_bronze.bronze_transactions, {PROJECT_ID}.fsi_bronze.bronze_loans,
{PROJECT_ID}.fsi_bronze.bronze_loan_payments, {PROJECT_ID}.fsi_bronze.bronze_credit_cards,
{PROJECT_ID}.fsi_bronze.bronze_card_transactions, {PROJECT_ID}.fsi_bronze.bronze_fraud_alerts,
{PROJECT_ID}.fsi_bronze.bronze_kyc_records, {PROJECT_ID}.fsi_bronze.bronze_branches,
{PROJECT_ID}.fsi_bronze.bronze_employees, {PROJECT_ID}.fsi_bronze.bronze_wire_transfers,
{PROJECT_ID}.fsi_bronze.bronze_ach_transfers, {PROJECT_ID}.fsi_bronze.bronze_atm_transactions,
{PROJECT_ID}.fsi_bronze.bronze_wm_clients, {PROJECT_ID}.fsi_bronze.bronze_portfolios,
{PROJECT_ID}.fsi_bronze.bronze_holdings, {PROJECT_ID}.fsi_bronze.bronze_trades,
{PROJECT_ID}.fsi_bronze.bronze_securities, {PROJECT_ID}.fsi_bronze.bronze_advisors,
{PROJECT_ID}.fsi_bronze.bronze_performance, {PROJECT_ID}.fsi_bronze.bronze_fee_schedules,
{PROJECT_ID}.fsi_bronze.bronze_benchmarks, {PROJECT_ID}.fsi_bronze.bronze_client_goals,
{PROJECT_ID}.fsi_bronze.bronze_risk_profiles, {PROJECT_ID}.fsi_bronze.bronze_distributions,
{PROJECT_ID}.fsi_bronze.bronze_custodian_feeds, {PROJECT_ID}.fsi_bronze.bronze_gl_entries,
{PROJECT_ID}.fsi_bronze.bronze_gl_accounts, {PROJECT_ID}.fsi_bronze.bronze_cost_centers,
{PROJECT_ID}.fsi_bronze.bronze_regulatory_capital, {PROJECT_ID}.fsi_bronze.bronze_risk_exposures,
{PROJECT_ID}.fsi_bronze.bronze_counterparties, {PROJECT_ID}.fsi_bronze.bronze_market_data,
{PROJECT_ID}.fsi_bronze.bronze_stress_tests, {PROJECT_ID}.fsi_bronze.bronze_audit_events,
{PROJECT_ID}.fsi_bronze.bronze_regulatory_filings, {PROJECT_ID}.fsi_bronze.bronze_interest_rates,
{PROJECT_ID}.fsi_bronze.bronze_fx_rates, {PROJECT_ID}.fsi_bronze.bronze_compliance_cases,
{PROJECT_ID}.fsi_silver.silver_customers, {PROJECT_ID}.fsi_silver.silver_accounts,
{PROJECT_ID}.fsi_silver.silver_transactions, {PROJECT_ID}.fsi_silver.silver_loans,
{PROJECT_ID}.fsi_silver.silver_loan_payments, {PROJECT_ID}.fsi_silver.silver_credit_cards,
{PROJECT_ID}.fsi_silver.silver_card_transactions, {PROJECT_ID}.fsi_silver.silver_fraud_alerts,
{PROJECT_ID}.fsi_silver.silver_kyc_records, {PROJECT_ID}.fsi_silver.silver_branches,
{PROJECT_ID}.fsi_silver.silver_employees, {PROJECT_ID}.fsi_silver.silver_wire_transfers,
{PROJECT_ID}.fsi_silver.silver_ach_transfers, {PROJECT_ID}.fsi_silver.silver_atm_transactions,
{PROJECT_ID}.fsi_silver.silver_wm_clients, {PROJECT_ID}.fsi_silver.silver_portfolios,
{PROJECT_ID}.fsi_silver.silver_holdings, {PROJECT_ID}.fsi_silver.silver_trades,
{PROJECT_ID}.fsi_silver.silver_securities, {PROJECT_ID}.fsi_silver.silver_advisors,
{PROJECT_ID}.fsi_silver.silver_performance, {PROJECT_ID}.fsi_silver.silver_fee_schedules,
{PROJECT_ID}.fsi_silver.silver_benchmarks, {PROJECT_ID}.fsi_silver.silver_client_goals,
{PROJECT_ID}.fsi_silver.silver_risk_profiles, {PROJECT_ID}.fsi_silver.silver_distributions,
{PROJECT_ID}.fsi_silver.silver_custodian_feeds, {PROJECT_ID}.fsi_silver.silver_gl_entries,
{PROJECT_ID}.fsi_silver.silver_gl_accounts, {PROJECT_ID}.fsi_silver.silver_cost_centers,
{PROJECT_ID}.fsi_silver.silver_regulatory_capital, {PROJECT_ID}.fsi_silver.silver_risk_exposures,
{PROJECT_ID}.fsi_silver.silver_counterparties, {PROJECT_ID}.fsi_silver.silver_market_data,
{PROJECT_ID}.fsi_silver.silver_stress_tests, {PROJECT_ID}.fsi_silver.silver_audit_events,
{PROJECT_ID}.fsi_silver.silver_regulatory_filings, {PROJECT_ID}.fsi_silver.silver_interest_rates,
{PROJECT_ID}.fsi_silver.silver_fx_rates, {PROJECT_ID}.fsi_silver.silver_compliance_cases,
{PROJECT_ID}.fsi_gold.gold_customer_360, {PROJECT_ID}.fsi_gold.gold_account_summary,
{PROJECT_ID}.fsi_gold.gold_transaction_patterns, {PROJECT_ID}.fsi_gold.gold_loan_portfolio_summary,
{PROJECT_ID}.fsi_gold.gold_delinquency_analysis, {PROJECT_ID}.fsi_gold.gold_fraud_analytics,
{PROJECT_ID}.fsi_gold.gold_aml_risk_scoring, {PROJECT_ID}.fsi_gold.gold_branch_performance,
{PROJECT_ID}.fsi_gold.gold_portfolio_performance, {PROJECT_ID}.fsi_gold.gold_client_revenue,
{PROJECT_ID}.fsi_gold.gold_asset_allocation, {PROJECT_ID}.fsi_gold.gold_advisor_scorecard,
{PROJECT_ID}.fsi_gold.gold_fee_revenue, {PROJECT_ID}.fsi_gold.gold_net_interest_margin,
{PROJECT_ID}.fsi_gold.gold_capital_adequacy, {PROJECT_ID}.fsi_gold.gold_liquidity_coverage,
{PROJECT_ID}.fsi_gold.gold_market_risk_var, {PROJECT_ID}.fsi_gold.gold_operational_risk,
{PROJECT_ID}.fsi_gold.gold_regulatory_dashboard, {PROJECT_ID}.fsi_gold.gold_balance_sheet_summary,
{PROJECT_ID}.fsi_reference.ref_naics_codes, {PROJECT_ID}.fsi_reference.ref_country_codes,
{PROJECT_ID}.fsi_reference.ref_currency_codes, {PROJECT_ID}.fsi_reference.ref_cusip_master,
{PROJECT_ID}.fsi_reference.ref_isin_mapping, {PROJECT_ID}.fsi_reference.ref_lei_registry,
{PROJECT_ID}.fsi_reference.ref_fed_district_codes, {PROJECT_ID}.fsi_reference.ref_product_catalog,
{PROJECT_ID}.fsi_reference.ref_fee_tiers, {PROJECT_ID}.fsi_reference.ref_gl_account_hierarchy,
{PROJECT_ID}.fsi_dashboards.vw_dq_scorecard, {PROJECT_ID}.fsi_dashboards.vw_dq_by_dimension,
{PROJECT_ID}.fsi_dashboards.vw_dq_failed_rules, {PROJECT_ID}.fsi_dashboards.vw_dq_rule_detail,
{PROJECT_ID}.fsi_dashboards.vw_profile_summary, {PROJECT_ID}.fsi_dashboards.vw_customer_total_relationship,
{PROJECT_ID}.fsi_dashboards.vw_branch_retail_wealth, {PROJECT_ID}.fsi_dashboards.vw_regulatory_summary,
{PROJECT_ID}.fsi_supplementary.staging_call_report_rc, {PROJECT_ID}.fsi_supplementary.staging_call_report_ri,
{PROJECT_ID}.fsi_supplementary.staging_call_report_rc_r, {PROJECT_ID}.fsi_supplementary.staging_call_report_rc_c,
{PROJECT_ID}.fsi_supplementary.staging_fr_y9c, {PROJECT_ID}.fsi_supplementary.snapshot_monthly_balances,
{PROJECT_ID}.fsi_supplementary.snapshot_quarterly_positions, {PROJECT_ID}.fsi_supplementary.snapshot_daily_market_data,
{PROJECT_ID}.fsi_supplementary.audit_data_access_log, {PROJECT_ID}.fsi_supplementary.audit_model_decisions

## How to answer

- Use fully qualified table names as listed above
- The BigQuery location is 'us' multi-region
- You do not have column descriptions or metadata — you must infer column meanings from
  their names or use INFORMATION_SCHEMA to inspect tables
- Format currency with $ and commas
- Provide business context with your answers
"""


@FunctionTool
def run_sql(sql: str) -> str:
    """Execute a SQL query against BigQuery and return results."""
    try:
        client = _get_bq_client()
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


root_agent = Agent(
    name="fsi_scaled_agent",
    model="gemini-2.5-flash",
    instruction=SYSTEM_INSTRUCTION,
    tools=[run_sql],
)

bq_analytics_plugin = BigQueryAgentAnalyticsPlugin(
    project_id=PROJECT_ID,
    dataset_id=BQ_ANALYTICS_DATASET,
    table_id="scaled_agent_events",
    location="US",
)

app = App(
    name="fsi_scaled_agent",
    root_agent=root_agent,
    plugins=[bq_analytics_plugin],
)


async def run_interactive():
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="fsi_scaled_agent", session_service=session_service)
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
