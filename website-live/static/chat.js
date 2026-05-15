// Chat Panel Logic — WebSocket live mode with static fallback

if (typeof marked !== 'undefined') {
  marked.use({ breaks: true, gfm: true });
}

const _DATASET_MAP = {
  'gold_': 'fsi_gold', 'silver_': 'fsi_silver', 'bronze_': 'fsi_bronze',
  'ref_': 'fsi_reference', 'vw_': 'fsi_dashboards',
  'staging_': 'fsi_supplementary', 'snapshot_': 'fsi_supplementary', 'audit_': 'fsi_supplementary',
};
const _GLOSSARY_TERMS = {
  'FICO Score': 'fico-score', 'AUM': 'aum-abbr', 'SAR': 'sar-abbr',
  'CET1 Ratio': 'cet1-ratio', 'Customer ID': 'customer-id',
  'Delinquency': 'delinquency', 'KYC': 'kyc-abbr', 'VaR': 'var-abbr',
  'CUSIP': 'cusip', 'NIM': 'nim-abbr', 'Risk Rating': 'risk-rating', 'Branch': 'branch',
  'AML': 'aml', 'Basel III': 'basel-iii', 'Wire Transfer': 'wire-transfer',
  'BSA': 'bsa', 'Sharpe Ratio': 'sharpe-ratio',
  'Stress Testing': 'stress-testing', 'Liquidity Risk': 'liquidity-risk',
  'Charge-Off': 'charge-off', 'ACH Transfer': 'ach',
};
const _GLOSSARY_ID = 'meridian-national-bank-glossary-us';
const _TABLE_RE = /\b((?:gold|silver|bronze|ref|vw|staging|snapshot|audit)_[a-z0-9_]+)\b/g;
let _projectNumber = '';

function _renderMarkdown(text) {
  const wrapper = document.createElement('div');
  wrapper.className = 'markdown-content';
  if (typeof marked !== 'undefined') {
    wrapper.innerHTML = marked.parse(text);
  } else {
    wrapper.textContent = text;
    wrapper.style.whiteSpace = 'pre-wrap';
  }
  return wrapper;
}

function _linkifyEntities(container, agentMode, projectId) {
  if (!projectId) return;

  // Pass 1: linkify table names in text nodes
  let walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let textNodes = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode);

  for (const node of textNodes) {
    if (node.parentElement?.closest('a')) continue;
    const text = node.textContent;
    let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    let modified = false;

    html = html.replace(_TABLE_RE, (match) => {
      let ds = '';
      for (const [prefix, dataset] of Object.entries(_DATASET_MAP)) {
        if (match.startsWith(prefix)) { ds = dataset; break; }
      }
      if (!ds) return match;
      const url = agentMode === 'kc'
        ? `https://console.cloud.google.com/dataplex/dp-entries/projects/${projectId}/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com%2Fprojects%2F${projectId}%2Fdatasets%2F${ds}%2Ftables%2F${match}?project=${projectId}`
        : `https://console.cloud.google.com/bigquery?referrer=search&amp;project=${projectId}&amp;ws=!1m5!1m4!4m3!1s${projectId}!2s${ds}!3s${match}`;
      modified = true;
      return `<a href="${url}" target="_blank" rel="noopener" class="entity-link table-link">${match}</a>`;
    });

    if (modified) {
      const span = document.createElement('span');
      span.innerHTML = html;
      node.parentNode.replaceChild(span, node);
    }
  }

  // Pass 2: linkify glossary terms (KC only) — runs after table links are in the DOM
  // so we only process text nodes that aren't inside <a> tags
  if (agentMode === 'kc') {
    walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);

    for (const node of textNodes) {
      if (node.parentElement?.closest('a, .glossary-chip')) continue;
      const text = node.textContent;
      let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      let modified = false;

      for (const [term, slug] of Object.entries(_GLOSSARY_TERMS)) {
        if (!html.includes(term)) continue;
        const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        html = html.replace(new RegExp(escaped, 'g'), (m) => {
          modified = true;
          return `<span class="glossary-chip" data-term="${m}">${m}</span>`;
        });
      }

      if (modified) {
        const span = document.createElement('span');
        span.innerHTML = html;
        node.parentNode.replaceChild(span, node);
      }
    }
  }
}

class ChatPanel {
  constructor(viz) {
    this.viz = viz;
    this.messagesEl = document.getElementById('chatMessages');
    this.inputEl = document.getElementById('chatInput');
    this.sendBtn = document.getElementById('sendBtn');
    this.typingEl = document.getElementById('typingIndicator');
    this.agentMode = 'basic';
    this.projectId = '';
    this.staticData = null;
    this.liveMode = false;
    this.ws = null;
    this._currentAgentMsg = null;

    this.sendBtn.addEventListener('click', () => this.send());
    this.inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.send(); }
    });

    this._agentContainers = {};
    this._initAgentContainer('basic');
    this._initAgentContainer('scaled');
    this._initAgentContainer('kc');

    this.popupEl = document.getElementById('tablePopup');
    this.viz.onNodeClick = (name, sx, sy) => this._showTablePopup(name, sx, sy);
    this.viz.onTermClick = (term, sx, sy) => this._showTermPopup(term, sx, sy);
    this.messagesEl.addEventListener('click', (e) => {
      const chip = e.target.closest('.glossary-chip');
      if (chip) {
        const term = chip.dataset.term;
        const rect = chip.getBoundingClientRect();
        this._showTermPopup(term, rect.left + rect.width / 2, rect.top);
        e.stopPropagation();
      }
    });
    document.addEventListener('click', (e) => {
      if (this.popupEl && !this.popupEl.contains(e.target) && !this.viz.canvas.contains(e.target) && !e.target.closest('.glossary-chip')) {
        this.popupEl.classList.add('hidden');
      }
    });

    this._loadStaticData();
    this._checkLiveMode();
  }

  async _loadStaticData() {
    try {
      const resp = await fetch('/static-responses.json');
      this.staticData = await resp.json();
    } catch (e) { /* no static data */ }
  }

  async _checkLiveMode() {
    try {
      const resp = await fetch('/api/config');
      const config = await resp.json();
      this.liveMode = config.live_mode;
      this.projectId = config.project_id || '';
      _projectNumber = config.project_number || '';
      const badge = document.getElementById('modeBadge');
      badge.className = 'mode-badge ' + (this.liveMode ? 'live' : 'static');
      badge.textContent = this.liveMode ? 'LIVE' : 'STATIC';
    } catch (e) {
      document.getElementById('modeBadge').className = 'mode-badge static';
      document.getElementById('modeBadge').textContent = 'STATIC';
    }
  }

  _initAgentContainer(mode) {
    const container = document.createElement('div');
    container.className = 'agent-messages-container';
    container.style.display = 'none';
    container.dataset.agent = mode;
    this.messagesEl.appendChild(container);
    this._agentContainers[mode] = container;

    const desc = {
      basic: 'Basic Agent — 5 gold tables, no Knowledge Catalog.',
      scaled: 'Scaled Agent — 150+ tables, no Knowledge Catalog.',
      kc: 'KC Agent — 150+ tables WITH Knowledge Catalog Context API.',
    };
    const sysMsg = document.createElement('div');
    sysMsg.className = 'message agent';
    sysMsg.style.cssText = 'color:var(--text-dim);font-style:italic;font-size:12px';
    sysMsg.textContent = desc[mode];
    container.appendChild(sysMsg);
  }

  setAgent(mode) {
    this.agentMode = mode;
    this._currentAgentMsg = null;
    document.body.className = `agent-${mode}`;

    for (const [key, container] of Object.entries(this._agentContainers)) {
      container.style.display = key === mode ? 'flex' : 'none';
    }
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  _activeContainer() {
    return this._agentContainers[this.agentMode] || this.messagesEl;
  }

  _addMessage(text, isUser) {
    const div = document.createElement('div');
    div.className = `message ${isUser ? 'user' : 'agent'}`;
    div.textContent = text;
    this._activeContainer().appendChild(div);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    return div;
  }

  _addAgentMessage(response, toolCalls) {
    const div = document.createElement('div');
    div.className = 'message agent';

    if (toolCalls && toolCalls.length > 0) {
      const chips = document.createElement('div');
      chips.className = 'tool-chips';
      for (const tc of toolCalls) {
        const chip = document.createElement('span');
        chip.className = 'tool-chip';
        if (tc.includes('search')) chip.className += ' search';
        else if (tc.includes('context') || tc.includes('lookup')) chip.className += ' lookup';
        else chip.className += ' sql';
        chip.textContent = tc;
        chips.appendChild(chip);
      }
      div.appendChild(chips);
    }

    const rendered = _renderMarkdown(response);
    _linkifyEntities(rendered, this.agentMode, this.projectId);
    div.appendChild(rendered);
    this._activeContainer().appendChild(div);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  _getOrCreateAgentMsg() {
    if (!this._currentAgentMsg) {
      this._currentAgentMsg = document.createElement('div');
      this._currentAgentMsg.className = 'message agent working';
      this._currentAgentMsg._chips = document.createElement('div');
      this._currentAgentMsg._chips.className = 'tool-chips';
      this._currentAgentMsg.appendChild(this._currentAgentMsg._chips);
      this._currentAgentMsg._status = document.createElement('div');
      this._currentAgentMsg._status.className = 'agent-working-status';
      this._currentAgentMsg._status.innerHTML = '<span class="working-dot"></span> Agent is working...';
      this._currentAgentMsg.appendChild(this._currentAgentMsg._status);
      this._currentAgentMsg._rawText = '';
      this._currentAgentMsg._rendered = document.createElement('div');
      this._currentAgentMsg.appendChild(this._currentAgentMsg._rendered);
      this._activeContainer().appendChild(this._currentAgentMsg);
    }
    return this._currentAgentMsg;
  }

  _addToolChip(name) {
    const msg = this._getOrCreateAgentMsg();
    const chip = document.createElement('span');
    chip.className = 'tool-chip';
    if (name.includes('search')) chip.className += ' search';
    else if (name.includes('context') || name.includes('lookup')) chip.className += ' lookup';
    else chip.className += ' sql';
    chip.textContent = name;
    msg._chips.appendChild(chip);
  }

  _appendText(text) {
    const msg = this._getOrCreateAgentMsg();
    msg._rawText += text;
    const rendered = _renderMarkdown(msg._rawText);
    _linkifyEntities(rendered, this.agentMode, this.projectId);
    msg._rendered.replaceChildren(rendered);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  _showTyping() { this.typingEl.classList.add('visible'); }
  _hideTyping() { this.typingEl.classList.remove('visible'); }

  _updateWorkingStatus(toolName) {
    const msg = this._getOrCreateAgentMsg();
    if (!msg._status) return;
    const labels = {
      search_entries: 'Searching Knowledge Catalog...',
      get_context: 'Reading metadata & schema...',
      run_sql: 'Querying BigQuery...',
    };
    msg._status.innerHTML = `<span class="working-dot"></span> ${labels[toolName] || 'Agent is working...'}`;
  }

  _hideWorkingStatus() {
    if (this._currentAgentMsg) {
      this._currentAgentMsg.classList.remove('working');
      if (this._currentAgentMsg._status) {
        this._currentAgentMsg._status.remove();
        this._currentAgentMsg._status = null;
      }
    }
  }

  _finalizeResponse() {
    if (!this._currentAgentMsg || this.agentMode !== 'kc') return;
    const rendered = this._currentAgentMsg._rendered;
    if (!rendered) return;

    const content = rendered.querySelector('.markdown-content');
    if (!content) return;

    const children = [...content.children];
    let discoveryStart = -1;
    let discoveryEnd = -1;

    for (let i = 0; i < children.length; i++) {
      const el = children[i];
      const text = el.textContent.toLowerCase().trim();
      if (el.tagName === 'H2' || (el.tagName === 'P' && /^\*?\*?data discovery\*?\*?/i.test(el.textContent.trim()))) {
        if (/data discovery/i.test(text)) {
          discoveryStart = i;
        } else if (discoveryStart >= 0 && discoveryEnd < 0) {
          discoveryEnd = i;
        }
      }
      if (discoveryStart >= 0 && discoveryEnd < 0 && el.tagName === 'H2' && !/data discovery/i.test(text)) {
        discoveryEnd = i;
      }
    }

    if (discoveryStart < 0) return;
    if (discoveryEnd < 0) discoveryEnd = children.length;
    if (discoveryEnd - discoveryStart < 2) return;

    const details = document.createElement('details');
    details.className = 'discovery-section';
    const summary = document.createElement('summary');
    summary.textContent = 'Data Discovery — how the agent found the right data';
    details.appendChild(summary);

    const wrapper = document.createElement('div');
    wrapper.className = 'discovery-content';
    for (let i = discoveryStart; i < discoveryEnd; i++) {
      wrapper.appendChild(children[i]);
    }
    details.appendChild(wrapper);

    if (children[discoveryEnd]) {
      content.insertBefore(details, children[discoveryEnd]);
    } else {
      content.appendChild(details);
    }
  }

  async send() {
    const text = this.inputEl.value.trim();
    if (!text) return;
    this.inputEl.value = '';
    this.sendBtn.disabled = true;
    this._addMessage(text, true);
    this._currentAgentMsg = null;
    this._showTyping();
    this.viz.clearAnimation();

    if (this.liveMode) {
      await this._sendWebSocket(text);
    } else {
      await this._sendStatic(text);
    }
    this.sendBtn.disabled = false;
  }

  async _sendWebSocket(question) {
    return new Promise((resolve) => {
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${proto}//${location.host}/api/ws`);
      let resolved = false;
      const done = () => { if (!resolved) { resolved = true; resolve(); } };

      ws.onopen = () => {
        ws.send(JSON.stringify({ agent: this.agentMode, question }));
      };

      ws.onmessage = (e) => {
        const event = JSON.parse(e.data);
        this._handleLiveEvent(event);
        if (event.type === 'done' || event.type === 'error') {
          this._hideTyping();
          ws.close();
          done();
        }
      };

      ws.onerror = () => {
        this._hideTyping();
        this._sendStatic(question).then(done);
      };

      ws.onclose = () => done();
      setTimeout(() => { ws.close(); done(); }, 120000);
    });
  }

  _handleLiveEvent(event) {
    switch (event.type) {
      case 'status':
        break;

      case 'tool_call':
        this._addToolChip(event.name);
        this._updateWorkingStatus(event.name);
        if (event.name === 'search_entries') {
          this.viz.triggerSearchPulse();
        }
        if (event.tables && event.tables.length > 0) {
          this.viz.illuminateTables(event.tables);
        }
        break;

      case 'tool_response':
        if (event.tables && event.tables.length > 0) {
          this.viz.illuminateTables(event.tables);
        }
        if (event.glossary_terms && event.glossary_terms.length > 0) {
          this.viz.showGlossaryArcsForTerms(event.glossary_terms);
        }
        break;

      case 'text_chunk':
        this._hideTyping();
        this._hideWorkingStatus();
        this._appendText(event.text);
        break;

      case 'done':
        this._hideTyping();
        this._hideWorkingStatus();
        this._finalizeResponse();
        if (event.all_tables) this.viz.illuminateTables(event.all_tables);
        if (event.all_glossary) this.viz.showGlossaryArcsForTerms(event.all_glossary);
        this.viz.zoomToActive();
        break;

      case 'error':
        this._hideTyping();
        this._appendText(`Error: ${event.message}`);
        break;
    }
  }

  async _sendStatic(question) {
    const scenario = this._findStaticScenario(question);
    if (!scenario) {
      await this._delay(1000);
      this._hideTyping();
      this._addAgentMessage("No pre-recorded response for that question. Try a preset.", []);
      return;
    }

    const agentData = scenario[this.agentMode];
    const animDelay = this.agentMode === 'kc' ? 5000 : this.agentMode === 'scaled' ? 3000 : 2000;

    this.viz.triggerQuery(
      agentData.tables_used || [],
      agentData.tool_calls || [],
      agentData.metadata_cited || [],
      agentData.lineage_path || [],
      agentData.glossary_terms_cited || []
    );

    await this._delay(animDelay);
    this._hideTyping();
    this._addAgentMessage(agentData.response, agentData.tool_calls || []);
  }

  _findStaticScenario(question) {
    if (!this.staticData?.scenarios) return null;
    const q = question.toLowerCase();
    let best = null, bestScore = 0;
    for (const s of this.staticData.scenarios) {
      const score = s.question.toLowerCase().split(/\s+/).filter(w => w.length > 3 && q.includes(w)).length;
      if (score > bestScore) { bestScore = score; best = s; }
    }
    return bestScore >= 2 ? best : null;
  }

  sendPreset(question) {
    this.inputEl.value = question;
    this.send();
  }

  _delay(ms) { return new Promise(r => setTimeout(r, ms)); }

  async _showTablePopup(tableName, screenX, screenY) {
    const popup = this.popupEl;
    if (!popup) return;

    popup.querySelector('.popup-name').textContent = tableName;
    popup.querySelector('.popup-desc').textContent = 'Loading...';
    popup.querySelector('.popup-cols').innerHTML = '';
    popup.querySelector('.popup-link').href = '#';

    const tier = tableName.match(/^(gold|silver|bronze|ref|staging|snapshot|audit|vw)_/)?.[1] || 'other';
    const tierEl = popup.querySelector('.popup-tier');
    tierEl.textContent = tier;
    tierEl.className = 'popup-tier ' + tier;

    popup.classList.remove('hidden');
    popup.classList.add('loading');

    const popupW = 280, popupH = 200;
    let left = screenX + 16;
    let top = screenY - popupH / 2;
    if (left + popupW > window.innerWidth - 10) left = screenX - popupW - 16;
    if (top < 10) top = 10;
    if (top + popupH > window.innerHeight - 10) top = window.innerHeight - popupH - 10;
    popup.style.left = left + 'px';
    popup.style.top = top + 'px';

    try {
      const resp = await fetch(`/api/table-info?table=${encodeURIComponent(tableName)}`);
      const info = await resp.json();

      popup.classList.remove('loading');
      popup.querySelector('.popup-desc').textContent = info.description || 'No description available.';
      const linkEl = popup.querySelector('.popup-link');
      if (this.agentMode === 'kc') {
        linkEl.href = info.catalog_url || '#';
        linkEl.innerHTML = 'Open in Knowledge Catalog &rarr;';
      } else {
        linkEl.href = info.bq_url || '#';
        linkEl.innerHTML = 'Open in BigQuery &rarr;';
      }

      const colsDiv = popup.querySelector('.popup-cols');
      if (info.columns && info.columns.length > 0) {
        colsDiv.innerHTML = `<div class="popup-cols-label">${info.column_count} columns</div><div class="popup-col-pills"></div>`;
        const pills = colsDiv.querySelector('.popup-col-pills');
        for (const col of info.columns) {
          const pill = document.createElement('span');
          pill.className = 'popup-col-pill';
          pill.textContent = col;
          pills.appendChild(pill);
        }
      }
    } catch (e) {
      popup.classList.remove('loading');
      popup.querySelector('.popup-desc').textContent = 'Could not load metadata.';
    }
  }

  async _showTermPopup(termName, screenX, screenY) {
    const popup = this.popupEl;
    if (!popup) return;

    popup.querySelector('.popup-name').textContent = termName;
    popup.querySelector('.popup-desc').textContent = 'Loading...';
    popup.querySelector('.popup-cols').innerHTML = '';
    popup.querySelector('.popup-link').href = '#';

    const tierEl = popup.querySelector('.popup-tier');
    tierEl.textContent = 'glossary';
    tierEl.className = 'popup-tier glossary';

    popup.classList.remove('hidden');
    popup.classList.add('loading');

    const popupW = 280, popupH = 140;
    let left = screenX + 16;
    let top = screenY - popupH / 2;
    if (left + popupW > window.innerWidth - 10) left = screenX - popupW - 16;
    if (top < 10) top = 10;
    if (top + popupH > window.innerHeight - 10) top = window.innerHeight - popupH - 10;
    popup.style.left = left + 'px';
    popup.style.top = top + 'px';

    try {
      const resp = await fetch(`/api/term-info?term=${encodeURIComponent(termName)}`);
      const info = await resp.json();

      popup.classList.remove('loading');
      popup.querySelector('.popup-desc').textContent = info.description || 'No description available.';
      popup.querySelector('.popup-link').href = info.catalog_url || '#';

      if (info.category) {
        const colsDiv = popup.querySelector('.popup-cols');
        colsDiv.innerHTML = `<div class="popup-cols-label">Category</div><div class="popup-col-pills"><span class="popup-col-pill">${info.category}</span></div>`;
      }
    } catch (e) {
      popup.classList.remove('loading');
      popup.querySelector('.popup-desc').textContent = 'Could not load term info.';
    }
  }
}

window.ChatPanel = ChatPanel;
