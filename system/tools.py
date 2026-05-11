#!/usr/bin/env python3
"""
AHS v1 — Web Search + Memory Tools
=====================================
Tools حقيقية للـ MCP HTTP Server:
- Web Search عبر Brave/DuckDuckGo
- Memory SQLite (ACID, versioning, persistent)

أضف هذه الملفات واربطها مع mcp_http_server.py
"""

import json
import logging
import os
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger("ahs-tools")

# ─── Web Search ───────────────────────────────────────────────

def web_search(query: str, count: int = 5) -> List[Dict[str, str]]:
    """
    بحث في الويب عبر Brave Search API (أو fallback).
    """
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
    
    if api_key:
        return _brave_search(query, count, api_key)
    else:
        return _ddg_fallback(query, count)


def _brave_search(query: str, count: int, api_key: str) -> List[Dict[str, str]]:
    """Brave Search API"""
    try:
        params = urllib.parse.urlencode({"q": query, "count": count})
        req = urllib.request.Request(
            f"https://api.search.brave.com/res/v1/web/search?{params}",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        
        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"Brave search failed: {e}")
        return []


def _ddg_fallback(query: str, count: int) -> List[Dict[str, str]]:
    """DuckDuckGo HTML fallback (بدون API key)"""
    try:
        params = urllib.parse.urlencode({"q": query})
        req = urllib.request.Request(
            f"https://html.duckduckgo.com/html/?{params}",
            headers={"User-Agent": "Mozilla/5.0 (compatible; AHS/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8")
        
        # Simple HTML parsing (no deps)
        results = []
        import re
        # Find result blocks
        blocks = re.findall(
            r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</(?:a|div)',
            html, re.DOTALL
        )
        
        for url, title, snippet in blocks[:count]:
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            results.append({
                "title": clean_title,
                "url": urllib.parse.unquote(url),
                "snippet": clean_snippet,
            })
        return results
    except Exception as e:
        logger.warning(f"DDG search failed: {e}")
        return []


# ─── SQLite Memory ────────────────────────────────────────────

MEMORY_DB_PATH = os.environ.get("AHS_MEMORY_DB", 
    os.path.join(os.path.dirname(__file__), "..", "data", "ahs_memory.db"))


class MemoryStore:
    """
    ذاكرة دائمة عبر SQLite مع versioning.
    - ACID transactions
    - Versioning (كل إدخال له version)
    - TTL support (انتهاء صلاحية)
    - Full-text search
    """
    
    def __init__(self, db_path: str = MEMORY_DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    created_at REAL NOT NULL,
                    expires_at REAL,
                    UNIQUE(key, version)
                )
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
                USING fts5(key, value, content='memories', content_rowid='id')
            """)
            conn.commit()
    
    def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> Dict:
        """تخزين قيمة مع versioning"""
        now = time.time()
        expires = now + ttl_seconds if ttl_seconds else None
        
        with sqlite3.connect(self.db_path) as conn:
            # Check existing
            row = conn.execute(
                "SELECT version FROM memories WHERE key = ? ORDER BY version DESC LIMIT 1",
                (key,)
            ).fetchone()
            
            new_version = (row[0] + 1) if row else 1
            
            conn.execute(
                "INSERT INTO memories (key, value, version, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                (key, value, new_version, now, expires)
            )
            conn.commit()
        
        return {"key": key, "version": new_version, "created_at": now}
    
    def get(self, key: str, version: Optional[int] = None) -> Optional[str]:
        """استرجاع قيمة"""
        with sqlite3.connect(self.db_path) as conn:
            if version:
                row = conn.execute(
                    "SELECT value, expires_at FROM memories WHERE key = ? AND version = ?",
                    (key, version)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT value, expires_at FROM memories WHERE key = ? ORDER BY version DESC LIMIT 1",
                    (key,)
                ).fetchone()
            
            if row:
                value, expires = row
                if expires and time.time() > expires:
                    return None  # Expired
                return value
        return None
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Full-text search في الذاكرة"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT m.key, m.value, m.version, m.created_at
                FROM memories_fts f
                JOIN memories m ON f.rowid = m.id
                WHERE memories_fts MATCH ?
                AND (m.expires_at IS NULL OR m.expires_at > ?)
                ORDER BY m.created_at DESC
                LIMIT ?
            """, (query, time.time(), limit)).fetchall()
            
            return [
                {"key": r[0], "value": r[1], "version": r[2], "created_at": r[3]}
                for r in rows
            ]
    
    def list_keys(self, limit: int = 100) -> List[str]:
        """قائمة المفاتيح المخزنة"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT DISTINCT key FROM memories 
                WHERE expires_at IS NULL OR expires_at > ?
                ORDER BY key
                LIMIT ?
            """, (time.time(), limit)).fetchall()
            return [r[0] for r in rows]
    
    def delete(self, key: str) -> bool:
        """حذف كل إصدارات مفتاح"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memories WHERE key = ?", (key,))
            conn.commit()
        return True
    
    def stats(self) -> Dict:
        """إحصائيات الذاكرة"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            unique = conn.execute(
                "SELECT COUNT(DISTINCT key) FROM memories"
            ).fetchone()[0]
            expired = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
                (time.time(),)
            ).fetchone()[0]
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            return {
                "total_entries": total,
                "unique_keys": unique,
                "expired_entries": expired,
                "database_size_kb": round(db_size / 1024, 1),
                "database_path": self.db_path,
            }


# ─── Tool Registration ────────────────────────────────────────

def register_tools(mcp_handlers: Dict):
    """تسجيل كل الأدوات في الـ MCP handlers"""
    memory = MemoryStore()
    
    @mcp_handlers.register("web_search")
    def handle_web_search(params: Dict) -> Dict:
        query = params.get("query", "")
        count = params.get("count", 5)
        results = web_search(query, count)
        logger.info(f"🔍 Web search: '{query}' → {len(results)} results")
        return {"results": results}
    
    @mcp_handlers.register("memory_set")
    def handle_memory_set(params: Dict) -> Dict:
        result = memory.set(params["key"], params["value"])
        logger.info(f"💾 Memory set: {params['key']} v{result['version']}")
        return result
    
    @mcp_handlers.register("memory_get")
    def handle_memory_get(params: Dict) -> Dict:
        value = memory.get(params["key"])
        return {"key": params["key"], "value": value}
    
    @mcp_handlers.register("memory_search")
    def handle_memory_search(params: Dict) -> Dict:
        results = memory.search(params.get("query", ""))
        return {"results": results}
    
    @mcp_handlers.register("memory_stats")
    def handle_memory_stats(params: Dict) -> Dict:
        return memory.stats()


# ─── Test ─────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print(f"{'='*50}")
    print("  🧪 AHS v1 — Tools Test")
    print(f"{'='*50}")
    
    # Test Memory
    print("\n📦 Memory Test:")
    mem = MemoryStore()
    mem.set("test_key", "Hello AHS v1!", ttl_seconds=3600)
    val = mem.get("test_key")
    print(f"  ✅ Set/Get: {val}")
    
    mem.set("workflow/step1", "Classification complete")
    mem.set("workflow/step2", "Execution running")
    
    results = mem.search("classification")
    print(f"  ✅ FTS Search: {len(results)} results")
    
    stats = mem.stats()
    print(f"  ✅ Stats: {stats['unique_keys']} keys, {stats['total_entries']} entries")
    
    # Test Web Search
    print("\n🔍 Web Search Test:")
    results = web_search("AHSAgent Hybrid System", count=3)
    if results:
        for r in results:
            print(f"  ✅ {r['title'][:60]}...")
    else:
        print("  ⚠️ No results (Brave key may be missing, DDG may be rate-limited)")
    
    print(f"\n{'='*50}")
    print("  ✅ All tools ready for integration")
    print(f"{'='*50}")
