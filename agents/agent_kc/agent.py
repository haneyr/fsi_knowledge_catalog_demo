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
FSI Knowledge Catalog Agent — Uses KC Context API to navigate 150+ tables.

Implements Knowledge Catalog discovery tools as native FunctionTools calling
the Dataplex REST API directly, making it fully compatible with Agent Engine
without needing an external MCP Toolbox binary.

Deploy to Vertex AI Agent Engine or run locally:
    export GOOGLE_CLOUD_PROJECT=your-project-id
    export DATAPLEX_PROJECT=your-project-id
    python3 agent.py
"""

import asyncio
import json
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
import google.auth
import google.auth.transport.requests
import requests as http_requests

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
DATAPLEX_PROJECT = os.environ.get("DATAPLEX_PROJECT", PROJECT_ID)
BQ_ANALYTICS_DATASET = os.environ.get("BQ_ANALYTICS_DATASET", "agent_analytics")
DATAPLEX_URL = "https://dataplex.googleapis.com/v1"

SYSTEM_INSTRUCTION = f"""You are a senior financial data analyst for Meridian National Bank. You have
access to Knowledge Catalog for discovering and understanding data assets, and BigQuery for
running SQL queries. Your answers should be thorough, well-structured, and demonstrate the
value of metadata-driven data discovery.

Your project is: {PROJECT_ID}

## How to answer questions — ALWAYS follow this process:

### Step 1: DISCOVER (use Knowledge Catalog tools)
Before writing ANY SQL, search Knowledge Catalog to find the right data:
- `search_entries` — semantic search for tables by topic (e.g., "customer deposits", "loan delinquency")
- `get_context` — pass discovered entry names + your question to the Context API, which returns
  rich pre-formatted metadata including schema with linked glossary terms, data quality info,
  custom aspects, and storage details — all ready for analysis

Search broadly. If a question touches multiple domains (e.g., "total relationship value" spans
retail banking AND wealth management), run multiple searches to cover each domain.
After searching, call `get_context` with the entry names of the best candidates to get
full metadata before writing SQL.

### Step 2: UNDERSTAND (read and explain the metadata)
Before querying, explain to the user what you found and WHY you chose specific tables:
- **Table selection rationale**: "I found gold_customer_360 which joins retail and wealth data
  into a single view — this is the best source because it already aggregates across both
  ATLAS (retail banking) and FORTUNA (wealth management) source systems."
- **Medallion layer choice**: Explain why you chose gold vs silver vs bronze
  (gold = pre-aggregated analytics, silver = cleansed detail, bronze = raw ingestion)
- **Data classification**: Note if data contains PII or restricted information
  (e.g., "This table has a Restricted classification with PII masking applied to SSN fields")
- **Data quality**: If aspects show quality scores or DQ rules, mention them
  (e.g., "This table has data quality rules ensuring FICO scores are validated in the 300-850 range")
- **Source lineage**: Explain where the data originates
  (e.g., "This data flows from ATLAS (IBM DB2 mainframe) → fsi_bronze → fsi_silver → fsi_gold")

### Step 3: QUERY (run SQL with full context)
- Use fully qualified table names: `{PROJECT_ID}.dataset.table`
- The BigQuery location is 'us' multi-region
- Write clear, well-structured SQL

### Step 4: PRESENT (thorough, insight-rich answers)
Structure every answer with these sections:

**Data Discovery**: Explain what you searched for and what Knowledge Catalog returned.
Mention the specific tables you found, their medallion layer, source systems, and why
you selected them over alternatives.

**Analysis**: Present the query results with full business context:
- Don't just show numbers — explain what they mean for the business
- Include percentages, rankings, and comparisons where relevant
- Format currency with dollar signs and commas
- Highlight notable patterns, outliers, or concerns

**Data Governance Notes**: Include relevant metadata from Knowledge Catalog:
- Data classification level and sensitivity
- Source system lineage (ATLAS/FORTUNA/ARGUS)
- Any data quality rules or scores that affect data trustworthiness
- Regulatory context if applicable (BSA/AML, Basel III, FDIC, etc.)
- Glossary term definitions for key business concepts mentioned in the answer

**Recommendations**: If the data suggests action items or further analysis, suggest them.

## Important rules:
- NEVER guess which table to use — always search Knowledge Catalog first
- Prefer gold tables for analytics, silver for detailed queries, bronze only when needed
- If a question spans multiple domains (retail + wealth), search for each domain separately
- Flag any data quality issues found in the metadata
- Be verbose and explanatory — your audience is banking executives who want to understand
  both the answer AND how you arrived at it through governed data discovery
"""


_creds_cache = [None, 0]

def _get_token():
    import time
    now = time.time()
    if _creds_cache[0] is None or now - _creds_cache[1] > 250:
        creds, _ = google.auth.default()
        creds.refresh(google.auth.transport.requests.Request())
        _creds_cache[0] = creds.token
        _creds_cache[1] = now
    return _creds_cache[0]


def _dataplex_get(path):
    headers = {"Authorization": f"Bearer {_get_token()}"}
    resp = http_requests.get(f"{DATAPLEX_URL}/{path}", headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}


def _dataplex_post(path, body):
    headers = {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}
    resp = http_requests.post(f"{DATAPLEX_URL}/{path}", headers=headers, json=body)
    if resp.status_code == 200:
        return resp.json()
    return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}


@FunctionTool
def search_entries(query: str) -> str:
    """Search for data entries in Knowledge Catalog using semantic search.

    Use this to discover tables, views, and other data assets by topic.
    Examples: "customer deposits", "loan delinquency", "portfolio performance"
    Returns entry names that can be passed to lookup_entry for details.
    """
    try:
        result = _dataplex_post(
            f"projects/{DATAPLEX_PROJECT}/locations/us:searchEntries",
            {"query": query, "pageSize": 10}
        )
        if "error" in result:
            return f"Search error: {result['error']}"

        entries = result.get("results", [])
        if not entries:
            return "No entries found for that search query."

        lines = [f"Found {len(entries)} entries:\n"]
        for entry in entries:
            snippets = entry.get("snippets", {})
            e = entry.get("dataplexEntry", {})
            name = e.get("name", "")
            fqn = e.get("fullyQualifiedName", "")
            entry_type = e.get("entryType", "").split("/")[-1] if e.get("entryType") else ""
            desc_snippet = snippets.get("dataplexEntry", {}).get("description", "")
            lines.append(f"- **{fqn}** ({entry_type})")
            if desc_snippet:
                lines.append(f"  {desc_snippet}")
            lines.append(f"  Entry: {name}")
            if fqn.startswith("bigquery:"):
                parts = fqn.replace("bigquery:", "").split(".")
                if len(parts) == 3:
                    lines.append(f"  BigQuery table: `{parts[0]}.{parts[1]}.{parts[2]}`")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Search error: {str(e)}"


@FunctionTool
def get_context(entry_names: list[str], question: str) -> str:
    """Get rich LLM-ready context for one or more data entries using the
    Knowledge Catalog Context API. Returns schema with linked glossary terms,
    data quality info, custom aspects, and storage metadata — all pre-formatted
    for analysis.

    Pass entry names from search_entries results (the lines starting with 'Entry:').
    Pass your question as context so the API can prioritize relevant metadata.

    Example:
        get_context(
            entry_names=["projects/123/locations/us/entryGroups/@bigquery/entries/..."],
            question="What is the total relationship value for HNW clients?"
        )
    """
    try:
        result = _dataplex_post(
            f"projects/{DATAPLEX_PROJECT}/locations/us:lookupContext",
            {
                "resources": entry_names[:10],
                "context": question,
                "options": {"format": "yaml", "context_budget": "8000"},
            }
        )
        if "error" in result:
            return f"Context API error: {result['error']}"

        context = result.get("context", "")
        if not context:
            return "No context returned. The entries may not exist or may not have metadata."

        return context
    except Exception as e:
        return f"Context API error: {str(e)}"


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


root_agent = Agent(
    name="fsi_kc_agent",
    model="gemini-2.5-flash",
    instruction=SYSTEM_INSTRUCTION,
    tools=[search_entries, get_context, run_sql],
)

bq_analytics_plugin = BigQueryAgentAnalyticsPlugin(
    project_id=PROJECT_ID,
    dataset_id=BQ_ANALYTICS_DATASET,
    table_id="kc_agent_events",
    location="US",
)

app = App(
    name="fsi_kc_agent",
    root_agent=root_agent,
    plugins=[bq_analytics_plugin],
)


async def run_interactive():
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="fsi_kc_agent", session_service=session_service)
    session = await session_service.create_session(app_name="fsi_kc_agent", user_id="demo_user")

    print("\n" + "=" * 60)
    print("FSI Knowledge Catalog Agent (150+ tables WITH KC guidance)")
    print("Powered by ADK + Knowledge Catalog Context API + BigQuery")
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


if __name__ == "__main__":
    asyncio.run(run_interactive())
