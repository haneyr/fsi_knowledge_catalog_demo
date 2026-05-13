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
FSI Basic Agent — Works with only 5 gold tables.

Demonstrates that a simple agent with a small, curated set of tables
can answer straightforward questions well. This is the "before scale" baseline.

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

SYSTEM_INSTRUCTION = f"""You are a financial data analyst for Meridian National Bank.
You have access to a small set of summary tables in BigQuery and can run SQL queries.

Your project is: {PROJECT_ID}

## Available Tables (5 tables only)

1. `{PROJECT_ID}.fsi_gold.gold_customer_360`
   - One row per customer with deposits, loans, cards, and wealth AUM
   - Columns: customer_id, first_name, last_name, customer_segment, total_deposit_balance,
     total_loan_balance, total_card_balance, total_aum, total_relationship_value

2. `{PROJECT_ID}.fsi_gold.gold_account_summary`
   - Account-level metrics with 90-day transaction activity
   - Columns: account_id, customer_id, account_type, current_balance, transaction_count_90d

3. `{PROJECT_ID}.fsi_gold.gold_loan_portfolio_summary`
   - Loan analytics by type, risk rating, and delinquency status
   - Columns: loan_type, risk_rating, delinquency_status, loan_count, total_outstanding, avg_fico

4. `{PROJECT_ID}.fsi_gold.gold_portfolio_performance`
   - Wealth portfolio performance with returns and risk metrics
   - Columns: portfolio_id, wm_client_id, market_value, ytd_return, avg_sharpe_ratio, avg_alpha

5. `{PROJECT_ID}.fsi_gold.gold_balance_sheet_summary`
   - High-level balance sheet: assets, liabilities, equity
   - Columns: category, line_item, amount

## How to answer

- Use fully qualified table names with the project ID
- The BigQuery location is 'us' multi-region
- **Be thorough and detailed in your answers.** Don't just return raw numbers — provide
  business context, explain what the numbers mean, highlight notable patterns, and offer
  actionable insights. Structure your response with clear sections.
- When presenting financial data, include relevant comparisons (e.g., percentages of total,
  ranking, period-over-period context where available).
- Format currency values with dollar signs and commas.
- If the data reveals something interesting or concerning, call it out proactively.
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


root_agent = Agent(
    name="fsi_basic_agent",
    model="gemini-2.5-flash",
    instruction=SYSTEM_INSTRUCTION,
    tools=[run_sql],
)

bq_analytics_plugin = BigQueryAgentAnalyticsPlugin(
    project_id=PROJECT_ID,
    dataset_id=BQ_ANALYTICS_DATASET,
    table_id="basic_agent_events",
    location="US",
)

app = App(
    name="fsi_basic_agent",
    root_agent=root_agent,
    plugins=[bq_analytics_plugin],
)


async def run_interactive():
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="fsi_basic_agent", session_service=session_service)
    session = await session_service.create_session(app_name="fsi_basic_agent", user_id="demo_user")

    print("\n" + "=" * 60)
    print("FSI Basic Agent (5 tables)")
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
