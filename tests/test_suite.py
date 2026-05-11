"""AHS v1.0 — Integration Tests (via httpx with live server)"""

import json
import os
import sys
import time
from pathlib import Path

import pytest
import httpx

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

BASE_URL = "http://localhost:18900"


@pytest.fixture(scope="module")
def server():
    """Start server if not already running."""
    import subprocess
    # Check if already running
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=2)
        if r.status_code == 200:
            yield
            return
    except Exception:
        pass

    # Start server
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "bridge/mcp_http_server.py")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    yield
    proc.terminate()
    proc.wait()


# ─── Module Tests ─────────────────────────────────────────────

class TestSystemInit:
    def test_imports(self):
        from system import AHSIntegration, bootstrap
        assert AHSIntegration
        assert callable(bootstrap)

    def test_tool_registry(self):
        from system.tool_registry import create_default_tools
        tools = create_default_tools()
        assert len(tools.list()) >= 5

    def test_all_modules_compile(self):
        modules = [
            "bridge/mcp_http_server.py",
            "bridge/hermes_bridge.py",
            "bridge/mcp_tools.py",
            "system/__init__.py",
            "system/integration.py",
            "system/self_learn.py",
            "system/skill_manager.py",
            "system/tool_registry.py",
            "system/tools.py",
            "main.py",
        ]
        for mod in modules:
            path = ROOT / mod
            assert path.exists(), f"Missing: {mod}"
            result = os.system(f"python3 -m py_compile {path} 2>/dev/null")
            assert result == 0, f"Compile error: {mod}"


# ─── HTTP Tests ──────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, server):
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "1.0.0" in data.get("version", "")
        assert "uptime" in data
        assert "requests" in data

    def test_metrics(self, server):
        r = httpx.get(f"{BASE_URL}/metrics", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "requests_total" in data
        assert "uptime_seconds" in data

    def test_status(self, server):
        r = httpx.get(f"{BASE_URL}/status", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "AHS MCP" in data.get("server", "")
        assert "uptime" in data


class TestExecute:
    def test_python_code(self, server):
        r = httpx.post(
            f"{BASE_URL}/execute",
            json={"code": "print(42)", "lang": "python3"},
            timeout=10,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["exit_code"] == 0
        assert "42" in data.get("stdout", "")

    def test_bash_code(self, server):
        r = httpx.post(
            f"{BASE_URL}/execute",
            json={"code": "echo hi", "lang": "bash"},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["exit_code"] == 0

    def test_empty_code_returns_400(self, server):
        r = httpx.post(
            f"{BASE_URL}/execute",
            json={"code": "", "lang": "python3"},
            timeout=5,
        )
        assert r.status_code == 400

    def test_code_timeout_504(self, server):
        r = httpx.post(
            f"{BASE_URL}/execute",
            json={"code": "import time; time.sleep(35)", "lang": "python3"},
            timeout=40,
        )
        assert r.status_code in (500, 504)  # server timeout or error


class TestMemory:
    def test_set_get_delete(self, server):
        key = f"test/{int(time.time())}"
        # Set
        r = httpx.post(f"{BASE_URL}/memory", json={
            "action": "set", "key": key, "value": "hello-world",
        }, timeout=5)
        assert r.status_code == 200
        # Get
        r = httpx.post(f"{BASE_URL}/memory", json={
            "action": "get", "key": key,
        }, timeout=5)
        assert r.status_code == 200
        assert r.json()["value"] == "hello-world"
        # Delete
        r = httpx.post(f"{BASE_URL}/memory", json={
            "action": "delete", "key": key,
        }, timeout=5)
        assert r.status_code == 200

    def test_list(self, server):
        """Memory list endpoint returns data."""
        # First add something so memory isn't empty
        httpx.post(f"{BASE_URL}/memory", json={"action": "set", "key": "test/listitem", "value": "x"}, timeout=5)
        r = httpx.post(f"{BASE_URL}/memory", json={"action": "list"}, timeout=5)
        data = r.json()
        assert r.status_code == 200, f"Status {r.status_code}: {data}"
        assert "count" in data
        assert "keys" in data


class TestValidation:
    def test_invalid_json_returns_400(self, server):
        r = httpx.post(f"{BASE_URL}/task", content=b"not-json", timeout=5)
        assert r.status_code == 400

    def test_empty_task_returns_400(self, server):
        r = httpx.post(f"{BASE_URL}/task", json={"task": ""}, timeout=5)
        assert r.status_code == 400

    def test_missing_field_returns_400(self, server):
        r = httpx.post(f"{BASE_URL}/task", json={}, timeout=5)
        assert r.status_code == 400


# ─── Edge Cases ──────────────────────────────────────────────

class TestEdgeCases:
    def test_parallel_requests(self, server):
        """10 parallel requests should all succeed."""
        import concurrent.futures

        def make_req(i):
            r = httpx.get(f"{BASE_URL}/health", timeout=10)
            return r.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as exe:
            futures = [exe.submit(make_req, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert all(s == 200 for s in results), f"Some failed: {results}"

    def test_large_payload(self, server):
        """Large (~10KB) payload should still work."""
        big = "x" * 10_000
        r = httpx.post(
            f"{BASE_URL}/execute",
            json={"code": f"s = '''{big}'''", "lang": "python3"},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["exit_code"] == 0
