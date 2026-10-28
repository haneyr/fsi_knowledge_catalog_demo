#!/usr/bin/env python3
"""
Phase P verification & latency instrumentation script.
Runs Merchandising #4 and Cross-Cloud #2 once each in headless Chrome
(--password-store=basic --use-mock-keychain) against the live Cloud Run UI,
streaming events incrementally into the browser as each line arrives from
Vertex AI Agent Engine (chunk_size=1).

Captures:
- P2: Elapsed ms and phase_ms for session_create, each tool_call, each tool_response,
      first_token, last_token, and total_ms.
- P3: Incremental tool-chip render timestamps, status line progression, and
      progressive graph edge counts per phase.
Writes logs/p_verify.json.
"""
import ast
import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
import urllib.request
import requests
import websockets

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE"] = "false"

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
CDP_PORT = 9244
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

    async def wait_for(self, js_predicate: str, timeout_s: float = 60.0, poll_s: float = 0.05):
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


async def stream_kc_to_browser(cdp: CDPClient, question: str, category: str, user_id: str):
    token = get_token()
    is_cross_cloud = _is_cross_cloud_category(category)
    scoped_question = _build_scoped_question("kc", question, category)

    t0 = time.perf_counter()
    await cdp.evaluate(f"window.__activeFakeWs._emit({json.dumps({'type': 'status', 'message': 'Connecting to agent...'})})")

    t_sess_start = time.perf_counter()
    session_url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{KC_AGENT_ID}:query"
    sresp = await asyncio.to_thread(
        requests.post,
        session_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"class_method": "async_create_session", "input": {"user_id": f"{user_id}-{category}"}},
        timeout=30,
    )
    session_create_ms = round((time.perf_counter() - t_sess_start) * 1000)
    elapsed_ms = round((time.perf_counter() - t0) * 1000)
    output = sresp.json().get("output", {})
    session_id = output.get("id", "") if isinstance(output, dict) else str(output)

    phase_timings = [{"phase": "session_create", "phase_ms": session_create_ms, "elapsed_ms": elapsed_ms}]
    last_phase_t = time.perf_counter()
    pending_tool_t = {}
    first_token_ms = None
    last_token_ms = None
    all_tables = []

    url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{KC_AGENT_ID}:streamQuery"
    resp = await asyncio.to_thread(
        requests.post,
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "class_method": "async_stream_query",
            "input": {"message": scoped_question, "user_id": f"{user_id}-{category}", "session_id": session_id},
        },
        stream=True,
        timeout=300,
    )

    def _iter_stream_lines(r):
        buf = b""
        for chunk in r.raw.stream(65536, decode_content=True):
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if line:
                    yield line.decode("utf-8", errors="replace")
        if buf.strip():
            yield buf.strip().decode("utf-8", errors="replace")

    line_iter = _iter_stream_lines(resp)
    while True:
        text = await asyncio.to_thread(next, line_iter, None)
        if text is None:
            break

        events = parse_stream_chunk(text, is_cross_cloud=is_cross_cloud)
        for event in events:
            now = time.perf_counter()
            elapsed_ms = round((now - t0) * 1000)
            event["elapsed_ms"] = elapsed_ms
            etype = event["type"]

            if etype == "tool_call":
                tname = event.get("name", "")
                step_ms = round((now - last_phase_t) * 1000)
                pending_tool_t[tname] = now
                last_phase_t = now
                phase_timings.append({
                    "phase": f"tool_call:{tname}",
                    "phase_ms": step_ms,
                    "elapsed_ms": elapsed_ms,
                })
                all_tables.extend(event.get("tables", []))

            elif etype == "tool_response":
                tname = event.get("name", "")
                t_call = pending_tool_t.pop(tname, last_phase_t)
                exec_ms = round((now - t_call) * 1000)
                last_phase_t = now
                event["tool_exec_ms"] = exec_ms
                phase_timings.append({
                    "phase": f"tool_response:{tname}",
                    "phase_ms": exec_ms,
                    "elapsed_ms": elapsed_ms,
                })
                all_tables.extend(event.get("tables", []))

            elif etype == "text_chunk":
                if first_token_ms is None:
                    first_token_ms = elapsed_ms
                    gen_ms = round((now - last_phase_t) * 1000)
                    phase_timings.append({
                        "phase": "first_token",
                        "phase_ms": gen_ms,
                        "elapsed_ms": first_token_ms,
                    })
                last_token_ms = elapsed_ms
                last_phase_t = now

            await cdp.evaluate(f"window.__activeFakeWs._emit({json.dumps(event)})")

    if last_token_ms is not None:
        stream_ms = last_token_ms - (first_token_ms or last_token_ms)
        phase_timings.append({
            "phase": "last_token",
            "phase_ms": stream_ms,
            "elapsed_ms": last_token_ms,
        })

    # Allow 400ms for any composing debounce on Cross-Cloud if needed before done
    await asyncio.sleep(0.4)
    total_ms = round((time.perf_counter() - t0) * 1000)
    done_ev = {
        "type": "done",
        "latency": round(total_ms / 1000.0, 1),
        "total_ms": total_ms,
        "phase_timings": phase_timings,
        "all_tables": list(set(all_tables)),
        "all_glossary": [],
    }
    await cdp.evaluate(f"window.__activeFakeWs._emit({json.dumps(done_ev)})")
    return phase_timings, total_ms


async def run_p():
    global ALL_BQ_TABLES, SNOWFLAKE_TABLES
    with urllib.request.urlopen(f"{CLOUD_RUN_URL}/api/config", timeout=15) as r:
        cfg = json.loads(r.read().decode())
    for tier, tlist in cfg.get("tables", {}).items():
        if tier == "snowflake":
            SNOWFLAKE_TABLES.extend(tlist)
        else:
            ALL_BQ_TABLES.extend(tlist)
    SNOWFLAKE_TABLES.extend(cfg.get("snowflake_tables", []))
    ALL_BQ_TABLES = list(dict.fromkeys(ALL_BQ_TABLES))
    SNOWFLAKE_TABLES = list(dict.fromkeys(SNOWFLAKE_TABLES))

    user_data_dir = f"/tmp/chrome_p_{os.getpid()}"
    os.makedirs(user_data_dir, exist_ok=True)
    proc = subprocess.Popen(
        [
            "google-chrome",
            "--headless=new",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--password-store=basic",
            "--use-mock-keychain",
            "--window-size=1600,1000",
            f"--user-data-dir={user_data_dir}",
            f"--remote-debugging-port={CDP_PORT}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        ws_url = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/list", timeout=1) as r:
                    pages = json.loads(r.read().decode())
                    for p in pages:
                        if p.get("type") == "page" and "webSocketDebuggerUrl" in p:
                            ws_url = p["webSocketDebuggerUrl"]
                            break
                if ws_url:
                    break
            except Exception:
                pass
            time.sleep(0.1)

        if not ws_url:
            raise RuntimeError("Could not connect to headless Chrome CDP")

        mock_jwt = make_mock_jwt()
        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            cdp = CDPClient(ws)
            await cdp.send("Page.enable")
            await cdp.send("Runtime.enable")
            await cdp.send(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": f"""
                        localStorage.setItem('id_token', '{mock_jwt}');
                        window.__pendingWsPayload = null;
                        window.__activeFakeWs = null;
                        class CDPBridgedWebSocket {{
                            constructor(url) {{
                                this.url = url;
                                this.readyState = 0;
                                window.__activeFakeWs = this;
                                setTimeout(() => {{
                                    this.readyState = 1;
                                    if (this.onopen) this.onopen({{}});
                                }}, 5);
                            }}
                            send(data) {{
                                window.__pendingWsPayload = JSON.parse(data);
                            }}
                            _emit(evObj) {{
                                if (this.onmessage) {{
                                    this.onmessage({{ data: JSON.stringify(evObj) }});
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
            await cdp.evaluate("switchAgent('kc')")
            await asyncio.sleep(0.3)

            targets = [
                ("Merchandising #4", "merchandising", 3),
                ("Cross-Cloud #2", "multicloud", 1),
            ]
            results = []

            for label, cat_key, chip_idx in targets:
                await cdp.evaluate(
                    f"""(() => {{
                        const container = chat._agentContainers['kc'];
                        if (container) container.innerHTML = '';
                        chat._currentAgentMsg = null;
                        viz.clearAnimation();
                        switchNarrative('{cat_key}');
                        document.getElementById('sendBtn').disabled = false;
                        window.__pendingWsPayload = null;
                        const btns = document.querySelectorAll('#presetQuestions .preset-btn');
                        btns[{chip_idx}].click();
                    }})()"""
                )
                payload = await cdp.wait_for("window.__pendingWsPayload", timeout_s=15.0)
                question = payload.get("question", "")
                sent_category = payload.get("category", "")

                phase_timings, total_ms = await stream_kc_to_browser(
                    cdp, question, sent_category, f"p-{cat_key}-{chip_idx}"
                )
                await asyncio.sleep(0.2)

                ui_telemetry = await cdp.evaluate(
                    """(() => {
                        const msgs = document.querySelectorAll('.agent-messages-container[data-agent="kc"] .message.agent');
                        const lastMsg = msgs[msgs.length - 1];
                        return {
                            status_history: lastMsg ? (lastMsg._statusHistory || []) : [],
                            chip_timeline: lastMsg ? (lastMsg._chipTimeline || []) : [],
                            edge_timeline: lastMsg ? (lastMsg._edgeTimeline || []) : [],
                            final_edges: viz._getCappedEdgeTargets().map(n => n.name),
                        };
                    })()"""
                )

                row = {
                    "chip": label,
                    "category": sent_category,
                    "total_ms": total_ms,
                    "phase_timings": phase_timings,
                    "status_history": ui_telemetry["status_history"],
                    "chip_timeline": ui_telemetry["chip_timeline"],
                    "edge_timeline": ui_telemetry["edge_timeline"],
                    "final_edges": ui_telemetry["final_edges"],
                }
                results.append(row)

            os.makedirs("logs", exist_ok=True)
            with open("logs/p_verify.json", "w") as f:
                json.dump(results, f, indent=2)

            for r in results:
                print(f"=== {r['chip']} (total={r['total_ms']} ms) ===")
                print("phase | phase_ms | elapsed_ms")
                for pt in r["phase_timings"]:
                    print(f"{pt['phase']} | {pt['phase_ms']} | {pt['elapsed_ms']}")
                print("status_history:", r["status_history"])
                print("chip_timeline:", r["chip_timeline"])
                print("edge_timeline:", r["edge_timeline"])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        shutil.rmtree(user_data_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_p())
