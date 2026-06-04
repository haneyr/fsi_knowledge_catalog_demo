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

def _get_bq_client():
    return bigquery.Client(project=PROJECT_ID)

_BASE_SUFFIXES = [
    'customers','accounts','transactions','loans','loan_payments','credit_cards',
    'card_transactions','fraud_alerts','kyc_records','branches','employees','wire_transfers',
    'ach_transfers','atm_transactions','wm_clients','portfolios','holdings','trades',
    'securities','advisors','performance','fee_schedules','benchmarks','client_goals',
    'risk_profiles','distributions','custodian_feeds','gl_entries','gl_accounts',
    'cost_centers','regulatory_capital','risk_exposures','counterparties','market_data',
    'stress_tests','audit_events','regulatory_filings','interest_rates','fx_rates',
    'compliance_cases',
]
_GOLD_TABLES = [
    'gold_customer_360','gold_account_summary','gold_transaction_patterns',
    'gold_loan_portfolio_summary','gold_delinquency_analysis','gold_fraud_analytics',
    'gold_aml_risk_scoring','gold_branch_performance','gold_portfolio_performance',
    'gold_client_revenue','gold_asset_allocation','gold_advisor_scorecard',
    'gold_fee_revenue','gold_net_interest_margin','gold_capital_adequacy',
    'gold_liquidity_coverage','gold_market_risk_var','gold_operational_risk',
    'gold_regulatory_dashboard','gold_balance_sheet_summary',
]
_VIEW_TABLES = [
    'vw_dq_scorecard','vw_dq_by_dimension','vw_dq_failed_rules','vw_dq_rule_detail',
    'vw_profile_summary','vw_customer_total_relationship','vw_branch_retail_wealth',
    'vw_regulatory_summary',
]
_OTHER_TABLES = [
    'ref_naics_codes','ref_country_codes','ref_currency_codes','ref_cusip_master',
    'ref_isin_mapping','ref_lei_registry','ref_fed_district_codes','ref_product_catalog',
    'staging_call_report_rc','staging_call_report_ri','staging_fr_y9c',
    'snapshot_monthly_balances','snapshot_quarterly_positions','audit_data_access_log',
]

_DATASET_PREFIX = {
    'bronze_': 'fsi_bronze_nokc', 'silver_': 'fsi_silver_nokc',
    'gold_': 'fsi_gold_nokc', 'vw_': 'fsi_dashboards_nokc',
    'ref_': 'fsi_reference_nokc', 'staging_': 'fsi_staging_nokc',
    'snapshot_': 'fsi_snapshots_nokc', 'audit_': 'fsi_audit_nokc',
}

def _table_fqn(table_name):
    for prefix, dataset in _DATASET_PREFIX.items():
        if table_name.startswith(prefix):
            return f"{PROJECT_ID}.{dataset}.{table_name}"
    return f"{PROJECT_ID}.fsi_gold_nokc.{table_name}"

_ALL_TABLE_NAMES = (
    [f'bronze_{s}' for s in _BASE_SUFFIXES]
    + [f'silver_{s}' for s in _BASE_SUFFIXES]
    + _GOLD_TABLES + _VIEW_TABLES + _OTHER_TABLES
)
_NOKC_TABLES = [_table_fqn(t) for t in _ALL_TABLE_NAMES]

SYSTEM_INSTRUCTION = f"""You are a financial data analyst for Meridian National Bank.
You have access to BigQuery and can run SQL queries against the bank's data warehouse.

Your project is: {PROJECT_ID}

## Available Tables ({len(_NOKC_TABLES)} tables)

The following tables are available. You must figure out which tables are relevant to
each question based on their names. You do not have descriptions, column details, or
metadata for any of them.

{chr(10).join(_NOKC_TABLES)}

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
