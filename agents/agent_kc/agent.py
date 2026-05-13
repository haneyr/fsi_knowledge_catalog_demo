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
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.cloud import bigquery
import google.auth
import google.auth.transport.requests
import requests as http_requests

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
DATAPLEX_PROJECT = os.environ.get("DATAPLEX_PROJECT", PROJECT_ID)
DATAPLEX_URL = "https://dataplex.googleapis.com/v1"

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


def _get_token():
    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _dataplex_request(method, path, body=None):
    headers = {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}
    url = f"{DATAPLEX_URL}/{path}"
    if method == "GET":
        resp = http_requests.get(url, headers=headers, params=body)
    else:
        resp = http_requests.post(url, headers=headers, json=body)
    if resp.status_code in (200, 201):
        return resp.json() if resp.text.strip() else {}
    return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}


@FunctionTool
def search_entries(query: str) -> str:
    """Search for data entries in Knowledge Catalog using semantic search.

    Use this to discover tables, views, and other data assets by topic.
    Examples: "customer deposits", "loan delinquency", "portfolio performance"
    """
    try:
        result = _dataplex_request("POST",
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
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"Search error: {str(e)}"


@FunctionTool
def lookup_entry(entry_name: str) -> str:
    """Look up details about a specific data entry by its full resource name.

    Use the entry name returned from search_entries.
    """
    try:
        result = _dataplex_request("GET", entry_name)
        if "error" in result:
            return f"Lookup error: {result['error']}"

        fqn = result.get("fullyQualifiedName", "")
        entry_type = result.get("entryType", "").split("/")[-1] if result.get("entryType") else ""
        source = result.get("entrySource", {})

        lines = [f"**{fqn}** ({entry_type})\n"]
        if source.get("description"):
            lines.append(f"Description: {source['description']}")
        if source.get("system"):
            lines.append(f"System: {source['system']}")

        aspects = result.get("aspects", {})
        for key, aspect in aspects.items():
            aspect_name = key.split(".")[-1]
            data = aspect.get("data", {})
            if data:
                lines.append(f"\n**{aspect_name}:**")
                for k, v in data.items():
                    if isinstance(v, dict) and "fields" in v:
                        lines.append(f"  Schema fields: {len(v['fields'])}")
                    elif isinstance(v, list):
                        lines.append(f"  {k}: {len(v)} items")
                    else:
                        lines.append(f"  {k}: {v}")

        return "\n".join(lines)
    except Exception as e:
        return f"Lookup error: {str(e)}"


@FunctionTool
def lookup_context(resource_name: str) -> str:
    """Get rich context metadata for a BigQuery table including glossary terms,
    data quality scores, lineage, and custom aspects.

    Pass a fully qualified BigQuery resource like:
    //bigquery.googleapis.com/projects/PROJECT/datasets/DATASET/tables/TABLE
    """
    try:
        result = _dataplex_request("GET",
            f"projects/{DATAPLEX_PROJECT}/locations/us:lookupContext",
            {"resourceName": resource_name}
        )
        if "error" in result:
            return f"Context lookup error: {result['error']}"

        lines = [f"Context for: {resource_name}\n"]

        context = result.get("context", {})
        if not context:
            context = result

        glossary_terms = context.get("glossaryTerms", result.get("glossaryTerms", []))
        if glossary_terms:
            lines.append(f"**Glossary Terms ({len(glossary_terms)}):**")
            for term in glossary_terms[:10]:
                term_name = term.get("name", "").split("/")[-1]
                desc = term.get("description", "")
                lines.append(f"  - {term_name}: {desc[:200]}")

        dq = context.get("dataQuality", result.get("dataQuality", {}))
        if dq:
            lines.append(f"\n**Data Quality:**")
            score = dq.get("score", dq.get("overallScore"))
            if score:
                lines.append(f"  Overall score: {score}")
            dimensions = dq.get("dimensions", [])
            for dim in dimensions:
                lines.append(f"  {dim.get('name', 'unknown')}: {dim.get('score', 'N/A')}")

        lineage = context.get("lineage", result.get("lineage", {}))
        if lineage:
            lines.append(f"\n**Lineage:**")
            sources = lineage.get("sources", [])
            for src in sources[:5]:
                lines.append(f"  Source: {src.get('fullyQualifiedName', src.get('name', 'unknown'))}")

        aspects = context.get("aspects", result.get("aspects", {}))
        for key, aspect in aspects.items():
            if "dataplex-types" in key:
                continue
            aspect_name = key.split(".")[-1]
            data = aspect.get("data", {})
            if data:
                lines.append(f"\n**{aspect_name}:**")
                for k, v in data.items():
                    if not isinstance(v, (dict, list)):
                        lines.append(f"  {k}: {v}")

        if len(lines) <= 1:
            lines.append("No rich context available. Try using search_entries to find the correct entry name, then lookup_entry.")

        return "\n".join(lines)
    except Exception as e:
        return f"Context lookup error: {str(e)}"


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
    tools=[search_entries, lookup_entry, lookup_context, run_sql],
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
