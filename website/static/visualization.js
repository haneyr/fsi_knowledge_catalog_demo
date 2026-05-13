// Point Cloud Visualization Engine for FSI Knowledge Catalog Demo

const COLORS = {
  basic: '#4285F4', scaled: '#EA4335', kc: '#34A853',
  bronze: '#FF8F00', silver: '#90A4AE', gold: '#FFD600',
  ref: '#546E7A', bg: '#0a0e1a', metadata: 'rgba(52,168,83,0.15)',
  lineage: 'rgba(255,255,255,0.35)', glossaryArc: 'rgba(52,168,83,0.6)',
};

const TABLES = {
  bronze: [
    'bronze_customers','bronze_accounts','bronze_transactions','bronze_loans',
    'bronze_loan_payments','bronze_credit_cards','bronze_card_transactions',
    'bronze_fraud_alerts','bronze_kyc_records','bronze_branches','bronze_employees',
    'bronze_wire_transfers','bronze_ach_transfers','bronze_atm_transactions',
    'bronze_wm_clients','bronze_portfolios','bronze_holdings','bronze_trades',
    'bronze_securities','bronze_advisors','bronze_performance','bronze_fee_schedules',
    'bronze_benchmarks','bronze_client_goals','bronze_risk_profiles','bronze_distributions',
    'bronze_custodian_feeds','bronze_gl_entries','bronze_gl_accounts','bronze_cost_centers',
    'bronze_regulatory_capital','bronze_risk_exposures','bronze_counterparties',
    'bronze_market_data','bronze_stress_tests','bronze_audit_events',
    'bronze_regulatory_filings','bronze_interest_rates','bronze_fx_rates','bronze_compliance_cases',
  ],
  silver: [
    'silver_customers','silver_accounts','silver_transactions','silver_loans',
    'silver_loan_payments','silver_credit_cards','silver_card_transactions',
    'silver_fraud_alerts','silver_kyc_records','silver_branches','silver_employees',
    'silver_wire_transfers','silver_ach_transfers','silver_atm_transactions',
    'silver_wm_clients','silver_portfolios','silver_holdings','silver_trades',
    'silver_securities','silver_advisors','silver_performance','silver_fee_schedules',
    'silver_benchmarks','silver_client_goals','silver_risk_profiles','silver_distributions',
    'silver_custodian_feeds','silver_gl_entries','silver_gl_accounts','silver_cost_centers',
    'silver_regulatory_capital','silver_risk_exposures','silver_counterparties',
    'silver_market_data','silver_stress_tests','silver_audit_events',
    'silver_regulatory_filings','silver_interest_rates','silver_fx_rates','silver_compliance_cases',
  ],
  gold: [
    'gold_customer_360','gold_account_summary','gold_transaction_patterns',
    'gold_loan_portfolio_summary','gold_delinquency_analysis','gold_fraud_analytics',
    'gold_aml_risk_scoring','gold_branch_performance','gold_portfolio_performance',
    'gold_client_revenue','gold_asset_allocation','gold_advisor_scorecard',
    'gold_fee_revenue','gold_net_interest_margin','gold_capital_adequacy',
    'gold_liquidity_coverage','gold_market_risk_var','gold_operational_risk',
    'gold_regulatory_dashboard','gold_balance_sheet_summary',
  ],
  ref: [
    'ref_naics_codes','ref_country_codes','ref_currency_codes','ref_cusip_master',
    'ref_isin_mapping','ref_lei_registry','ref_fed_district_codes','ref_product_catalog',
    'staging_call_report_rc','staging_call_report_ri','staging_fr_y9c',
    'snapshot_monthly_balances','snapshot_quarterly_positions','audit_data_access_log',
  ],
};

const BASIC_TABLES = [
  'gold_customer_360','gold_account_summary','gold_loan_portfolio_summary',
  'gold_portfolio_performance','gold_balance_sheet_summary',
];

// Silver → Gold source dependencies (from lineage script)
const GOLD_SOURCES = {
  gold_customer_360: ['silver_customers','silver_accounts','silver_loans','silver_credit_cards','silver_wm_clients'],
  gold_account_summary: ['silver_accounts','silver_transactions'],
  gold_transaction_patterns: ['silver_transactions'],
  gold_loan_portfolio_summary: ['silver_loans'],
  gold_delinquency_analysis: ['silver_loans'],
  gold_fraud_analytics: ['silver_fraud_alerts'],
  gold_aml_risk_scoring: ['silver_customers','silver_kyc_records','silver_compliance_cases','silver_wire_transfers'],
  gold_branch_performance: ['silver_branches','silver_accounts','silver_loans','silver_transactions'],
  gold_portfolio_performance: ['silver_portfolios','silver_performance','silver_holdings','silver_benchmarks'],
  gold_client_revenue: ['silver_wm_clients','silver_fee_schedules','silver_portfolios','silver_trades'],
  gold_asset_allocation: ['silver_holdings'],
  gold_advisor_scorecard: ['silver_advisors','silver_portfolios','silver_performance','silver_trades'],
  gold_fee_revenue: ['silver_fee_schedules','silver_wm_clients'],
  gold_net_interest_margin: ['silver_accounts','silver_loans'],
  gold_capital_adequacy: ['silver_regulatory_capital'],
  gold_liquidity_coverage: ['silver_accounts'],
  gold_market_risk_var: ['silver_holdings','silver_market_data'],
  gold_operational_risk: ['silver_audit_events'],
  gold_regulatory_dashboard: ['silver_regulatory_capital','silver_kyc_records','silver_regulatory_filings'],
  gold_balance_sheet_summary: ['silver_accounts','silver_loans','silver_holdings','silver_regulatory_capital'],
};

// Glossary terms → tables they connect (for semantic arc visualization)
const GLOSSARY_LINKS = {
  'FICO Score': ['gold_loan_portfolio_summary','silver_loans','bronze_loans','gold_delinquency_analysis'],
  'AUM': ['gold_customer_360','gold_advisor_scorecard','gold_client_revenue','silver_wm_clients'],
  'SAR': ['gold_fraud_analytics','gold_aml_risk_scoring','bronze_fraud_alerts','bronze_compliance_cases'],
  'CET1 Ratio': ['gold_capital_adequacy','silver_regulatory_capital','bronze_regulatory_capital'],
  'Customer ID': ['gold_customer_360','silver_customers','bronze_customers','gold_account_summary'],
  'Delinquency': ['gold_loan_portfolio_summary','gold_delinquency_analysis','silver_loans'],
  'KYC': ['gold_aml_risk_scoring','bronze_kyc_records','gold_customer_360'],
  'VaR': ['gold_market_risk_var','silver_holdings','silver_market_data'],
  'CUSIP': ['silver_securities','bronze_securities','gold_asset_allocation'],
  'Branch': ['gold_branch_performance','gold_customer_360','bronze_branches','gold_net_interest_margin'],
  'NIM': ['gold_net_interest_margin','silver_accounts','silver_loans'],
  'Risk Rating': ['gold_loan_portfolio_summary','silver_loans','bronze_loans'],
};

class PointCloud {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.nodes = [];
    this.nodeMap = {};
    this.agentMode = 'basic';
    this.activeNodes = [];
    this.animationState = null;
    this.animationTime = 0;
    this.hoveredNode = null;
    this.metadataLines = [];
    this.activeLineage = [];
    this.activeGlossaryArcs = [];
    this._searchPulseRadius = 0;
    this._searchPulseAlpha = 0;
    this.resize();
    this._buildNodes();
    this._setupMouse();
    this._animate();
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * window.devicePixelRatio;
    this.canvas.height = rect.height * window.devicePixelRatio;
    this.canvas.style.width = rect.width + 'px';
    this.canvas.style.height = rect.height + 'px';
    this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    this.w = rect.width;
    this.h = rect.height;
    this.cx = this.w / 2;
    this.cy = this.h / 2;
    if (this.nodes.length) this._positionNodes();
  }

  _buildNodes() {
    let id = 0;
    for (const [layer, tables] of Object.entries(TABLES)) {
      for (const name of tables) {
        const node = {
          id: id++, name, layer,
          x: 0, y: 0, baseX: 0, baseY: 0,
          radius: layer === 'gold' ? 4 : layer === 'ref' ? 2 : 3,
          color: COLORS[layer],
          alpha: 1, glow: 0, label: '', labelAlpha: 0,
          orbitAngle: Math.random() * Math.PI * 2,
          orbitSpeed: (0.0002 + Math.random() * 0.0003) * (Math.random() > 0.5 ? 1 : -1),
          jitterX: 0, jitterY: 0,
        };
        this.nodes.push(node);
        this.nodeMap[name] = node;
      }
    }
    this._positionNodes();
  }

  _positionNodes() {
    const maxR = Math.min(this.cx, this.cy) * 0.85;
    for (const node of this.nodes) {
      if (this.agentMode === 'basic') this._positionBasic(node, maxR);
      else if (this.agentMode === 'scaled') this._positionScaled(node, maxR);
      else this._positionKC(node, maxR);
    }
  }

  _positionBasic(node, maxR) {
    const isBasic = BASIC_TABLES.includes(node.name);
    if (isBasic) {
      const idx = BASIC_TABLES.indexOf(node.name);
      const angle = (idx / BASIC_TABLES.length) * Math.PI * 2 - Math.PI / 2;
      node.baseX = this.cx + Math.cos(angle) * maxR * 0.25;
      node.baseY = this.cy + Math.sin(angle) * maxR * 0.25;
      node.alpha = 1; node.radius = 6;
    } else {
      node.baseX = this.cx + Math.cos(node.orbitAngle) * maxR * (0.7 + Math.random() * 0.3);
      node.baseY = this.cy + Math.sin(node.orbitAngle) * maxR * (0.7 + Math.random() * 0.3);
      node.alpha = 0.08; node.radius = 1.5;
    }
  }

  _positionScaled(node, maxR) {
    const r = maxR * (0.15 + Math.random() * 0.8);
    node.baseX = this.cx + Math.cos(node.orbitAngle) * r;
    node.baseY = this.cy + Math.sin(node.orbitAngle) * r;
    node.alpha = 0.5 + Math.random() * 0.3;
    node.radius = node.layer === 'gold' ? 3.5 : node.layer === 'ref' ? 2 : 3;
  }

  _positionKC(node, maxR) {
    const rings = { bronze: 0.75, silver: 0.55, gold: 0.3, ref: 0.9 };
    const ringR = maxR * (rings[node.layer] || 0.7);
    const tables = TABLES[node.layer];
    const idx = tables.indexOf(node.name);
    const angle = (idx / tables.length) * Math.PI * 2 + (node.layer === 'silver' ? 0.1 : 0);
    node.baseX = this.cx + Math.cos(angle) * ringR;
    node.baseY = this.cy + Math.sin(angle) * ringR;
    node.alpha = node.layer === 'ref' ? 0.3 : 0.7;
    node.radius = node.layer === 'gold' ? 4.5 : node.layer === 'ref' ? 2 : 3;
  }

  setMode(mode) {
    this.agentMode = mode;
    this.activeNodes = [];
    this.animationState = null;
    this.metadataLines = [];
    this.activeLineage = [];
    this.activeGlossaryArcs = [];
    this._searchPulseRadius = 0;
    this._searchPulseAlpha = 0;
    for (const n of this.nodes) { n.glow = 0; n.labelAlpha = 0; n.label = ''; }
    this._positionNodes();
  }

  triggerQuery(tablesUsed, toolCalls, metadataCited, lineagePath, glossaryTermsCited) {
    this.activeNodes = [];
    this.metadataLines = [];
    this.activeLineage = [];
    this.activeGlossaryArcs = [];
    for (const n of this.nodes) { n.glow = 0; n.labelAlpha = 0; n.label = ''; }

    const used = new Set(tablesUsed || []);
    this.activeNodes = this.nodes.filter(n => used.has(n.name));

    if (metadataCited) {
      for (let i = 0; i < this.activeNodes.length && i < metadataCited.length; i++) {
        this.activeNodes[i].label = metadataCited[i];
      }
    }

    // Build lineage lines for active tables
    if (this.agentMode === 'kc' && tablesUsed) {
      this._buildLineageForTables(tablesUsed, lineagePath);
    }

    // Build glossary arcs for cited terms
    if (this.agentMode === 'kc' && glossaryTermsCited) {
      this._buildGlossaryArcs(glossaryTermsCited);
    }

    this.animationState = this.agentMode;
    this.animationTime = 0;
  }

  _buildLineageForTables(tablesUsed, lineagePath) {
    const allLineage = [];

    if (lineagePath && lineagePath.length > 1) {
      for (let i = 0; i < lineagePath.length - 1; i++) {
        const src = this.nodeMap[lineagePath[i]];
        const tgt = this.nodeMap[lineagePath[i + 1]];
        if (src && tgt) allLineage.push({ src, tgt, alpha: 0 });
      }
    }

    for (const tbl of tablesUsed) {
      // Gold → silver source links
      if (tbl.startsWith('gold_') && GOLD_SOURCES[tbl]) {
        for (const silverTbl of GOLD_SOURCES[tbl]) {
          const src = this.nodeMap[silverTbl];
          const tgt = this.nodeMap[tbl];
          if (src && tgt) allLineage.push({ src, tgt, alpha: 0 });

          // Silver → bronze (same base name)
          const baseName = silverTbl.replace('silver_', '');
          const bronzeTbl = 'bronze_' + baseName;
          const bSrc = this.nodeMap[bronzeTbl];
          if (bSrc && src) allLineage.push({ src: bSrc, tgt: src, alpha: 0 });
        }
      }
      // Silver → bronze direct
      if (tbl.startsWith('silver_')) {
        const bronzeTbl = tbl.replace('silver_', 'bronze_');
        const src = this.nodeMap[bronzeTbl];
        const tgt = this.nodeMap[tbl];
        if (src && tgt) allLineage.push({ src, tgt, alpha: 0 });
      }
    }

    // Deduplicate
    const seen = new Set();
    this.activeLineage = allLineage.filter(l => {
      const key = l.src.name + '->' + l.tgt.name;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  _buildGlossaryArcs(termsCited) {
    this.activeGlossaryArcs = [];
    for (const term of termsCited) {
      const tables = GLOSSARY_LINKS[term];
      if (!tables || tables.length < 2) continue;
      const nodes = tables.map(t => this.nodeMap[t]).filter(Boolean);
      if (nodes.length < 2) continue;
      for (let i = 0; i < nodes.length - 1; i++) {
        this.activeGlossaryArcs.push({
          a: nodes[i], b: nodes[i + 1],
          term, alpha: 0, labelAlpha: 0,
        });
      }
    }
  }

  _setupMouse() {
    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      this.hoveredNode = null;
      for (const n of this.nodes) {
        if (n.alpha < 0.15) continue;
        const dx = n.x - mx, dy = n.y - my;
        if (dx * dx + dy * dy < 100) { this.hoveredNode = n; break; }
      }
      this.canvas.style.cursor = this.hoveredNode ? 'pointer' : 'default';
    });
  }

  _animate() {
    this.animationTime += 16;
    const t = this.animationTime;

    for (const n of this.nodes) {
      n.orbitAngle += n.orbitSpeed;
      n.jitterX = Math.sin(t * 0.001 + n.id) * 1.5;
      n.jitterY = Math.cos(t * 0.0012 + n.id * 1.3) * 1.5;
      n.x += (n.baseX + n.jitterX - n.x) * 0.03;
      n.y += (n.baseY + n.jitterY - n.y) * 0.03;
    }

    if (this.animationState) this._updateQueryAnimation();
    this._draw();
    requestAnimationFrame(() => this._animate());
  }

  _updateQueryAnimation() {
    const elapsed = this.animationTime;

    if (this.agentMode === 'basic') {
      for (const n of this.activeNodes)
        n.glow = elapsed > 500 ? Math.min((elapsed - 500) / 500, 1) : 0;
      if (elapsed > 2000) this.animationState = null;

    } else if (this.agentMode === 'scaled') {
      if (elapsed < 1500) {
        for (const n of this.nodes) {
          if (n.alpha < 0.15) continue;
          n.glow = (Math.random() < 0.03 && elapsed < 1200) ? 0.6 : n.glow * 0.9;
        }
      }
      for (const n of this.activeNodes)
        n.glow = elapsed > 1500 ? Math.min((elapsed - 1500) / 500, 0.7) : n.glow;
      if (elapsed > 3000) this.animationState = null;

    } else if (this.agentMode === 'kc') {
      // Search pulse (0-1s)
      this._searchPulseRadius = elapsed < 1000 ? (elapsed / 1000) * Math.min(this.cx, this.cy) : 0;
      this._searchPulseAlpha = elapsed < 1000 ? 1 - elapsed / 1000 : 0;

      // Tables illuminate (1s+)
      for (let i = 0; i < this.activeNodes.length; i++) {
        const delay = 1000 + i * 400;
        const n = this.activeNodes[i];
        n.glow = elapsed > delay ? Math.min((elapsed - delay) / 400, 1) : 0;
        n.labelAlpha = elapsed > delay + 2000 ? Math.min((elapsed - delay - 2000) / 500, 1) : 0;
      }

      // Lineage lines light up (1.5s+)
      for (const line of this.activeLineage) {
        line.alpha = elapsed > 1500 ? Math.min((elapsed - 1500) / 600, 0.5) : 0;
      }

      // Glossary arcs appear (2.5s+)
      for (const arc of this.activeGlossaryArcs) {
        arc.alpha = elapsed > 2500 ? Math.min((elapsed - 2500) / 500, 0.6) : 0;
        arc.labelAlpha = elapsed > 3000 ? Math.min((elapsed - 3000) / 500, 0.7) : 0;
      }

      if (elapsed > 5000) this.animationState = null;
    }
  }

  _draw() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.w, this.h);

    // KC ring hints
    if (this.agentMode === 'kc') {
      const maxR = Math.min(this.cx, this.cy) * 0.85;
      for (const r of [0.75, 0.55, 0.3]) {
        ctx.beginPath();
        ctx.arc(this.cx, this.cy, maxR * r, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255,255,255,0.04)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    // Search pulse
    if (this._searchPulseRadius > 0 && this._searchPulseAlpha > 0) {
      ctx.beginPath();
      ctx.arc(this.cx, this.cy, this._searchPulseRadius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(52,168,83,${this._searchPulseAlpha * 0.4})`;
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // --- Layer 1: Lineage lines (straight, white/gray) ---
    for (const line of this.activeLineage) {
      if (line.alpha <= 0) continue;
      ctx.beginPath();
      ctx.moveTo(line.src.x, line.src.y);
      ctx.lineTo(line.tgt.x, line.tgt.y);
      ctx.strokeStyle = `rgba(200,210,230,${line.alpha})`;
      ctx.lineWidth = 1;
      ctx.stroke();

      // Small directional dot at midpoint
      const mx = (line.src.x + line.tgt.x) / 2;
      const my = (line.src.y + line.tgt.y) / 2;
      ctx.beginPath();
      ctx.arc(mx, my, 1.5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200,210,230,${line.alpha * 0.8})`;
      ctx.fill();
    }

    // --- Layer 2: Glossary arcs (curved, green, dashed) ---
    for (const arc of this.activeGlossaryArcs) {
      if (arc.alpha <= 0) continue;
      const a = arc.a, b = arc.b;
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      const dx = b.x - a.x, dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const curvature = Math.min(dist * 0.3, 60);
      const cpx = mx - (dy / dist) * curvature;
      const cpy = my + (dx / dist) * curvature;

      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.quadraticCurveTo(cpx, cpy, b.x, b.y);
      ctx.strokeStyle = `rgba(52,168,83,${arc.alpha})`;
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1.2;
      ctx.stroke();
      ctx.setLineDash([]);

      // Term label at curve midpoint
      if (arc.labelAlpha > 0) {
        const labelX = (a.x + 2 * cpx + b.x) / 4;
        const labelY = (a.y + 2 * cpy + b.y) / 4;
        ctx.font = '9px system-ui';
        ctx.fillStyle = `rgba(52,168,83,${arc.labelAlpha})`;
        const tw = ctx.measureText(arc.term).width;
        ctx.fillStyle = `rgba(10,14,26,${arc.labelAlpha * 0.7})`;
        ctx.fillRect(labelX - tw / 2 - 3, labelY - 8, tw + 6, 14);
        ctx.fillStyle = `rgba(52,168,83,${arc.labelAlpha})`;
        ctx.fillText(arc.term, labelX - tw / 2, labelY + 3);
      }
    }

    // Beams from active nodes to center
    for (const n of this.activeNodes) {
      if (n.glow > 0.3) {
        const col = COLORS[this.agentMode];
        ctx.beginPath();
        ctx.moveTo(n.x, n.y);
        ctx.lineTo(this.cx, this.cy);
        ctx.strokeStyle = `${col}${Math.floor(n.glow * 80).toString(16).padStart(2, '0')}`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }

    // Nodes
    for (const n of this.nodes) {
      if (n.alpha < 0.01) continue;
      const alpha = Math.min(n.alpha + n.glow * 0.5, 1);
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + n.glow * 3, 0, Math.PI * 2);
      ctx.fillStyle = n.color + Math.floor(alpha * 255).toString(16).padStart(2, '0');
      ctx.fill();

      if (n.glow > 0.2) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius + n.glow * 8, 0, Math.PI * 2);
        ctx.fillStyle = n.color + Math.floor(n.glow * 40).toString(16).padStart(2, '0');
        ctx.fill();
      }

      if (n.labelAlpha > 0 && n.label) {
        ctx.font = '10px system-ui';
        ctx.fillStyle = `rgba(255,255,255,${n.labelAlpha * 0.8})`;
        ctx.fillText(n.label, n.x + n.radius + 6, n.y + 3);
      }
    }

    // Agent center orb
    const agentColor = COLORS[this.agentMode];
    const pulseSize = this.animationState ? 18 + Math.sin(this.animationTime * 0.005) * 4 : 15;
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, pulseSize, 0, Math.PI * 2);
    const grad = ctx.createRadialGradient(this.cx, this.cy, 0, this.cx, this.cy, pulseSize);
    grad.addColorStop(0, agentColor);
    grad.addColorStop(1, agentColor + '00');
    ctx.fillStyle = grad;
    ctx.fill();

    ctx.beginPath();
    ctx.arc(this.cx, this.cy, 8, 0, Math.PI * 2);
    ctx.fillStyle = agentColor;
    ctx.fill();

    ctx.beginPath();
    ctx.arc(this.cx, this.cy, pulseSize + 10, 0, Math.PI * 2);
    ctx.fillStyle = agentColor + '10';
    ctx.fill();

    // Tooltip
    if (this.hoveredNode) {
      const n = this.hoveredNode;
      ctx.font = '12px system-ui';
      const tw = ctx.measureText(n.name).width;
      ctx.fillStyle = 'rgba(15,21,37,0.9)';
      ctx.fillRect(n.x + 8, n.y - 18, tw + 8, 20);
      ctx.fillStyle = '#e0e0e0';
      ctx.fillText(n.name, n.x + 12, n.y - 4);
    }

    // Basic agent labels
    if (this.agentMode === 'basic') {
      ctx.font = '11px system-ui';
      for (const n of this.nodes) {
        if (BASIC_TABLES.includes(n.name) && n.alpha > 0.5) {
          ctx.fillStyle = 'rgba(255,255,255,0.6)';
          ctx.fillText(n.name.replace('gold_', ''), n.x + n.radius + 6, n.y + 3);
        }
      }
    }
  }
}

window.PointCloud = PointCloud;
