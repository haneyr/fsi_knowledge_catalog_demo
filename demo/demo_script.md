# FSI Knowledge Catalog Demo — Walkthrough Script

## Narrative Arc

> "Every bank wants AI agents. But most agents break at enterprise scale.
> Knowledge Catalog is how you fix that."

### Act 1: The Promise (2 min)
Show Agent 1 (Basic) answering simple questions about 5 tables.
It works perfectly — fast, accurate, well-formatted.

**Key message:** "When an agent knows its data, it works great."

### Act 2: The Problem (3 min)
Show Agent 2 (Scaled) with the same questions — it still works.
Then ask cross-domain or ambiguous questions.
The agent picks wrong tables, hallucinates columns, gives incomplete answers.

**Key message:** "But real banks don't have 5 tables. They have hundreds,
across multiple systems. The agent drowns in complexity."

### Act 3: The Solution (5 min)
Show Agent 3 (KC-Guided) with the hard questions.
Walk through its reasoning:
1. It searches Knowledge Catalog semantically
2. It discovers the right tables (sometimes ones the analyst didn't know about)
3. It reads metadata — glossary definitions, data quality scores, lineage
4. It generates accurate SQL grounded in real metadata
5. It cites its sources — glossary terms, DQ scores, sensitivity classifications

**Key message:** "Knowledge Catalog gives the agent a map.
Instead of guessing, it discovers. Instead of hallucinating, it reasons."

### Act 4: Multi-Cloud (5 min) — *Snowflake required*
Show the KC agent answering questions that span BigQuery and Snowflake.
The agent discovers that some data lives in an external vendor's Snowflake
database, queries both platforms, and combines the results.

Walk through the cross-platform flow:
1. It searches Knowledge Catalog and finds entries from *both* BigQuery and Snowflake
2. It reads metadata to understand both schemas and identify join keys
3. It queries BigQuery for internal data (portfolios, NIM, risk)
4. It queries Snowflake for external market data (prices, benchmarks, yield curves)
5. It combines the results and cites both source systems

**Key message:** "The agent didn't know in advance that pricing data lives in
Snowflake. Knowledge Catalog told it where to look — across clouds."

---

## Before the Demo

### Check your deployment

```bash
# Verify all agents are deployed
curl -s https://YOUR-CLOUD-RUN-URL/api/config | python3 -m json.tool
```

You should see:
- `"live_mode": true` — all 3 agents connected
- `"agents": {"basic": true, "scaled": true, "kc": true}`

### Check Snowflake (optional)

If you have Snowflake configured, the config response also shows:
- `"snowflake_enabled": true`
- `"snowflake_tables": [...]` — 10 NEXUS market data tables

If `snowflake_enabled` is `false` or missing, skip Act 4 and the Multi-Cloud
narrative tab. The demo works perfectly without it — Acts 1-3 are the core story.

### Setup Checklist

- [ ] Deploy all three agents to Vertex AI Agent Engine
- [ ] Verify `post_deploy.sh` completed successfully
- [ ] Open Knowledge Catalog UI in a browser tab
- [ ] Open BigQuery console in another tab
- [ ] Test each agent with at least one question before the demo
- [ ] If Snowflake: verify `snowflake_enabled: true` in `/api/config`

---

## Demo Flow

### Without Snowflake (~20 minutes)

| Step | What to show | Time |
|---|---|---|
| 1 | **Baseline:** All 3 agents answer "Top 5 customers" → all succeed | 2 min |
| 2 | **Baseline:** "Loan portfolio by type" → all succeed → "not a model issue" | 1 min |
| 3 | **Disambiguation:** "Suspicious activity trends" → Scaled picks wrong table → KC finds right one | 3 min |
| 4 | **Cross-domain:** "HNW total exposure" → Scaled misses cross-domain → KC discovers gold table | 3 min |
| 5 | **Regulatory:** "Basel III capital requirements" → KC cites glossary definitions & regulatory context | 3 min |
| 6 | **Data trust:** "FICO score — should we trust it?" → KC cites data quality rules | 3 min |
| 7 | **Impossible:** "CRE stress test" → Scaled fails → KC multi-table reasoning | 3 min |
| 8 | **Console:** Walk through glossary, lineage, DQ in Knowledge Catalog UI | 2 min |

### With Snowflake (~28 minutes)

Run steps 1-8 above, then continue:

| Step | What to show | Time |
|---|---|---|
| 9 | Switch to **Multi-Cloud** narrative tab. Point out the Snowflake cluster in the visualization. | 1 min |
| 10 | **Benchmark comparison:** "How do portfolios compare to benchmarks?" → agent queries both BQ and Snowflake | 3 min |
| 11 | **Yield curve + NIM:** "Show SOFR and Treasury yields alongside our NIM" → cross-platform rate analysis | 3 min |
| 12 | **FX rates:** "Compare internal FX rates with NEXUS spot rates" → reconciliation across platforms | 1 min |

---

## What to Highlight

### After Every KC Agent Answer (Acts 1-3)

1. **"It searched before it queried"** — show the `search_entries` tool call chip
2. **"It chose the right table and explained why"** — table selection rationale citing metadata
3. **"It cited the glossary"** — business term definitions in the response
4. **"It checked data quality"** — DQ rules and trust assessment
5. **"It traced the lineage"** — source system attribution (ATLAS / FORTUNA / ARGUS)
6. **"It flagged sensitivity"** — data classification level in the response

### After Multi-Cloud Answers (Act 4)

1. **"It searched and found two platforms"** — show the search results spanning BQ and Snowflake
2. **"It used the right tool for each platform"** — `run_sql` for BigQuery, `query_snowflake` for Snowflake
3. **"It combined the results"** — unified analysis citing both source systems
4. **"Look at the visualization"** — cross-platform dashed lines connecting BQ rings to the Snowflake cluster
5. **"No hardcoded connections"** — the agent discovered NEXUS data through Knowledge Catalog metadata, not a pre-built integration

### Visualization Talking Points

- **Snowflake cluster:** "The cyan nodes in the bottom right are tables from NEXUS, an external market data vendor running on Snowflake. They appeared because Knowledge Catalog catalogs them alongside our BigQuery data."
- **Cross-platform lines:** "The dashed cyan lines show the agent querying data across both platforms in a single response."
- **Multi-Cloud tab:** "These preset questions are designed to require data from both BigQuery and Snowflake. The agent figures out which platform to query based on what Knowledge Catalog tells it."

---

## Talking Points by Slide

### "Why Knowledge Catalog for Agents?"
- Agents need to understand data semantics, not just schemas
- Business glossary gives agents domain vocabulary
- Data quality scores tell agents which data to trust
- Lineage tells agents where data comes from
- Sensitivity classifications tell agents what to protect

### "The Scale Problem"
- 128+ tables across 3 source systems (ATLAS, FORTUNA, ARGUS)
- 40 bronze, 40 silver, 20 gold, plus reference, staging, snapshots
- Cross-domain: retail banking + wealth management + finance & risk
- No single human knows all the tables — and neither can a naive agent

### "The Knowledge Catalog Solution"
- Context API provides rich metadata at query time
- MCP server enables any agent framework to use KC as a tool
- Glossary terms standardize business vocabulary (80+ FSI terms)
- Data products organize assets for consumption
- Data quality rules ensure trust in the data

### "Multi-Cloud Data Discovery" *(Snowflake required)*
- Knowledge Catalog catalogs data across BigQuery *and* Snowflake
- The agent discovers external market data without being told where it lives
- Cross-platform queries combine internal analytics with external vendor data
- Same metadata governance (glossary links, aspects, lineage) applied to both platforms
- Extensible to other platforms (Databricks, etc.) using the same pattern

### "Business Impact"
- Move from single-use agents to enterprise agent frameworks
- Reduce agent development time (no more hardcoding table lists)
- Improve accuracy on cross-domain queries
- Enable non-technical users to build agents against governed data
- Scale from 5 tables to 500 — across any cloud — without rewriting the agent
