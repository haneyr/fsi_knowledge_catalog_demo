# P0 Reconnaissance Report (`RECON.md`)

## 1. Repository Map & File Inventory (238 Files)

The repository (`knowledge_catalog_demo`) contains **238 non-git files** organized into 8 functional areas. All business domain content is stored directly in SQL files, Python governance scripts (as in-code dicts/lists rather than external YAML/JSON manifests), agent prompts, and static frontend assets.

| Area | Path(s) | Files | Purpose & DDL / Manifest Location |
|---|---|---:|---|
| **BigQuery DDL & Seed Data** | `modules/bigquery-{medallion,reference,dashboards}/sql/` | 128 `.sql` | Pure BigQuery `CREATE OR REPLACE TABLE/VIEW ... AS SELECT` statements generating deterministic synthetic data (`UNNEST(GENERATE_ARRAY(...))`). |
| **Terraform / Terragrunt** | `modules/*/main.tf`, `stacks/*/`, `env/*.tfvars`, `terragrunt.hcl` | 27 | Mirrors BQ datasets/tables, Dataplex entry/aspect types, taxonomy, APIs, IAM. *(Not executed in bq CLI path, refactored for parity).* |
| **Governance Scripts** | `scripts/*.py`, `post_deploy.sh` | 19 | 15-step Python pipeline calling Dataplex, Data Lineage, BigQuery, and Data Catalog REST APIs directly via `common.py`. |
| **ADK Agents** | `agents/agent_{basic,scaled,kc}/`, `agents/deploy_agents.sh` | 16 | 3 Vertex AI Agent Engine (`google.adk`) agents + deployment script. |
| **Live Demo Website** | `website-live/` (`app.py`, `static/*`, `deploy.sh`, `Dockerfile`) | 9 | Flask + WebSocket backend streaming Agent Engine events to an interactive 3D/canvas frontend (`visualization.js`, `chat.js`, `static-responses.json`). |
| **Demo & Evaluation** | `demo/`, `eval/` | 11 | `demo_questions.md`, `demo_script.md`, `agent_comparison.ipynb`, and ADK evaluation harness (`test_cases.yaml`, `run_eval.py`). |
| **Deploy & Lifecycle Scripts** | `deploy*.sh`, `bootstrap.sh`, `clean_up.sh`, `cloudbuild*.yaml` | 15 | Shell orchestrators (`deploy-bq.sh`, `deploy-bq-nokc.sh`, `deploy-full.sh`, `clean_up.sh`) and Cloud Build configs. |
| **Snowflake (Optional/Skipped)** | `snowflake/` | 8 | NEXUS 4th source system scripts. *(Skipped per scope lock; code paths preserved).* |

### Top 15 Largest Content Files (Where Domain Copy Lives)
1. [`scripts/12_enrich_glossary.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/12_enrich_glossary.py) (134 KB) — Rich HTML overviews for 83 glossary terms.
2. [`scripts/01_create_glossary.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/01_create_glossary.py) (53 KB) — 10 L1 + 18 L2 categories, 84 terms, 10 contacts, 14 synonym links, 67 related links, 181 column definition links.
3. [`website-live/app.py`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/app.py) (29.5 KB) — WebSocket server, OAuth token verification, Agent Engine streaming parser.
4. [`website-live/static/styles.css`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/styles.css) (27.5 KB) — UI styling.
5. [`website-live/static/visualization.js`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/visualization.js) (27.0 KB) — Point-cloud metadata & table node visualization.
6. [`website-live/static/static-responses.json`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/static-responses.json) (24.7 KB) — Pre-cached fallback responses for demo scenarios.
7. [`website-live/static/chat.js`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/chat.js) (23.5 KB) — Scenario picker, chat streaming, and comparison cards.
8. [`demo/agent_comparison.ipynb`](file:///home/aelitchfield/knowledge_catalog_demo/demo/agent_comparison.ipynb) (19.5 KB) — Side-by-side notebook comparing the 3 agents.
9. [`modules/dataplex-entry-types/main.tf`](file:///home/aelitchfield/knowledge_catalog_demo/modules/dataplex-entry-types/main.tf) (17.6 KB) — Terraform definitions of entry types, aspect types, entry groups.
10. [`README.md`](file:///home/aelitchfield/knowledge_catalog_demo/README.md) (16.5 KB) — Architecture & deployment guide.
11. [`eval/test_cases.yaml`](file:///home/aelitchfield/knowledge_catalog_demo/eval/test_cases.yaml) (16.0 KB) — Evaluation test cases and expected SQL/answers.
12. [`demo/demo_questions.md`](file:///home/aelitchfield/knowledge_catalog_demo/demo/demo_questions.md) (15.0 KB) — Prompt scenarios, failure analyses, and console walkthrough notes.
13. [`website-live/static/index.html`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/index.html) (14.8 KB) — Main UI layout and branding copy.
14. [`scripts/00_create_dataplex_infra.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/00_create_dataplex_infra.py) (14.0 KB) — Entry types (9), marker aspects (7), custom aspects (7), entry groups (3).
15. [`agents/agent_kc/agent.py`](file:///home/aelitchfield/knowledge_catalog_demo/agents/agent_kc/agent.py) (13.6 KB) — KC-Guided agent with Dataplex discovery tools and system prompt.

---

## 2. Actual Repo Counts vs. README Claims (Delta Report)

Per instruction ("If the repo's actual counts differ from the README, trust the repo and report the delta"), below is the exact comparison:

| Artifact | README Claim | Actual Repo Count | Notes / Explanation of Delta |
|---|---:|---:|---|
| **BigQuery Tables & Views** | 128 | **128** | Exact match: 40 bronze + 40 silver + 20 gold + 8 dashboard views + 10 reference + 5 staging + 3 snapshots + 2 audit. |
| **Bronze Source Split** | 14 / 13 / 13 | **14 / 13 / 13** | Exact match in [`scripts/07_create_lineage.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/07_create_lineage.py) (`atlas_src`=14, `fortuna_src`=13, `argus_src`=13). Note: [`scripts/03_create_source_entries.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/03_create_source_entries.py) registers 13 representative custom entries with full schemas (5 + 4 + 4). |
| **BigQuery Datasets** | 10 | **9 + 1 + 8 (`_nokc`)** | [`deploy-bq.sh`](file:///home/aelitchfield/knowledge_catalog_demo/deploy-bq.sh) creates 9 `fsi_*` datasets; the 10th is `agent_analytics` (created by TF/agents). [`deploy-bq-nokc.sh`](file:///home/aelitchfield/knowledge_catalog_demo/deploy-bq-nokc.sh) creates 8 `fsi_*_nokc` shadow datasets (128 tables). |
| **Glossary Categories** | 28 (or 10 L1 + 20 L2) | **28** | 10 L1 categories + 18 L2 subcategories = 28 total categories in [`scripts/01_create_glossary.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/01_create_glossary.py). |
| **Glossary Terms** | 83 | **84 (83 enriched)** | [`scripts/01_create_glossary.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/01_create_glossary.py) creates **84** terms (72 core + 12 abbreviations). [`scripts/12_enrich_glossary.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/12_enrich_glossary.py) enriches **83** terms (all except `aml`). We will enrich all 84 in Retail. |
| **Glossary-to-Column Links** | 77 | **181** | `DEFINITION_LINKS` in [`scripts/01_create_glossary.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/01_create_glossary.py) contains **181** `(term_id, dataset, table, column)` tuples (plus 14 synonym links and 67 related-term links). |
| **Lineage Links & Processes** | 98 links / 5 processes | **125 links / 5 processes** | [`scripts/07_create_lineage.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/07_create_lineage.py) creates 5 processes with 14 (P1) + 13 (P2) + 13 (P3) + 40 (P4: Bronze→Silver) + 45 (P5: Silver→Gold across 17 gold tables) = **125 links**. (98 counted Gold tables once instead of per silver input edge). |
| **Data Scans** | 300+ (100 tables) | **308** | [`scripts/02_create_scans.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/02_create_scans.py): 100 Profile + 100 Table Insights + 100 Quality + 8 Dataset Insights = **308 scans**. |
| **Data Products** | 5 | **5** | Exact match in [`scripts/05_create_data_products.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/05_create_data_products.py). |
| **Custom Aspect Types** | 7 | **7** (+7 marker aspects) | Exact match in [`scripts/00_create_dataplex_infra.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/00_create_dataplex_infra.py). |
| **Rule Library Templates** | 10 | **10** | Exact match in [`scripts/10_create_rule_library.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/10_create_rule_library.py). |
| **Personas / Simulated Queries** | 5 personas / 24 queries | **5 / 24** | Exact match in [`scripts/09_simulate_queries.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/09_simulate_queries.py). |
| **Dirty Data Injections** | 6 tables | **6** | [`scripts/15_inject_dirty_data.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/15_inject_dirty_data.py) injects intentional DQ violations into 6 bronze tables. |
| **Policy Tags** | 4 tags / 32 columns | **4 / 32** | [`scripts/16_create_policy_tags.py`](file:///home/aelitchfield/knowledge_catalog_demo/scripts/16_create_policy_tags.py). |

---

## 3. Git Remotes Verification

Confirmed matching repository context:
- **Current branch**: `main` (clean except `AGENTS.md`)
- **`origin`**: `https://github.com/aelitchfield/knowledge_catalog_demo.git` (safe to push when approved)
- **`upstream`**: `https://github.com/haneyr/fsi_knowledge_catalog_demo.git` (NEVER push)

---

## 4. Read-Only Pre-Flight of `alitch-ca-demo`

| Check | Status / Finding | Action / Mitigation |
|---|---|---|
| **Project Metadata & Billing** | `projectId: alitch-ca-demo`, `projectNumber: 98236392654`, `lifecycleState: ACTIVE`, `billingEnabled: true` (`018FA4-AF46D9-9DE300`). Active account `admin@aelitchfield.altostrat.com` holds `roles/owner`, `roles/bigquery.admin`, `roles/dataplex.admin`. | Ready. |
| **Required APIs (11)** | `bigquery`, `dataplex`, `datalineage`, `aiplatform`, `cloudresourcemanager`, `iam`, `cloudaicompanion`, `run`, `cloudbuild`, `secretmanager`, `artifactregistry`, `datacatalog` are **all already enabled**. | P2 API enable step will be a fast idempotent no-op. |
| **Org Policies (2)** | Both policies are **already overridden** on project `98236392654`:<br>• `iam.allowedPolicyMemberDomains` → `allowAll: true`<br>• `run.managed.requireInvokerIam` → `enforce: false` | Public `allUsers` Cloud Run invoker binding is permitted! |
| **Agent Engine (`us-central1`)** | Active and responsive (`v1beta1/.../reasoningEngines` lists 2 existing `AmFam_Portfolio_Intelligence_Agent` instances). | Ready for `retail-agent-{basic,scaled,kc}` deployment. |
| **`bq` CLI mTLS Bug Diagnosis** | Plain `bq ls` crashes with `MutualTLSChannelError: Cert provider command returns non-zero status code -11` on Python 3.14 because gcloud's CBA cert helper segfaults. Setting `GOOGLE_API_USE_CLIENT_CERTIFICATE=false CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false` fixes `bq` CLI completely. | Export both env vars at the top of `deploy-bq.sh`, `deploy-bq-nokc.sh`, `deploy-full.sh`, and `clean_up.sh`. |
| **Existing Resources & Collisions** | `alitch-ca-demo` is a shared demo project containing prior `fsi_*` and `insurance_*` deployments:<br>• **BQ Datasets**: `fsi_*`, `fsi_*_nokc`, `insurance_*`, `agent_analytics` (empty), etc. **Zero `retail_*` datasets exist.**<br>• **EntryGroups (`us`)**: `atlas-core-banking`, `fortuna-wealth-mgmt`, `argus-finance-risk`, `snowflake-nexus`.<br>• **EntryTypes & AspectTypes (`global`)**: `db2-*`, `temenos-*`, `sap-*`, `snowflake-*`, `fsi-*` exist.<br>• **Glossaries (`us`)**: `meridian-national-bank-glossary-us`.<br>• **DataProducts (`us`)**: `ins-*`, `testing-product`.<br>• **Taxonomies (`us`)**: `FSI Data Classification`. | **Zero `retail_*` / `retail-` collisions.** Per Rule 11 (never overwrite existing resources) and the Naming Standard, all new EntryTypes (`retail-ibmi-*`, `retail-sfcc-*`, `retail-sap-*`), AspectTypes (`retail-*`), EntryGroups (`retail-orion-*`, `retail-lumen-*`, `retail-helios-*`), Glossary (`retail-northwind-glossary-us`), DataProducts (`retail-*`), and BQ datasets (`retail_*`, including `retail_agent_analytics`) will use the `retail` prefix so existing `fsi_*` / `sap-*` / `db2-*` resources remain untouched. |
