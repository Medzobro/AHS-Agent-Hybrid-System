"""
AHS v1.0 — Async MCP HTTP Server
==================================
Uses aiohttp for async, multi-request handling.
"""

import asyncio
import json
import logging
import os
import sys
import time

import aiohttp
from pathlib import Path

from aiohttp import web

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from system.tools import MemoryStore, web_search

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ahs.mcp")

AHS_VERSION = "1.0.0"
PORT = int(os.environ.get("AHS_MCP_PORT", "18900"))
HOST = os.environ.get("AHS_MCP_HOST", "0.0.0.0")

# Monitoring
_request_count = 0
_start_time = time.time()

# In-memory rate limiter
_rate_limit: dict[str, list[float]] = {}


def _rate_check(ip: str, max_req: int = 60, window: int = 60) -> bool:
    now = time.time()
    if ip not in _rate_limit:
        _rate_limit[ip] = []
    _rate_limit[ip] = [t for t in _rate_limit[ip] if now - t < window]
    if len(_rate_limit[ip]) >= max_req:
        return False
    _rate_limit[ip].append(now)
    return True


# ─── Routes ───────────────────────────────────────────────────

async def health(request: web.Request) -> web.Response:
    global _request_count
    _request_count += 1
    return web.json_response({
        "status": "ok",
        "version": AHS_VERSION,
        "uptime": round(time.time() - _start_time, 2),
        "requests": _request_count,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })


async def metrics(request: web.Request) -> web.Response:
    global _request_count
    _request_count += 1
    return web.json_response({
        "requests_total": _request_count,
        "uptime_seconds": round(time.time() - _start_time, 2),
        "version": AHS_VERSION,
        "rate_limit_active": len(_rate_limit),
    })


async def status_handler(request: web.Request) -> web.Response:
    global _request_count
    _request_count += 1
    return web.json_response({
        "server": "AHS MCP Bridge v" + AHS_VERSION,
        "uptime": round(time.time() - _start_time, 2),
        "requests": _request_count,
        "version": AHS_VERSION,
    })


async def task_handler(request: web.Request) -> web.Response:
    global _request_count
    _request_count += 1

    client_ip = request.remote or "127.0.0.1"
    if not _rate_check(client_ip):
        return web.json_response({"error": "429 Too Many Requests"}, status=429)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    task = body.get("task", "")
    mode = body.get("mode", "hybrid")
    timeout_s = min(int(body.get("timeout", 120)), 300)

    if not task:
        return web.json_response({"error": "Empty task"}, status=400)

    t0 = time.time()
    try:
        # Import hermes bridge here to avoid circular imports
        from bridge.hermes_bridge import HermesBridge
        bridge = HermesBridge()
        result = bridge.send_task(task, timeout=timeout_s)
        elapsed = round(time.time() - t0, 2)
        resp = result.get("response", "")
        if not resp:
            resp = str(result)
        return web.json_response({
            "response": str(resp)[:2000],
            "mode": mode,
            "elapsed": elapsed,
        })
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        return web.json_response({
            "error": str(e),
            "elapsed": elapsed,
        }, status=500)


async def execute_handler(request: web.Request) -> web.Response:
    global _request_count
    _request_count += 1
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    code = body.get("code", "")
    lang = body.get("lang", "python3")
    if not code:
        return web.json_response({"error": "Empty code"}, status=400)

    t0 = time.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            lang, "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        return web.json_response({
            "stdout": stdout.decode()[:1000],
            "stderr": stderr.decode()[:1000],
            "exit_code": proc.returncode,
            "elapsed": round(time.time() - t0, 2),
        })
    except asyncio.TimeoutError:
        return web.json_response({"error": "Execution timeout", "elapsed": 30}, status=504)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def web_search_handler(request: web.Request) -> web.Response:
    global _request_count
    _request_count += 1
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    query = body.get("query", "")
    count = min(int(body.get("count", 5)), 10)
    if not query:
        return web.json_response({"error": "Empty query"}, status=400)

    try:
        results = web_search(query, count=count)
        return web.json_response({
            "results": results[:10],
            "count": len(results),
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def memory_handler(request: web.Request) -> web.Response:
    global _request_count
    _request_count += 1
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    action = body.get("action", "get")
    key = body.get("key", "")
    value = body.get("value", "")

    try:
        store = MemoryStore()
        if action == "set" and key and value:
            store.set(key, value)
        elif action == "get" and key:
            val = store.get(key)
            return web.json_response({"key": key, "value": val})
        elif action == "delete" and key:
            store.delete(key)
        elif action == "list":
            all_mem = store.list_keys(50)
            return web.json_response({"count": len(all_mem), "keys": all_mem[:50]})
        return web.json_response({"status": "ok", "action": action})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def memory_search_handler(request: web.Request) -> web.Response:
    body = await _safe_read_json(request)
    query = (body or {}).get("query", "")
    try:
        store = MemoryStore()
        results = store.search(query)
        return web.json_response({"results": results[:10], "count": len(results)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def memory_stats_handler(request: web.Request) -> web.Response:
    try:
        store = MemoryStore()
        return web.json_response(store.stats())
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def _safe_read_json(request: web.Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


# ─── App ──────────────────────────────────────────────────────

def create_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get("/", dashboard_handler),
        web.get("/dashboard", dashboard_handler),
        web.get("/health", health),
        web.get("/metrics", metrics),
        web.get("/status", status_handler),
        web.post("/task", task_handler),
        web.post("/execute", execute_handler),
        web.post("/web_search", web_search_handler),
        web.post("/memory", memory_handler),
        web.post("/memory/search", memory_search_handler),
        web.post("/memory/stats", memory_stats_handler),
    ])
    return app


async def dashboard_handler(request: web.Request) -> web.Response:
    html_path = Path(__file__).parent / "dashboard.html"
    if html_path.exists():
        content = html_path.read_text(encoding="utf-8")
        return web.Response(text=content, content_type="text/html")
    return web.Response(text="Dashboard not found", status=404)

async def cleanup(app: web.Application):
    """Graceful shutdown."""
    log.info("Shutting down AHS MCP server...")
    await asyncio.sleep(0.1)


def main():
    log.info(f"🤝 AHS v{AHS_VERSION} Async MCP Bridge — {HOST}:{PORT}")
    app = create_app()
    web.run_app(app, host=HOST, port=PORT, print=lambda _: None, shutdown_timeout=3)


if __name__ == "__main__":
    main()
