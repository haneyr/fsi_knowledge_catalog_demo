#!/usr/bin/env python3
"""
FSI Knowledge Catalog Demo — Web Application

Serves the interactive point cloud visualization and proxies agent queries
to Vertex AI Agent Engine. Supports both static (pre-recorded) and live
(WebSocket) modes.

Usage:
    # Static mode (for demos):
    python app.py

    # Live mode (with Agent Engine):
    BASIC_AGENT_ID=123 SCALED_AGENT_ID=456 KC_AGENT_ID=789 python app.py
"""

import json
import os
import time
import logging

from flask import Flask, send_from_directory, request, jsonify

app = Flask(__name__, static_folder="static")
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

AGENT_IDS = {
    "basic": os.environ.get("BASIC_AGENT_ID", ""),
    "scaled": os.environ.get("SCALED_AGENT_ID", ""),
    "kc": os.environ.get("KC_AGENT_ID", ""),
}

_agents_initialized = False
_agents = {}


def _init_agents():
    global _agents_initialized, _agents
    if _agents_initialized:
        return
    if not any(AGENT_IDS.values()):
        logger.info("No agent IDs configured — running in static-only mode")
        _agents_initialized = True
        return
    try:
        import vertexai
        from vertexai import agent_engines
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        for name, aid in AGENT_IDS.items():
            if aid:
                _agents[name] = agent_engines.get(aid)
                logger.info("Connected to %s agent: %s", name, aid)
        _agents_initialized = True
    except Exception as e:
        logger.warning("Failed to initialize agents: %s", e)
        _agents_initialized = True


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


@app.route("/api/config")
def config():
    return jsonify({
        "project_id": PROJECT_ID,
        "live_mode": bool(_agents),
        "agents": {k: bool(v) for k, v in AGENT_IDS.items()},
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    _init_agents()
    data = request.json
    agent_type = data.get("agent", "basic")
    question = data.get("question", "")

    if agent_type not in _agents:
        return jsonify({"error": "Agent not available — using static mode", "static": True}), 200

    agent = _agents[agent_type]
    start = time.time()
    try:
        result = agent.query(input=question)
        latency = time.time() - start
        if isinstance(result, dict):
            response_text = result.get("output", result.get("response", json.dumps(result)))
        else:
            response_text = str(result)

        return jsonify({
            "response": response_text,
            "latency": round(latency, 1),
            "agent": agent_type,
            "live": True,
        })
    except Exception as e:
        return jsonify({"error": str(e)[:500], "agent": agent_type}), 500


try:
    from flask_sock import Sock
    sock = Sock(app)

    @sock.route("/api/ws")
    def websocket_chat(ws):
        _init_agents()
        while True:
            data = ws.receive()
            if data is None:
                break
            msg = json.loads(data)
            agent_type = msg.get("agent", "basic")
            question = msg.get("question", "")

            if agent_type not in _agents:
                ws.send(json.dumps({"type": "error", "message": "Agent not available in live mode"}))
                continue

            ws.send(json.dumps({"type": "status", "message": "Querying agent..."}))
            agent = _agents[agent_type]
            start = time.time()

            try:
                result = agent.query(input=question)
                latency = time.time() - start
                if isinstance(result, dict):
                    response_text = result.get("output", result.get("response", json.dumps(result)))
                else:
                    response_text = str(result)

                ws.send(json.dumps({
                    "type": "response",
                    "text": response_text,
                    "latency": round(latency, 1),
                    "agent": agent_type,
                }))
            except Exception as e:
                ws.send(json.dumps({"type": "error", "message": str(e)[:500]}))

except ImportError:
    logger.info("flask-sock not available — WebSocket mode disabled")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
