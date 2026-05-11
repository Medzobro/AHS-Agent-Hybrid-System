#!/usr/bin/env python3
"""
AHS - Cache System
===================
نظام الStore المؤقت — للنتائج المتكررة.

Features:
  - In-memory storage
  - Expiration (TTL)
  - LRU Eviction
  - Statistics
  - Serialization
"""

import json
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    """Cache entry"""
    key: str
    value: Any
    ttl: float = 300.0  # 5 minutes by default
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0

    @property
    def expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return time.time() - self.created_at > self.ttl

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "ttl": self.ttl,
            "age": round(self.age, 1),
            "expired": self.expired,
            "access_count": self.access_count,
            "size_bytes": self.size_bytes,
        }


class Cache:
    """
    In-memory cache with LRU eviction.
    """

    def __init__(self, max_size: int = 200, default_ttl: float = 300.0,
                 max_memory_mb: float = 100.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.max_memory = max_memory_mb * 1024 * 1024
        self._data: dict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = {
            "hits": 0, "misses": 0, "evictions": 0,
            "expirations": 0, "sets": 0,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get value"""
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                self._stats["misses"] += 1
                return default

            if entry.expired:
                del self._data[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return default

            entry.access_count += 1
            self._data.move_to_end(key)
            self._stats["hits"] += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """Store value"""
        with self._lock:
            # حساب الحجم
            try:
                size = len(json.dumps(value))
            except Exception:
                size = len(str(value))

            # إخلاء مساحة إذا لزم
            while len(self._data) >= self.max_size:
                self._evict_one()

            # إخلاء مساحة حسب الذاكرة
            total_size = sum(e.size_bytes for e in self._data.values())
            while total_size + size > self.max_memory and self._data:
                self._evict_one()
                total_size = sum(e.size_bytes for e in self._data.values())

            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl if ttl is not None else self.default_ttl,
                size_bytes=size,
            )
            self._data[key] = entry
            self._data.move_to_end(key)
            self._stats["sets"] += 1
            return True

    def delete(self, key: str) -> bool:
        """Delete key"""
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
        return False

    def clear(self):
        """Clear cache"""
        with self._lock:
            self._data.clear()
            self._stats = {k: 0 for k in self._stats}

    def exists(self, key: str) -> bool:
        """Does key exist?"""
        with self._lock:
            entry = self._data.get(key)
            if entry and not entry.expired:
                return True
        return False

    def get_or_set(self, key: str, factory: Callable,
                   ttl: float | None = None) -> Any:
        """Get or create value"""
        value = self.get(key)
        if value is not None:
            return value
        value = factory()
        self.set(key, value, ttl)
        return value

    def _evict_one(self):
        """Evict one entry (LRU)"""
        if not self._data:
            return
        # أقدم مدخل
        self._data.popitem(last=False)
        self._stats["evictions"] += 1

    def cleanup(self):
        """Cleanup expired entries"""
        with self._lock:
            expired = [k for k, v in self._data.items() if v.expired]
            for k in expired:
                del self._data[k]
                self._stats["expirations"] += 1
            return len(expired)

    def size(self) -> int:
        return len(self._data)

    def keys(self) -> list[str]:
        with self._lock:
            return [k for k, v in self._data.items() if not v.expired]

    def get_stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

        with self._lock:
            entries_info = [
                e.to_dict() for e in self._data.values()
            ]

        return {
            **self._stats,
            "size": len(self._data),
            "max_size": self.max_size,
            "hit_rate": round(hit_rate, 1),
            "total_memory_mb": round(
                sum(e.size_bytes for e in self._data.values()) / 1024 / 1024, 2
            ),
            "max_memory_mb": round(self.max_memory / 1024 / 1024, 1),
            "entries": entries_info[:10],
        }


# ====== كاش مخصص ======

class HermesCache(Cache):
    """Cache specific to Hermes responses"""
    def __init__(self):
        super().__init__(max_size=100, default_ttl=600)

    def get_or_query(self, task: str, hermes_bridge) -> str:
        """Get from cache or query Hermes"""
        cache_key = f"hermes:{hash(task)}"
        cached = self.get(cache_key)
        if cached:
            return cached

        result = hermes_bridge.send_task(task)
        response = str(result.get("response", {}).get("content", ""))
        if response:
            self.set(cache_key, response, ttl=300)
        return response


class ToolResultCache(Cache):
    """Tool result cache"""
    def __init__(self):
        super().__init__(max_size=500, default_ttl=60)

    def get_or_call(self, tool_name: str, *args, tool_registry, **kwargs) -> Any:
        cache_key = f"tool:{tool_name}:{hash(str(args) + str(kwargs))}"
        cached = self.get(cache_key)
        if cached:
            return cached

        result = tool_registry.call(tool_name, *args, **kwargs)
        if result.success:
            self.set(cache_key, result.data, ttl=30)
        return result.data


# ====== الـ Cache Manager الشامل ======

class CacheManager:
    """Central cache manager"""
    def __init__(self):
        self.caches: dict[str, Cache] = {}
        self.default = Cache()

    def register(self, name: str, cache: Cache):
        self.caches[name] = cache

    def get(self, name: str) -> Cache | None:
        return self.caches.get(name)

    def get_all_stats(self) -> dict:
        return {
            name: cache.get_stats()
            for name, cache in self.caches.items()
        }

    def cleanup_all(self):
        total = 0
        for cache in self.caches.values():
            total += cache.cleanup()
        total += self.default.cleanup()
        return total


if __name__ == "__main__":
    cache = Cache(max_size=10, default_ttl=60)

    # Store
    cache.set("test1", {"value": 42})
    cache.set("test2", "hello AHS")

    # Retrieve
    print(f"test1: {cache.get('test1')}")
    print(f"test2: {cache.get('test2')}")
    print(f"missing: {cache.get('missing', 'NOT_FOUND')}")

    # إحصائيات
    print(f"\n📊 Stats: {cache.get_stats()}")

    # LRU
    for i in range(15):
        cache.set(f"key_{i}", i)

    print(f"\nSize after 15 (max=10): {cache.size()}")
    print(f"Evictions: {cache._stats['evictions']}")

    print("\n✅ Cache ready")
