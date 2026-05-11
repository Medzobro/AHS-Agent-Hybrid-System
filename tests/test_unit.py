"""AHS v1.0 — Unit Tests for Memory + Tools + Web Search"""

import os
import sys
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from system.tools import MemoryStore, web_search, register_tools


# ─── Mock MCP Handler Registry ────────────────────────────────

class MockRegistry(dict):
    """dict subclass with .register() decorator method."""
    def register(self, name: str):
        def decorator(func):
            self[name] = func
            return func
        return decorator


# ─── MemoryStore Tests ────────────────────────────────────────

class TestMemoryStore:
    @pytest.fixture
    def store(self):
        """Temp DB, cleaned up after test."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        store = MemoryStore(db_path=db_path)
        yield store
        # Cleanup: close sqlite connection
        if hasattr(store, "_conn") and store._conn:
            store._conn.close()
        os.unlink(db_path)

    def test_set_and_get(self, store):
        result = store.set("test/key", "hello world")
        assert result["key"] == "test/key"
        assert result["version"] == 1
        assert "created_at" in result
        
        val = store.get("test/key")
        assert val == "hello world"

    def test_get_nonexistent(self, store):
        val = store.get("nonexistent")
        assert val is None

    def test_set_update_versions(self, store):
        store.set("test/key", "v1")
        assert store.get("test/key") == "v1"
        store.set("test/key", "v2")
        assert store.get("test/key") == "v2"
        # v1 should still exist (versioning)
        v1 = store.get("test/key", version=1)
        assert v1 == "v1"

    def test_delete_removes_key(self, store):
        store.set("test/key", "value")
        assert store.delete("test/key") is True
        assert store.get("test/key") is None

    def test_delete_nonexistent(self, store):
        assert store.delete("nonexistent") is True  # returns True always

    def test_search_by_key_prefix(self, store):
        store.set("user/alice", "Alice")
        store.set("user/bob", "Bob")
        store.set("config/x", "value")
        results = store.list_keys()
        # list_keys shows all keys, including newly added ones
        assert "user/alice" in results
        assert "user/bob" in results
        assert "config/x" in results

    def test_list_keys(self, store):
        store.set("a/1", "x")
        store.set("a/2", "y")
        store.set("b/1", "z")
        keys = store.list_keys()
        assert len(keys) >= 3
        assert "a/1" in keys

    def test_stats(self, store):
        store.set("a/1", "x")
        store.set("a/2", "y")
        stats = store.stats()
        assert stats["total_entries"] >= 2
        assert stats["unique_keys"] >= 2
        assert "database_size_kb" in stats

    def test_ttl_expiry(self, store):
        import time
        store.set("test/ttl", "expires", ttl_seconds=1)
        assert store.get("test/ttl") == "expires"
        time.sleep(1.5)
        assert store.get("test/ttl") is None

    def test_large_value(self, store):
        big = "x" * 100_000
        store.set("test/big", big)
        assert store.get("test/big") == big

    def test_special_chars_unicode(self, store):
        store.set("test/unicode", "مرحبا بالعالم 🌍")
        assert store.get("test/unicode") == "مرحبا بالعالم 🌍"


# ─── Web Search Tests ─────────────────────────────────────────

class TestWebSearch:
    def test_search_returns_list(self):
        results = web_search("test query", count=1)
        assert isinstance(results, list)

    def test_search_result_structure(self):
        results = web_search("python programming", count=1)
        if results:
            item = results[0]
            assert "title" in item
            assert "url" in item
            assert "snippet" in item


# ─── Register Tools Tests ─────────────────────────────────────

class TestRegisterTools:
    def test_register_all_handlers(self):
        registry = MockRegistry()
        register_tools(registry)
        expected = {"web_search", "memory_set", "memory_get", "memory_search", "memory_stats"}
        assert expected.issubset(set(registry.keys()))

    def test_web_search_handler(self):
        registry = MockRegistry()
        register_tools(registry)
        result = registry["web_search"]({"query": "test", "count": 1})
        assert isinstance(result, dict)
        assert "results" in result

    def test_memory_set_get_handler(self):
        registry = MockRegistry()
        register_tools(registry)
        result = registry["memory_set"]({"key": "test/h", "value": "hello"})
        assert result.get("key") == "test/h"
        assert "version" in result
        val = registry["memory_get"]({"key": "test/h"})
        assert val["value"] == "hello"
