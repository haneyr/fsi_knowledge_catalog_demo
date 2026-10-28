// Point Cloud Visualization Engine for [Retail] Northwind Retail Knowledge Catalog Demo

const COLORS = {
  basic: '#58a6ff', scaled: '#f85149', kc: '#3fb950',
  bronze: '#ff9f43', silver: '#a5b4fc', gold: '#ffd33d',
  ref: '#8b949e', snowflake: '#00e5ff',
  bg: '#0d1117', metadata: 'rgba(63,185,80,0.22)',
};

const MAX_VISIBLE_EDGES = 5;

let TABLES = { bronze: [], silver: [], gold: [], ref: [] };
let BASIC_TABLES = [];

class PointCloud {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.nodes = [];
    this.nodeMap = {};
    this.agentMode = 'basic';
    this.activeCategory = 'merchandising';
    this.activeNodes = [];
    this.renderedEdges = [];
    this.fadingEdges = [];
    this._touchSeq = 0;
    this.animationState = null;
    this.animationTime = 0;
    this.hoveredNode = null;
    this.metadataLines = [];
    this.activeLineage = [];
    this.activeGlossaryArcs = [];
    this._searchPulseRadius = 0;
    this._searchPulseAlpha = 0;
    this._pulseStartTime = 0;
    this.zoom = 1; this.targetZoom = 1;
    this.panX = 0; this.panY = 0;
    this.targetPanX = 0; this.targetPanY = 0;
    this._zoomedIn = false;
    this._termLabelPositions = [];
    this.activeGlossaryTerm = null;
    this.renderedGlossaryLabels = [];
    this.onNodeClick = null;
    this.onTermClick = null;
    this.resize();
    this._buildNodes();
    this._setupMouse();
    this._animate();
  }

  configure(config) {
    TABLES = config.tables || { bronze: [], silver: [], gold: [], ref: [] };
    BASIC_TABLES = config.basic_tables || [];
    this.nodes = [];
    this.nodeMap = {};
    this.nodeMapLower = {};
    this.activeNodes = [];
    this.renderedEdges = [];
    this.fadingEdges = [];
    this._touchSeq = 0;
    this.animationState = null;
    this.metadataLines = [];
    this._buildNodes();
  }

  _findNode(tableName) {
    if (!tableName) return null;
    return this.nodeMap[tableName] || this.nodeMapLower[tableName.toLowerCase()] || null;
  }

  setSnowflakeTables(tableNames) {
    if (!tableNames || tableNames.length === 0) return;
    TABLES.snowflake = tableNames;
    this.nodes = this.nodes.filter(n => n.layer !== 'snowflake');
    for (const name of tableNames) {
      const node = {
        id: this.nodes.length, name, layer: 'snowflake',
        x: 0, y: 0, baseX: 0, baseY: 0,
        radius: 5,
        color: COLORS.snowflake,
        alpha: 0.9, glow: 0, label: '', labelAlpha: 0,
        queriedBySql: false, touchedOrder: 0,
        orbitAngle: Math.random() * Math.PI * 2,
        orbitSpeed: (0.0002 + Math.random() * 0.0003) * (Math.random() > 0.5 ? 1 : -1),
        jitterX: 0, jitterY: 0,
      };
      this.nodes.push(node);
      this.nodeMap[name] = node;
      this.nodeMapLower[name.toLowerCase()] = node;
    }
    this._positionNodes();
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
          queriedBySql: false, touchedOrder: 0,
          orbitAngle: Math.random() * Math.PI * 2,
          orbitSpeed: (0.0002 + Math.random() * 0.0003) * (Math.random() > 0.5 ? 1 : -1),
          jitterX: 0, jitterY: 0,
        };
        this.nodes.push(node);
        this.nodeMap[name] = node;
        this.nodeMapLower[name.toLowerCase()] = node;
      }
    }
    this._positionNodes();
  }

  _positionNodes() {
    const maxR = Math.min(this.cx, this.cy) * 0.85;
    for (const node of this.nodes) {
      if (node.layer === 'snowflake') this._positionSnowflake(node, maxR);
      else if (this.agentMode === 'basic') this._positionBasic(node, maxR);
      else if (this.agentMode === 'scaled') this._positionScaled(node, maxR);
      else this._positionKC(node, maxR);
      if ((node.x === 0 && node.y === 0) || this.agentMode === 'kc') {
        node.x = node.baseX;
        node.y = node.baseY;
      }
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
      node.alpha = 0.18; node.radius = 1.5;
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
    const rings = { gold: 0.30, silver: 0.52, bronze: 0.72, ref: 0.90 };
    const ringR = maxR * (rings[node.layer] || 0.72);
    const tables = TABLES[node.layer] || [];
    const idx = Math.max(0, tables.indexOf(node.name));
    const count = Math.max(1, tables.length);
    const offset = node.layer === 'silver' ? (Math.PI / count) : 0;
    const angle = (idx / count) * Math.PI * 2 - Math.PI / 2 + offset;
    node.baseX = this.cx + Math.cos(angle) * ringR;
    node.baseY = this.cy + Math.sin(angle) * ringR;
    node.alpha = node.layer === 'ref' ? 0.45 : 0.85;
    node.radius = node.layer === 'gold' ? 4.5 : node.layer === 'ref' ? 2.5 : 3.5;
  }

  _positionSnowflake(node, maxR) {
    const tables = TABLES.snowflake || [];
    const idx = tables.indexOf(node.name);
    const count = tables.length || 1;
    const clusterCx = this.cx + maxR * 0.72;
    const clusterCy = this.cy + maxR * 0.65;
    const clusterR = Math.min(54, maxR * 0.23);
    const angle = (idx / count) * Math.PI * 2 - Math.PI / 2;
    node.baseX = clusterCx + Math.cos(angle) * clusterR;
    node.baseY = clusterCy + Math.sin(angle) * clusterR;
    if (this.agentMode !== 'kc') {
      node.alpha = 0;
      node.glow = 0;
      node.radius = 0;
      return;
    }
    node.alpha = 0.92;
    node.radius = 5.5;
  }

  setMode(mode) {
    this.agentMode = mode;
    this.activeNodes = [];
    this.renderedEdges = [];
    this.renderedLabels = [];
    this.renderedGlossaryLabels = [];
    this.activeGlossaryTerm = null;
    this._termLabelPositions = [];
    this.fadingEdges = [];
    this._touchSeq = 0;
    this.animationState = null;
    this.metadataLines = [];
    this._searchPulseRadius = 0;
    this._searchPulseAlpha = 0;
    this._resetZoom();
    for (const n of this.nodes) {
      n.glow = 0;
      n.labelAlpha = 0;
      n.label = '';
      n.queriedBySql = false;
      n.touchedOrder = 0;
    }
    this._positionNodes();
  }

  setCategory(category) {
    this.activeCategory = category || 'merchandising';
  }

  triggerQuery(tablesUsed, toolCalls, metadataCited, lineagePath, glossaryTermsCited) {
    this.clearAnimation();
    const used = new Set(tablesUsed || []);
    let seq = 1;
    const allowSnowflake = this.agentMode === 'kc' && this.activeCategory === 'multicloud';
    this.activeNodes = this.nodes.filter(n => {
      if (!used.has(n.name)) return false;
      if (n.layer === 'snowflake' && !allowSnowflake) return false;
      n.queriedBySql = true;
      n.touchedOrder = seq++;
      return true;
    });

    if (metadataCited) {
      for (let i = 0; i < this.activeNodes.length && i < metadataCited.length; i++) {
        this.activeNodes[i].label = metadataCited[i];
      }
    }

    if (this.agentMode === 'kc' && Array.isArray(glossaryTermsCited) && glossaryTermsCited.length > 0) {
      this.setGlossaryEdgeLabel(glossaryTermsCited[0]);
    }

    this.animationState = this.agentMode;
    this.animationTime = 0;
  }

  setGlossaryEdgeLabel(term, targetTable = null) {
    if (!term || this.agentMode !== 'kc') {
      this.activeGlossaryTerm = null;
      return;
    }
    const raw = String(term).trim();
    const display = raw.replace(/^\[Retail\]\s*/i, '').trim();
    if (!display) return;
    this.activeGlossaryTerm = {
      raw: raw.startsWith('[Retail]') ? raw : `[Retail] ${display}`,
      display,
      targetTable: targetTable ? String(targetTable).toLowerCase() : null,
    };
  }

  _getCappedEdgeTargets() {
    const tierPriority = { gold: 0, silver: 1, bronze: 2, ref: 3 };
    const allowSnowflake = this.agentMode === 'kc' && this.activeCategory === 'multicloud';
    const candidates = this.activeNodes.filter(
      n => n.glow > 0.3 && (allowSnowflake || n.layer !== 'snowflake')
    );
    if (candidates.length === 0) return [];

    const sfNodes = candidates
      .filter(n => n.layer === 'snowflake')
      .sort((a, b) => {
        const qa = a.queriedBySql ? 0 : 1;
        const qb = b.queriedBySql ? 0 : 1;
        if (qa !== qb) return qa - qb;
        return (a.touchedOrder || 999) - (b.touchedOrder || 999);
      });

    const bqNodes = candidates
      .filter(n => n.layer !== 'snowflake')
      .sort((a, b) => {
        const qa = a.queriedBySql ? 0 : 1;
        const qb = b.queriedBySql ? 0 : 1;
        if (qa !== qb) return qa - qb;
        const ta = tierPriority[a.layer] ?? 4;
        const tb = tierPriority[b.layer] ?? 4;
        if (ta !== tb) return ta - tb;
        return (a.touchedOrder || 999) - (b.touchedOrder || 999);
      });

    if (this.agentMode === 'kc') {
      const maxKcEdges = 6;
      const selected = [];
      const seen = new Set();

      // 1. At least one edge reaches a cyan NEXUS node when Snowflake was queried/touched
      if (sfNodes.length > 0) {
        selected.push(sfNodes[0]);
        seen.add(sfNodes[0].name);
      }

      // 2. Prioritize layer diversity across touched BigQuery layers (gold, silver, bronze, ref)
      for (const layer of ['gold', 'silver', 'bronze', 'ref']) {
        if (selected.length >= maxKcEdges) break;
        const match = bqNodes.find(n => n.layer === layer && !seen.has(n.name));
        if (match) {
          selected.push(match);
          seen.add(match.name);
        }
      }

      // 3. Fill remaining slots up to 6 from other touched nodes
      for (const n of bqNodes) {
        if (selected.length >= maxKcEdges) break;
        if (!seen.has(n.name)) {
          selected.push(n);
          seen.add(n.name);
        }
      }
      for (const n of sfNodes) {
        if (selected.length >= maxKcEdges) break;
        if (!seen.has(n.name)) {
          selected.push(n);
          seen.add(n.name);
        }
      }

      return selected.slice(0, maxKcEdges);
    }

    const selected = [];
    for (let i = 0; i < bqNodes.length && selected.length < MAX_VISIBLE_EDGES; i++) {
      selected.push(bqNodes[i]);
    }
    return selected.slice(0, MAX_VISIBLE_EDGES);
  }

  _screenToWorld(screenX, screenY) {
    return {
      x: (screenX - this.cx) / this.zoom + this.cx - this.panX,
      y: (screenY - this.cy) / this.zoom + this.cy - this.panY,
    };
  }

  _worldToScreen(wx, wy) {
    return {
      x: this.cx + (wx - this.cx + this.panX) * this.zoom,
      y: this.cy + (wy - this.cy + this.panY) * this.zoom,
    };
  }

  _hitTest(screenX, screenY) {
    const { x: mx, y: my } = this._screenToWorld(screenX, screenY);
    for (const n of this.nodes) {
      if (n.layer === 'snowflake' && this.agentMode !== 'kc') continue;
      if (n.alpha < 0.15) continue;
      const dx = n.x - mx, dy = n.y - my;
      if (dx * dx + dy * dy < 100) return n;
    }
    return null;
  }

  _setupMouse() {
    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      this.hoveredNode = this._hitTest(e.clientX - rect.left, e.clientY - rect.top);
      this.canvas.style.cursor = this.hoveredNode ? 'pointer' : 'default';
    });

    this.canvas.addEventListener('click', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const screenX = e.clientX - rect.left, screenY = e.clientY - rect.top;
      const { x: wx, y: wy } = this._screenToWorld(screenX, screenY);
      for (const tl of this._termLabelPositions) {
        if (Math.abs(wx - tl.x) < tl.hw && Math.abs(wy - tl.y) < tl.hh) {
          if (this.onTermClick) {
            const sp = this._worldToScreen(tl.x, tl.y);
            this.onTermClick(tl.term, sp.x + rect.left, sp.y + rect.top);
          }
          return;
        }
      }
      const node = this._hitTest(screenX, screenY);
      if (node && this.onNodeClick) {
        const sp = this._worldToScreen(node.x, node.y);
        this.onNodeClick(node.name, sp.x + rect.left, sp.y + rect.top);
      }
    });
  }

  _animate() {
    this.animationTime += 16;
    const t = this.animationTime;

    for (const n of this.nodes) {
      n.orbitAngle += n.orbitSpeed;
      if (this.agentMode === 'kc') {
        n.jitterX = 0;
        n.jitterY = 0;
        n.x += (n.baseX - n.x) * 0.2;
        n.y += (n.baseY - n.y) * 0.2;
      } else {
        n.jitterX = Math.sin(t * 0.001 + n.id) * 1.5;
        n.jitterY = Math.cos(t * 0.0012 + n.id * 1.3) * 1.5;
        n.x += (n.baseX + n.jitterX - n.x) * 0.06;
        n.y += (n.baseY + n.jitterY - n.y) * 0.06;
      }
    }

    this.zoom += (this.targetZoom - this.zoom) * 0.04;
    this.panX += (this.targetPanX - this.panX) * 0.04;
    this.panY += (this.targetPanY - this.panY) * 0.04;

    if (this._searchPulseAlpha > 0) {
      const pulseElapsed = t - this._pulseStartTime;
      this._searchPulseRadius = (pulseElapsed / 1000) * Math.min(this.cx, this.cy);
      this._searchPulseAlpha = Math.max(0, 1 - pulseElapsed / 1000);
    }

    if (this.fadingEdges.length > 0) {
      for (const fe of this.fadingEdges) fe.alpha -= 0.04;
      this.fadingEdges = this.fadingEdges.filter(fe => fe.alpha > 0);
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
      this._searchPulseRadius = elapsed < 1000 ? (elapsed / 1000) * Math.min(this.cx, this.cy) : 0;
      this._searchPulseAlpha = elapsed < 1000 ? 1 - elapsed / 1000 : 0;

      for (let i = 0; i < this.activeNodes.length; i++) {
        const delay = 1000 + i * 400;
        const n = this.activeNodes[i];
        n.glow = elapsed > delay ? Math.min((elapsed - delay) / 400, 1) : 0;
        n.labelAlpha = elapsed > delay + 2000 ? Math.min((elapsed - delay - 2000) / 500, 1) : 0;
      }

      if (elapsed > 4000 && !this._zoomedIn) this._triggerZoomToActive();
      if (elapsed > 6000) this.animationState = null;
    }
  }

  _draw() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.w, this.h);

    // Subtle radial vignette on dark canvas
    const bgGrad = ctx.createRadialGradient(this.cx, this.cy, 20, this.cx, this.cy, Math.max(this.w, this.h) * 0.7);
    bgGrad.addColorStop(0, '#131922');
    bgGrad.addColorStop(1, '#0d1117');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, this.w, this.h);

    // Apply zoom/pan transform
    ctx.save();
    ctx.translate(this.cx, this.cy);
    ctx.scale(this.zoom, this.zoom);
    ctx.translate(-this.cx + this.panX, -this.cy + this.panY);

    // Orbital ring guides (4 concentric rings in KC mode: gold, silver, bronze, ref)
    if (this.agentMode === 'kc') {
      const maxR = Math.min(this.cx, this.cy) * 0.85;
      ctx.setLineDash([]);
      for (const r of [0.30, 0.52, 0.72, 0.90]) {
        ctx.beginPath();
        ctx.arc(this.cx, this.cy, maxR * r, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(230,237,243,0.14)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    // Snowflake NEXUS cluster boundary and label (KC Agent only)
    if (this.agentMode === 'kc' && TABLES.snowflake && TABLES.snowflake.length > 0) {
      const maxR = Math.min(this.cx, this.cy) * 0.85;
      const clusterCx = this.cx + maxR * 0.72;
      const clusterCy = this.cy + maxR * 0.65;
      const clusterR = Math.min(54, maxR * 0.23);

      ctx.beginPath();
      ctx.arc(clusterCx, clusterCy, clusterR + 18, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0,229,255,0.04)';
      ctx.fill();
      ctx.strokeStyle = 'rgba(0,229,255,0.38)';
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1.2;
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.font = '600 10px system-ui';
      ctx.fillStyle = 'rgba(0,229,255,0.88)';
      ctx.textAlign = 'center';
      ctx.fillText('NEXUS · Snowflake (External)', clusterCx, clusterCy - clusterR - 24);
      ctx.textAlign = 'left';
    }

    // Search pulse
    if (this._searchPulseRadius > 0 && this._searchPulseAlpha > 0) {
      ctx.beginPath();
      ctx.arc(this.cx, this.cy, this._searchPulseRadius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(63,185,80,${this._searchPulseAlpha * 0.45})`;
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Fade-out edges from previous query when a new query starts
    ctx.setLineDash([]);
    for (const fe of this.fadingEdges) {
      if (fe.alpha <= 0) continue;
      ctx.beginPath();
      ctx.moveTo(this.cx, this.cy);
      ctx.lineTo(fe.x, fe.y);
      ctx.strokeStyle = `rgba(63,185,80,${fe.alpha.toFixed(2)})`;
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Active query-path edges ONLY: solid green (#3fb950), center -> touched nodes only, cap 5 (6 for KC), 0 at idle
    const selectedTargets = this._getCappedEdgeTargets();
    this.renderedEdges = [];
    this.renderedLabels = [];
    this.renderedGlossaryLabels = [];
    this._termLabelPositions = [];
    ctx.setLineDash([]);
    for (const n of selectedTargets) {
      ctx.beginPath();
      ctx.moveTo(this.cx, this.cy);
      ctx.lineTo(n.x, n.y);
      ctx.strokeStyle = '#3fb950';
      ctx.lineWidth = 2;
      ctx.stroke();
      this.renderedEdges.push({
        from: 'center',
        to: n.name,
        layer: n.layer,
        isNexus: n.layer === 'snowflake',
        x: n.x,
        y: n.y,
        color: '#3fb950',
        dashed: false,
      });
    }

    // Nodes (Diamonds for NEXUS Snowflake in KC mode, Circles for BigQuery Medallion)
    for (const n of this.nodes) {
      if (n.layer === 'snowflake' && this.agentMode !== 'kc') continue;
      if (n.alpha < 0.01) continue;
      const alpha = Math.min(n.alpha + n.glow * 0.5, 1);
      const hexAlpha = Math.floor(alpha * 255).toString(16).padStart(2, '0');

      if (n.layer === 'snowflake') {
        const r = n.radius + n.glow * 3.5;
        ctx.save();
        ctx.translate(n.x, n.y);
        ctx.rotate(Math.PI / 4);
        ctx.beginPath();
        ctx.rect(-r * 0.85, -r * 0.85, r * 1.7, r * 1.7);
        ctx.fillStyle = n.color + hexAlpha;
        ctx.fill();
        ctx.strokeStyle = `rgba(230,237,243,${Math.min(alpha * 0.7, 0.9)})`;
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.restore();

        if (n.glow > 0.2) {
          const gr = n.radius + n.glow * 9;
          ctx.save();
          ctx.translate(n.x, n.y);
          ctx.rotate(Math.PI / 4);
          ctx.beginPath();
          ctx.rect(-gr * 0.85, -gr * 0.85, gr * 1.7, gr * 1.7);
          ctx.fillStyle = n.color + Math.floor(n.glow * 50).toString(16).padStart(2, '0');
          ctx.fill();
          ctx.restore();
        }
      } else {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius + n.glow * 3, 0, Math.PI * 2);
        ctx.fillStyle = n.color + hexAlpha;
        ctx.fill();

        if (n.glow > 0.2) {
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius + n.glow * 8, 0, Math.PI * 2);
          ctx.fillStyle = n.color + Math.floor(n.glow * 45).toString(16).padStart(2, '0');
          ctx.fill();
        }
      }
    }

    // Labels ONLY on touched nodes + glossary edge label (KC)
    if (selectedTargets.length > 0) {
      const placedRects = [];
      if (this.agentMode === 'kc' && TABLES.snowflake && TABLES.snowflake.length > 0) {
        const maxR = Math.min(this.cx, this.cy) * 0.85;
        const clusterCx = this.cx + maxR * 0.72;
        const clusterCy = this.cy + maxR * 0.65;
        const clusterR = Math.min(54, maxR * 0.23);
        placedRects.push({
          x1: clusterCx - 85, y1: clusterCy - clusterR - 36,
          x2: clusterCx + 85, y2: clusterCy - clusterR - 16,
        });
      }

      // Glossary term cited in Governance Context rendered as a small green floating text label near the relevant edge
      if (this.agentMode === 'kc' && this.activeGlossaryTerm && this.activeGlossaryTerm.display) {
        let edgeNode = null;
        if (this.activeGlossaryTerm.targetTable) {
          edgeNode = selectedTargets.find(n => n.name.toLowerCase() === this.activeGlossaryTerm.targetTable);
        }
        if (!edgeNode) {
          edgeNode = selectedTargets.find(n => n.layer === 'gold') || selectedTargets[0];
        }
        if (edgeNode) {
          ctx.font = '600 10px system-ui';
          const gText = this.activeGlossaryTerm.display;
          const gTw = ctx.measureText(gText).width;
          const gLw = gTw + 10;
          const gLh = 16;
          const dx = edgeNode.x - this.cx;
          const dy = edgeNode.y - this.cy;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const nx = -dy / dist;
          const ny = dx / dist;
          const midX = this.cx + dx * 0.52 + nx * 14;
          const midY = this.cy + dy * 0.52 + ny * 14;
          const gx1 = midX - gLw / 2;
          const gy1 = midY - gLh / 2;

          ctx.fillStyle = 'rgba(13,17,23,0.92)';
          ctx.fillRect(gx1, gy1, gLw, gLh);
          ctx.strokeStyle = 'rgba(63,185,80,0.88)';
          ctx.lineWidth = 1;
          ctx.strokeRect(gx1, gy1, gLw, gLh);
          ctx.fillStyle = '#3fb950';
          ctx.fillText(gText, gx1 + 5, gy1 + 11);

          placedRects.push({ x1: gx1 - 3, y1: gy1 - 3, x2: gx1 + gLw + 3, y2: gy1 + gLh + 3 });
          this._termLabelPositions.push({
            term: this.activeGlossaryTerm.raw,
            display: gText,
            x: midX,
            y: midY,
            hw: gLw / 2,
            hh: gLh / 2,
          });
          const gLabelObj = {
            name: 'glossary:' + gText,
            text: gText,
            type: 'glossary',
            edgeTo: edgeNode.name,
            x: gx1,
            y: gy1,
          };
          this.renderedGlossaryLabels.push(gLabelObj);
          this.renderedLabels.push(gLabelObj);
        }
      }

      ctx.font = '10px system-ui';
      const topLeft = this._screenToWorld(8, 8);
      const bottomRight = this._screenToWorld(this.w - 8, this.h - 8);

      for (const n of selectedTargets) {
        const label = n.name.replace(/^(gold|silver|bronze|ref)_/, '');
        const tw = ctx.measureText(label).width;
        const bw = tw + 6;
        const bh = 14;
        const r = n.radius + 4;

        const candidates = [
          { x: n.x + r, y: n.y - 7 },
          { x: n.x - r - bw, y: n.y - 7 },
          { x: n.x - bw / 2, y: n.y - r - bh - 2 },
          { x: n.x - bw / 2, y: n.y + r + 2 },
          { x: n.x + r, y: n.y - 22 },
          { x: n.x + r, y: n.y + 8 },
          { x: n.x - r - bw, y: n.y - 22 },
          { x: n.x - r - bw, y: n.y + 8 },
        ];

        let chosen = null;
        for (const c of candidates) {
          const rect = { x1: c.x, y1: c.y, x2: c.x + bw, y2: c.y + bh };
          if (rect.x1 < topLeft.x || rect.x2 > bottomRight.x || rect.y1 < topLeft.y || rect.y2 > bottomRight.y) {
            continue;
          }
          const overlaps = placedRects.some(p =>
            !(rect.x2 + 2 < p.x1 || rect.x1 - 2 > p.x2 || rect.y2 + 2 < p.y1 || rect.y1 - 2 > p.y2)
          );
          if (!overlaps) {
            chosen = rect;
            break;
          }
        }

        if (!chosen) {
          chosen = { x1: candidates[0].x, y1: candidates[0].y, x2: candidates[0].x + bw, y2: candidates[0].y + bh };
        }
        placedRects.push(chosen);
        this.renderedLabels.push({ name: n.name, text: label, x: chosen.x1, y: chosen.y1 });

        const isSF = n.layer === 'snowflake';
        ctx.fillStyle = `rgba(22,27,34,${n.glow * 0.95})`;
        ctx.fillRect(chosen.x1, chosen.y1, bw, bh);
        ctx.strokeStyle = isSF
          ? `rgba(0,229,255,${n.glow * 0.85})`
          : `rgba(63,185,80,${n.glow * 0.85})`;
        ctx.lineWidth = 1;
        ctx.strokeRect(chosen.x1, chosen.y1, bw, bh);
        ctx.fillStyle = isSF
          ? `rgba(0,229,255,${n.glow * 0.95})`
          : `rgba(230,237,243,${n.glow * 0.95})`;
        ctx.fillText(label, chosen.x1 + 3, chosen.y1 + 11);
      }
    }

    // Agent center orb + glow: Basic=blue (#58a6ff), Scaled=red (#f85149), KC=green (#3fb950)
    const agentColor = COLORS[this.agentMode] || '#58a6ff';
    const pulse = this.animationState ? Math.sin(this.animationTime * 0.004) * 0.15 : 0;
    const size = 12;

    // Prominent radial center glow per agent
    const glowR = 54 + pulse * 30;
    const grad = ctx.createRadialGradient(this.cx, this.cy, 0, this.cx, this.cy, glowR);
    grad.addColorStop(0, agentColor + '66');
    grad.addColorStop(0.45, agentColor + '28');
    grad.addColorStop(1, agentColor + '00');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, glowR, 0, Math.PI * 2);
    ctx.fill();

    // Outer pulsing ring
    const ringR = 24 + pulse * 30;
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, ringR, 0, Math.PI * 2);
    ctx.strokeStyle = agentColor + '88';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Second ring (dashed)
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, ringR + 10, 0, Math.PI * 2);
    ctx.setLineDash([3, 5]);
    ctx.strokeStyle = agentColor + '44';
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);

    // Diamond shape (rotated square)
    ctx.save();
    ctx.translate(this.cx, this.cy);
    ctx.rotate(Math.PI / 4);
    ctx.beginPath();
    ctx.rect(-size / 2, -size / 2, size, size);
    ctx.fillStyle = agentColor;
    ctx.fill();
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();

    // Inner dot
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#FFFFFF';
    ctx.fill();

    ctx.restore();

    // Tooltip (drawn outside zoom transform so it stays crisp at screen scale)
    if (this.hoveredNode) {
      const n = this.hoveredNode;
      const sx = this.cx + (n.x - this.cx + this.panX) * this.zoom;
      const sy = this.cy + (n.y - this.cy + this.panY) * this.zoom;
      ctx.font = '12px system-ui';
      const tw = ctx.measureText(n.name).width;
      ctx.fillStyle = 'rgba(22,27,34,0.96)';
      const rx = sx + 8, ry = sy - 18, rw = tw + 12, rh = 22, rr = 4;
      ctx.beginPath();
      ctx.moveTo(rx + rr, ry);
      ctx.lineTo(rx + rw - rr, ry);
      ctx.quadraticCurveTo(rx + rw, ry, rx + rw, ry + rr);
      ctx.lineTo(rx + rw, ry + rh - rr);
      ctx.quadraticCurveTo(rx + rw, ry + rh, rx + rw - rr, ry + rh);
      ctx.lineTo(rx + rr, ry + rh);
      ctx.quadraticCurveTo(rx, ry + rh, rx, ry + rh - rr);
      ctx.lineTo(rx, ry + rr);
      ctx.quadraticCurveTo(rx, ry, rx + rr, ry);
      ctx.fill();
      ctx.strokeStyle = n.layer === 'snowflake' ? '#00e5ff' : '#30363d';
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.fillStyle = '#e6edf3';
      ctx.fillText(n.name, sx + 14, sy - 3);
    }
  }

  // === Event-driven animation methods (for live WebSocket mode) ===

  triggerSearchPulse() {
    this._searchPulseRadius = 0;
    this._searchPulseAlpha = 1;
    this._pulseStartTime = this.animationTime;
  }

  illuminateTable(tableName, isPrimary = false) {
    const node = this._findNode(tableName);
    if (!node) return;
    if (node.layer === 'snowflake' && (this.agentMode !== 'kc' || this.activeCategory !== 'multicloud')) return;
    node.glow = 1;
    node.alpha = 1;
    if (isPrimary) node.queriedBySql = true;
    if (!node.touchedOrder) node.touchedOrder = ++this._touchSeq;
    if (!this.activeNodes.includes(node)) this.activeNodes.push(node);
  }

  illuminateTables(tableNames, isPrimary = false) {
    for (const name of tableNames || []) {
      this.illuminateTable(name, isPrimary);
    }
  }

  _computeActiveRegion() {
    const pts = [];
    const targets = this._getCappedEdgeTargets();
    const regionNodes = targets.length > 0 ? targets : this.activeNodes;
    for (const n of regionNodes) pts.push({ x: n.x, y: n.y });
    pts.push({ x: this.cx, y: this.cy });
    if (pts.length <= 1) return null;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const p of pts) {
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.x > maxX) maxX = p.x;
      if (p.y > maxY) maxY = p.y;
    }
    const pad = 80;
    return {
      cx: (minX + maxX) / 2, cy: (minY + maxY) / 2,
      w: maxX - minX + pad * 2, h: maxY - minY + pad * 2,
    };
  }

  _triggerZoomToActive() {
    this.targetZoom = 1;
    this.targetPanX = 0;
    this.targetPanY = 0;
    this._zoomedIn = false;
  }

  _resetZoom() {
    this.targetZoom = 1; this.targetPanX = 0; this.targetPanY = 0;
    this._zoomedIn = false;
  }

  zoomToActive() {
    this._triggerZoomToActive();
  }

  setNodeLabel(tableName, label) {
    const node = this._findNode(tableName);
    if (node) { node.label = label; node.labelAlpha = 1; }
  }

  clearAnimation() {
    if (this.renderedEdges && this.renderedEdges.length > 0) {
      this.fadingEdges = this.renderedEdges.map(e => ({ ...e, alpha: 0.55 }));
    }
    this.renderedEdges = [];
    this.renderedLabels = [];
    this.renderedGlossaryLabels = [];
    this.activeGlossaryTerm = null;
    this._termLabelPositions = [];
    this.activeNodes = [];
    this._touchSeq = 0;
    this.metadataLines = [];
    this.animationState = null;
    this._searchPulseRadius = 0;
    this._searchPulseAlpha = 0;
    this._resetZoom();
    for (const n of this.nodes) {
      n.glow = 0;
      n.labelAlpha = 0;
      n.label = '';
      n.queriedBySql = false;
      n.touchedOrder = 0;
    }
    this._positionNodes();
  }
}

window.PointCloud = PointCloud;
