#!/usr/bin/env python3
"""
Headless Chrome (CDP) verification for Phase O1 against live Cloud Run URL:
https://retail-kc-demo-ui-live-98236392654.us-central1.run.app
Always uses --password-store=basic --use-mock-keychain.
Verifies across all 3 agents (basic, scaled, kc) and with CROSS-CLOUD selected on kc:
1. No badge on CROSS-CLOUD tab (reads exact string "CROSS-CLOUD").
2. Secondary blue banner (.cross-cloud-banner / "◆ NEXUS · Snowflake (External): Simulated connector — NEXUS reference data") is removed from the DOM.
3. Neither "Simulated connector" nor "◆ NEXUS · Snowflake (External):" appears anywhere in rendered DOM on any of the 3 agents.
"""
import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
import urllib.request
import websockets

CLOUD_RUN_URL = "https://retail-kc-demo-ui-live-98236392654.us-central1.run.app"
CDP_PORT = 9234


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

    async def wait_for(self, js_predicate: str, timeout_s: float = 30.0, poll_s: float = 0.2):
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


async def run():
    profile_dir = "/tmp/chrome_phase_o1_profile"
    shutil.rmtree(profile_dir, ignore_errors=True)
    os.makedirs(profile_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    chrome_log = open("logs/phase_o1_chrome.log", "w")
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

        async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
            cdp = CDPClient(ws)
            await cdp.send("Page.enable")
            await cdp.send("Runtime.enable")
            await cdp.send(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": f"localStorage.setItem('id_token', '{mock_jwt}');"},
            )
            await cdp.send("Page.navigate", {"url": f"{CLOUD_RUN_URL}/?t={int(time.time())}"})
            await cdp.wait_for("typeof viz !== 'undefined' && viz.nodes.length >= 128")

            results = {}
            for agent in ("basic", "scaled", "kc"):
                await cdp.evaluate(f"switchAgent('{agent}')")
                await asyncio.sleep(0.3)
                if agent == "kc":
                    await cdp.evaluate("switchNarrative('multicloud')")
                    await asyncio.sleep(0.3)

                state = await cdp.evaluate(
                    """(() => {
                        const html = document.documentElement.innerHTML;
                        const text = document.body.innerText;
                        const ccTab = document.querySelector('[data-narrative="multicloud"]');
                        const badgeEl = document.querySelector('.nexus-tab-badge');
                        const bannerEl = document.querySelector('.cross-cloud-banner');
                        const legendNexus = document.querySelector('.legend-nexus');
                        return {
                            ccTabExists: Boolean(ccTab),
                            ccTabText: ccTab ? ccTab.textContent : null,
                            ccTabTitle: ccTab ? ccTab.title : null,
                            badgeElExists: Boolean(badgeEl),
                            bannerElExists: Boolean(bannerEl),
                            hasSimulatedStringInDOM: html.includes('Simulated connector') || text.includes('Simulated connector'),
                            hasBannerStringInDOM: html.includes('◆ NEXUS · Snowflake (External):') || text.includes('◆ NEXUS · Snowflake (External):'),
                            legendNexusText: legendNexus ? legendNexus.textContent.trim() : null,
                            snowflakeNodesCount: (typeof viz !== 'undefined' && viz.nodes) ? viz.nodes.filter(p => p.tier === 'snowflake').length : 0
                        };
                    })()"""
                )
                results[agent] = state

            with open("logs/o1_verify.json", "w") as f:
                json.dump(results, f, indent=2)
            print(json.dumps(results, indent=2))
    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=5)
        except Exception:
            chrome_proc.kill()
        chrome_log.close()


if __name__ == "__main__":
    asyncio.run(run())
