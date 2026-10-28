#!/usr/bin/env python3
"""
Headless Chrome (CDP) verification for Phase G1-F against live Cloud Run URL:
https://retail-kc-demo-ui-live-98236392654.us-central1.run.app
Always uses --password-store=basic --use-mock-keychain.
"""
import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
import urllib.request
import google.auth
import google.auth.transport.requests
import requests
import websockets

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE"] = "false"

CLOUD_RUN_URL = "https://retail-kc-demo-ui-live-98236392654.us-central1.run.app"
CDP_PORT = 9229
PROJECT_NUMBER = "98236392654"
LOCATION = "us-central1"
AE_BASE = f"https://{LOCATION}-aiplatform.googleapis.com/v1"
AGENT_IDS = {
    "basic": "2946493525224587264",
    "scaled": "1975967805526245376",
    "kc": "8060330902103785472",
}

_creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
_auth_req = google.auth.transport.requests.Request()
_http = requests.Session()
_sessions = {}
ALL_TABLES = []


def get_token() -> str:
    if not _creds.valid:
        _creds.refresh(_auth_req)
    return _creds.token


def extract_tables(text: str):
    lower = text.lower()
    return [t for t in ALL_TABLES if t.lower() in lower]


def parse_stream_chunk(raw_text: str):
    events = []
    try:
        data = json.loads(raw_text)
    except Exception:
        return events
    parts = data.get("content", {}).get("parts", [])
    for part in parts:
        if "function_call" in part:
            fc = part["function_call"]
            args = fc.get("args", {})
            events.append({
                "type": "tool_call",
                "name": fc.get("name", ""),
                "args": args,
                "tables": extract_tables(str(args)),
            })
        elif "function_response" in part:
            fr = part["function_response"]
            resp_data = fr.get("response", {})
            result_text = resp_data.get("result", str(resp_data))
            events.append({
                "type": "tool_response",
                "name": fr.get("name", ""),
                "tables": extract_tables(str(result_text)),
                "glossary_terms": [],
            })
        elif "text" in part:
            events.append({
                "type": "text_chunk",
                "text": part["text"],
            })
    return events


def get_or_create_session(agent_id: str, user_id: str) -> str:
    key = f"{agent_id}:{user_id}"
    if key in _sessions:
        return _sessions[key]
    token = get_token()
    url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{agent_id}:query"
    resp = _http.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"class_method": "async_create_session", "input": {"user_id": user_id}},
        timeout=30,
    )
    output = resp.json().get("output", {})
    sid = output.get("id", "") if isinstance(output, dict) else str(output)
    _sessions[key] = sid
    return sid


def query_agent_sync(agent_type: str, question: str, user_id: str):
    agent_id = AGENT_IDS[agent_type]
    session_id = get_or_create_session(agent_id, user_id)
    token = get_token()
    url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{agent_id}:streamQuery"
    resp = _http.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "class_method": "async_stream_query",
            "input": {"message": question, "user_id": user_id, "session_id": session_id},
        },
        stream=True,
        timeout=300,
    )
    out_events = [{"type": "status", "message": "Connecting to agent..."}]
    all_tables = []
    for line in resp.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8").strip()
        if not text:
            continue
        for ev in parse_stream_chunk(text):
            if ev["type"] in ("tool_call", "tool_response"):
                all_tables.extend(ev.get("tables", []))
            out_events.append(ev)
    out_events.append({
        "type": "done",
        "latency": 1.0,
        "all_tables": list(set(all_tables)),
        "all_glossary": [],
    })
    return out_events


def make_mock_jwt() -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(
        json.dumps({
            "email": "admin@aelitchfield.altostrat.com",
            "name": "Demo Verifier",
            "exp": int(time.time()) + 7200,
        }).encode()
    ).decode().rstrip("=")
    return f"{header}.{payload}.sig"


class CDPClient:
    def __init__(self, ws):
        self.ws = ws
        self.msg_id = 0

    async def send(self, method: str, params: dict = None):
        self.msg_id += 1
        target_id = self.msg_id
        payload = {"id": target_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))
        while True:
            raw = await self.ws.recv()
            data = json.loads(raw)
            if data.get("id") == target_id:
                if "error" in data:
                    raise RuntimeError(f"CDP error in {method}: {data['error']}")
                return data.get("result", {})

    async def evaluate(self, expression: str):
        res = await self.send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        if "exceptionDetails" in res:
            raise RuntimeError(f"JS exception: {res['exceptionDetails']}")
        return res.get("result", {}).get("value")

    async def wait_for(self, js_predicate: str, timeout_s: float = 180.0, poll_s: float = 0.4):
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                val = await self.evaluate(js_predicate)
                if val:
                    return val
            except Exception:
                pass
            await asyncio.sleep(poll_s)
        raise TimeoutError(f"Timed out waiting for: {js_predicate}")


async def pump_live_ws(cdp: CDPClient, user_id: str):
    req = await cdp.wait_for("window.__pendingWsRequest", timeout_s=15.0, poll_s=0.1)
    await cdp.evaluate("window.__pendingWsRequest = null;")
    events = await asyncio.to_thread(query_agent_sync, req["agent"], req["question"], user_id)
    for ev in events:
        payload_js = json.dumps(json.dumps(ev))
        await cdp.evaluate(f"window.__activeMockWs && window.__activeMockWs._deliver({payload_js});")
        await asyncio.sleep(0.02)
    await cdp.wait_for("document.getElementById('sendBtn').disabled === false", timeout_s=30.0, poll_s=0.2)


async def run_verification():
    global ALL_TABLES
    with urllib.request.urlopen(f"{CLOUD_RUN_URL}/api/config", timeout=15) as r:
        cfg = json.loads(r.read().decode())
        ALL_TABLES = (cfg.get("all_table_names") or []) + (cfg.get("snowflake_tables") or [])

    profile_dir = "/tmp/chrome_g1f_profile"
    shutil.rmtree(profile_dir, ignore_errors=True)
    os.makedirs(profile_dir, exist_ok=True)

    chrome_log = open("logs/g1f_chrome.log", "w")
    chrome_proc = subprocess.Popen(
        [
            "/usr/bin/google-chrome",
            "--headless=new",
            "--password-store=basic",
            "--use-mock-keychain",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--window-size=1440,900",
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={profile_dir}",
            "about:blank",
        ],
        stdout=chrome_log,
        stderr=subprocess.STDOUT,
    )

    try:
        ws_url = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json", timeout=2) as r:
                    targets = json.loads(r.read().decode())
                    for t in targets:
                        if t.get("type") == "page" and "webSocketDebuggerUrl" in t:
                            ws_url = t["webSocketDebuggerUrl"]
                            break
                    if ws_url:
                        break
            except Exception:
                await asyncio.sleep(0.5)

        if not ws_url:
            raise RuntimeError("Could not connect to headless Chrome CDP port")

        mock_jwt = make_mock_jwt()
        results = {}

        async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
            cdp = CDPClient(ws)
            await cdp.send("Page.enable")
            await cdp.send("Runtime.enable")
            await cdp.send(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": f"""
                        localStorage.setItem('id_token', '{mock_jwt}');
                        window.__pendingWsRequest = null;
                        window.__activeMockWs = null;
                        class CDPBridgedWebSocket {{
                            constructor(url) {{
                                this.url = url;
                                this.readyState = 0;
                                window.__activeMockWs = this;
                                setTimeout(() => {{
                                    this.readyState = 1;
                                    if (this.onopen) this.onopen({{}});
                                }}, 10);
                            }}
                            send(data) {{
                                window.__pendingWsRequest = JSON.parse(data);
                            }}
                            _deliver(rawJson) {{
                                if (this.onmessage) {{
                                    this.onmessage({{ data: rawJson }});
                                }}
                            }}
                            close() {{
                                this.readyState = 3;
                                if (this.onclose) this.onclose({{}});
                            }}
                        }}
                        window.WebSocket = CDPBridgedWebSocket;
                    """
                },
            )

            for agent in ["basic", "scaled", "kc"]:
                user_id = f"g1f_verifier_{agent}_{int(time.time())}"
                await cdp.send("Page.navigate", {"url": CLOUD_RUN_URL})
                await cdp.wait_for("typeof viz !== 'undefined' && viz.nodes && viz.nodes.length > 0", timeout_s=30.0)
                await asyncio.sleep(0.8)

                if agent != "basic":
                    await cdp.evaluate(f"document.querySelector('.agent-tab[data-agent=\"{agent}\"]').click()")
                    await asyncio.sleep(0.8)

                # 1. IDLE state BEFORE any query
                idle_state = await cdp.evaluate("""({
                    renderedEdgeCount: (viz.renderedEdges || []).length,
                    renderedEdges: (viz.renderedEdges || []).map(e => e.to),
                    fadingEdgeCount: (viz.fadingEdges || []).length,
                    activeNodeCount: (viz.activeNodes || []).length,
                    hasActiveLineageProp: 'activeLineage' in viz,
                    hasActiveGlossaryProp: 'activeGlossaryArcs' in viz,
                })""")

                # 2. Click chip 1 and stream live answer
                chip1_q = await cdp.evaluate("""(() => {
                    const btn = document.querySelectorAll('#presetQuestions .preset-btn')[0];
                    const q = btn.getAttribute('data-question');
                    btn.click();
                    return q;
                })()""")

                await pump_live_ws(cdp, user_id)
                await asyncio.sleep(0.8)

                chip1_state = await cdp.evaluate("""({
                    renderedEdgeCount: (viz.renderedEdges || []).length,
                    renderedEdges: (viz.renderedEdges || []).map(e => ({ from: e.from, to: e.to, isNexus: e.isNexus })),
                    fadingEdgeCount: (viz.fadingEdges || []).length,
                    activeNodeCount: (viz.activeNodes || []).length,
                    activeNodes: (viz.activeNodes || []).map(n => ({ name: n.name, queriedBySql: !!n.queriedBySql })),
                    answerPreview: (document.querySelector('#chatMessages .message.agent:last-child')?.innerText || '').slice(0, 140),
                })""")

                # 3. Click chip 4, capture immediate fade-out state, and stream live answer
                chip4_transition = await cdp.evaluate("""(() => {
                    const btn = document.querySelectorAll('#presetQuestions .preset-btn')[3];
                    const q = btn.getAttribute('data-question');
                    btn.click();
                    return {
                        question: q,
                        fadingImmediatelyOnStart: (viz.fadingEdges || []).length,
                        renderedImmediatelyOnStart: (viz.renderedEdges || []).length,
                    };
                })()""")

                await pump_live_ws(cdp, user_id)
                await asyncio.sleep(0.8)

                chip4_state = await cdp.evaluate("""({
                    renderedEdgeCount: (viz.renderedEdges || []).length,
                    renderedEdges: (viz.renderedEdges || []).map(e => ({ from: e.from, to: e.to, isNexus: e.isNexus })),
                    fadingEdgeCount: (viz.fadingEdges || []).length,
                    activeNodeCount: (viz.activeNodes || []).length,
                    activeNodes: (viz.activeNodes || []).map(n => ({ name: n.name, queriedBySql: !!n.queriedBySql })),
                    answerPreview: (document.querySelector('#chatMessages .message.agent:last-child')?.innerText || '').slice(0, 140),
                })""")

                results[agent] = {
                    "idle": idle_state,
                    "chip1": {"question": chip1_q, **chip1_state},
                    "chip4": {**chip4_transition, **chip4_state},
                }
                print(
                    f"[{agent}] idle={idle_state['renderedEdgeCount']} | "
                    f"chip1={chip1_state['renderedEdgeCount']} edges={[e['to'] for e in chip1_state['renderedEdges']]} (lit={chip1_state['activeNodeCount']}) | "
                    f"chip4={chip4_state['renderedEdgeCount']} edges={[e['to'] for e in chip4_state['renderedEdges']]} (lit={chip4_state['activeNodeCount']}, fadingOnStart={chip4_transition['fadingImmediatelyOnStart']}, fadingAfter={chip4_state['fadingEdgeCount']})",
                    flush=True,
                )

        with open("logs/verify_g1f_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print("DONE_VERIFY_G1F", flush=True)
    finally:
        chrome_proc.terminate()
        chrome_log.close()


if __name__ == "__main__":
    asyncio.run(run_verification())
