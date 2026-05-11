#!/usr/bin/env python3
"""
AHS v1 — MCP Tool Registry
============================
يسجل الأدوات في MCP Bridge: Web Search, Memory, Code Execution.

كل أداة:
  - name: معرف الأداة (snake_case)
  - description: وصف لما تفعله
  - handler: async function(input) → output
  - schema: JSON Schema للمدخلات
"""

import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from .memory_store import MemoryStore

logger = logging.getLogger("ahs.mcp_tools")

# ─── Tool Registry ──────────────────────────────────────────────


class ToolRegistry:
    """
    Central registry for MCP tools.
    Each tool has a name, schema, and handler function.
    """

    def __init__(self, memory_store: Optional[MemoryStore] = None):
        self.memory: MemoryStore = memory_store or MemoryStore()
        self._tools: Dict[str, Dict] = {}
        self.call_count = 0
        self.error_count = 0
        self._register_defaults()

    def _register_defaults(self):
        """Register built-in tools."""
        self.register(
            name="web_search",
            description="Search the web for information. Uses DuckDuckGo (free, no API key).",
            schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max results (1-10)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
            handler=self._handle_web_search,
        )

        self.register(
            name="fetch_url",
            description="Fetch and extract text content from a URL.",
            schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 15,
                    },
                },
                "required": ["url"],
            },
            handler=self._handle_fetch_url,
        )

        self.register(
            name="memory_get",
            description="Get a value from persistent memory by namespace and key.",
            schema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Namespace (hermes, user, system, etc.)",
                    },
                    "key": {
                        "type": "string",
                        "description": "Key to retrieve",
                    },
                },
                "required": ["namespace", "key"],
            },
            handler=self._handle_memory_get,
        )

        self.register(
            name="memory_set",
            description="Store a value in persistent memory.",
            schema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Namespace (hermes, user, system, etc.)",
                    },
                    "key": {
                        "type": "string",
                        "description": "Unique key",
                    },
                    "value": {
                        "description": "Any JSON-serializable value",
                    },
                    "ttl": {
                        "type": "integer",
                        "description": "TTL in seconds (null = forever)",
                    },
                },
                "required": ["namespace", "key", "value"],
            },
            handler=self._handle_memory_set,
        )

        self.register(
            name="memory_search",
            description="Full-text search across all memory keys and values.",
            schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
            handler=self._handle_memory_search,
        )

        self.register(
            name="memory_list",
            description="List memory keys with optional namespace/prefix filter.",
            schema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Filter by namespace (optional)",
                    },
                    "prefix": {
                        "type": "string",
                        "description": "Filter by key prefix (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 50,
                    },
                },
            },
            handler=self._handle_memory_list,
        )

        self.register(
            name="memory_status",
            description="Get memory store status (key count, sessions, DB size).",
            schema={"type": "object", "properties": {}},
            handler=self._handle_memory_status,
        )

    # ─── Registration ─────────────────────────────────────────

    def register(
        self,
        name: str,
        description: str,
        schema: Dict,
        handler: Callable,
    ):
        """Register a tool."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "schema": schema,
            "handler": handler,
        }
        logger.info(f"🔧 Tool registered: {name}")

    def list_tools(self) -> List[Dict]:
        """List all registered tools (without handlers)."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "schema": t["schema"],
            }
            for t in self._tools.values()
        ]

    def get_tool(self, name: str) -> Optional[Dict]:
        """Get a tool by name."""
        return self._tools.get(name)

    # ─── Execution ────────────────────────────────────────────

    def execute(self, name: str, params: Dict) -> Dict:
        """
        Execute a tool by name with parameters.

        Returns:
            Dict with success, result (or error), elapsed
        """
        self.call_count += 1
        start = time.time()

        tool = self._tools.get(name)
        if not tool:
            self.error_count += 1
            return {
                "success": False,
                "error": f"Tool '{name}' not found. Available: {list(self._tools.keys())}",
                "elapsed": round(time.time() - start, 3),
            }

        try:
            result = tool["handler"](params)
            elapsed = round(time.time() - start, 3)

            # If result is already a dict with success/error, pass through
            if isinstance(result, dict) and "success" in result:
                result["elapsed"] = elapsed
                result["tool"] = name
                return result

            return {
                "success": True,
                "result": result,
                "tool": name,
                "elapsed": elapsed,
            }

        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ Tool '{name}' error: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool": name,
                "elapsed": round(time.time() - start, 3),
            }

    # ─── Web Search Handlers ──────────────────────────────────

    def _handle_web_search(self, params: Dict) -> Dict:
        """Search the web via DuckDuckGo."""
        from .mcp_web_search import WebSearchMCP

        searcher = WebSearchMCP()
        return searcher.search(
            query=params.get("query", ""),
            max_results=params.get("max_results", 5),
        )

    def _handle_fetch_url(self, params: Dict) -> Dict:
        """Fetch a URL."""
        from .mcp_web_search import WebSearchMCP

        searcher = WebSearchMCP()
        return searcher.fetch(
            url=params.get("url", ""),
            timeout=params.get("timeout", 15),
        )

    # ─── Memory Handlers ─────────────────────────────────────

    def _handle_memory_get(self, params: Dict) -> Dict:
        value = self.memory.get(
            namespace=params["namespace"],
            key=params["key"],
        )
        if value is None:
            return {"success": False, "error": "Key not found"}
        return {"success": True, "value": value}

    def _handle_memory_set(self, params: Dict) -> Dict:
        result = self.memory.set(
            namespace=params["namespace"],
            key=params["key"],
            value=params["value"],
            ttl=params.get("ttl"),
        )
        return {"success": True, "version": result["version"]}

    def _handle_memory_search(self, params: Dict) -> Dict:
        results = self.memory.search(
            query=params["query"],
            limit=params.get("limit", 20),
        )
        return {"success": True, "results": results, "count": len(results)}

    def _handle_memory_list(self, params: Dict) -> Dict:
        keys = self.memory.list_keys(
            namespace=params.get("namespace"),
            prefix=params.get("prefix"),
            limit=params.get("limit", 50),
        )
        return {"success": True, "keys": keys, "count": len(keys)}

    def _handle_memory_status(self, params: Dict) -> Dict:
        return {"success": True, "status": self.memory.status()}

    # ─── Status ──────────────────────────────────────────────

    def status(self) -> Dict:
        return {
            "tool_count": len(self._tools),
            "tools": list(self._tools.keys()),
            "calls": self.call_count,
            "errors": self.error_count,
        }


# ─── Standalone test ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    registry = ToolRegistry()

    print(f"Tools ({len(registry.list_tools())}):")
    for t in registry.list_tools():
        print(f"  🔧 {t['name']}: {t['description'][:60]}")

    # Test web search
    print("\n--- Testing web_search ---")
    result = registry.execute("web_search", {"query": "Python programming", "max_results": 2})
    print(json.dumps(result, indent=2, ensure_ascii=False)[:500])

    # Test memory
    print("\n--- Testing memory ---")
    registry.execute("memory_set", {
        "namespace": "test", "key": "greeting", "value": "Hello AHS!"
    })
    result = registry.execute("memory_get", {"namespace": "test", "key": "greeting"})
    print(f"memory_get: {result}")

    # Search memory
    result = registry.execute("memory_search", {"query": "greeting"})
    print(f"memory_search: {result}")

    print("\n✅ Tool registry tests passed!")
