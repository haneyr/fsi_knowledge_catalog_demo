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

_bq_client = None


def _get_bq_client():
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=PROJECT_ID)
    return _bq_client


_http_session = None


def _get_http_session():
    global _http_session
    if _http_session is None:
        _http_session = http_requests.Session()
    return _http_session

SYSTEM_INSTRUCTION = f"""You are a senior financial data analyst for Meridian National Bank. You have
access to Knowledge Catalog for discovering and understanding data assets, and BigQuery for
running SQL queries.

Your project is: {PROJECT_ID}

## How to answer questions — ALWAYS follow this process:

1. **DISCOVER**: Search Knowledge Catalog (`search_entries`) to find relevant tables.
   Search broadly — if a question spans multiple domains, run multiple searches.

2. **UNDERSTAND**: Call `get_context` with discovered entry names + the user's question
   to get schema, glossary terms, data quality info, and lineage.

3. **QUERY**: Run SQL using fully qualified table names (`{PROJECT_ID}.dataset.table`).
   BigQuery location is 'us' multi-region. If results look wrong, silently retry with
   corrective queries rather than explaining failures.

4. **RESPOND**: Write ONE structured response with these sections:

   **Data Discovery** — Briefly explain what you searched for in Knowledge Catalog, which
   tables you found, their medallion layer (gold/silver/bronze), and why you selected them.
   Show your reasoning about table selection — this demonstrates the value of metadata.

   **Analysis** — Present the actual query results with business context. Always include
   real numbers, formatted with $ and commas. Explain what they mean for the business.

   **Data Governance Notes** — Relevant metadata: data classification, source lineage
   (ATLAS/FORTUNA/ARGUS), data quality rules, glossary definitions for key terms.

   **Recommendations** — Suggested actions or further analysis based on findings.

IMPORTANT: Always complete your tool calls and present actual query results in the
Analysis section. Never end a response with just a plan to query something — always
include the data.

## Important rules:
- NEVER guess which table to use — always search Knowledge Catalog first
- Prefer gold tables for analytics, silver for detail, bronze only when needed
- Your audience is banking executives — be thorough but results-focused
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
    resp = _get_http_session().get(f"{DATAPLEX_URL}/{path}", headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}


def _dataplex_post(path, body):
    headers = {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}
    resp = _get_http_session().post(f"{DATAPLEX_URL}/{path}", headers=headers, json=body)
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


# --- Conditional Snowflake integration ---
_sf_conn = None
SNOWFLAKE_ENABLED = bool(os.environ.get("SNOWFLAKE_ACCOUNT"))

if SNOWFLAKE_ENABLED:
    import snowflake.connector

    def _new_sf_connection():
        return snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_AGENT_USER"],
            password=os.environ["SNOWFLAKE_AGENT_PASSWORD"],
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "NEXUS_WH"),
            database=os.environ.get("SNOWFLAKE_DATABASE", "NEXUS_MARKET_DATA"),
            role="FSI_KC_AGENT_ROLE",
        )

    def _get_sf_connection():
        global _sf_conn
        if _sf_conn is None:
            _sf_conn = _new_sf_connection()
        return _sf_conn

    def _reset_sf_connection():
        global _sf_conn
        try:
            if _sf_conn is not None:
                _sf_conn.close()
        except Exception:
            pass
        _sf_conn = _new_sf_connection()
        return _sf_conn

    def _run_sf_query(sql: str) -> str:
        conn = _get_sf_connection()
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchmany(50)
        if not rows:
            return "Query returned 0 rows."

        col_names = [desc[0] for desc in cur.description]
        header = " | ".join(col_names)
        lines = [header, "-" * len(header)]
        for row in rows:
            lines.append(" | ".join(str(v) for v in row))

        total = cur.rowcount if cur.rowcount >= 0 else len(rows)
        return f"Query returned {total} rows (showing first {len(rows)}):\n\n" + "\n".join(lines)

    @FunctionTool
    def query_snowflake(sql: str) -> str:
        """Execute a SQL query against Snowflake and return results.

        Use this when Knowledge Catalog search reveals data in Snowflake
        (NEXUS market data). Use fully qualified names: DATABASE.SCHEMA.TABLE.
        For example: NEXUS_MARKET_DATA.SECURITIES.SECURITY_PRICES
        """
        try:
            return _run_sf_query(sql)
        except Exception:
            try:
                _reset_sf_connection()
                return _run_sf_query(sql)
            except Exception as e:
                return f"Snowflake SQL Error: {str(e)}"

    SNOWFLAKE_PROMPT_EXTENSION = """

## Snowflake (NEXUS Market Data)

You also have access to Snowflake for querying external market data from the NEXUS data provider.
When Knowledge Catalog search results include Snowflake entries (entry type `snowflake-table`),
use `query_snowflake` instead of `run_sql`. Use fully qualified Snowflake table names:
`NEXUS_MARKET_DATA.SCHEMA.TABLE` (e.g., `NEXUS_MARKET_DATA.SECURITIES.SECURITY_PRICES`).

For cross-platform questions, you may need to query both BigQuery and Snowflake, then combine
the results in your response. For example, portfolio holdings live in BigQuery while current
security prices live in Snowflake.

**IMPORTANT — Snowflake discovery:** A general search may only return BigQuery tables. When a
question involves market data, external benchmarks, rates, prices, or any topic NEXUS might
cover, ALWAYS run a second search using the word "snowflake" as the FIRST keyword followed by
the topic (e.g., `search_entries("snowflake FX")`, `search_entries("snowflake benchmark")`).
This specific pattern reliably surfaces Snowflake entries. Do not assume a topic has no
Snowflake data just because the first search returned only BigQuery results.

When querying Snowflake for pricing data, prefer broad filters (date range, asset class) over
large IN-lists of identifiers. If a BigQuery result returns more than ~20 securities, query
Snowflake for the full pricing universe for that date and match in your analysis rather than
passing all CUSIPs into a single WHERE clause.

NEXUS provides: security prices, fundamentals, corporate actions, benchmark returns,
index constituents, interest rate curves (SOFR, Fed Funds, Treasuries), economic indicators,
FX spot rates, credit spreads, and volatility surfaces.
"""

_kc_tools = [search_entries, get_context, run_sql]
if SNOWFLAKE_ENABLED:
    _kc_tools.append(query_snowflake)

_kc_instruction = SYSTEM_INSTRUCTION
if SNOWFLAKE_ENABLED:
    _kc_instruction += SNOWFLAKE_PROMPT_EXTENSION

root_agent = Agent(
    name="fsi_kc_agent",
    model="gemini-2.5-flash",
    instruction=_kc_instruction,
    tools=_kc_tools,
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
