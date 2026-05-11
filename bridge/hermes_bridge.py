#!/usr/bin/env python3
"""
AHS — Hermes Bridge (MCP Native)
==================================
No subprocess. No CLI. Uses native HTTP + MCP only.
Fast, reliable, no Python subprocess overhead.
"""

import json
import logging
import os
import sys
import time
from urllib.request import Request, urlopen

WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, WORKSPACE)

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

logger = logging.getLogger("ahs.hermes_bridge")

MCP_HTTP_PORT = int(os.environ.get("AHS_MCP_PORT", "18900"))
MCP_HTTP_HOST = os.environ.get("AHS_MCP_HOST", "localhost")


class HermesBridge:
    """Native MCP Bridge — HTTP only. No subprocess, no CLI."""

    def __init__(self):
        self.last_response: str | None = None
        self.last_reasoning: str | None = None
        self._mcp_bridge = None
        self._check_mcp_module()

    def _check_mcp_module(self):
        """Try to import openclaw_mcp_bridge for direct MCP access"""
        try:
            from openclaw_mcp_bridge import hermes_send
            self._mcp_bridge = hermes_send
        except ImportError:
            self._mcp_bridge = None

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def send_task(
        self,
        task: str,
        skills: str = "",
        timeout: int = 60,
        thinking_mode: bool = False,
        context: list[dict] | None = None,
    ) -> dict:
        """Send a task. HTTP first, MCP second."""
        # 1. Try MCP HTTP Bridge
        try:
            return self._send_via_http(task, timeout)
        except Exception as e:
            logger.debug(f"HTTP bridge failed: {e}")

        # 2. Try MCP Python bridge
        if self._mcp_bridge:
            try:
                return self._send_via_mcp(task, timeout)
            except Exception as e:
                logger.debug(f"MCP bridge failed: {e}")

        return self._error("all_methods_failed", "cannot_reach_hermes")

    def _send_via_http(self, task: str, timeout: int) -> dict:
        """MCP HTTP Bridge — fastest path."""
        payload = json.dumps({"task": task, "mode": "hybrid", "timeout": timeout}).encode()
        url = f"http://{MCP_HTTP_HOST}:{MCP_HTTP_PORT}/task"

        t0 = time.time()
        req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=timeout + 5) as resp:
            result = json.loads(resp.read())
        elapsed = round(time.time() - t0, 2)

        response_text = ""
        if isinstance(result.get("response"), dict):
            response_text = result["response"].get("content", str(result["response"]))
        elif isinstance(result.get("response"), str):
            response_text = result["response"]
        else:
            response_text = str(result.get("response", result.get("content", "")))

        self.last_response = response_text

        return {
            "success": result.get("success", False),
            "method": "mcp_http",
            "response": response_text,
            "elapsed": elapsed,
        }

    def _send_via_mcp(self, task: str, timeout: int) -> dict:
        """MCP Python bridge — openclaw_mcp_bridge."""
        t0 = time.time()
        try:
            response = self._mcp_bridge(task)
        except Exception as e:
            return self._error("mcp_bridge_error", str(e))

        elapsed = round(time.time() - t0, 2)
        content = str(response) if response else ""

        reasoning = ""
        if "Thinking:" in content:
            parts = content.split("Thinking:", 1)
            if len(parts) > 1 and "Response:" in parts[1]:
                reasoning, content = parts[1].split("Response:", 1)
            elif len(parts) > 1:
                content = parts[0]
                reasoning = parts[1]

        self.last_response = content.strip() if not reasoning else content.strip()
        self.last_reasoning = reasoning.strip() if reasoning else None

        return {
            "success": True,
            "method": "mcp",
            "response": content.strip(),
            "elapsed": elapsed,
        }

    def _error(self, code: str, message: str) -> dict:
        """Return structured error without CLI fallback."""
        return {
            "success": False,
            "method": "error",
            "error": message,
            "response": f"❌ {message}",
            "elapsed": 0,
        }

    def analyze_with_hermes(self, task: str) -> dict:
        """Analyze with Hermes — alias for send_task."""
        return self.send_task(task, timeout=90)

    def status(self) -> dict:
        """Bridge health."""
        return {
            "http_available": self._check_http(),
            "mcp_available": self._mcp_bridge is not None,
            "last_response": bool(self.last_response),
        }

    def _check_http(self) -> bool:
        """Quick HTTP health check."""
        try:
            req = Request(f"http://{MCP_HTTP_HOST}:{MCP_HTTP_PORT}/health", method="GET")
            with urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False
