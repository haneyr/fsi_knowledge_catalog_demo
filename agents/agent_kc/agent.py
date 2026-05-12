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
FSI Knowledge Catalog Agent — Uses KC MCP tools to navigate 150+ tables intelligently.

Demonstrates that Knowledge Catalog solves the agent scale problem by providing
semantic search, rich metadata, glossary terms, data quality scores, and lineage
to guide the agent to the right data.

Deploy to Vertex AI Agent Engine or run locally:
    export GOOGLE_CLOUD_PROJECT=your-project-id
    export DATAPLEX_PROJECT=your-project-id
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
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters
from google.cloud import bigquery

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
DATAPLEX_PROJECT = os.environ.get("DATAPLEX_PROJECT", PROJECT_ID)
TOOLBOX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toolbox")

SYSTEM_INSTRUCTION = f"""You are a financial data analyst for Meridian National Bank with access to
Knowledge Catalog for discovering data and BigQuery for running SQL queries.

Your project is: {PROJECT_ID}

## How to answer questions — ALWAYS follow this process:

1. **DISCOVER**: Use Knowledge Catalog tools FIRST to find relevant data:
   - `search_entries` — semantic search for tables by topic (e.g., "customer deposits", "loan delinquency")
   - `lookup_context` — get rich metadata for a specific table including glossary terms, data quality, lineage
   - `lookup_entry` — get details about a specific data asset

2. **UNDERSTAND**: Read the metadata returned by Knowledge Catalog:
   - Check which medallion layer is best (prefer gold > silver > bronze)
   - Read the glossary term definitions to understand business meaning
   - Check data quality scores before trusting results
   - Note sensitivity classifications and access requirements
   - Understand data lineage (which source system the data comes from)

3. **QUERY**: Use `run_sql` to execute SQL against the right tables
   - Use fully qualified table names: `{PROJECT_ID}.dataset.table`
   - The BigQuery location is 'us' multi-region

4. **CITE**: When answering, mention:
   - Which tables you used and why (citing KC discovery)
   - Relevant glossary terms and their definitions
   - Data quality scores and any caveats
   - Data lineage (source system: ATLAS, FORTUNA, or ARGUS)
   - Sensitivity classifications if the data contains PII

## Important rules:
- NEVER guess which table to use — always search Knowledge Catalog first
- Prefer gold tables for analytics, silver for detailed queries
- If a question spans multiple domains (retail + wealth), search for each domain separately
- Flag any data quality issues found in the metadata
"""


@FunctionTool
def run_sql(sql: str) -> str:
    """Execute a SQL query against BigQuery and return results.

    Use this after discovering the right tables via Knowledge Catalog.
    Always use fully qualified table names: `project.dataset.table`.
    """
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


def create_agent():
    kc_toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=TOOLBOX_PATH,
                args=["--prebuilt", "dataplex", "--stdio"],
                env={
                    "DATAPLEX_PROJECT": DATAPLEX_PROJECT,
                    "GOOGLE_CLOUD_PROJECT": PROJECT_ID,
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": os.environ.get("HOME", ""),
                },
            ),
            timeout=30.0,
        ),
    )

    kc_agent = Agent(
        name="fsi_kc_agent",
        model="gemini-2.5-flash",
        instruction=SYSTEM_INSTRUCTION,
        tools=[run_sql, kc_toolset],
    )

    return kc_agent, kc_toolset


agent, _kc_toolset = create_agent()


async def run_interactive():
    global _kc_toolset
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="fsi_kc_agent", session_service=session_service)
    session = await session_service.create_session(app_name="fsi_kc_agent", user_id="demo_user")

    print("\n" + "=" * 60)
    print("FSI Knowledge Catalog Agent (150+ tables WITH KC guidance)")
    print("Powered by ADK + Knowledge Catalog MCP + BigQuery")
    print("=" * 60)
    print("\nExample questions:")
    print('  "What is our total relationship value for high-net-worth clients?"')
    print('  "Show me suspicious activity trends by quarter"')
    print('  "What is our CET1 capital ratio and how does it compare to minimums?"')
    print('  "Which branches have the highest combined retail + wealth revenue?"')
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
    finally:
        await _kc_toolset.close()


if __name__ == "__main__":
    asyncio.run(run_interactive())
