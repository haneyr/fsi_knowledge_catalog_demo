"""Report generation for FSI KC agent evaluation."""

import html
import json
import time


def print_terminal_report(all_results, agents):
    metric_names = ["outcome", "table_selection", "data_in_response",
                    "graceful_failure", "glossary_citation", "metadata_citation"]

    agent_metric_sums = {a: {m: [] for m in metric_names} for a in agents}
    agent_latencies = {a: [] for a in agents}

    for cr in all_results:
        for agent_type, data in cr["agents"].items():
            if agent_type not in agents:
                continue
            agent_latencies[agent_type].append(data["result"].latency)
            for m in metric_names:
                if m in data["scores"]:
                    agent_metric_sums[agent_type][m].append(data["scores"][m].value)

    print(f"\n{'=' * 65}")
    print(f"  SUMMARY ({len(all_results)} cases)")
    print(f"{'=' * 65}")

    header = f"{'Metric':<22}"
    for a in agents:
        header += f"  {a:>8}"
    print(header)
    print("-" * 65)

    for m in metric_names:
        row = f"{m:<22}"
        for a in agents:
            vals = agent_metric_sums[a][m]
            if vals:
                avg = sum(vals) / len(vals)
                row += f"  {avg:>8.2f}"
            else:
                row += f"  {'—':>8}"
        print(row)

    row = f"{'avg_latency_s':<22}"
    for a in agents:
        vals = agent_latencies[a]
        if vals:
            avg = sum(vals) / len(vals)
            row += f"  {avg:>7.1f}s"
        else:
            row += f"  {'—':>8}"
    print(row)
    print()

    # Group by complexity
    by_complexity = {}
    for cr in all_results:
        cx = cr["case"].get("tags", {}).get("complexity", "unknown")
        by_complexity.setdefault(cx, []).append(cr)

    for cx, cases in sorted(by_complexity.items()):
        print(f"  {cx} ({len(cases)} cases):")
        for a in agents:
            outcomes = []
            for cr in cases:
                if a in cr["agents"]:
                    score = cr["agents"][a]["scores"].get("outcome")
                    if score:
                        outcomes.append(score.value)
            if outcomes:
                avg = sum(outcomes) / len(outcomes)
                sym = "+" if avg >= 0.8 else "~" if avg >= 0.4 else "-"
                passed = sum(1 for o in outcomes if o >= 0.8)
                print(f"    [{sym}] {a}: {passed}/{len(outcomes)} ({avg:.2f})")
        print()


def generate_html_report(all_results, agents, output_path):
    results_json = []
    for cr in all_results:
        entry = {
            "id": cr["case"]["id"],
            "question": cr["case"]["question"],
            "tags": cr["case"].get("tags", {}),
            "agents": {},
        }
        for agent_type, data in cr["agents"].items():
            r = data["result"]
            entry["agents"][agent_type] = {
                "tool_calls": r.tool_calls,
                "tables": r.tables_queried,
                "response_excerpt": r.response_text[:500],
                "latency": round(r.latency, 1),
                "error": r.error,
                "scores": {k: {"v": s.value, "r": s.reason} for k, s in data["scores"].items()},
            }
        results_json.append(entry)

    html_content = _build_html(results_json, agents)
    with open(output_path, "w") as f:
        f.write(html_content)


def _build_html(results, agents):
    data_json = json.dumps(results)
    agents_json = json.dumps(agents)
    ts = time.strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FSI KC Agent Evaluation Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #0a0e1a; color: #e0e0e0; font-family: 'Google Sans','Segoe UI',system-ui,sans-serif; padding: 24px; }}
h1 {{ font-size: 20px; margin-bottom: 4px; }}
.subtitle {{ color: #6b7280; font-size: 13px; margin-bottom: 20px; }}
.filters {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }}
.filters label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }}
.filters select {{ background: #1a2035; border: 1px solid #1e2a42; color: #e0e0e0; padding: 6px 10px; border-radius: 6px; font-size: 13px; }}
.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 24px; }}
.summary-card {{ background: #0f1525; border: 1px solid #1e2a42; border-radius: 10px; padding: 14px; }}
.summary-card .agent-name {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }}
.summary-card .agent-name.basic {{ color: #4285F4; }}
.summary-card .agent-name.scaled {{ color: #EA4335; }}
.summary-card .agent-name.kc {{ color: #34A853; }}
.summary-card .metric-row {{ display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; }}
.summary-card .metric-val {{ font-weight: 600; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
th {{ background: #1a2035; padding: 8px 10px; text-align: left; font-weight: 600; color: #fff; border: 1px solid #1e2a42; }}
td {{ padding: 8px 10px; border: 1px solid #1e2a42; vertical-align: top; }}
tr:nth-child(even) {{ background: rgba(255,255,255,0.02); }}
.tag {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin: 1px; }}
.tag-complexity {{ background: rgba(66,133,244,0.15); color: #4285F4; }}
.tag-audience {{ background: rgba(255,143,0,0.15); color: #FF8F00; }}
.tag-kc_feature {{ background: rgba(52,168,83,0.15); color: #34A853; }}
.score {{ font-weight: 600; }}
.score-high {{ color: #34A853; }}
.score-mid {{ color: #FFC107; }}
.score-low {{ color: #EA4335; }}
.score-na {{ color: #546E7A; }}
.expand-btn {{ background: none; border: none; color: #4285F4; cursor: pointer; font-size: 11px; }}
.detail-row {{ display: none; }}
.detail-row.open {{ display: table-row; }}
.detail-cell {{ padding: 12px; background: #0f1525; }}
.detail-cell pre {{ font-size: 11px; white-space: pre-wrap; color: #90A4AE; max-height: 200px; overflow-y: auto; }}
.tool-chip {{ display: inline-block; padding: 2px 6px; border-radius: 8px; font-size: 10px; font-weight: 600; margin: 1px; }}
.tool-chip.search {{ background: rgba(52,168,83,0.2); color: #34A853; }}
.tool-chip.context {{ background: rgba(66,133,244,0.2); color: #4285F4; }}
.tool-chip.sql {{ background: rgba(255,193,7,0.2); color: #FFC107; }}
.chart-container {{ margin: 20px 0; text-align: center; }}
canvas {{ max-width: 400px; }}
</style>
</head>
<body>
<h1>FSI Knowledge Catalog Agent Evaluation</h1>
<div class="subtitle">{ts} &middot; {len(results)} test cases &middot; {len(agents)} agents</div>

<div class="filters">
  <div><label>Complexity</label><br><select id="fComplexity" onchange="applyFilters()"><option value="">All</option></select></div>
  <div><label>Audience</label><br><select id="fAudience" onchange="applyFilters()"><option value="">All</option></select></div>
  <div><label>KC Feature</label><br><select id="fKcFeature" onchange="applyFilters()"><option value="">All</option></select></div>
</div>

<div class="summary-grid" id="summaryGrid"></div>
<div class="chart-container"><canvas id="radarChart" width="400" height="400"></canvas></div>
<table id="resultsTable"><thead><tr id="tableHead"></tr></thead><tbody id="tableBody"></tbody></table>

<script>
const DATA = {data_json};
const AGENTS = {agents_json};
const AGENT_COLORS = {{basic:'#4285F4', scaled:'#EA4335', kc:'#34A853'}};
const METRICS = ['outcome','table_selection','data_in_response','glossary_citation','metadata_citation'];

// Populate filter dropdowns
function initFilters() {{
  const dims = {{'fComplexity':'complexity','fAudience':'audience','fKcFeature':'kc_feature'}};
  for (const [selId, tagKey] of Object.entries(dims)) {{
    const vals = [...new Set(DATA.map(d => d.tags[tagKey]).filter(Boolean))].sort();
    const sel = document.getElementById(selId);
    for (const v of vals) {{
      const opt = document.createElement('option');
      opt.value = v; opt.textContent = v.replace(/_/g,' ');
      sel.appendChild(opt);
    }}
  }}
}}

function getFiltered() {{
  const fc = document.getElementById('fComplexity').value;
  const fa = document.getElementById('fAudience').value;
  const ff = document.getElementById('fKcFeature').value;
  return DATA.filter(d => {{
    if (fc && d.tags.complexity !== fc) return false;
    if (fa && d.tags.audience !== fa) return false;
    if (ff && d.tags.kc_feature !== ff) return false;
    return true;
  }});
}}

function scoreClass(v) {{
  if (v >= 0.8) return 'score-high';
  if (v >= 0.4) return 'score-mid';
  return 'score-low';
}}

function renderSummary(filtered) {{
  const grid = document.getElementById('summaryGrid');
  grid.innerHTML = '';
  for (const agent of AGENTS) {{
    const card = document.createElement('div');
    card.className = 'summary-card';
    let rows = '';
    for (const m of METRICS) {{
      const vals = filtered.flatMap(d => {{
        const a = d.agents[agent];
        return a && a.scores[m] ? [a.scores[m].v] : [];
      }});
      if (vals.length === 0) continue;
      const avg = vals.reduce((a,b) => a+b, 0) / vals.length;
      rows += `<div class="metric-row"><span>${{m.replace(/_/g,' ')}}</span><span class="metric-val ${{scoreClass(avg)}}">${{avg.toFixed(2)}}</span></div>`;
    }}
    const lats = filtered.flatMap(d => d.agents[agent] ? [d.agents[agent].latency] : []);
    const avgLat = lats.length ? (lats.reduce((a,b)=>a+b,0)/lats.length).toFixed(1) : '—';
    rows += `<div class="metric-row"><span>avg latency</span><span class="metric-val">${{avgLat}}s</span></div>`;
    card.innerHTML = `<div class="agent-name ${{agent}}">${{agent.toUpperCase()}}</div>${{rows}}`;
    grid.appendChild(card);
  }}
}}

function renderTable(filtered) {{
  const head = document.getElementById('tableHead');
  const body = document.getElementById('tableBody');
  head.innerHTML = '<th>Case</th><th>Tags</th>';
  for (const a of AGENTS) head.innerHTML += `<th>${{a}}</th>`;
  body.innerHTML = '';

  for (const d of filtered) {{
    const tr = document.createElement('tr');
    let tagHtml = '';
    for (const [k,v] of Object.entries(d.tags)) {{
      tagHtml += `<span class="tag tag-${{k}}">${{v.replace(/_/g,' ')}}</span> `;
    }}
    let cells = `<td><button class="expand-btn" onclick="toggleDetail('${{d.id}}')">${{d.id}}</button><br><span style="font-size:11px;color:#6b7280">${{d.question.substring(0,60)}}...</span></td><td>${{tagHtml}}</td>`;
    for (const a of AGENTS) {{
      const ag = d.agents[a];
      if (!ag) {{ cells += '<td class="score-na">—</td>'; continue; }}
      const os = ag.scores.outcome;
      const sc = os ? `<span class="score ${{scoreClass(os.v)}}">${{os.v.toFixed(1)}}</span>` : '—';
      const tools = (ag.tool_calls||[]).map(t => {{
        let cls = 'sql';
        if (t.includes('search')) cls = 'search';
        else if (t.includes('context') || t.includes('lookup')) cls = 'context';
        return `<span class="tool-chip ${{cls}}">${{t}}</span>`;
      }}).join(' ');
      const tables = (ag.tables||[]).map(t => `<span style="font-size:10px;color:#90A4AE">${{t}}</span>`).join(', ');
      cells += `<td>${{sc}}<br>${{tools}}<br>${{tables}}</td>`;
    }}
    tr.innerHTML = cells;
    body.appendChild(tr);

    // Detail row
    const detailTr = document.createElement('tr');
    detailTr.className = 'detail-row';
    detailTr.id = `detail-${{d.id}}`;
    let detailHtml = `<td colspan="${{2+AGENTS.length}}" class="detail-cell">`;
    for (const a of AGENTS) {{
      const ag = d.agents[a];
      if (!ag) continue;
      detailHtml += `<strong style="color:${{AGENT_COLORS[a]}}">${{a}}</strong> (${{ag.latency}}s)`;
      if (ag.scores) {{
        detailHtml += '<br>';
        for (const [m, s] of Object.entries(ag.scores)) {{
          detailHtml += `&nbsp;&nbsp;<span class="score ${{scoreClass(s.v)}}">${{m}}: ${{s.v.toFixed(2)}}</span> <span style="color:#546E7A;font-size:10px">(${{s.r}})</span><br>`;
        }}
      }}
      if (ag.response_excerpt) {{
        const escaped = ag.response_excerpt.replace(/</g,'&lt;').replace(/>/g,'&gt;');
        detailHtml += `<pre>${{escaped}}</pre>`;
      }}
      detailHtml += '<br>';
    }}
    detailHtml += '</td>';
    detailTr.innerHTML = detailHtml;
    body.appendChild(detailTr);
  }}
}}

function toggleDetail(id) {{
  const el = document.getElementById(`detail-${{id}}`);
  if (el) el.classList.toggle('open');
}}

function drawRadar(filtered) {{
  const canvas = document.getElementById('radarChart');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, 400, 400);
  const cx = 200, cy = 200, maxR = 150;
  const metrics = METRICS.filter(m => {{
    return AGENTS.some(a => filtered.some(d => d.agents[a]?.scores[m]));
  }});
  if (metrics.length < 3) return;
  const step = (Math.PI * 2) / metrics.length;

  // Grid
  for (let r = 0.25; r <= 1; r += 0.25) {{
    ctx.beginPath();
    for (let i = 0; i <= metrics.length; i++) {{
      const angle = i * step - Math.PI/2;
      const x = cx + Math.cos(angle) * maxR * r;
      const y = cy + Math.sin(angle) * maxR * r;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }}
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.stroke();
  }}

  // Labels
  ctx.font = '10px system-ui';
  ctx.fillStyle = '#6b7280';
  for (let i = 0; i < metrics.length; i++) {{
    const angle = i * step - Math.PI/2;
    const x = cx + Math.cos(angle) * (maxR + 20);
    const y = cy + Math.sin(angle) * (maxR + 20);
    ctx.textAlign = 'center';
    ctx.fillText(metrics[i].replace(/_/g,' '), x, y);
  }}

  // Agent polygons
  for (const agent of AGENTS) {{
    const color = AGENT_COLORS[agent];
    ctx.beginPath();
    for (let i = 0; i < metrics.length; i++) {{
      const m = metrics[i];
      const vals = filtered.flatMap(d => d.agents[agent]?.scores[m] ? [d.agents[agent].scores[m].v] : []);
      const avg = vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length : 0;
      const angle = i * step - Math.PI/2;
      const x = cx + Math.cos(angle) * maxR * avg;
      const y = cy + Math.sin(angle) * maxR * avg;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }}
    ctx.closePath();
    ctx.fillStyle = color + '20';
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();
  }}
}}

function applyFilters() {{
  const filtered = getFiltered();
  renderSummary(filtered);
  renderTable(filtered);
  drawRadar(filtered);
}}

initFilters();
applyFilters();
</script>
</body>
</html>"""
