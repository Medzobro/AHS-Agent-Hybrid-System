#!/usr/bin/env python3
"""
AHS v1 — MCP HTTP Bridge Server
=================================
Server HTTP للربط بين TypeScript Core و Python Service.
يستمع على port 18900 (قابل للتحديد عبر env AHS_MCP_PORT).

Endpoints:
  GET  /health        → {"status":"ok","version":"0.4.0"}
  POST /task          → يُرسل المهمة لـ Hermes ويرد بالنتيجة
  POST /execute       → ينفذ كود (Python/Bash)
  POST /web_search    → بحث ويب
  POST /memory        → ذاكرة (get/set/delete)
  POST /memory/search → بحث في الذاكرة
  POST /memory/stats  → إحصائيات الذاكرة
"""

import http.server
import json
import logging
import os
import subprocess
import sys
import urllib.parse
from typing import Dict, Any

# AHS Tools — import مرة واحدة
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from system.tools import MemoryStore, web_search

# ─── Config ───────────────────────────────────────────────────
AHS_VERSION = "0.4.0"
PORT = int(os.environ.get("AHS_MCP_PORT", "18900"))
HOST = os.environ.get("AHS_MCP_HOST", "0.0.0.0")
HERMES_CLI = os.environ.get("HERMES_CLI", "/data/.local/bin/hermes")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

logging.basicConfig(
    level=logging.INFO,
    format="[AHS-MCP] %(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ahs-mcp")


# ─── Response helpers ─────────────────────────────────────────

def json_response(data: Dict, status: int = 200) -> bytes:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return (
        f"HTTP/1.1 {status} {'OK' if status == 200 else 'Error'}\r\n"
        f"Content-Type: application/json; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"\r\n"
    ).encode("utf-8") + body


def error_response(message: str, status: int = 500) -> bytes:
    return json_response({"success": False, "error": message}, status)


# ─── Hermes sender ────────────────────────────────────────────

def send_to_hermes(message: str, timeout: int = 120) -> Dict[str, Any]:
    """
    أرسل رسالة إلى Hermes عبر CLI.
    في المرحلة القادمة: سيصبح عبر WebSocket MCP.
    """
    try:
        result = subprocess.run(
            [HERMES_CLI, "chat", "-Q", "-q", message],
            capture_output=True,
            timeout=timeout,
            text=True,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            response = lines[-1].strip() if lines else ""
            return {"success": True, "content": response}
        else:
            return {"success": False, "error": result.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Hermes timeout (>120s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── AHS MCP Handler ──────────────────────────────────────────

class AHSMCPHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for MCP bridge requests"""
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == "/health":
            self._send_json({
                "status": "ok",
                "version": AHS_VERSION,
                "uptime": 0,  # TODO: track uptime
            })
        else:
            self._send_json({"error": "Not found"}, 404)
    
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_raw(error_response("Invalid JSON"))
            return
        
        if parsed.path == "/task":
            self._handle_task(data)
        elif parsed.path == "/execute":
            self._handle_execute(data)
        elif parsed.path == "/web_search":
            self._handle_web_search(data)
        elif parsed.path == "/memory":
            self._handle_memory(data)
        elif parsed.path == "/memory/search":
            self._handle_memory_search(data)
        elif parsed.path == "/memory/stats":
            self._handle_memory_stats(data)
        else:
            self._send_json({"error": "Not found"}, 404)
    
    def do_OPTIONS(self):
        """CORS preflight"""
        self._send_json({"ok": True})
    
    # ─── Task handler ─────────────────────────────────
    
    def _handle_task(self, data: Dict):
        task = data.get("task", "")
        mode = data.get("mode", "auto")
        
        if not task:
            self._send_json({"success": False, "error": "Missing 'task' field"}, 400)
            return
        
        logger.info(f"📥 Task: {task[:80]}... (mode={mode})")
        
        # Quick mode — no Hermes needed
        if mode == "quick":
            self._send_json({
                "success": True,
                "mode": "quick",
                "response": "✅ تم",
                "elapsed": 0.01,
            })
            return
        
        # Deep/Hybrid — send to Hermes
        message = f"أجب على هذا السؤال بإجابة مباشرة ومفيدة:\n{task}"
        result = send_to_hermes(message, timeout=120)
        
        if result["success"]:
            logger.info(f"📤 Response: {result['content'][:80]}...")
            self._send_json({
                "success": True,
                "mode": mode,
                "response": result["content"],
            })
        else:
            logger.error(f"❌ Hermes failed: {result['error']}")
            self._send_json(result, 502)
    
    # ─── Execute handler ──────────────────────────────
    
    def _handle_execute(self, data: Dict):
        code = data.get("code", "")
        lang = data.get("lang", "python3")
        
        if not code:
            self._send_json({"success": False, "error": "Missing 'code'"}, 400)
            return
        
        logger.info(f"⚡ Execute: {lang} ({len(code)} chars)")
        
        try:
            if lang == "python3":
                result = subprocess.run(
                    ["python3", "-c", code],
                    capture_output=True, text=True, timeout=30
                )
                response = {
                    "success": result.returncode == 0,
                    "stdout": result.stdout[:1000],
                    "stderr": result.stderr[:500],
                    "exit_code": result.returncode,
                }
            elif lang == "bash":
                result = subprocess.run(
                    ["bash", "-c", code],
                    capture_output=True, text=True, timeout=30
                )
                response = {
                    "success": result.returncode == 0,
                    "stdout": result.stdout[:1000],
                    "stderr": result.stderr[:500],
                    "exit_code": result.returncode,
                }
            else:
                response = {"success": False, "error": f"Unsupported language: {lang}"}
            
            self._send_json(response)
        except subprocess.TimeoutExpired:
            self._send_json({"success": False, "error": "Execution timeout (>30s)"}, 504)
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)
    
    # ─── Web Search handler ───────────────────────────
    
    def _handle_web_search(self, data: Dict):
        query = data.get("query", data.get("q", ""))
        count = data.get("count", 5)
        
        if not query:
            self._send_json({"success": False, "error": "Missing 'query'"}, 400)
            return
        
        results = web_search(query, count)
        self._send_json({"success": True, "results": results, "count": len(results)})
    
    # ─── Memory handlers ──────────────────────────────
    
    def _get_memory(self):
        """Get or create global MemoryStore instance"""
        if not hasattr(self.__class__, '_memory'):
            db_path = os.environ.get("AHS_MEMORY_DB",
                os.path.join(os.path.dirname(__file__), '..', 'data', 'ahs_memory.db'))
            self.__class__._memory = MemoryStore(db_path)
        return self.__class__._memory
    
    def _handle_memory(self, data: Dict):
        action = data.get("action", "get")
        key = data.get("key", "")
        value = data.get("value", "")
        mem = self._get_memory()
        
        if action == "set":
            ttl = data.get("ttl")
            result = mem.set(key, value, ttl)
            self._send_json({"success": True, **result})
        elif action == "get":
            val = mem.get(key)
            self._send_json({"success": True, "key": key, "value": val})
        elif action == "delete":
            mem.delete(key)
            self._send_json({"success": True})
        else:
            self._send_json({"success": False, "error": f"Unknown action: {action}"}, 400)
    
    def _handle_memory_search(self, data: Dict):
        query = data.get("query", "")
        mem = self._get_memory()
        results = mem.search(query)
        self._send_json({"success": True, "results": results})
    
    def _handle_memory_stats(self, data: Dict):
        mem = self._get_memory()
        stats = mem.stats()
        self._send_json({"success": True, **stats})
    
    # ─── Helpers ──────────────────────────────────────
    
    def _send_json(self, data: Dict, status: int = 200):
        self._send_raw(json_response(data, status))
    
    def _send_raw(self, data: bytes):
        self.wfile.write(data)
    
    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - {format % args}")


# ─── Server ────────────────────────────────────────────────────

class ReuseHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True

def main():
    print(f"\n{'='*50}")
    print(f"  🔌 AHS MCP Bridge Server v{AHS_VERSION}")
    print(f"  ربط TypeScript Core ↔ Python Service")
    print(f"{'='*50}")
    print(f"\n  🌐 Listening on {HOST}:{PORT}")
    print(f"     GET  /health  → Health check")
    print(f"     POST /task    → Process task via Hermes")
    print(f"     POST /execute → Execute code\n")
    
    server = ReuseHTTPServer((HOST, PORT), AHSMCPHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  👋 Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
