# [Retail] Northwind Retail Group — Knowledge Catalog Demo Script & Runtime Handoff

## 1. Runtime State (Not Stored in Git)

### Cloud Run Service
| Property | Value |
|---|---|
| **GCP Project** | `alitch-ca-demo` (`98236392654`) |
| **Service Name** | `retail-kc-demo-ui-live` |
| **Region** | `us-central1` |
| **Live Revision** | `retail-kc-demo-ui-live-00015-dkx` (`minScale: 1`, rollback: `retail-kc-demo-ui-live-00013-qvw`) |
| **Canonical URL** | `https://retail-kc-demo-ui-live-98236392654.us-central1.run.app` |
| **Regional Alias URL** | `https://retail-kc-demo-ui-live-esoohbbsma-uc.a.run.app` |

### Vertex AI Agent Engine (`reasoningEngines` in `us-central1`)
| Tier | Display Name | ReasoningEngine ID | Full Resource Name |
|---|---|---|---|
| **Basic** | `[Retail] retail-agent-basic` | `2946493525224587264` | `projects/98236392654/locations/us-central1/reasoningEngines/2946493525224587264` |
| **Scaled** | `[Retail] retail-agent-scaled` | `1975967805526245376` | `projects/98236392654/locations/us-central1/reasoningEngines/1975967805526245376` |
| **KC-Guided** | `[Retail] retail-agent-kc` | `8060330902103785472` | `projects/98236392654/locations/us-central1/reasoningEngines/8060330902103785472` |

### Secret Manager Key Names (Names Only — Never Commit Values)
- `retail-basic-agent-id` (stores Basic Agent `reasoningEngine` resource ID)
- `retail-scaled-agent-id` (stores Scaled Agent `reasoningEngine` resource ID)
- `retail-kc-agent-id` (stores KC-Guided Agent `reasoningEngine` resource ID)
- `retail-oauth-client-id` (stores OAuth 2.0 Web Client ID for the live Cloud Run UI)

### OAuth 2.0 Client Configuration & Authorized JS Origins
- **OAuth Client ID Reference**: Stored in Secret Manager key `retail-oauth-client-id` (never committed to git; injected at deploy time by `website-live/deploy.sh` via `gcloud secrets versions access latest --secret=retail-oauth-client-id --project=alitch-ca-demo`).
- **Authorized JavaScript Origins** (both must be registered on the OAuth 2.0 Web Client in Google Cloud Console → APIs & Services → Credentials):
  1. `https://retail-kc-demo-ui-live-98236392654.us-central1.run.app`
  2. `https://retail-kc-demo-ui-live-esoohbbsma-uc.a.run.app`

---

## 2. Demo Click Path

1. **`Basic` → `Customer & Loyalty` → `Loyalty Tiers`**
   - **What happens:** Basic Agent has 5 curated Gold tables hardcoded in its prompt (`retail_gold_nokc`). On a straightforward single-table question, it queries `gold_customer_360` and returns loyalty tier counts and balances cleanly.
   - **Talking point:** *"In a narrow prototype with 5 hand-picked Gold tables, a basic prompt works fine."*

2. **`Basic` → `Merchandising` → `Governed Markdown Plan`**
   - **What happens:** Basic Agent hits its ceiling — it only sees 5 Gold summary tables and has zero access to SKU/store-level inventory positions, markdown risk, data quality rules, or business glossary definitions.
   - **Talking point:** *"As soon as merchandising asks for a governed markdown plan, the prototype fails because it lacks table coverage and governance context."*

3. **`Scaled` → `Merchandising` → `Markdown Exposure`**
   - **What happens:** Scaled Agent is given all 128 `_nokc` tables across ORION POS, LUMEN Commerce, and HELIOS ERP with **no** Knowledge Catalog metadata. It burns multiple tool turns probing `INFORMATION_SCHEMA` / SQL across raw tables and cannot verify data quality rules or official glossary formulas (`GMROI`, `MVaR`, `Markdown Exposure`).
   - **Talking point:** *"Giving an agent all 128 enterprise tables without a semantic catalog causes schema-guessing and blind trust in unvalidated numbers."*

4. **`KC` → `Cross-Cloud` → `Price Gaps`**
   - **What happens:** KC-Guided Agent uses Dataplex Knowledge Catalog MCP (`search_entries`, `lookup_context`), bridges BigQuery (`gold_assortment_performance`) with NEXUS Snowflake (`COMPETITOR_PRICE_INDEX` via `query_snowflake`), streams tokens live over ADK SSE (`~3.7s` to first visible token), illuminates 6 active graph connections (including cyan cross-cloud NEXUS edges and a floating green glossary pill), and outputs a structured 4-section brief (`Data discovery`, `Finding`, `Governance Context`, `Recommendations`).
   - **Talking point:** *"Knowledge Catalog turns 128 tables plus cross-cloud Snowflake datasets into a navigable semantic map with governed definitions and lineage."*

5. **`Dataplex` → `Glossary` → `GTIN-13`**
   - **What happens:** Click the glossary deep-link in the KC response (or open `retail-northwind-glossary-us` in the Dataplex Knowledge Catalog console) to inspect `[Retail] Global Trade Item Number (GTIN-13)`.
   - **Talking point:** *"Every glossary badge and table link in the UI resolves directly to the live Dataplex entry—showing the HTML business definition, stewardship aspects, linked BigQuery columns, and the 13-digit GS1 data quality rule."*

---

## 3. Rebuild Quirks & Workarounds

1. **BigQuery & Python SDK mTLS Environment Variables**
   - In workstation/cloud environments where context-aware mTLS client certificates are enabled in gcloud config but no cert is provisioned, `bq` and Python SDK calls fail unless mTLS client certificates are disabled:
     ```bash
     export GOOGLE_API_USE_CLIENT_CERTIFICATE=false
     export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false
     ```
   - All top-level deployment scripts export both variables automatically.

2. **`--condition=None` on Project IAM Bindings**
   - `alitch-ca-demo` has conditional IAM bindings in its project policy. Every non-conditional `gcloud projects add-iam-policy-binding` command must explicitly pass `--condition=None`, otherwise `gcloud` prompts interactively or fails in non-interactive shells.

3. **Data Catalog / Dataplex Policy Tag Taxonomy Display-Name Collision Workaround**
   - Policy Tag Taxonomy `display_name` values must be unique across the multi-region (`us`). To avoid `409 ALREADY_EXISTS` collisions with residual or parallel taxonomies, `scripts/16_create_policy_tags.py` and `post_deploy.sh` scope the display name via `RETAIL_TAXONOMY_DISPLAY_NAME="Retail Demo Sensitivity Taxonomy - alitch"` (active taxonomy resource: `projects/alitch-ca-demo/locations/us/taxonomies/6328323030724665961`) and lookup existing taxonomies by display name for idempotency.

---

## 4. End-to-End Rebuild Order

Run the deployment scripts in this exact sequence from the repository root (` retail-refactor` branch):

```bash
# 1. Governed BigQuery datasets & 128 medallion/reference/dashboard tables
bash deploy-bq.sh

# 2. Ungoverned shadow (_nokc) BigQuery datasets & tables for Basic/Scaled agents
bash deploy-bq-nokc.sh

# 3. Dataplex Knowledge Catalog governance layer (entry types, aspects, glossary,
#    data products, lineage, DQ rule library, 360 DataScans, dirty data injection, policy tags)
bash post_deploy.sh

# 4. Vertex AI Agent Engine deployment (basic, scaled, kc) + Secret Manager IDs + IAM bindings
bash agents/deploy_agents.sh

# 5. Live Cloud Run web UI deployment (reads agent IDs & OAuth Client ID from Secret Manager)
bash website-live/deploy.sh
```
