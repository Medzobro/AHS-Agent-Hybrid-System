import pytest
"""AHS Integration Tests — Full Stack"""

import json
import threading
import time
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent.parent
MCP_SERVER = ROOT / "bridge" / "mcp_http_server.py"


@pytest.fixture(scope="module")
def mcp_server():
    """Start MCP HTTP server for testing."""
    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)
    yield
    proc.terminate()
    proc.wait()


def test_health(mcp_server):
    """GET /health returns ok."""
    import urllib.request
    req = urllib.request.Request("http://localhost:18900/health", method="GET")
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    assert data["status"] == "ok"
    assert "version" in data


def test_execute_code(mcp_server):
    """POST /execute runs Python code."""
    import urllib.request
    payload = json.dumps({"code": "print(42)", "lang": "python3"}).encode()
    req = urllib.request.Request(
        "http://localhost:18900/execute",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    assert data["exit_code"] == 0
    assert data["stdout"].strip() == "42"


def test_web_search(mcp_server):
    """POST /web_search returns results."""
    import urllib.request
    payload = json.dumps({"query": "test", "count": 1}).encode()
    req = urllib.request.Request(
        "http://localhost:18900/web_search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    assert data["count"] > 0
    assert len(data["results"]) > 0


def test_memory_set_get(mcp_server):
    """Memory CRUD works."""
    import urllib.request
    # Set
    payload = json.dumps({"action": "set", "key": "test/integration", "value": "works"}).encode()
    req = urllib.request.Request(
        "http://localhost:18900/memory",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    assert data["action"] == "set"

    # Get
    payload = json.dumps({"action": "get", "key": "test/integration"}).encode()
    req = urllib.request.Request(
        "http://localhost:18900/memory",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    assert "works" in str(data)
