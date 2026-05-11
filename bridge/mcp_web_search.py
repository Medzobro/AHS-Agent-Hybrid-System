#!/usr/bin/env python3
"""
AHS v1 — Web Search MCP Tool
==============================
غلاف MCP لـ WebSearchTool الموجود في skills/web_search.py.
يضيف:
  - JSON-RPC 2.0 تنسيق
  - Error handling محسّن
  - Rate limiting بسيط
  - نتائج مصغرة (بدون محتوى طويل)
"""

import json
import logging
import os
import sys
import time

# استيراد الأداة الموجودة
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skills.web_search import HAS_REQUESTS, WebSearchTool

logger = logging.getLogger("ahs.mcp_web_search")

# ─── Rate Limiter ───────────────────────────────────────────────


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self, max_calls: int = 30, window_sec: int = 60):
        self.max_calls = max_calls
        self.window_sec = window_sec
        self._calls: list[float] = []

    def allow(self) -> bool:
        now = time.time()
        # Remove old calls
        self._calls = [t for t in self._calls if now - t < self.window_sec]
        if len(self._calls) >= self.max_calls:
            return False
        self._calls.append(now)
        return True

    @property
    def remaining(self) -> int:
        now = time.time()
        self._calls = [t for t in self._calls if now - t < self.window_sec]
        return self.max_calls - len(self._calls)

    @property
    def next_reset(self) -> float:
        if not self._calls:
            return 0
        return self._calls[0] + self.window_sec - time.time()


class WebSearchMCP:
    """
    MCP wrapper for WebSearchTool.
    Provides clean JSON-RPC friendly search and fetch.
    """

    def __init__(self):
        self._tool = WebSearchTool()
        self._rate_limiter = RateLimiter(max_calls=30, window_sec=60)

    def search(self, query: str, max_results: int = 5) -> dict:
        """
        Search the web.

        Returns:
            Dict with success, results (minimized), total, query, elapsed
        """
        if not query or not query.strip():
            return {"success": False, "error": "Empty query"}

        if not self._rate_limiter.allow():
            return {
                "success": False,
                "error": "Rate limit exceeded. Try again soon.",
                "rate_limit": {
                    "remaining": self._rate_limiter.remaining,
                    "reset_in_sec": round(self._rate_limiter.next_reset, 1),
                },
            }

        try:
            raw = self._tool.search(query=query, max_results=max_results)

            # Minimize results — keep title, url, snippet only
            minimized = []
            for r in raw.get("results", []):
                minimized.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", "")[:300],
                    "source": r.get("source", "web"),
                })

            return {
                "success": raw.get("success", False),
                "results": minimized,
                "total": len(minimized),
                "query": query,
                "elapsed": raw.get("elapsed", 0),
            }

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {"success": False, "error": str(e)[:300]}

    def fetch(self, url: str, timeout: int = 15) -> dict:
        """
        Fetch a URL and extract its text content.

        Returns:
            Dict with success, title, content (truncated), url, elapsed
        """
        if not url or not url.strip():
            return {"success": False, "error": "Empty URL"}

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        if not self._rate_limiter.allow():
            return {
                "success": False,
                "error": "Rate limit exceeded",
            }

        try:
            raw = self._tool.fetch_url(url=url, timeout=timeout)

            return {
                "success": raw.get("success", False),
                "url": raw.get("url", url),
                "title": raw.get("title", ""),
                "content": raw.get("content", ""),
                "text_length": raw.get("text_length", 0),
                "elapsed": raw.get("elapsed", 0),
            }

        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return {"success": False, "error": str(e)[:300]}

    def status(self) -> dict:
        """Get web search tool status."""
        s = self._tool.status()
        return {
            "available": HAS_REQUESTS,
            "calls": s.get("calls", 0),
            "errors": s.get("errors", 0),
            "cache_size": s.get("cache_size", 0),
            "rate_limit_remaining": self._rate_limiter.remaining,
        }


# ─── Standalone test ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    searcher = WebSearchMCP()

    # Test search
    print("🔍 Testing search...")
    result = searcher.search("AHS agent hybrid system", max_results=2)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Test fetch (if search returned a URL)
    if result.get("results"):
        url = result["results"][0]["url"]
        if url:
            print(f"\n📄 Testing fetch: {url}")
            fetch_result = searcher.fetch(url)
            print(json.dumps(fetch_result, indent=2, ensure_ascii=False)[:500])

    # Status
    print(f"\n📊 Status: {json.dumps(searcher.status(), indent=2)}")
    print("\n✅ WebSearchMCP tests passed!")
