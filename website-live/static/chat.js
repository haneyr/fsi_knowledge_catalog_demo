// Chat Panel Logic — WebSocket live mode with static fallback

class ChatPanel {
  constructor(viz) {
    this.viz = viz;
    this.messagesEl = document.getElementById('chatMessages');
    this.inputEl = document.getElementById('chatInput');
    this.sendBtn = document.getElementById('sendBtn');
    this.typingEl = document.getElementById('typingIndicator');
    this.agentMode = 'basic';
    this.staticData = null;
    this.liveMode = false;
    this.ws = null;
    this._currentAgentMsg = null;

    this.sendBtn.addEventListener('click', () => this.send());
    this.inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.send(); }
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
      const badge = document.getElementById('modeBadge');
      badge.className = 'mode-badge ' + (this.liveMode ? 'live' : 'static');
      badge.textContent = this.liveMode ? 'LIVE' : 'STATIC';
    } catch (e) {
      document.getElementById('modeBadge').className = 'mode-badge static';
      document.getElementById('modeBadge').textContent = 'STATIC';
    }
  }

  setAgent(mode) {
    this.agentMode = mode;
    this.messagesEl.innerHTML = '';
    this._currentAgentMsg = null;
    document.body.className = `agent-${mode}`;

    const desc = {
      basic: 'Basic Agent — 5 gold tables, no Knowledge Catalog.',
      scaled: 'Scaled Agent — 150+ tables, no Knowledge Catalog.',
      kc: 'KC Agent — 150+ tables WITH Knowledge Catalog Context API.',
    };
    this._addSystemMessage(desc[mode]);
  }

  _addSystemMessage(text) {
    const div = document.createElement('div');
    div.className = 'message agent';
    div.style.cssText = 'color:var(--text-dim);font-style:italic;font-size:12px';
    div.textContent = text;
    this.messagesEl.appendChild(div);
  }

  _addMessage(text, isUser) {
    const div = document.createElement('div');
    div.className = `message ${isUser ? 'user' : 'agent'}`;
    div.textContent = text;
    this.messagesEl.appendChild(div);
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

    const textEl = document.createElement('div');
    textEl.textContent = response;
    div.appendChild(textEl);
    this.messagesEl.appendChild(div);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  _getOrCreateAgentMsg() {
    if (!this._currentAgentMsg) {
      this._currentAgentMsg = document.createElement('div');
      this._currentAgentMsg.className = 'message agent';
      this._currentAgentMsg._chips = document.createElement('div');
      this._currentAgentMsg._chips.className = 'tool-chips';
      this._currentAgentMsg.appendChild(this._currentAgentMsg._chips);
      this._currentAgentMsg._text = document.createElement('div');
      this._currentAgentMsg.appendChild(this._currentAgentMsg._text);
      this.messagesEl.appendChild(this._currentAgentMsg);
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
    msg._text.textContent += text;
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  _showTyping() { this.typingEl.classList.add('visible'); }
  _hideTyping() { this.typingEl.classList.remove('visible'); }

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
        if (event.name === 'search_entries') {
          this.viz.triggerSearchPulse();
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
        this._appendText(event.text);
        break;

      case 'done':
        this._hideTyping();
        if (event.all_tables) this.viz.illuminateTables(event.all_tables);
        if (event.all_glossary) this.viz.showGlossaryArcsForTerms(event.all_glossary);
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
}

window.ChatPanel = ChatPanel;
