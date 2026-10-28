#!/usr/bin/env python3
"""
Headless Chrome (CDP) verification for Phase O2:
Tests 4 KC chips: Merchandising #4, Customer #4, Privacy #4, Cross-Cloud #2.
Verifies bidirectional NEXUS gate:
  - Merchandising #4, Customer #4, Privacy #4: query_snowflake=N, NEXUS mentioned=N
  - Cross-Cloud #2: query_snowflake=Y, NEXUS mentioned=Y, nexus_* edge drawn
  - Scope instruction is appended server-side and NEVER appears in user chat bubble.
Writes full results to logs/o2_verify.json.
Always uses --password-store=basic --use-mock-keychain.
"""
import asyncio
import base64
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import requests
import websockets

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE"] = "false"

import ast

_app_py_path = os.path.join(os.path.dirname(__file__), "..", "website-live", "app.py")
with open(_app_py_path, "r", encoding="utf-8") as _f:
    _app_src = _f.read()
_app_tree = ast.parse(_app_src, filename=_app_py_path)
_wanted_names = {
    "_INTERNAL_SCOPE_INSTRUCTION",
    "_CROSS_CLOUD_SCOPE_INSTRUCTION",
    "_CROSS_CLOUD_EXCLUDED_INTERNAL",
    "_is_cross_cloud_category",
    "_build_scoped_question",
}
_selected_nodes = [
    node for node in _app_tree.body
    if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in _wanted_names for t in node.targets))
    or (isinstance(node, ast.FunctionDef) and node.name in _wanted_names)
]
_scope_ns = {}
exec(compile(ast.Module(body=_selected_nodes, type_ignores=[]), _app_py_path, "exec"), _scope_ns)
_build_scoped_question = _scope_ns["_build_scoped_question"]
_is_cross_cloud_category = _scope_ns["_is_cross_cloud_category"]
_CROSS_CLOUD_EXCLUDED_INTERNAL = _scope_ns["_CROSS_CLOUD_EXCLUDED_INTERNAL"]

CLOUD_RUN_URL = "https://retail-kc-demo-ui-live-98236392654.us-central1.run.app"
CDP_PORT = 9241
PROJECT_NUMBER = "98236392654"
LOCATION = "us-central1"
AE_BASE = f"https://{LOCATION}-aiplatform.googleapis.com/v1"
KC_AGENT_ID = "8060330902103785472"

ALL_BQ_TABLES = []
SNOWFLAKE_TABLES = []


def get_token() -> str:
    env = {
        **os.environ,
        "GOOGLE_API_USE_CLIENT_CERTIFICATE": "false",
        "CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE": "false",
    }
    return subprocess.check_output(["gcloud", "auth", "print-access-token"], env=env).decode().strip()


def extract_tables(text: str, is_cross_cloud: bool = False):
    lower = text.lower()
    if is_cross_cloud:
        candidates = [
            t for t in (ALL_BQ_TABLES + SNOWFLAKE_TABLES)
            if t not in _CROSS_CLOUD_EXCLUDED_INTERNAL
        ]
    else:
        candidates = ALL_BQ_TABLES
    return [t for t in candidates if t.lower() in lower]


def parse_stream_chunk(raw_text: str, is_cross_cloud: bool = False):
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
                "tables": extract_tables(str(args), is_cross_cloud=is_cross_cloud),
            })
        elif "function_response" in part:
            fr = part["function_response"]
            resp_data = fr.get("response", {})
            result_text = resp_data.get("result", str(resp_data))
            events.append({
                "type": "tool_response",
                "name": fr.get("name", ""),
                "tables": extract_tables(str(result_text), is_cross_cloud=is_cross_cloud),
                "glossary_terms": [],
            })
        elif "text" in part:
            events.append({
                "type": "text_chunk",
                "text": part["text"],
            })
    return events


def query_kc_sync(question: str, category: str, user_id: str):
    token = get_token()
    is_cross_cloud = _is_cross_cloud_category(category)
    scoped_question = _build_scoped_question("kc", question, category)
    session_url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{KC_AGENT_ID}:query"
    sresp = requests.post(
        session_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"class_method": "async_create_session", "input": {"user_id": f"{user_id}-{category}"}},
        timeout=30,
    )
    output = sresp.json().get("output", {})
    session_id = output.get("id", "") if isinstance(output, dict) else str(output)

    url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{KC_AGENT_ID}:streamQuery"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "class_method": "async_stream_query",
            "input": {"message": scoped_question, "user_id": f"{user_id}-{category}", "session_id": session_id},
        },
        stream=True,
        timeout=300,
    )
    out_events = [{"type": "status", "message": "Connecting to agent..."}]
    all_tables = []
    tools_called = []
    text_chunks = []
    for line in resp.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8").strip()
        if not text:
            continue
        for ev in parse_stream_chunk(text, is_cross_cloud=is_cross_cloud):
            if ev["type"] == "tool_call":
                tools_called.append(ev.get("name", ""))
                all_tables.extend(ev.get("tables", []))
            elif ev["type"] == "tool_response":
                all_tables.extend(ev.get("tables", []))
            elif ev["type"] == "text_chunk":
                text_chunks.append(ev.get("text", ""))
            out_events.append(ev)
    out_events.append({
        "type": "done",
        "latency": 1.0,
        "all_tables": list(set(all_tables)),
        "all_glossary": [],
    })
    return out_events, tools_called, "".join(text_chunks)


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
            msg = json.loads(raw)
            if msg.get("id") == target_id:
                if "error" in msg:
                    raise RuntimeError(f"CDP error: {msg['error']}")
                return msg.get("result", {})

    async def evaluate(self, expression: str):
        res = await self.send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        if "exceptionDetails" in res:
            raise RuntimeError(f"JS exception: {res['exceptionDetails']}")
        return res.get("result", {}).get("value")

    async def wait_for(self, js_predicate: str, timeout_s: float = 180.0, poll_s: float = 0.2):
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


def has_nexus_mention(text: str) -> tuple[bool, list[str]]:
    low = text.lower()
    terms = [
        "nexus",
        "snowflake",
        "vendor data license",
        "third-party licensed",
        "external market data",
        "syndicated_intel",
        "nwr-nexus",
    ]
    matched = [t for t in terms if t in low]
    return (len(matched) > 0), matched


async def run_o2():
    global ALL_BQ_TABLES, SNOWFLAKE_TABLES
    with urllib.request.urlopen(f"{CLOUD_RUN_URL}/api/config", timeout=15) as r:
        cfg = json.loads(r.read().decode())
        ALL_BQ_TABLES = cfg.get("all_table_names") or []
        SNOWFLAKE_TABLES = cfg.get("snowflake_tables") or []

    profile_dir = "/tmp/chrome_phase_o2_profile"
    shutil.rmtree(profile_dir, ignore_errors=True)
    os.makedirs(profile_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    chrome_log = open("logs/phase_o2_chrome.log", "w")
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

    chips_to_test = [
        {"label": "Merchandising #4", "narrative": "merchandising", "idx": 3},
        {"label": "Customer #4", "narrative": "customer", "idx": 3},
        {"label": "Privacy #4", "narrative": "privacy", "idx": 3},
        {"label": "Cross-Cloud #2", "narrative": "multicloud", "idx": 1},
    ]

    results = []

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

            await cdp.send("Page.navigate", {"url": f"{CLOUD_RUN_URL}/?cb={int(time.time())}"})
            await cdp.wait_for("typeof viz !== 'undefined' && viz.nodes.length >= 128", timeout_s=30.0)
            await cdp.evaluate("switchAgent('kc');")
            await asyncio.sleep(0.3)

            # First capture the 4 chip requests via real DOM clicks and verify user bubble cleanliness
            captured_requests = []
            for item in chips_to_test:
                await cdp.evaluate(f"switchNarrative('{item['narrative']}');")
                await asyncio.sleep(0.15)
                await cdp.evaluate("document.getElementById('sendBtn').disabled = false;")
                await cdp.evaluate(f"document.querySelectorAll('#presetQuestions .preset-btn')[{item['idx']}].click();")
                req = await cdp.wait_for("window.__pendingWsRequest", timeout_s=15.0, poll_s=0.1)
                await cdp.evaluate("window.__pendingWsRequest = null;")
                user_bubble_text = await cdp.evaluate(
                    "Array.from(document.querySelectorAll('.agent-messages-container[data-agent=\"kc\"] .message.user')).slice(-1)[0]?.textContent || ''"
                )
                captured_requests.append((item, req, user_bubble_text))

            # Query the 4 KC requests in parallel for speed
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                futures = [
                    loop.run_in_executor(
                        pool,
                        query_kc_sync,
                        req["question"],
                        req.get("category", item["narrative"]),
                        f"o2-{item['narrative']}-{item['idx']}",
                    )
                    for item, req, _ in captured_requests
                ]
                query_outputs = await asyncio.gather(*futures)

            # Replay each chip in sequence in the browser to measure exact rendered graph edges
            for (item, req, _), (events, tools_called, full_text) in zip(captured_requests, query_outputs):
                await cdp.evaluate(f"switchNarrative('{item['narrative']}');")
                await asyncio.sleep(0.15)
                await cdp.evaluate("document.getElementById('sendBtn').disabled = false;")
                await cdp.evaluate(f"document.querySelectorAll('#presetQuestions .preset-btn')[{item['idx']}].click();")
                await cdp.wait_for("window.__pendingWsRequest", timeout_s=15.0, poll_s=0.05)
                await cdp.evaluate("window.__pendingWsRequest = null;")

                user_bubble = await cdp.evaluate(
                    "Array.from(document.querySelectorAll('.agent-messages-container[data-agent=\"kc\"] .message.user')).slice(-1)[0]?.textContent || ''"
                )

                for ev in events:
                    payload_js = json.dumps(json.dumps(ev))
                    await cdp.evaluate(f"window.__activeMockWs && window.__activeMockWs._deliver({payload_js});")
                    await asyncio.sleep(0.01)

                await cdp.wait_for("document.getElementById('sendBtn').disabled === false", timeout_s=30.0, poll_s=0.1)
                await asyncio.sleep(0.35)

                viz_metrics = await cdp.evaluate("""
                    ({
                        edges: (viz.renderedEdges || []).length,
                        labels: (viz.renderedLabels || []).length,
                        glossary_labels: (viz.renderedGlossaryLabels || []).map(g => g.text),
                        edge_targets: (viz.renderedEdges || []).map(e => e.to)
                    })
                """)

                q_sf = "Y" if "query_snowflake" in tools_called else "N"
                nexus_bool, matched_terms = has_nexus_mention(full_text)
                nexus_str = "Y" if nexus_bool else "N"
                bubble_clean = "MANDATORY SCOPE GATE" not in user_bubble and user_bubble == req["question"]

                results.append({
                    "chip": item["label"],
                    "category_sent": req.get("category"),
                    "user_bubble_clean": bubble_clean,
                    "query_snowflake": q_sf,
                    "nexus_mentioned": nexus_str,
                    "matched_nexus_terms": matched_terms,
                    "edges": viz_metrics["edges"],
                    "edge_targets": viz_metrics["edge_targets"],
                    "tools_called": tools_called,
                    "response": full_text,
                })

        with open("logs/o2_verify.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print("chip | query_snowflake Y/N | NEXUS mentioned Y/N | edges")
        for r in results:
            print(
                f"{r['chip']} | {r['query_snowflake']} | {r['nexus_mentioned']} | {r['edges']} ({r['edge_targets']}) | cat={r['category_sent']} | bubble_clean={r['user_bubble_clean']}"
            )

    finally:
        chrome_proc.terminate()
        chrome_log.close()


if __name__ == "__main__":
    asyncio.run(run_o2())
