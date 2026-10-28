# STATE.md — Retail KC Demo Refactor Memory

## RESUME HERE — 2026-10-24 (Phase Q1 Deployed & Verified; Phase Q2 Abandoned & Rolled Back to Q1)

- **Q1 COMPLETE and deployed** (SSE streaming, `3.7s` to first token on Cloud Run `retail-kc-demo-ui-live-00015-dkx` and `retail-agent-kc` `8060330902103785472`).
- **Q2 ABANDONED** — multi-redeploy thrash, rolled back [`agents/agent_kc/agent.py`](file:///home/aelitchfield/knowledge_catalog_demo/agents/agent_kc/agent.py) to Q1 prompt (`075635c`) and redeployed `retail-agent-kc`.
- **Remaining**: demo-path verification of 4 chips, then `git push`.
- **Demo click path**: `Basic→Merch#1`, `Scaled→Merch#4`, `KC→Merch#4`, `KC→Cross-Cloud#2`, plus Dataplex glossary `GMROI`.

### Phase Q1 Details
- **Phase Q1 Status (Enable ADK SSE Streaming)**: **COMPLETE & VERIFIED**.
  - Updated [`agents/agent_kc/agent.py`](file:///home/aelitchfield/knowledge_catalog_demo/agents/agent_kc/agent.py) to default `RunConfig.streaming_mode = StreamingMode.SSE` and redeployed `retail-agent-kc` (`8060330902103785472`) via [`tools/deploy_kc_agent.py`](file:///home/aelitchfield/knowledge_catalog_demo/tools/deploy_kc_agent.py).
  - Updated [`website-live/app.py`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/app.py) (`_parse_stream_chunk` with `sse_mode=True` and `"run_config": {"streaming_mode": "sse"}` for `kc`) so partial token deltas (`partial=True`) stream live to the client while the turn-end aggregated duplicate (`partial=False`) and duplicate `partial=True` `function_call` events are filtered out.
  - Updated [`website-live/static/chat.js`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/chat.js) and [`website-live/static/index.html`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/index.html) (`?v=11`) and deployed Cloud Run revision `retail-kc-demo-ui-live-00015-dkx` (rollback: `retail-kc-demo-ui-live-00013-qvw`).
  - Re-ran P2 instrumentation on `Cross-Cloud #2` via [`tools/verify_phase_q1.py`](file:///home/aelitchfield/knowledge_catalog_demo/tools/verify_phase_q1.py) (`logs/q1_verify.json`):
    - **Time to first visible character (`first_token`)**: **`3,716 ms` phase (`27,107 ms` cumulative from click)** — down from `21,065 ms` phase (`44,860 ms` cumulative) in Phase P2 (meets `< 5s` phase target; first character appears **17.8s earlier**).
    - **`last_token - first_token`**: **`7,418 ms`** across **28 live streamed chunks** (vs `0 ms` / 1 chunk in Phase P2).
    - **Total time**: `36,432 ms` (down from `45,411 ms`), `6` graph edges drawn progressively.
- **Phase P Status**: **COMPLETE & VERIFIED**.
  - **P1 (Cloud Run cold starts)**: `retail-kc-demo-ui-live` in `us-central1` already had `autoscaling.knative.dev/minScale: '1'` (before: `1`, after: `1`).
  - **P2 (Per-phase elapsed-ms instrumentation in [`website-live/app.py`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/app.py))**:
    - Replaced `resp.iter_lines()` (which buffered `<512B` `tool_call` lines in `urllib3`) with unbuffered HTTP chunk line streaming [`_iter_stream_lines(resp)`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/app.py#L260-L273) (`resp.raw.stream(65536, decode_content=True)`), and added `[LATENCY]` / `[LATENCY_SUMMARY]` logging + `phase_timings` telemetry across `session_create`, each `tool_call`, each `tool_response`, `first_token`, and `last_token`.
    - Measured `Merchandising #4` (`70,578 ms`) and `Cross-Cloud #2` (`45,411 ms`) via [`tools/verify_phase_p.py`](file:///home/aelitchfield/knowledge_catalog_demo/tools/verify_phase_p.py) (`logs/p_verify.json`): actual tool executions take only `0.8–2.4s` each (`10–12%` of total latency); `88–90%` of latency is LLM tool-planning turns (`5–9s` per turn after ~40 KB `lookup_context` payload, compounded when the agent makes multiple sequential `run_sql` calls) plus final answer token generation (`21–23s`, delivered in a single chunk at the end of the turn by `AdkApp.async_stream_query` so `first_token == last_token`).
  - **P3 (Progressive UI feedback in [`website-live/static/chat.js`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/chat.js) & [`website-live/static/index.html`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/index.html) `?v=10`)**:
    - Verified tool chips render incrementally at the exact moment each `tool_call` fires (`5.4s → 9.1s → 20.2s...` on Merchandising #4; `9.5s → 14.1s → 21.4s` on Cross-Cloud #2).
    - Status line progresses across all phases: `"Searching Knowledge Catalog..."` → `"Reading table metadata..."` → `"Querying BigQuery..."` / `"Querying Snowflake..."` → `"Composing answer..."`.
    - Graph edges draw progressively as each tool touches tables (`0 → 2 → 5 → 6` edges).
  - **P4 (Agent models)**: All 3 agents (`agent_basic`, `agent_scaled`, `agent_kc`) run `gemini-2.5-flash`.
  - Deployed Cloud Run revision `retail-kc-demo-ui-live-00013-qvw` (rollback: `retail-kc-demo-ui-live-00012-wsj`).
- **Phase O2 Status**: **COMPLETE & VERIFIED**.
  - Implemented the **no-agent-redeploy** bidirectional NEXUS scope gate across [`website-live/static/index.html`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/index.html), [`website-live/static/chat.js`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/chat.js), [`website-live/static/visualization.js`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/visualization.js), and [`website-live/app.py`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/app.py).
  - UI passes active `category` (`merchandising` / `customer` / `privacy` / `multicloud`) in the `/ws/chat` payload while rendering only the clean user question in the chat bubble; `app.py` isolates Vertex AI sessions per category (`f"{agent_id}:{user_id}:{cat_key}"`), appends `_INTERNAL_SCOPE_INSTRUCTION` or `_CROSS_CLOUD_SCOPE_INSTRUCTION` server-side for `kc`, and filters extracted tables by tab scope.
  - Deployed Cloud Run revision `retail-kc-demo-ui-live-00012-wsj` (rollback: `retail-kc-demo-ui-live-00011-n5f`) and verified headlessly (`tools/verify_phase_o2.py` → `logs/o2_verify.json`, `--password-store=basic --use-mock-keychain`):
    - `Merchandising #4`: `query_snowflake=N`, `NEXUS mentioned=N`, `edges=6`
    - `Customer #4`: `query_snowflake=N`, `NEXUS mentioned=N`, `edges=6`
    - `Privacy #4`: `query_snowflake=N`, `NEXUS mentioned=N`, `edges=6`
    - `Cross-Cloud #2`: `query_snowflake=Y`, `NEXUS mentioned=Y`, `edges=6` (`nexus_competitor_prices` reached)
- **Phase O1 Status**: **COMPLETE & VERIFIED**.
  - Edited [`website-live/static/index.html`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/index.html#L226-L250) to remove both the `.nexus-tab-badge` (`[Simulated connector — NEXUS reference data]`) on the `CROSS-CLOUD` tab and the `.cross-cloud-banner` DOM element (`◆ NEXUS · Snowflake (External): Simulated connector — NEXUS reference data`).
  - Known-good rollback Cloud Run revision recorded before deploy: `retail-kc-demo-ui-live-00010-877`.
  - Deployed Cloud Run revision `retail-kc-demo-ui-live-00011-n5f` and verified headlessly (`tools/verify_phase_o1.py` → `logs/o1_verify.json`, `--password-store=basic --use-mock-keychain`) across all 3 agents (`basic`, `scaled`, `kc` with `CROSS-CLOUD` active) that neither string appears in the rendered DOM while `NEXUS · Snowflake (External) (6)` legend, cyan diamonds, and dashed cluster boundary remain intact.
- **Phase L Status**: **COMPLETE** across all 16 BigQuery datasets (`retail_bronze`, `retail_silver`, `retail_gold`, `retail_reference`, `retail_dashboards`, `retail_staging`, `retail_snapshots`, `retail_audit` and `retail_bronze_nokc`, `retail_silver_nokc`, `retail_gold_nokc`, `retail_reference_nokc`, `retail_dashboards_nokc`, `retail_staging_nokc`, `retail_snapshots_nokc`, `retail_audit_nokc`).
  - `INFORMATION_SCHEMA.COLUMNS` check across all 16 datasets: **0 tables / 0 columns** with old names (`avg_sharpe_ratio`, `total_return_pct`, `unrealized_gain_loss`, `cost_basis`, `market_value`); **22 tables / 44 columns** with new names (`gmroi`, `sell_through_pct`, `markdown_exposure`, `inventory_at_cost`, `current_retail_value`).
  - `gold_assortment_performance` deduplicated to 12 unique assortments (`gmroi` = `2.08–3.85`, `sell_through_pct` = `0.4384–0.8455`); intentional DQ defects re-injected (`scripts/15_inject_dirty_data.py`) and DQ rescans triggered.
- **Next**: Verify `Merchandising #4` shows GMROI `2.0–4.0` with no FSI columns (verified in `logs/l_verify.json`: GMROI `2.08–2.44` across 5 unique seasonal assortments, zero FSI columns).
- **Then**: Phase M 40-chip sweep, Phase N demo script, then push.

### DONE
- **P0–P6 + Phases A–E + F1–F5 + Phase G1-F + Phases I-A, I-B, I-C Complete**: 18 BigQuery datasets (`10` governed `retail_*` + `8` `retail_*_nokc` shadow), 128 tables/views, 9 Dataplex governance pillars, 6 NEXUS cross-cloud catalog entries + 14 lineage links, 3 Vertex AI Agent Engine instances (`basic=2946493525224587264`, `scaled=1975967805526245376`, `kc=8060330902103785472`), and live Cloud Run UI (`https://retail-kc-demo-ui-live-98236392654.us-central1.run.app`, revision `retail-kc-demo-ui-live-00008-*`, rollback `retail-kc-demo-ui-live-00007-cdz`).
- **Phase I-C (40-Chip Headless Verification — `tools/verify_all_chips.py` → `logs/chip_verification.json`) — COMPLETE**:
  - Clicked all 40 chips headlessly (`basic`: 12, `scaled`: 12, `kc`: 16) with `--password-store=basic --use-mock-keychain`: **0 BROKEN** (`23 CORRECT`, `17 ARTICULATE_FAIL`).
- **Phase I-B (Rendering — KC concentric orbital rings, solid green edges to touched nodes only, labels on touched nodes only, agent center glow/tabs/send colors, uppercase color-coded tool chips, borderless agent description) — DEPLOYED & VERIFIED**:
  - Updated [`website-live/static/visualization.js`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/visualization.js), [`website-live/static/chat.js`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/chat.js), [`website-live/static/styles.css`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/styles.css), and [`website-live/static/index.html`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/index.html) (`?v=7`).
  - Live headless Chrome verification on KC agent, Chip 1 (`tools/verify_phase_ib.py`): `edge_count = 4`, `label_count = 4`.
- **Phase G1-F (Remove static lineage mesh, active-path edges only) — FIXED, DEPLOYED (`retail-kc-demo-ui-live-00006-6rx`) & LIVE-VERIFIED (`logs/verify_g1f_results.json`)**:
  - **Root cause vs. upstream**: Upstream (`main:website-live/static/visualization.js`) initialized `this.activeLineage` edges with `alpha: 0` and only incremented `alpha` inside `_updateQueryAnimation()` (static fallback mode), so in live WebSocket mode (`illuminateTables()`) `line.alpha` remained `0` and **0 lineage mesh edges** were drawn. Phase C1/D changed `_buildLineageForTables()` to `const defaultAlpha = this.animationState ? 0 : 0.65;` and invoked `_buildLineageForTables()` inside `illuminateTables()` plus `showGlossaryArcsForTerms()` (`alpha: 0.6`) on every `search_entries` `tool_response`, cascading across `GOLD_SOURCES` (`48` gold→silver + `22` silver→bronze), `GLOSSARY_LINKS` (`58` chain arcs), and `NEXUS_TARGETS` (`14` links) to draw 50–100+ background mesh lines per query.
  - **Fix**: Deleted `_buildLineageForTables()`, `_buildGlossaryArcs()`, `showGlossaryArcsForTerms()`, `this.activeLineage`, `this.activeGlossaryArcs`, and idle static `BASIC_TABLES` labels in `website-live/static/visualization.js` and `website-live/static/chat.js`. Added `MAX_VISIBLE_EDGES = 5`, active query-path edge selection (`center -> queried tables`, plus at most 1 solid cyan edge to NEXUS when a Snowflake table is active), smooth fade-out (`this.fadingEdges`) when a new query starts, and labels-only-on-active-nodes across all 3 agent modes.
  - **Verification (`tools/verify_g1f.py` on live `retail-kc-demo-ui-live-00006-6rx`)**:
    - `basic`: Idle `0` edges | Chip 1 `1` edge (`gold_assortment_performance`) | Chip 4 `1` edge (`gold_assortment_performance`, previous edge faded out `fadingAfter=0`)
    - `scaled`: Idle `0` edges | Chip 1 `4` edges | Chip 4 `5` edges (`10` active nodes lit, capped at `5` edges, previous query's edges gone)
    - `kc`: Idle `0` edges | Chip 1 `5` edges (`19` active nodes lit, capped at `5` edges) | Chip 4 `5` edges (`4` BQ + `1` solid cyan edge to `nexus_syndicated_promo_benchmarks`, `10` active nodes lit, previous query's edges gone)
- **Keyring & Canonical URL Directives**:
  - Enforced `--password-store=basic --use-mock-keychain` on every headless Chrome invocation (zero GNOME Keyring / Secret Service prompts).
  - Verified via `grep -rn "762777230453"` that `762777230453` does **not** exist in any file in the repo (it was a one-off terminal typo). All files (`STATE.md`, `tools/validate.sh`, `tools/verify_p6.py`, `tools/run_bcd_tier_matrix.py`, `tools/run_live_f1_to_f5.sh`, `scripts/config.json`) use the canonical URL `https://retail-kc-demo-ui-live-98236392654.us-central1.run.app`.
- **F1 (Blocker — Tier chips produce no output) — FIXED, DEPLOYED & LIVE-VERIFIED (`3a48c29`)**:
  - **Root cause**: `sendPreset(q)` in `index.html` set `document.getElementById('chatInput').value = q` and called `chatManager.send()`, but `chatManager.send()` in `website-live/static/chat.js` unconditionally ran `this.inputEl.value = '';` **before** `const question = text.trim();`, wiping the input before reading it. Additionally, `.hidden { display: none !important; }` was missing from `styles.css`.
  - **Fix**: `chatManager.send(presetText)` now accepts `presetText` directly (`const raw = (typeof presetText === 'string' && presetText.length > 0) ? presetText : (this.inputEl ? this.inputEl.value : '');`) before clearing the input, immediately renders the working bubble, closes any prior WebSocket, and awaits `_checkLiveMode()` if needed. Added delegated click handler on `#presetQuestions` and `.preset-num { pointer-events: none; }`.
  - **Verification**: Clicked all **16/16** preset chips across all 4 tabs locally (`logs/ui_f1_f3_f4_verification.json`) AND clicked 1 chip on each of the 4 tabs (`merchandising #1`, `customer #1`, `privacy #1`, `multicloud #1`) on live Cloud Run (`https://retail-kc-demo-ui-live-98236392654.us-central1.run.app`, revision `retail-kc-demo-ui-live-00006-6rx`) in headless Chrome (`--password-store=basic --use-mock-keychain`), confirming streamed WebSocket answers from Vertex AI Agent Engine (`logs/live_cloud_run_smoke.json`).
- **F2 (Phase E Option 1 — Purge FSI semantics from SQL data) — DEPLOYED TO BIGQUERY & VERIFIED (`d07e042`, `761f165`)**:
  - Executed [`tools/apply_phase_e_option1.py`](file:///home/aelitchfield/knowledge_catalog_demo/tools/apply_phase_e_option1.py) across **34 SQL files** and ran `deploy-bq.sh --refresh`, `deploy-bq-nokc.sh --refresh`, `10_create_rule_library.py`, `02_create_scans.py`, and `15_inject_dirty_data.py` (`logs/f2_phase_e.log`).
  - Eliminated all FSI strings (`Pass`/`Special Mention`/`Substandard`/`Doubtful` → `Low`/`Watch`/`Elevated`/`High Risk`; `HELOC`/`SBA`/`EXTENDED_FINANCING` → `PAY_IN_4`/`MONTHLY_3M`/`MONTHLY_6M`/`SEASONAL_PROMO_12M`/`APPLIANCE_FINANCING_18M`/`VIP_FLEX_PAY`; `ROTH_IRA`/`401K` → `POINTS_REWARDS`/`VIP_CASHBACK`/`STORE_CREDIT`/`GIFT_WALLET`/`EMPLOYEE_PERKS`; `CET1` → `Core Working Capital`; `US Large Cap Equity` → `Apparel & Outerwear`, etc.).
  - Replaced FICO `567–580` (`300–850`) with `1–100` `return_risk_score` correlated by risk tier (`Low ~12.48`, `Watch ~34.97`, `Elevated ~58.02`, `High Risk ~81.99`), BNPL balances `$35–$1,900` (avg `~$296`), overdue review rates varying by tier (`Low ~1.31%`, `Watch ~4.05%`, `Elevated ~8.85%`, `High Risk ~17.50%`), and realistic retail loyalty balances (`~$253` avg).
  - Verified intentional DQ defects survived in BigQuery (`dirty_bnpl_scores=150`, `dirty_loyalty_accts=50`, `dirty_customers=20,140`, `dirty_bronze_gtins=149`, `dirty_silver_gtins=74`, `vw_dq_failed_rules=3`).
  - Re-ran all 3 agents on `"Give me an overview of customer risk across the retailer"` (`logs/f2_customer_risk_overview.json`), confirming pure retail risk tiers and retail dollar balances.
- **F3 (NEXUS graph — too many edges & label collisions) — DEPLOYED & VERIFIED (`4ca6d2a`)**:
  - Removed the `activeBQ × activeSF` cartesian-product loop and radial center beams for `snowflake` nodes in [`website-live/static/visualization.js`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/visualization.js).
  - Cross-cloud chips now draw **10** cyan dashed edges (down from **246** before); stress test with 40 BQ + 6 NEXUS nodes active draws **11** cyan dashed edges (strictly registered `NEXUS_TARGETS` lineage links).
  - Added bounding-box label collision de-confliction + viewport bounds clamping so active node labels never overlap or clip off-screen.
- **F4 (NEXUS fully absent from Basic & Scaled) — DEPLOYED & LIVE-VERIFIED (`7512a68`)**:
  - Verified on live Cloud Run (`retail-kc-demo-ui-live-00006-6rx`) that `basic` and `scaled` have strictly 3 tabs (`merchandising`, `customer`, `privacy`), 4 legend items (`Gold (20)`, `Silver (40)`, `Bronze (40)`, `Other (28)`), `visibleSfNodes: 0`, and `crossEdges: 0`. `kc` view retains all 4 tabs, 5 legend items, and 6 NEXUS diamonds (`logs/live_cloud_run_smoke.json`).
- **F5 (Harden Tier 2 questions `M_T2` & `C_T2`) — DEPLOYED & EVALUATED (`8f9eefb`)**:
  - Updated `M_T2` and `C_T2` in [`website-live/static/index.html`](file:///home/aelitchfield/knowledge_catalog_demo/website-live/static/index.html), [`tools/run_bcd_tier_matrix.py`](file:///home/aelitchfield/knowledge_catalog_demo/tools/run_bcd_tier_matrix.py), and [`demo/demo_questions.md`](file:///home/aelitchfield/knowledge_catalog_demo/demo/demo_questions.md), and evaluated `M_T2`, `C_T2`, `P_T2` × 3 agents (`logs/bcd_tier_matrix.json`):
    - `M_T2`: Basic ❌ FAIL (0 tools, no SKU/loss/manager/VaR in its 5 tables); Scaled ⚠️ PARTIAL / WRONG RANKING (found tables via 5 `LIMIT 1` probes, but summed across all historical snapshots instead of latest inventory and sorted lexicographically on `FORMAT('$%.2f', ...)` returning `-10006.03`..`-10.84` instead of `-73822.53`..`-68700.28`); KC ✅ PASS (`LatestInventory` CTE, accurate top-5 SKUs `-73822.53`..`-68700.28`, glossary definitions + unassigned manager governance gap).
    - `C_T2`: Basic ❌ FAIL (missing e-commerce orders, return-risk score, and store region); Scaled ❌ FAIL (ran 9 `LIMIT 10` probes, failed to bridge `customer_id -> account_id` for `silver_ecom_orders` or link `silver_bnpl_plans.return_risk_score_at_signup`, explicitly stating it could not compare e-commerce order volume or Return-Risk Score); KC ✅ PASS (4 catalog calls + 1 SQL join across `gold_customer_360`, `silver_stores`, `silver_bnpl_plans`, `silver_ecom_orders`, returning 0–100 Return-Risk Scores `30.26–31.75` and flagging the `silver_ecom_orders` linkage gap in Data Governance Notes).
    - `P_T2`: Basic ❌ FAIL (missing origination vintage history); Scaled ⚠️ PARTIAL / MISINTERPRETED (queried `bronze_bnpl_plans` for vintage trends, but misinterpreted `classified_rate_pct` on `90+ DPD` rows in `gold_bnpl_delinquency_analysis` as 100% store-level delinquency rates); KC ✅ PASS (`gold_bnpl_delinquency_analysis` segment averages `3.8%` / `2.5%` / `1.2%` + glossary & PCI/CCPA/GDPR notes).

### ENVIRONMENT FACTS to reload
- **Project**: `alitch-ca-demo` / project number `98236392654` (`us-central1` region, `us` multi-region)
- **Agents (`us-central1` ReasoningEngines)**:
  - `basic`: `2946493525224587264` (`[Retail] retail-agent-basic`, secret `retail-basic-agent-id`)
  - `scaled`: `1975967805526245376` (`[Retail] retail-agent-scaled`, secret `retail-scaled-agent-id`)
  - `kc`: `8060330902103785472` (`[Retail] retail-agent-kc`, secret `retail-kc-agent-id`)
- **Cloud Run URL**: `https://retail-kc-demo-ui-live-98236392654.us-central1.run.app` (live revision: `retail-kc-demo-ui-live-00007-cdz`, rollback revision: `retail-kc-demo-ui-live-00006-6rx`)
- **Chrome Headless Flags (Mandatory)**: `--password-store=basic --use-mock-keychain`
- **`bq` CLI mTLS workaround**: Requires `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` and `CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false`

---

## Current Phase
- **Phase P0 (Recon & Plan)**: COMPLETE & APPROVED (🛑 GATE 1 passed).
- **Phase P1 (Local Refactor)**: COMPLETE & COMMITTED on branch `retail-refactor`.
  - `tools/transform.py` renamed 102 `.sql` files and updated 189 files (4,308 replacements).
  - `tools/author_retail_glossary.py` generated `scripts/01_create_glossary.py` (28 categories prefixed `Retail — `, 84 terms prefixed `[Retail] `, 14 synonyms, 67 related links, 181 validated `DEFINITION_LINKS`) and `scripts/12_enrich_glossary.py` (84 HTML overviews).
  - `tools/update_governance_scripts.py` and `tools/finalize_retail_refactor.py` updated `scripts/00`..`16`, `deploy-bq*.sh`, `modules/bigquery-*/main.tf`, `agents/`, `demo/`, `eval/`, and `website-live/`.
  - Wrote [`RETAIL_MAPPING.md`](file:///home/aelitchfield/knowledge_catalog_demo/RETAIL_MAPPING.md).
  - Banking-term purge gate verified: **Tier A = 0 hits** (excluding English substring `merchandising`/`exercising`/`arising`), **Tier B = 7 hits** (all legitimate Git `branch` references).
  - All `.sh` (`bash -n`) and `.py` (`py_compile`) syntax checks passed.
- **Phase P2 (GCP Pre-Flight)**: COMPLETE & APPROVED (🛑 GATE 2 passed).
  - Enabled & verified all 13 required APIs on `alitch-ca-demo` (`98236392654`).
  - Wrote `scripts/config.json` (`project_id=alitch-ca-demo`, `project_number=98236392654`, `region=us-central1`, `multi_region=us`, `gcp_account_name=admin@aelitchfield.altostrat.com`).
  - Both org-policy overrides succeeded on `projects/98236392654`:
    - `iam.allowedPolicyMemberDomains` -> `allowAll: true`
    - `run.managed.requireInvokerIam` -> `enforce: false`
  - Vertex AI Agent Engine API (`us-central1`) returned HTTP 200.
  - Confirmed **0 `retail_*` / `retail-*` collisions** across BigQuery datasets, Dataplex glossaries, data products, ReasoningEngines, and Cloud Run services.
- **Phase P3 (Data Layer)**: COMPLETE, VERIFIED & COMMITTED (`753668c` on `retail-refactor`).
  - Executed `deploy-bq.sh` and `deploy-bq-nokc.sh` with 0 errors.
  - Verified via `tools/verify_p3.py`:
    - **18/18 datasets** (`10` governed `retail_*` + `8` `retail_*_nokc` shadow datasets) carry `[Retail] ` descriptions and all 4 required labels (`use-case=retail`, `demo=retail-knowledge-catalog`, `owner=alitch`, `env=demo`).
    - **128/128 governed tables & views** populated with **0 empty tables**.
    - **128/128 `_nokc` shadow tables** copied cleanly.
- **Phase P4 (Governance Layer)**: COMPLETE, VERIFIED & COMMITTED on `retail-refactor`.
  - Executed `post_deploy.sh` and verified all 9 governance pillars via `tools/verify_p4.py`:
    1. **Custom Entry Types (`global`)**: 9 (`retail-ibmi-*`, `retail-sfcc-*`, `retail-sap-*`).
    2. **Aspect Types (`global`)**: 14 (7 custom `retail-*` + 7 marker aspect types); applied 490+ aspect instances to tables and glossary terms.
    3. **Custom Source Entry Groups (`us`)**: 3 groups (`retail-orion-store-pos`, `retail-lumen-commerce-loyalty`, `retail-helios-merch-supply`), 3 instances, 3 schemas, 13 source tables.
    4. **Business Glossary (`us`, `retail-northwind-glossary-us` — `[Retail] Northwind Retail Business Glossary`)**: 28 categories (prefixed `Retail — `), 84 terms (prefixed `[Retail] `), 84 enriched HTML overviews, 81 term links (`synonym`/`related`), 180+ BQ `definition` links.
    5. **Data Products (`us`)**: 5 (`retail-customer-loyalty-360`, `retail-pricing-promo-margin`, `retail-merch-inventory`, `retail-privacy-consent-pci`, `retail-store-channel-performance`).
    6. **Lineage (`us`)**: 5 processes, 125 links.
    7. **Reusable Rule Library (`global`, `retail-rule-library-global`)**: 10 rule templates + 1 index entry.
    8. **DataScans (`us-central1`)**: 360 total (`128` profile, `132` insights, `100` quality) + published labels applied via `08_publish_scans.py` + dirty data injected via `15_inject_dirty_data.py`.
    9. **Policy Tag Taxonomy (`us`)**: `Retail Demo Sensitivity Taxonomy - alitch` (`projects/alitch-ca-demo/locations/us/taxonomies/6328323030724665961`), 4 policy tags, 32 columns tagged, `roles/datacatalog.categoryFineGrainedReader` granted to Agent Engine SA, Dataplex SA, Compute SA, and `admin@aelitchfield.altostrat.com`.
- **Phase P5 (Agents + Website)**: COMPLETE & COMMITTED on `retail-refactor`.
  - Deployed all 3 Vertex AI Agent Engine instances in `us-central1` and persisted IDs in Secret Manager:
    - `[Retail] retail-agent-basic`: `2946493525224587264` (`retail-basic-agent-id`)
    - `[Retail] retail-agent-scaled`: `1975967805526245376` (`retail-scaled-agent-id`)
    - `[Retail] retail-agent-kc`: `8060330902103785472` (`retail-kc-agent-id`)
  - Granted dataset access (`_nokc` datasets to basic & scaled; governed `retail_*` datasets + Dataplex/Lineage/MCP roles to KC; `WRITER` on `retail_agent_analytics` to all 3; `roles/datacatalog.categoryFineGrainedReader` on taxonomy `6328323030724665961` to all 3 per-agent `principal://` identities; `--condition=None` on project IAM bindings).
  - Stored OAuth 2.0 Web Client ID in Secret Manager (`retail-oauth-client-id`) and deployed Cloud Run service `retail-kc-demo-ui-live` in `us-central1` (revision `retail-kc-demo-ui-live-00002-fgn`):
    - Canonical URL: `https://retail-kc-demo-ui-live-98236392654.us-central1.run.app`
    - Regional Alias URL: `https://retail-kc-demo-ui-live-esoohbbsma-uc.a.run.app`
    - Verified `allUsers` bound to `roles/run.invoker`.
    - Fixed `DATASET_MAP`, `_RETAIL_DATASETS`, and `_DATASET_TO_TIER` in `website-live/app.py` (`retail_staging`, `retail_snapshots`, `retail_audit` replacing nonexistent `retail_supplementary`), bringing `/api/config` `all_table_names` to **128/128** (`40` bronze, `40` silver, `20` gold, `28` ref/staging/snapshots/audit).
- **Phase P6 (End-to-End Validation & Live 15×3 Tier Matrix)**: COMPLETE & VERIFIED via `tools/validate.sh`, `tools/verify_p6.py` (`logs/verify_p6.json`), and `tools/run_p6_tier_matrix.py` (`logs/p6_tier_matrix.json`).
  - Canonical Cloud Run URL (`https://retail-kc-demo-ui-live-98236392654.us-central1.run.app`) updated across `DEMO_SCRIPT.md`, `demo/demo_script.md`, `README.md`, `website-live/deploy.sh`, `tools/verify_p6.py`, and `tools/validate.sh`.
  - `clean_up.sh` syntax and retail resource safety verified (`bash -n clean_up.sh`).
  - Live 45-Query Tier Matrix (`15 questions × 3 agents`, zero prompt tuning):
    - **Tier 1 (Q01–Q05)**: Basic `5/5 PASS`; Scaled `4/5 PASS` (failed Q04 after 17 SQL queries across 14 tables due to "returns" vs "product returns" ambiguity); KC `5/5 PASS`.
    - **Tier 2 (Q06–Q10)**: Basic `0/5 PASS` (lacks Silver/Bronze/Supplementary tables and governance metadata); Scaled `0/5 PASS` (wrong table on Q07, false DQ trust on Q08/Q09, zero glossary/PAIR/CWCR/PCI-DSS context on Q06/Q10); KC `3/5 PASS` (passed Q06, Q08, Q10 with full glossary/DQ/lineage metadata; partial/failed Q07 by querying `silver_inventory_positions` instead of `gold_markdown_risk_var`; failed Q09 because `search_entries` returned custom source entry `custom:lumen-prod.DIGITAL_COMMERCE.PRODUCT_SKUS` first and KC tried querying it in BigQuery).
    - **Tier 3 (Q11–Q15)**: Basic `0/5 PASS` (lacks cross-domain tables, lineage, and PII policy tags); Scaled `0/5 PASS` (listed `_nokc` bronze tables as upstream systems on Q11, missed loyalty domain on Q12, zero SIV/EFR/HCRL governance on Q13, refused stress test on Q14, false join key `account_id = customer_id` across 15 SQLs on Q15); KC `3/5 PASS` (passed Q11 with LUMEN/ORION lineage, Q12 omnichannel POS+Loyalty, Q15 cross-sell with PII/PCI-DSS/CCPA governance; failed Q13 when 4-table LEFT JOIN returned 0 rows and stream ended without text summary; failed Q14 due to querying custom source entry `FINANCE_RISK.GL_ENTRIES` in BigQuery).
- **Phase A (Fix Agent 400 Blocker)**: COMPLETE, DEPLOYED (`retail-kc-demo-ui-live-00003-vtx`) & VERIFIED (`logs/phase_a_three_agents.json`).
  - Root cause: `website-live/app.py` and `eval/run_eval.py` omitted `"class_method"` in the `:streamQuery` payload; with `google-adk==2.8.0` and `google-cloud-aiplatform==2.6.0` registering 3 streaming methods (`stream_query`, `async_stream_query`, `streaming_agent_run_with_events`), Vertex AI Reasoning Engine returned `400 INVALID_ARGUMENT`.
  - Verified `"class_method": "async_create_session"` returns `200 OK` on all 3 ReasoningEngines before streaming.
  - Updated `website-live/app.py` and `eval/run_eval.py` to use `async_create_session` and `async_stream_query`, and added permanent `logger.error("streamQuery failed: agent=%s status=%d body=%s", ...)` in `website-live/app.py`.
  - Pinned `google-adk==2.8.0` and `google-cloud-aiplatform==2.6.0` across `agents/agent_{basic,scaled,kc}/requirements.txt` (and `mcp==1.30.0` in `agent_kc/requirements.txt`).
  - Redeployed `retail-kc-demo-ui-live` (revision `00003-vtx`) and verified all 3 agents return HTTP 200 and full answers on `"Give me an overview of customer risk across the retailer."`.
- **Phase B (Retail-ify Question Categories & API Fixes)**: COMPLETE.
  - Known-good rollback revision recorded before B+C1+D deploy: `retail-kc-demo-ui-live-00003-vtx`.
  - Replaced FSI tabs (`Executive Briefing | Risk & Compliance | Data Governance`) with 3 persona-mapped retail tabs (`MERCHANDISING & INVENTORY`, `CUSTOMER & LOYALTY`, `PRIVACY & COMPLIANCE`) × 4 difficulty tiers = 12 retail questions synchronized across `website-live/static/index.html` and `demo/demo_questions.md`.
  - Verified `dataset_map` (`retail_audit`, `retail_snapshots`, `retail_staging`), `all_table_names` (`128`), and `ENVIRONMENT_LABEL="demo"` in `website-live/app.py` and `website-live/deploy.sh`.
  - Deferred `gold_financial_summary → gold_store_channel_performance` rename per scope instructions (blast radius touches 18 repo files + deployed BQ tables, shadow `_nokc` tables, Dataplex DataProducts/Lineage/Scans, and deployed agent prompts).
- **Phase C1 (Cross-Cloud / NEXUS Catalog + Visual Layer)**: COMPLETE.
  - Created and executed `scripts/17_create_nexus_c1.py`: registered `us` entry group `retail-nexus-market-intel` (`[Retail] NEXUS — Syndicated Retail Market Intelligence (Snowflake)`), global entry/aspect types `retail-snowflake-{instance,schema,table}`, 6 retail NEXUS tables (`nexus_competitor_prices`, `nexus_category_market_share`, `nexus_consumer_panel`, `nexus_regional_demand_index`, `nexus_promo_calendar_benchmark`, `nexus_basket_affinity`), 48 governance aspect attachments (`cloud_platform="Snowflake"`, `data_residency="External / Non-GCP"`, `classification_level="Third-Party Licensed"`, `access_level="External Vendor Agreement"`), and 14 cross-cloud Data Lineage links to `retail_gold` tables.
  - Synchronized `snowflake/common_snowflake.py`, `snowflake/00_setup_nexus_data.py`, `snowflake/01_create_dataplex_infra.py`, and `agents/agent_kc/agent.py` with the 6 retail `SYNDICATED_INTEL.nexus_*` tables.
  - Updated `website-live/app.py`, `website-live/static/index.html`, and `website-live/static/chat.js`: `CROSS-CLOUD` tab is active ONLY on the KC Agent tab (with badge `"Catalog-only — live Snowflake query not connected"`), and renders as a disabled/ghosted chip with tooltip `"Requires Knowledge Catalog — this agent cannot discover data outside BigQuery."` on Basic and Scaled Agent tabs.
- **Phase D (Dark Theme & NEXUS Diamond Canvas Visualization)**: COMPLETE & COMMITTED (`ee44de3`).
  - Defined CSS custom properties in `website-live/static/styles.css` (`--bg: #0d1117`, `--surface: #161b22`, `--border: #30363d`, `--text: #e6edf3`, `--text-muted: #8b949e`, `--accent: #3fb950`, `--node-gold: #ffd33d`, `--node-silver: #a5b4fc`, `--node-bronze: #ff9f43`, `--node-other: #8b949e`, `--node-nexus: #00e5ff`) with WCAG AA/AAA body contrast (`15.8:1` `#e6edf3` on `#0d1117`, `14.3:1` `#e6edf3` on `#161b22`, `6.0:1` `#8b949e` on `#0d1117`).
  - Updated `website-live/static/visualization.js`: rendered NEXUS Snowflake nodes as cyan `#00e5ff` diamonds in a separated `NEXUS · Snowflake (External)` boundary, wired 14 cross-cloud lineage links in `NEXUS_TARGETS`, and themed canvas rings, lineage lines, glossary arcs, labels, and tooltips for dark mode.
- **Batched Cloud Run Redeploy & Smoke Test (`retail-kc-demo-ui-live-00004-fbd`)**: COMPLETE & VERIFIED.
  - Deployed single batched Cloud Run revision `retail-kc-demo-ui-live-00004-fbd` (rollback revision `retail-kc-demo-ui-live-00003-vtx` preserved).
  - Verified `GET /api/config` returns `200 OK`, `environment="demo"`, `all_table_names == 128` (`40` bronze, `40` silver, `20` gold, `28` ref), `snowflake_enabled=True`, `snowflake_live=False`, `snowflake_tables` (6 `nexus_*` tables), and `dataset_map` (`retail_audit`, `retail_snapshots`, `retail_staging`).
  - Verified all 40 live queries in `logs/bcd_tier_matrix.json` (`12 retail questions × 3 agents = 36` + `4 Cross-Cloud questions × KC = 4`):
    - **Tier 1 (`M_T1`, `C_T1`, `P_T1`)**: Basic `3/3 PASS`, Scaled `3/3 PASS`, KC `3/3 PASS`.
    - **Tier 2 (`M_T2`, `C_T2`, `P_T2`)**: Basic `0/3 PASS` (tables outside 10-table prompt); Scaled `2/3 PASS` (heavy 7–10 tool-call exploration on `M_T2`/`C_T2`, timed out on `P_T2` scanning unenriched tables); KC `3/3 PASS`.
    - **Tier 3 (`M_T3`, `C_T3`, `P_T3`)**: Basic `0/3 PASS`; Scaled `0/3 PASS` (lacks Dataplex certification, lineage, stewards, PCI/CCPA tags); KC `3/3 PASS`.
    - **Tier 4 (`M_T4`, `C_T4`, `P_T4`)**: Basic `0/3 PASS` (partial single-table on `M_T4`, fails `C_T4`/`P_T4`); Scaled `1/3 PASS` (fails `M_T4`/`P_T4`, partial uncertified SQL on `C_T4`); KC `3/3 PASS`.
    - **Cross-Cloud (`X_T1`–`X_T4`, KC only)**: KC `4/4 PASS` (discovers 6 `nexus_*` Snowflake tables, governance aspects, cross-cloud lineage, and joins catalog metadata with `retail_gold` SQL).
- **Phase E (Data Semantics Audit ONLY — `PHASE_E_DATA_AUDIT.md`)**: COMPLETE & COMMITTED.
  - Audited all 128 SQL files and documented every surviving FSI literal string, uncorrelated random generator, and mortgage/wealth numeric distribution in [`PHASE_E_DATA_AUDIT.md`](file:///home/aelitchfield/knowledge_catalog_demo/PHASE_E_DATA_AUDIT.md) (no data or deploy scripts modified).
  - **STOPPED at Phase C2 / Post-Phase-E per autonomy rules** — awaiting user review of `PHASE_E_DATA_AUDIT.md` and Snowflake credentials if Phase C2 is desired.

- **Phase K1 (Deterministic NEXUS Connector + FSI-Quality Response Template)**: COMPLETE & VERIFIED.
  - Known-good rollback Cloud Run revision recorded before K1 deploy: `retail-kc-demo-ui-live-00008-cxg` (active revision: `retail-kc-demo-ui-live-00009-xfh`).
  - Seeded deterministic `alitch-ca-demo.retail_reference.nexus_connector_data` in BigQuery via `tools/seed_nexus_connector_data.py` with 46 realistic rows across all 6 `nexus_*` tables (`nexus_competitor_prices`, `nexus_category_market_share`, `nexus_consumer_panel`, `nexus_regional_demand_index`, `nexus_promo_calendar_benchmark`, `nexus_basket_affinity`) labeled `"[Retail] NEXUS connector reference data (simulated external feed)"` (and excluded `nexus_connector_data` from `website-live/app.py` canvas table discovery so `all_table_names` remains `128`).
  - Implemented `query_snowflake(sql: str) -> str` in `agents/agent_kc/agent.py` to execute real SQL against `retail_reference.nexus_connector_data` using `NEXUS_MARKET_DATA.<SCHEMA>.<TABLE>` naming, returning rows shaped like a Snowflake response with deterministic fallback. Normalized `PROJECT_ID` to `"alitch-ca-demo"` when Vertex AI Reasoning Engine sets numeric project number `98236392654`.
  - Updated UI badge in `website-live/static/index.html` to `"Simulated connector — NEXUS reference data"` and enforced honesty/voice/provenance guardrails and the mandatory 4-section template (`**Data discovery.**`, `**Finding.**`, `**Governance Context.**`, `**Recommendations.**`) in `agents/agent_kc/agent.py`.
  - Deployed `retail-agent-kc` (`8060330902103785472`) and Cloud Run `retail-kc-demo-ui-live-00009-xfh`; verified Cross-Cloud #2 (`Price Gaps`) in `logs/k1.json` (`search_entries`, `lookup_context`, `query_snowflake`, `run_sql`, all 4 sections present).

- **Phase K2 (4+ Graph Connections with Glossary Edge Labels)**: COMPLETE & VERIFIED.
  - Known-good rollback Cloud Run revision recorded before K2 deploy: `retail-kc-demo-ui-live-00009-xfh` (active revision: `retail-kc-demo-ui-live-00010-877`).
  - Updated `website-live/static/visualization.js`, `website-live/static/chat.js`, and `website-live/static/index.html` (`?v=8`):
    - KC Agent graph draws 4–6 solid green (`#3fb950`) edges from the glowing center node to touched tables across layers (`bronze`, `silver`, `gold`, `ref`, plus at least 1 cyan `nexus_*` node when Snowflake was queried).
    - Pulls the cited glossary term from the KC agent's `Governance Context` section (`_extractGovernanceGlossaryTerm`) and renders it as a small green floating text pill near the relevant edge (`setGlossaryEdgeLabel`).
    - Zero edges at idle; clears on new query; faint dashed cyan inside NEXUS cluster stays as texture only.
  - Headless Chrome verification on `retail-kc-demo-ui-live-00010-877` (`tools/verify_phase_ib.py`, `--password-store=basic --use-mock-keychain`): `edges_drawn = 6`, `labels_visible = 7` (6 touched node labels + 1 glossary edge label).

- **Phase L (Targeted Column Rename + Realistic GMROI + Duplicate Assortment Fix)**: COMPLETE & VERIFIED.
  - Renamed 5 FSI columns that surfaced in demo output across 16 SQL files (`tools/apply_phase_l.py`) and in-place in BigQuery (`ALTER TABLE ... RENAME COLUMN IF EXISTS ... TO ...` on both `retail_*` and `retail_*_nokc`):
    - `avg_sharpe_ratio` → `gmroi`
    - `total_return_pct` → `sell_through_pct`
    - `unrealized_gain_loss` → `markdown_exposure`
    - `cost_basis` → `inventory_at_cost`
    - `market_value` → `current_retail_value`
  - Regenerated `gmroi` as `ROUND(SAFE_DIVIDE(current_retail_value - inventory_at_cost, inventory_at_cost), 2)` (`gross_margin / avg_inventory_cost`) in `[2.08, 3.85]` (never negative) and `sell_through_pct` in `[0.4384, 0.8455]` (`43.84%–84.55%`), internally consistent with `current_retail_value`, `inventory_at_cost`, and `markdown_exposure`.
  - Fixed duplicate `"Seasonal Holiday Gifting"` rows in `gold_assortment_performance` (caused by `bronze_merch_assortments` cycling through 8 static names across 15,000 `PORT-*` rows without deduplicating by `assortment_name` in `gold_assortment_performance`) by expanding to 12 distinct retail assortment names and adding `QUALIFY ROW_NUMBER() OVER (PARTITION BY p.assortment_name ORDER BY COUNT(DISTINCT h.holding_id) DESC, p.assortment_id) = 1`.
  - Executed `deploy-bq.sh --refresh`, `deploy-bq-nokc.sh --refresh`, `scripts/15_inject_dirty_data.py` (preserving all intentional DQ defects), and triggered DQ rescans (`tools/run_phase_l_deploy.sh`). Verified `Merchandising #4` headlessly (`tools/verify_phase_l.py` → `logs/l_verify.json`).

## Summarized Files (Do NOT Re-Read)
- `deploy-bq.sh`, `deploy-bq-nokc.sh`, `deploy-full.sh`, `post_deploy.sh`, `clean_up.sh`: Updated with mTLS client-cert disable exports (`GOOGLE_API_USE_CLIENT_CERTIFICATE=false`, `CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false`), `RETAIL_TAXONOMY_DISPLAY_NAME="Retail Demo Sensitivity Taxonomy (alitch)"`, `[Retail] ` dataset descriptions, and 4 required dataset labels (`use-case=retail`, `demo=retail-knowledge-catalog`, `owner=alitch`, `env=demo`).
- `modules/bigquery-{medallion,reference,dashboards}/main.tf`: Updated dataset IDs, table lists, `[Retail] ` descriptions, and 4 dataset labels.
- `modules/bigquery-medallion/sql/*.sql`, `modules/bigquery-reference/sql/*.sql`, `modules/bigquery-dashboards/sql/*.sql`: All 128 SQL files renamed and refactored with consistent retail string literals.
- `scripts/common.py` & `scripts/00_create_dataplex_infra.py` .. `scripts/16_create_policy_tags.py`: Refactored to `retail_` / `retail-` IDs and `[Retail] ` display names/descriptions.
- `agents/agent_{basic,scaled,kc}/agent.py` & `agents/deploy_agents.sh`: Fixed `BigQueryAgentAnalyticsPlugin` import, updated `_BASE_SUFFIXES` and `_OTHER_TABLES` in `agent_scaled` (128 tables), set `[Retail] ` display names and `retail-*-agent-id` secrets.
- `website-live/app.py`, `website-live/deploy.sh`, `website-live/static/index.html`, `website-live/static/static-responses.json`: Updated to Northwind Retail Group branding, retail narratives, and `[Retail] ` glossary link matching.
- `demo/demo_questions.md`, `demo/demo_script.md`, `eval/metrics.py`, `eval/run_eval.py`, `eval/test_cases.yaml`: Refactored to retail scenarios and metrics.


## FINAL STATE — Handoff Before Teardown (2026-10-28)

- **Phases Complete**:
  - **P0–P6**: Baseline retail refactor, 18 BigQuery datasets (`10` governed `retail_*` + `8` `retail_*_nokc` shadow), 128 tables/views, 9 Dataplex governance pillars, 3 Vertex AI Agent Engine instances (`basic=2946493525224587264`, `scaled=1975967805526245376`, `kc=8060330902103785472`), and Cloud Run UI (`retail-kc-demo-ui-live`).
  - **Phases A–E & F1–F5**: Fixed Agent Engine `:streamQuery` `class_method` (`async_create_session` / `async_stream_query`), retail question categories & tier chips, purged residual FSI strings/metrics from SQL data, and cleaned up NEXUS cross-cloud graph rendering.
  - **Phases G1-F, I-A, I-B, I-C**: Removed static lineage mesh, enforced active-path edges only, added KC concentric orbital rings + touched-node labels, and verified all 40 preset chips headlessly (`0 BROKEN`).
  - **Phases K1, K2, L**: Deterministic `query_snowflake` NEXUS connector + 4-section KC response template, 4–6 active graph edges with floating green glossary edge pills, targeted column rename (`gmroi`, `sell_through_pct`, `markdown_exposure`, `inventory_at_cost`, `current_retail_value`), realistic GMROI (`2.08–3.85`), and deduplicated `gold_assortment_performance`.
  - **Phases O1, O2, P, Q1**: Removed simulated-connector UI labels, gated NEXUS access to the Cross-Cloud tab, added per-phase latency telemetry + progressive UI status updates, and enabled ADK SSE token streaming (`StreamingMode.SSE`) on `retail-agent-kc` (`~3.7s` to first token on live revision `retail-kc-demo-ui-live-00015-dkx`).
- **Phase Q2 Abandoned**:
  - Multi-redeploy prompt compression experiment (`Q2`) caused regression/thrash; abandoned and rolled `agents/agent_kc/agent.py` back to the verified `Q1` prompt (`075635c`) and redeployed `retail-agent-kc` (`8060330902103785472`).
- **Rebuild Sequence**:
  1. `bash deploy-bq.sh`
  2. `bash deploy-bq-nokc.sh`
  3. `bash post_deploy.sh`
  4. `bash agents/deploy_agents.sh`
  5. `bash website-live/deploy.sh`
