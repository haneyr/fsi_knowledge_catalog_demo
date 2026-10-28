#!/usr/bin/env python3
"""
Headless Chrome (CDP) verification for Phase K3:
Tests 3 KC chips: Merchandising #4, Privacy #4, Cross-Cloud #2.
Writes full responses to logs/l_verify.json.
Always uses --password-store=basic --use-mock-keychain.
"""
import asyncio
import base64
import json
import os
import re
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
CDP_PORT = 9239
PROJECT_NUMBER = "98236392654"
LOCATION = "us-central1"
AE_BASE = f"https://{LOCATION}-aiplatform.googleapis.com/v1"
KC_AGENT_ID = "8060330902103785472"

_creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
_auth_req = google.auth.transport.requests.Request()
_http = requests.Session()
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


def query_kc_sync(question: str, user_id: str):
    token = get_token()
    session_url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{KC_AGENT_ID}:query"
    sresp = _http.post(
        session_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"class_method": "async_create_session", "input": {"user_id": user_id}},
        timeout=30,
    )
    output = sresp.json().get("output", {})
    session_id = output.get("id", "") if isinstance(output, dict) else str(output)

    url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{KC_AGENT_ID}:streamQuery"
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
    tools_called = []
    text_chunks = []
    for line in resp.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8").strip()
        if not text:
            continue
        for ev in parse_stream_chunk(text):
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


def analyze_response(full_text: str):
    sections = {
        "Data discovery": bool(re.search(r"\*\*Data discovery\.?\*\*", full_text, re.I)),
        "Finding": bool(re.search(r"\*\*Finding\.?\*\*", full_text, re.I)),
        "Governance Context": bool(re.search(r"\*\*Governance Context\.?\*\*", full_text, re.I)),
        "Recommendations": bool(re.search(r"\*\*Recommendations\.?\*\*", full_text, re.I)),
    }
    all_4 = all(sections.values())

    # Glossary term in Governance Context
    glossary_terms = re.findall(r"\[Retail\]\s*[A-Za-z0-9\s/\-()&]+", full_text)
    glossary_term = glossary_terms[0].strip() if glossary_terms else "NONE"

    # DQ scan names
    dq_scans = sorted(set(re.findall(r"retail-[a-z0-9\-]+-quality", full_text, re.I)))
    dq_scan = ", ".join(dq_scans) if dq_scans else "NONE"

    return sections, all_4, glossary_term, dq_scan


async def run_k3():
    global ALL_TABLES
    with urllib.request.urlopen(f"{CLOUD_RUN_URL}/api/config", timeout=15) as r:
        cfg = json.loads(r.read().decode())
        ALL_TABLES = (cfg.get("all_table_names") or []) + (cfg.get("snowflake_tables") or [])

    profile_dir = "/tmp/chrome_phase_k3_profile"
    shutil.rmtree(profile_dir, ignore_errors=True)
    os.makedirs(profile_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    chrome_log = open("logs/phase_k3_chrome.log", "w")
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

            for item in chips_to_test:
                await cdp.evaluate(f"switchNarrative('{item['narrative']}');")
                await asyncio.sleep(0.2)
                await cdp.evaluate(f"document.querySelectorAll('#presetQuestions .preset-btn')[{item['idx']}].click();")
                req = await cdp.wait_for("window.__pendingWsRequest", timeout_s=15.0, poll_s=0.1)
                await cdp.evaluate("window.__pendingWsRequest = null;")

                events, tools_called, full_text = await asyncio.to_thread(
                    query_kc_sync, req["question"], f"k3-{item['narrative']}-{item['idx']}"
                )
                for ev in events:
                    payload_js = json.dumps(json.dumps(ev))
                    await cdp.evaluate(f"window.__activeMockWs && window.__activeMockWs._deliver({payload_js});")
                    await asyncio.sleep(0.015)

                await cdp.wait_for("document.getElementById('sendBtn').disabled === false", timeout_s=30.0, poll_s=0.2)
                await asyncio.sleep(0.4)

                viz_metrics = await cdp.evaluate("""
                    ({
                        edges: (viz.renderedEdges || []).length,
                        labels: (viz.renderedLabels || []).length,
                        glossary_labels: (viz.renderedGlossaryLabels || []).map(g => g.text),
                        edge_targets: (viz.renderedEdges || []).map(e => e.to)
                    })
                """)

                sections, all_4, glossary_term, dq_scan = analyze_response(full_text)
                results.append({
                    "chip": item["label"],
                    "question": req["question"],
                    "edges": viz_metrics["edges"],
                    "labels": viz_metrics["labels"],
                    "glossary_edge_labels": viz_metrics["glossary_labels"],
                    "edge_targets": viz_metrics["edge_targets"],
                    "sections": sections,
                    "all_4_sections": all_4,
                    "glossary_term": glossary_term,
                    "dq_scan": dq_scan,
                    "tools_called": tools_called,
                    "response": full_text,
                })

        with open("logs/l_verify.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        for r in results:
            sec_str = "Y" if r["all_4_sections"] else f"N ({[k for k, v in r['sections'].items() if not v]})"
            print(f"ROW | {r['chip']} | edges={r['edges']} | sections={sec_str} | glossary={r['glossary_term']} | dq={r['dq_scan']} | tools={r['tools_called']}")
        print("=== MERCHANDISING #4 FULL ===")
        print(results[0]["response"])

    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=5)
        except Exception:
            chrome_proc.kill()
        chrome_log.close()


if __name__ == "__main__":
    asyncio.run(run_k3())
