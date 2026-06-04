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

def _discover_nokc_tables():
    client = _get_bq_client()
    tables = []
    for dataset in client.list_datasets():
        if not dataset.dataset_id.endswith("_nokc"):
            continue
        for table in client.list_tables(dataset.dataset_id):
            tables.append(f"{PROJECT_ID}.{dataset.dataset_id}.{table.table_id}")
    return sorted(tables)

_NOKC_TABLES = _discover_nokc_tables() if PROJECT_ID else []

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
