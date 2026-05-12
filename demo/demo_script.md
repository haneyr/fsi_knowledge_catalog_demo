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

## Setup Checklist

- [ ] Deploy all three agents to Vertex AI Agent Engine
- [ ] Verify `post_deploy.sh` completed successfully
- [ ] Open Knowledge Catalog UI in a browser tab (Dataplex > Knowledge Catalog)
- [ ] Open BigQuery console in another tab
- [ ] Have `demo_questions.md` ready for reference
- [ ] Test each agent with at least one question before the demo

## Environment Variables

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export DATAPLEX_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
```

## Talking Points by Slide

### "Why Knowledge Catalog for Agents?"
- Agents need to understand data semantics, not just schemas
- Business glossary gives agents domain vocabulary
- Data quality scores tell agents which data to trust
- Lineage tells agents where data comes from
- Sensitivity classifications tell agents what to protect

### "The Scale Problem"
- 150+ tables across 3 source systems (ATLAS, FORTUNA, ARGUS)
- 40 bronze, 40 silver, 20 gold, plus reference, staging, snapshots
- Cross-domain: retail banking + wealth management + finance & risk
- No single human knows all the tables — and neither can a naive agent

### "The Knowledge Catalog Solution"
- Context API provides rich metadata at query time
- MCP server enables any agent framework to use KC as a tool
- Glossary terms standardize business vocabulary (80+ FSI terms)
- Data products organize assets for consumption
- Data quality rules ensure trust in the data

### "Business Impact"
- Move from single-use agents to enterprise agent frameworks
- Reduce agent development time (no more hardcoding table lists)
- Improve accuracy on cross-domain queries
- Enable non-technical users to build agents against governed data
- Scale from 5 tables to 500 without rewriting the agent
