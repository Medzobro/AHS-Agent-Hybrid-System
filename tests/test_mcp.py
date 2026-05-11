"""AHS v1.0 — Unit Tests for MCP Tools + Web Search

Note: MCP ToolRegistry expects MemoryStore with namespace/key/value API
but system.tools.MemoryStore uses plain key/value API.
We test the ToolRegistry struct and execution flow with a mock memory store
that matches the expected interface.
"""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest

# Mock MemoryStore that matches mcp_tools.py expectations
class MockMemoryStore:
    _store: dict = {}

    def get(self, namespace="", key=""):
        full_key = f"{namespace}:{key}"
        return self._store.get(full_key)

    def set(self, namespace="", key="", value=None, ttl=None):
        full_key = f"{namespace}:{key}"
        self._store[full_key] = value
        return {"version": 1}

    def search(self, query="", limit=20):
        return [{"key": k, "value": v} for k, v in self._store.items() if query in k][:limit]

    def list_keys(self, namespace="", prefix="", limit=50):
        prefix_str = prefix or ''
        ns_str = f"{namespace}:" if namespace else ''
        return [k for k in self._store if k.startswith(ns_str) and prefix_str in k][:limit]

    def status(self):
        return {"key_count": len(self._store)}


# Mock the missing bridge.memory_store module
sys.modules["bridge.memory_store"] = types.ModuleType("bridge.memory_store")
sys.modules["bridge.memory_store"].MemoryStore = MockMemoryStore

from bridge.mcp_tools import ToolRegistry
from bridge.mcp_web_search import WebSearchMCP


# ─── MCP ToolRegistry Tests ────────────────────────────────────

class TestMCPToolRegistry:
    @pytest.fixture
    def reg(self):
        return ToolRegistry(memory_store=MockMemoryStore())

    def test_initialization(self, reg):
        assert reg.call_count == 0
        assert reg.error_count == 0
        assert len(reg.list_tools()) >= 6

    def test_list_tools_structure(self, reg):
        tools = reg.list_tools()
        tool = tools[0]
        assert "name" in tool
        assert "description" in tool
        assert "schema" in tool

    def test_known_tools_present(self, reg):
        names = [t["name"] for t in reg.list_tools()]
        for required in ["web_search", "fetch_url", "memory_get",
                         "memory_set", "memory_search", "memory_list",
                         "memory_status"]:
            assert required in names, f"Missing: {required}"

    def test_get_tool_exists(self, reg):
        t = reg.get_tool("web_search")
        assert t is not None
        assert t["name"] == "web_search"

    def test_get_tool_missing(self, reg):
        assert reg.get_tool("nonexistent") is None

    def test_execute_missing_tool(self, reg):
        result = reg.execute("no_such_tool", {})
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_execute_memory_roundtrip(self, reg):
        result = reg.execute("memory_set", {
            "namespace": "test_unit", "key": "mcp_t1", "value": "test_value"
        })
        assert result["success"] is True
        assert "version" in result

        result = reg.execute("memory_get", {
            "namespace": "test_unit", "key": "mcp_t1"
        })
        assert result["success"] is True
        assert result["value"] == "test_value"

    def test_execute_memory_search(self, reg):
        reg.execute("memory_set", {
            "namespace": "test_unit", "key": "searchable", "value": "xyz"
        })
        result = reg.execute("memory_search", {"query": "searchable", "limit": 5})
        assert result["success"] is True
        assert result["count"] >= 1

    def test_execute_memory_list(self, reg):
        reg.execute("memory_set", {"namespace": "test_list", "key": "item_1", "value": "a"})
        reg.execute("memory_set", {"namespace": "test_list", "key": "item_2", "value": "b"})
        result = reg.execute("memory_list", {"namespace": "test_list"})
        assert result["success"] is True
        assert result["count"] >= 2 or len(result["keys"]) >= 2

    def test_execute_memory_status(self, reg):
        result = reg.execute("memory_status", {})
        assert result["success"] is True
        assert "status" in result
        assert "key_count" in result["status"]

    def test_execute_memory_get_missing(self, reg):
        result = reg.execute("memory_get", {
            "namespace": "nonexistent", "key": "no_key"
        })
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_tool_execution_counts(self, reg):
        initial = reg.call_count
        reg.execute("web_search", {"query": "test", "max_results": 1})
        assert reg.call_count == initial + 1

    def test_status(self, reg):
        s = reg.status()
        assert "tool_count" in s
        assert "calls" in s
        assert "errors" in s
        assert s["tool_count"] >= 6

    def test_register_custom_tool(self, reg):
        def my_handler(params):
            return {"custom": params.get("x") * 2}
        reg.register(
            name="custom_double",
            description="Double a number",
            schema={"type": "object", "properties": {"x": {"type": "number"}}},
            handler=my_handler,
        )
        assert reg.get_tool("custom_double") is not None
        result = reg.execute("custom_double", {"x": 21})
        assert result["success"] is True
        assert result["result"]["custom"] == 42


# ─── MCP WebSearch Tests ───────────────────────────────────────

class TestWebSearchMCP:
    @pytest.fixture
    def searcher(self):
        return WebSearchMCP()

    def test_search_basic(self, searcher):
        result = searcher.search("test query", max_results=1)
        assert "success" in result
        assert "results" in result

    def test_search_result_structure(self, searcher):
        result = searcher.search("python programming", max_results=1)
        assert "success" in result
        if result["success"] and result["total"] > 0:
            item = result["results"][0]
            assert "title" in item
            assert "url" in item
            assert "snippet" in item

    def test_fetch_url(self, searcher):
        result = searcher.fetch("https://example.com", timeout=10)
        assert "success" in result
        if result["success"]:
            assert "content" in result

    def test_fetch_url_empty(self, searcher):
        result = searcher.fetch("", timeout=5)
        assert result["success"] is False

    def test_fetch_url_invalid(self, searcher):
        result = searcher.fetch("not-a-valid-url", timeout=5)
        assert result["success"] is False

    def test_search_empty_query(self, searcher):
        result = searcher.search("", max_results=5)
        assert result["success"] is False
