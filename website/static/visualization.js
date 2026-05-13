// Point Cloud Visualization Engine for FSI Knowledge Catalog Demo

const COLORS = {
  basic: '#4285F4', scaled: '#EA4335', kc: '#34A853',
  bronze: '#FF8F00', silver: '#90A4AE', gold: '#FFD600',
  ref: '#546E7A', bg: '#0a0e1a', metadata: 'rgba(52,168,83,0.15)',
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

class PointCloud {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.nodes = [];
    this.agentMode = 'basic';
    this.activeNodes = [];
    this.animationState = null;
    this.animationTime = 0;
    this.hoveredNode = null;
    this.metadataLines = [];
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
        this.nodes.push({
          id: id++, name, layer,
          x: 0, y: 0, baseX: 0, baseY: 0,
          radius: layer === 'gold' ? 4 : layer === 'ref' ? 2 : 3,
          color: COLORS[layer],
          alpha: 1, glow: 0, label: '', labelAlpha: 0,
          orbitAngle: Math.random() * Math.PI * 2,
          orbitSpeed: (0.0002 + Math.random() * 0.0003) * (Math.random() > 0.5 ? 1 : -1),
          jitterX: 0, jitterY: 0,
        });
      }
    }
    this._positionNodes();
  }

  _positionNodes() {
    const maxR = Math.min(this.cx, this.cy) * 0.85;
    for (const node of this.nodes) {
      if (this.agentMode === 'basic') {
        this._positionBasic(node, maxR);
      } else if (this.agentMode === 'scaled') {
        this._positionScaled(node, maxR);
      } else {
        this._positionKC(node, maxR);
      }
    }
  }

  _positionBasic(node, maxR) {
    const isBasic = BASIC_TABLES.includes(node.name);
    if (isBasic) {
      const idx = BASIC_TABLES.indexOf(node.name);
      const angle = (idx / BASIC_TABLES.length) * Math.PI * 2 - Math.PI / 2;
      const r = maxR * 0.25;
      node.baseX = this.cx + Math.cos(angle) * r;
      node.baseY = this.cy + Math.sin(angle) * r;
      node.alpha = 1;
      node.radius = 6;
    } else {
      const angle = node.orbitAngle;
      const r = maxR * (0.7 + Math.random() * 0.3);
      node.baseX = this.cx + Math.cos(angle) * r;
      node.baseY = this.cy + Math.sin(angle) * r;
      node.alpha = 0.08;
      node.radius = 1.5;
    }
  }

  _positionScaled(node, maxR) {
    const angle = node.orbitAngle;
    const r = maxR * (0.15 + Math.random() * 0.8);
    node.baseX = this.cx + Math.cos(angle) * r;
    node.baseY = this.cy + Math.sin(angle) * r;
    node.alpha = 0.5 + Math.random() * 0.3;
    node.radius = node.layer === 'gold' ? 3.5 : node.layer === 'ref' ? 2 : 3;
  }

  _positionKC(node, maxR) {
    const layerRings = { bronze: 0.75, silver: 0.55, gold: 0.3, ref: 0.9 };
    const ringR = maxR * (layerRings[node.layer] || 0.7);
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
    for (const n of this.nodes) { n.glow = 0; n.labelAlpha = 0; n.label = ''; }
    this._positionNodes();
  }

  triggerQuery(tablesUsed, toolCalls, metadataCited) {
    this.activeNodes = [];
    this.metadataLines = [];
    for (const n of this.nodes) { n.glow = 0; n.labelAlpha = 0; n.label = ''; }

    const used = new Set(tablesUsed || []);
    this.activeNodes = this.nodes.filter(n => used.has(n.name));

    if (metadataCited) {
      for (let i = 0; i < this.activeNodes.length && i < metadataCited.length; i++) {
        this.activeNodes[i].label = metadataCited[i];
      }
    }

    this.animationState = this.agentMode;
    this.animationTime = 0;
  }

  _setupMouse() {
    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
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

      const lerpSpeed = 0.03;
      n.x += (n.baseX + n.jitterX - n.x) * lerpSpeed;
      n.y += (n.baseY + n.jitterY - n.y) * lerpSpeed;
    }

    if (this.animationState) {
      this._updateQueryAnimation(t);
    }

    this._draw();
    requestAnimationFrame(() => this._animate());
  }

  _updateQueryAnimation(t) {
    const elapsed = this.animationTime;
    const agentColor = COLORS[this.agentMode];

    if (this.agentMode === 'basic') {
      for (const n of this.activeNodes) {
        n.glow = elapsed > 500 ? Math.min((elapsed - 500) / 500, 1) : 0;
      }
      if (elapsed > 2000) this.animationState = null;

    } else if (this.agentMode === 'scaled') {
      if (elapsed < 1500) {
        const flickerCount = Math.floor(elapsed / 200);
        for (const n of this.nodes) {
          if (n.alpha < 0.15) continue;
          n.glow = (Math.random() < 0.03 && elapsed < 1200) ? 0.6 : n.glow * 0.9;
        }
      }
      for (const n of this.activeNodes) {
        n.glow = elapsed > 1500 ? Math.min((elapsed - 1500) / 500, 0.7) : n.glow;
      }
      if (elapsed > 3000) this.animationState = null;

    } else if (this.agentMode === 'kc') {
      this._searchPulseRadius = elapsed < 1000 ? (elapsed / 1000) * Math.min(this.cx, this.cy) : 0;
      this._searchPulseAlpha = elapsed < 1000 ? 1 - elapsed / 1000 : 0;

      for (let i = 0; i < this.activeNodes.length; i++) {
        const delay = 1000 + i * 500;
        const n = this.activeNodes[i];
        n.glow = elapsed > delay ? Math.min((elapsed - delay) / 400, 1) : 0;
        n.labelAlpha = elapsed > delay + 1500 ? Math.min((elapsed - delay - 1500) / 500, 1) : 0;
      }

      if (elapsed > 1500 && this.activeNodes.length >= 2) {
        this.metadataLines = [];
        for (let i = 0; i < this.activeNodes.length - 1; i++) {
          const a = this.activeNodes[i], b = this.activeNodes[i + 1];
          const lineAlpha = Math.min((elapsed - 1500) / 500, 0.5);
          this.metadataLines.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y, alpha: lineAlpha });
        }
      }

      if (elapsed > 4000) this.animationState = null;
    }
  }

  _draw() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.w, this.h);

    // KC metadata ring hints
    if (this.agentMode === 'kc') {
      const maxR = Math.min(this.cx, this.cy) * 0.85;
      for (const [r, label] of [[0.75, 'Bronze'], [0.55, 'Silver'], [0.3, 'Gold']]) {
        ctx.beginPath();
        ctx.arc(this.cx, this.cy, maxR * r, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255,255,255,0.04)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    // Search pulse (KC only)
    if (this._searchPulseRadius > 0 && this._searchPulseAlpha > 0) {
      ctx.beginPath();
      ctx.arc(this.cx, this.cy, this._searchPulseRadius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(52,168,83,${this._searchPulseAlpha * 0.4})`;
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Metadata lines
    for (const line of this.metadataLines) {
      ctx.beginPath();
      ctx.moveTo(line.x1, line.y1);
      ctx.lineTo(line.x2, line.y2);
      ctx.strokeStyle = `rgba(52,168,83,${line.alpha})`;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Beams from active nodes to center
    for (const n of this.activeNodes) {
      if (n.glow > 0.3) {
        const agentColor = COLORS[this.agentMode];
        ctx.beginPath();
        ctx.moveTo(n.x, n.y);
        ctx.lineTo(this.cx, this.cy);
        ctx.strokeStyle = `${agentColor}${Math.floor(n.glow * 80).toString(16).padStart(2, '0')}`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }

    // Nodes
    for (const n of this.nodes) {
      if (n.alpha < 0.01) continue;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + n.glow * 3, 0, Math.PI * 2);
      const alpha = Math.min(n.alpha + n.glow * 0.5, 1);
      ctx.fillStyle = n.color + Math.floor(alpha * 255).toString(16).padStart(2, '0');
      ctx.fill();

      if (n.glow > 0.2) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius + n.glow * 8, 0, Math.PI * 2);
        ctx.fillStyle = n.color + Math.floor(n.glow * 40).toString(16).padStart(2, '0');
        ctx.fill();
      }

      // Labels (KC metadata citations)
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

    // Outer glow
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, pulseSize + 10, 0, Math.PI * 2);
    ctx.fillStyle = agentColor + '10';
    ctx.fill();

    // Tooltip
    if (this.hoveredNode) {
      const n = this.hoveredNode;
      const text = n.name;
      ctx.font = '12px system-ui';
      const tw = ctx.measureText(text).width;
      const px = n.x + 12, py = n.y - 8;
      ctx.fillStyle = 'rgba(15,21,37,0.9)';
      ctx.fillRect(px - 4, py - 14, tw + 8, 20);
      ctx.fillStyle = '#e0e0e0';
      ctx.fillText(text, px, py);
    }

    // Basic agent labels
    if (this.agentMode === 'basic') {
      ctx.font = '11px system-ui';
      for (const n of this.nodes) {
        if (BASIC_TABLES.includes(n.name) && n.alpha > 0.5) {
          ctx.fillStyle = 'rgba(255,255,255,0.6)';
          const label = n.name.replace('gold_', '');
          ctx.fillText(label, n.x + n.radius + 6, n.y + 3);
        }
      }
    }
  }
}

window.PointCloud = PointCloud;
