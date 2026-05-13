// Chat Panel Logic — handles static fallback and live WebSocket modes

class ChatPanel {
  constructor(viz) {
    this.viz = viz;
    this.messagesEl = document.getElementById('chatMessages');
    this.inputEl = document.getElementById('chatInput');
    this.sendBtn = document.getElementById('sendBtn');
    this.typingEl = document.getElementById('typingIndicator');
    this.agentMode = 'basic';
    this.staticData = null;
    this.ws = null;
    this.liveMode = false;

    this.sendBtn.addEventListener('click', () => this.send());
    this.inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.send(); }
    });

    this._loadStaticData();
    this._tryLiveMode();
  }

  async _loadStaticData() {
    try {
      const resp = await fetch('/static-responses.json');
      this.staticData = await resp.json();
    } catch (e) {
      console.log('No static responses available');
    }
  }

  async _tryLiveMode() {
    try {
      const resp = await fetch('/api/config');
      const config = await resp.json();
      this.liveMode = config.live_mode;
      document.getElementById('modeBadge').className = 'mode-badge ' + (this.liveMode ? 'live' : 'static');
      document.getElementById('modeBadge').textContent = this.liveMode ? 'LIVE' : 'STATIC';
    } catch (e) {
      document.getElementById('modeBadge').className = 'mode-badge static';
      document.getElementById('modeBadge').textContent = 'STATIC';
    }
  }

  setAgent(mode) {
    this.agentMode = mode;
    this.messagesEl.innerHTML = '';
    document.body.className = `agent-${mode}`;

    const descriptions = {
      basic: 'Basic Agent — 5 gold tables, no Knowledge Catalog. Works for simple queries.',
      scaled: 'Scaled Agent — 150+ tables, no Knowledge Catalog. Struggles with ambiguity.',
      kc: 'KC Agent — 150+ tables WITH Knowledge Catalog. Discovers the right data through metadata.',
    };
    this._addSystemMessage(descriptions[mode]);
  }

  _addSystemMessage(text) {
    const div = document.createElement('div');
    div.className = 'message agent';
    div.style.color = 'var(--text-dim)';
    div.style.fontStyle = 'italic';
    div.style.fontSize = '12px';
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

  _addAgentMessage(response, toolCalls, metadataCited) {
    const div = document.createElement('div');
    div.className = 'message agent';

    if (toolCalls && toolCalls.length > 0) {
      const chips = document.createElement('div');
      chips.className = 'tool-chips';
      for (const tc of toolCalls) {
        const chip = document.createElement('span');
        chip.className = 'tool-chip';
        if (tc.includes('search')) chip.className += ' search';
        else if (tc.includes('lookup')) chip.className += ' lookup';
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

  _showTyping() { this.typingEl.classList.add('visible'); }
  _hideTyping() { this.typingEl.classList.remove('visible'); }

  async send() {
    const text = this.inputEl.value.trim();
    if (!text) return;

    this.inputEl.value = '';
    this.sendBtn.disabled = true;
    this._addMessage(text, true);
    this._showTyping();

    if (this.liveMode) {
      await this._sendLive(text);
    } else {
      await this._sendStatic(text);
    }

    this.sendBtn.disabled = false;
  }

  async _sendStatic(question) {
    const scenario = this._findStaticScenario(question);
    if (!scenario) {
      await this._delay(1500);
      this._hideTyping();
      const agentData = { response: "I don't have a pre-recorded response for that question. Try one of the preset questions below.", tables_used: [], tool_calls: [] };
      this._addAgentMessage(agentData.response, [], []);
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
    this._addAgentMessage(
      agentData.response,
      agentData.tool_calls || [],
      agentData.metadata_cited || []
    );
  }

  async _sendLive(question) {
    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent: this.agentMode, question }),
      });
      const data = await resp.json();
      this._hideTyping();

      if (data.static || data.error) {
        return this._sendStatic(question);
      }

      const tablesUsed = this._extractTables(data.response);
      const toolCalls = this._extractToolCalls(data.response);
      this.viz.triggerQuery(tablesUsed, toolCalls, []);
      this._addAgentMessage(data.response, toolCalls, []);
    } catch (e) {
      this._hideTyping();
      return this._sendStatic(question);
    }
  }

  _findStaticScenario(question) {
    if (!this.staticData || !this.staticData.scenarios) return null;
    const q = question.toLowerCase();
    let best = null, bestScore = 0;
    for (const s of this.staticData.scenarios) {
      const words = s.question.toLowerCase().split(/\s+/);
      const score = words.filter(w => w.length > 3 && q.includes(w)).length;
      if (score > bestScore) { bestScore = score; best = s; }
    }
    return bestScore >= 2 ? best : null;
  }

  _extractTables(text) {
    const all = [...TABLES.bronze, ...TABLES.silver, ...TABLES.gold, ...TABLES.ref];
    return all.filter(t => text.toLowerCase().includes(t));
  }

  _extractToolCalls(text) {
    const tools = [];
    if (text.includes('search_entries') || text.includes('Search')) tools.push('search_entries');
    if (text.includes('lookup_entry') || text.includes('Lookup')) tools.push('lookup_entry');
    if (text.includes('lookup_context')) tools.push('lookup_context');
    if (text.includes('run_sql') || text.includes('SQL') || text.includes('SELECT')) tools.push('run_sql');
    return tools.length ? tools : ['run_sql'];
  }

  sendPreset(question) {
    this.inputEl.value = question;
    this.send();
  }

  _delay(ms) { return new Promise(r => setTimeout(r, ms)); }
}

window.ChatPanel = ChatPanel;
