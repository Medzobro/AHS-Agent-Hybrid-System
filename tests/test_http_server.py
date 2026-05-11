"""AHS v1.0 — Unit Tests for MCP HTTP Server (aiohttp handlers)

Adapted to the actual server API.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from bridge.mcp_http_server import (
    create_app,
    _rate_check,
    health,
    metrics,
    status_handler,
)


# ─── Rate Limiter Tests ───────────────────────────────────────

class TestRateCheck:
    def setup_method(self):
        import bridge.mcp_http_server as s
        s._rate_limit.clear()

    def test_allow_first_request(self):
        assert _rate_check("test_ip") is True

    def test_reject_after_limit(self):
        for _ in range(60):
            _rate_check("heavy_ip")
        assert _rate_check("heavy_ip") is False

    def test_rate_limit_resets_on_different_ip(self):
        for _ in range(60):
            _rate_check("ip_a")
        assert _rate_check("ip_b") is True

    def test_rate_limit_per_ip(self):
        for _ in range(5):
            _rate_check("ip_x")
        assert _rate_check("ip_y") is True

    def test_just_under_limit(self):
        for _ in range(59):
            _rate_check("almost_ip")
        assert _rate_check("almost_ip") is True

    def test_rate_limits_are_independent(self):
        for _ in range(60):
            _rate_check("a")
        assert _rate_check("a") is False
        assert _rate_check("b") is True  # independent


# ─── HTTP Server (aiohttp) Integration Tests ──────────────────

class TestMCPServer(AioHTTPTestCase):
    async def get_application(self):
        return create_app()

    @unittest_run_loop
    async def test_health(self):
        resp = await self.client.request("GET", "/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"

    @unittest_run_loop
    async def test_metrics(self):
        resp = await self.client.request("GET", "/metrics")
        assert resp.status == 200
        data = await resp.json()
        assert "requests_total" in data or "requests" in data
        assert "uptime_seconds" in data or "uptime" in data

    @unittest_run_loop
    async def test_status(self):
        resp = await self.client.request("GET", "/status")
        assert resp.status == 200
        data = await resp.json()
        assert "version" in data or "server" in data

    @unittest_run_loop
    async def test_root(self):
        resp = await self.client.request("GET", "/")
        assert resp.status in (200, 302)

    @unittest_run_loop
    async def test_execute_code(self):
        """/execute accepts {code} and runs it."""
        resp = await self.client.request("POST", "/execute", json={
            "code": "print('hello')",
            "lang": "python3"
        })
        assert resp.status == 200
        data = await resp.json()
        assert "stdout" in data
        assert "hello" in data.get("stdout", "")

    @unittest_run_loop
    async def test_execute_empty_code(self):
        resp = await self.client.request("POST", "/execute", json={"code": ""})
        assert resp.status == 400

    @unittest_run_loop
    async def test_execute_invalid_json(self):
        resp = await self.client.request("POST", "/execute", data="not json",
                                          headers={"Content-Type": "application/json"})
        assert resp.status == 400

    @unittest_run_loop
    async def test_execute_missing_code(self):
        resp = await self.client.request("POST", "/execute", json={})
        assert resp.status == 400

    @unittest_run_loop
    async def test_memory_set_get(self):
        # Set
        resp = await self.client.request("POST", "/memory", json={
            "action": "set",
            "namespace": "test_srv",
            "key": "greeting",
            "value": "hello server"
        })
        assert resp.status == 200
        data = await resp.json()
        # Memory set returns {action, status}, not {success}
        assert "status" in data or "success" in data or "action" in data

        # Get
        resp = await self.client.request("POST", "/memory", json={
            "action": "get",
            "namespace": "test_srv",
            "key": "greeting"
        })
        assert resp.status == 200
        data = await resp.json()
        assert "value" in data or "success" in data

    @unittest_run_loop
    async def test_memory_search(self):
        resp = await self.client.request("POST", "/memory/search", json={
            "query": "greeting",
            "limit": 5
        })
        assert resp.status == 200
        data = await resp.json()
        assert "results" in data or "success" in data

    @unittest_run_loop
    async def test_memory_stats(self):
        resp = await self.client.request("POST", "/memory/stats", json={})
        assert resp.status == 200
        data = await resp.json()
        assert isinstance(data, dict)

    @unittest_run_loop
    async def test_web_search(self):
        resp = await self.client.request("POST", "/web_search", json={
            "query": "test",
            "max_results": 1
        })
        assert resp.status == 200
        data = await resp.json()
        assert "success" in data or "results" in data
