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
Retail Scaled Agent — Exposed to all 150+ tables with no Knowledge Catalog guidance.

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
BQ_ANALYTICS_DATASET = os.environ.get("BQ_ANALYTICS_DATASET", "retail_agent_analytics")

def _get_bq_client():
    return bigquery.Client(project=PROJECT_ID)

_BASE_SUFFIXES = [
    'customers','loyalty_accounts','pos_transactions','bnpl_plans','bnpl_payments','store_cards',
    'payment_tenders','fraud_alerts','privacy_consents','stores','store_associates','high_value_refunds',
    'vendor_settlements','kiosk_transactions','vip_members','merch_assortments','inventory_positions','ecom_orders',
    'product_skus','category_managers','assortment_performance','promo_rules','category_benchmarks','customer_preferences',
    'return_risk_profiles','reward_redemptions','carrier_feeds','gl_entries','gl_accounts',
    'cost_centers','working_capital','shrinkage_exposures','suppliers','competitor_pricing',
    'demand_scenarios','audit_events','compliance_attestations','markdown_rates','fx_rates',
    'promo_abuse_cases',
]
_GOLD_TABLES = [
    'gold_customer_360','gold_loyalty_account_summary','gold_order_patterns',
    'gold_bnpl_plan_summary','gold_bnpl_delinquency_analysis','gold_return_fraud_analytics',
    'gold_promo_fraud_scoring','gold_store_performance','gold_assortment_performance',
    'gold_vip_member_revenue','gold_inventory_allocation','gold_category_manager_scorecard',
    'gold_promo_margin_impact','gold_gross_margin_analysis','gold_working_capital_adequacy',
    'gold_inventory_turnover_coverage','gold_markdown_risk_var','gold_shrinkage_operational_risk',
    'gold_compliance_dashboard','gold_financial_summary',
]
_VIEW_TABLES = [
    'vw_dq_scorecard','vw_dq_by_dimension','vw_dq_failed_rules','vw_dq_rule_detail',
    'vw_profile_summary','vw_customer_lifetime_value','vw_store_omnichannel_performance',
    'vw_compliance_summary',
]
_OTHER_TABLES = [
    'ref_merch_category_codes','ref_country_codes','ref_currency_codes','ref_gtin_master',
    'ref_sku_gtin_mapping','ref_supplier_registry','ref_sales_region_codes','ref_product_catalog',
    'ref_loyalty_tiers','ref_gl_account_hierarchy',
    'staging_pci_aoc_summary','staging_channel_revenue_recon','staging_supplier_audit_schedule',
    'staging_ccpa_dsar_log','staging_annual_omniretail_filing',
    'snapshot_monthly_loyalty_balances','snapshot_quarterly_inventory_positions','snapshot_daily_competitor_pricing',
    'audit_data_access_log','audit_model_decisions',
]

_DATASET_PREFIX = {
    'bronze_': 'retail_bronze_nokc', 'silver_': 'retail_silver_nokc',
    'gold_': 'retail_gold_nokc', 'vw_': 'retail_dashboards_nokc',
    'ref_': 'retail_reference_nokc', 'staging_': 'retail_staging_nokc',
    'snapshot_': 'retail_snapshots_nokc', 'audit_': 'retail_audit_nokc',
}

def _table_fqn(table_name):
    for prefix, dataset in _DATASET_PREFIX.items():
        if table_name.startswith(prefix):
            return f"{PROJECT_ID}.{dataset}.{table_name}"
    return f"{PROJECT_ID}.retail_gold_nokc.{table_name}"

_ALL_TABLE_NAMES = (
    [f'bronze_{s}' for s in _BASE_SUFFIXES]
    + [f'silver_{s}' for s in _BASE_SUFFIXES]
    + _GOLD_TABLES + _VIEW_TABLES + _OTHER_TABLES
)
_NOKC_TABLES = [_table_fqn(t) for t in _ALL_TABLE_NAMES]

SYSTEM_INSTRUCTION = f"""You are a retail data analyst for Northwind Retail Group.
You have access to BigQuery and can run SQL queries against the retailer's data warehouse.

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
    name="retail_scaled_agent",
    model="gemini-2.5-flash",
    description="[Retail] Northwind Retail Scaled Agent (128 tables without Knowledge Catalog)",
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
    name="retail_scaled_agent",
    root_agent=root_agent,
    plugins=[bq_analytics_plugin],
)


async def run_interactive():
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="retail_scaled_agent", session_service=session_service)
    session = await session_service.create_session(app_name="retail_scaled_agent", user_id="demo_user")

    print("\n" + "=" * 60)
    print("Retail Scaled Agent (150+ tables, NO Knowledge Catalog)")
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
