#!/usr/bin/env python3
"""
Phase Q1 verification & SSE latency instrumentation script.
Runs Cross-Cloud #2 in headless Chrome (--password-store=basic --use-mock-keychain)
against the live Cloud Run UI and redeployed retail-agent-kc (StreamingMode.SSE),
measuring:
- Per-phase elapsed_ms and phase_ms
- Time to first visible character (phase_ms after last tool response, and cumulative elapsed_ms)
- last_token - first_token (token streaming duration > 0 ms)
- Incremental text_chunk count rendered in chat.js DOM
Writes logs/q1_verify.json.
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
CDP_PORT = 9245
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
    is_partial = bool(data.get("partial"))
    parts = data.get("content", {}).get("parts", [])
    for part in parts:
        if "function_call" in part:
            if is_partial:
                continue
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
        elif "text" in part and part["text"] and not part.get("thought"):
            if not is_partial:
                continue
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
    first_token_phase_ms = None
    final_turn_first_token_ms = None
    final_turn_first_token_phase_ms = None
    last_token_ms = None
    all_tables = []

    url = f"{AE_BASE}/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{KC_AGENT_ID}:streamQuery"
    resp = await asyncio.to_thread(
        requests.post,
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "class_method": "async_stream_query",
            "input": {
                "message": scoped_question,
                "user_id": f"{user_id}-{category}",
                "session_id": session_id,
                "run_config": {"streaming_mode": "sse"},
            },
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
                final_turn_first_token_ms = None
                final_turn_first_token_phase_ms = None
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
                final_turn_first_token_ms = None
                final_turn_first_token_phase_ms = None
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
                gen_ms = round((now - last_phase_t) * 1000)
                if first_token_ms is None:
                    first_token_ms = elapsed_ms
                    first_token_phase_ms = gen_ms
                    phase_timings.append({
                        "phase": "first_token",
                        "phase_ms": gen_ms,
                        "elapsed_ms": first_token_ms,
                    })
                if final_turn_first_token_ms is None:
                    final_turn_first_token_ms = elapsed_ms
                    final_turn_first_token_phase_ms = gen_ms
                    if final_turn_first_token_ms != first_token_ms:
                        phase_timings.append({
                            "phase": "final_turn_first_token",
                            "phase_ms": gen_ms,
                            "elapsed_ms": final_turn_first_token_ms,
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
    return phase_timings, total_ms, first_token_phase_ms, first_token_ms, last_token_ms


async def run_q1():
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

    user_data_dir = f"/tmp/chrome_q1_{os.getpid()}"
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

            await cdp.evaluate(
                """(() => {
                    const container = chat._agentContainers['kc'];
                    if (container) container.innerHTML = '';
                    chat._currentAgentMsg = null;
                    viz.clearAnimation();
                    switchNarrative('multicloud');
                    document.getElementById('sendBtn').disabled = false;
                    window.__pendingWsPayload = null;
                    const btns = document.querySelectorAll('#presetQuestions .preset-btn');
                    btns[1].click();
                })()"""
            )
            payload = await cdp.wait_for("window.__pendingWsPayload", timeout_s=15.0)
            phase_timings, total_ms, first_token_phase_ms, first_token_ms, last_token_ms = await stream_kc_to_browser(
                cdp,
                payload["question"],
                payload["category"],
                f"q1-verify-{int(time.time())}",
            )
            await asyncio.sleep(0.2)

            ui_state = await cdp.evaluate(
                """(() => {
                    const msgs = document.querySelectorAll('.agent-messages-container[data-agent="kc"] .message.agent');
                    const last = msgs[msgs.length - 1];
                    return {
                        chip_timeline: last ? (last._chipTimeline || []) : [],
                        status_history: last ? (last._statusHistory || []) : [],
                        edge_timeline: last ? (last._edgeTimeline || []) : [],
                        text_chunk_timeline: last ? (last._textChunkTimeline || []) : [],
                        final_edge_count: viz._getCappedEdgeTargets().length,
                        answer_length: last ? (last._rawText || '').length : 0,
                    };
                })()"""
            )

            result = {
                "chip": "Cross-Cloud #2",
                "category": payload["category"],
                "question": payload["question"],
                "total_ms": total_ms,
                "first_token_phase_ms": first_token_phase_ms,
                "first_token_elapsed_ms": first_token_ms,
                "last_token_elapsed_ms": last_token_ms,
                "last_minus_first_ms": (last_token_ms - first_token_ms) if (last_token_ms is not None and first_token_ms is not None) else 0,
                "phase_timings": phase_timings,
                "text_chunks_rendered": len(ui_state["text_chunk_timeline"]),
                "chip_timeline": ui_state["chip_timeline"],
                "status_history": ui_state["status_history"],
                "final_edge_count": ui_state["final_edge_count"],
                "answer_length": ui_state["answer_length"],
            }
            os.makedirs("logs", exist_ok=True)
            with open("logs/q1_verify.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)

            print(f"=== Cross-Cloud #2 (total={total_ms} ms) ===")
            for pt in phase_timings:
                print(f"  {pt['phase']:32s} | phase_ms={pt['phase_ms']:6d} | elapsed_ms={pt['elapsed_ms']:6d}")
            print(f"  first_token_phase_ms (after last tool): {first_token_phase_ms} ms")
            print(f"  first_token_elapsed_ms (from start):    {first_token_ms} ms")
            print(f"  last_token - first_token:               {result['last_minus_first_ms']} ms")
            print(f"  text_chunks_rendered in DOM:            {result['text_chunks_rendered']}")
            print(f"  chips rendered:                         {[c['name'] for c in ui_state['chip_timeline']]}")
            print(f"  final_edge_count:                       {ui_state['final_edge_count']}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        shutil.rmtree(user_data_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_q1())
