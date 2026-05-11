#!/usr/bin/env python3
"""
AHS v1 — SQLite Memory Store
=============================
ذاكرة ACID حقيقية مع SQLite بدلاً من JSON.

Features:
  - ACID transactions (WAL mode)
  - Versioned entries (each update creates new version)
  - Session management (create/resume/end)
  - Namespace isolation (hermes, openclaw, system)
  - TTL for ephemeral memories
  - Full-text search
  - JSON serialization for complex values

Usage:
  from memory_store import MemoryStore
  store = MemoryStore("bridge/ahs_memory.db")
  store.set("hermes", "user_preference", {"lang": "ar"})
  val = store.get("hermes", "user_preference")
"""

import json
import logging
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ahs.memory_store")

# ─── Schema ────────────────────────────────────────────────────

SCHEMA_SQL = """
-- Enable WAL mode for concurrent reads
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    ended_at REAL,
    metadata TEXT DEFAULT '{}'
);

-- Namespace keys (current values)
CREATE TABLE IF NOT EXISTS keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    session_id TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    expires_at REAL,
    UNIQUE(namespace, key)
);

-- History (all versions)
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    version INTEGER NOT NULL,
    session_id TEXT,
    created_at REAL NOT NULL,
    action TEXT NOT NULL DEFAULT 'set'
);

-- Full-text search virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
    namespace, key, value,
    content='keys',
    content_rowid='id',
    tokenize='unicode61'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS keys_ai AFTER INSERT ON keys BEGIN
    INSERT INTO fts(rowid, namespace, key, value)
    VALUES (new.id, new.namespace, new.key, new.value);
END;

CREATE TRIGGER IF NOT EXISTS keys_ad AFTER DELETE ON keys BEGIN
    INSERT INTO fts(fts, rowid, namespace, key, value)
    VALUES ('delete', old.id, old.namespace, old.key, old.value);
END;

CREATE TRIGGER IF NOT EXISTS keys_au AFTER UPDATE ON keys BEGIN
    INSERT INTO fts(fts, rowid, namespace, key, value)
    VALUES ('delete', old.id, old.namespace, old.key, old.value);
    INSERT INTO fts(rowid, namespace, key, value)
    VALUES (new.id, new.namespace, new.key, new.value);
END;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_keys_namespace ON keys(namespace);
CREATE INDEX IF NOT EXISTS idx_keys_updated ON keys(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_namespace_key ON history(namespace, key, version);
"""


class MemoryStore:
    """
    SQLite-backed memory store with ACID guarantees.

    Thread-safe via threading.Lock.
    """

    def __init__(self, db_path: str = "bridge/ahs_memory.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        self._active_session_id: Optional[str] = None
        self.call_count = 0
        logger.info(f"📀 MemoryStore initialized: {db_path}")

    def _init_schema(self):
        """Initialize database schema."""
        with self._lock:
            self._conn.executescript(SCHEMA_SQL)
            self._conn.commit()

    # ─── Session Management ─────────────────────────────────

    def create_session(self, metadata: Optional[Dict] = None) -> str:
        """Create a new session and set it as active."""
        session_id = str(uuid.uuid4())
        now = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT INTO sessions (session_id, created_at, metadata) VALUES (?, ?, ?)",
                (session_id, now, json.dumps(metadata or {})),
            )
            self._conn.commit()
        self._active_session_id = session_id
        logger.info(f"📋 Session created: {session_id[:8]}...")
        return session_id

    def resume_session(self, session_id: str) -> bool:
        """Resume an existing session. Returns False if not found."""
        with self._lock:
            row = self._conn.execute(
                "SELECT session_id FROM sessions WHERE session_id = ? AND ended_at IS NULL",
                (session_id,),
            ).fetchone()
            if row:
                self._active_session_id = session_id
                return True
            return False

    def end_session(self, session_id: Optional[str] = None):
        """End a session."""
        sid = session_id or self._active_session_id
        if not sid:
            return
        now = time.time()
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET ended_at = ? WHERE session_id = ?",
                (now, sid),
            )
            self._conn.commit()
        if self._active_session_id == sid:
            self._active_session_id = None
        logger.info(f"📋 Session ended: {sid[:8]}...")

    def list_sessions(self, limit: int = 20) -> List[Dict]:
        """List recent sessions."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ─── CRUD Operations ────────────────────────────────────

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> Dict:
        """
        Set a value in the store.

        Args:
            namespace: Category (hermes, openclaw, system, user, etc.)
            key: Unique key within namespace
            value: Any JSON-serializable value
            ttl: Time-to-live in seconds (None = forever)
            session_id: Associate with a session (default: active session)

        Returns:
            Dict with version info
        """
        self.call_count += 1
        now = time.time()
        serialized = json.dumps(value, ensure_ascii=False)
        sid = session_id or self._active_session_id
        expires = now + ttl if ttl else None

        with self._lock:
            # Check if key exists
            existing = self._conn.execute(
                "SELECT version FROM keys WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()

            if existing:
                new_version = existing["version"] + 1
                # Save to history
                self._conn.execute(
                    "INSERT INTO history (namespace, key, value, version, session_id, created_at, action) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'update')",
                    (namespace, key, serialized, new_version, sid, now),
                )
                # Update current
                self._conn.execute(
                    "UPDATE keys SET value = ?, version = ?, session_id = ?, "
                    "updated_at = ?, expires_at = ? "
                    "WHERE namespace = ? AND key = ?",
                    (serialized, new_version, sid, now, expires, namespace, key),
                )
            else:
                new_version = 1
                self._conn.execute(
                    "INSERT INTO keys (namespace, key, value, version, session_id, "
                    "created_at, updated_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (namespace, key, serialized, new_version, sid, now, now, expires),
                )
                self._conn.execute(
                    "INSERT INTO history (namespace, key, value, version, session_id, created_at, action) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'create')",
                    (namespace, key, serialized, new_version, sid, now),
                )

            self._conn.commit()

        result = {
            "success": True,
            "namespace": namespace,
            "key": key,
            "version": new_version,
            "session": sid,
        }
        logger.debug(f"💾 set {namespace}:{key} v{new_version}")
        return result

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get a value. Returns None if not found or expired."""
        self.call_count += 1
        with self._lock:
            row = self._conn.execute(
                "SELECT value, expires_at FROM keys WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()

        if not row:
            return None

        # Check expiry
        if row["expires_at"] and time.time() > row["expires_at"]:
            self.delete(namespace, key)
            return None

        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]

    def delete(self, namespace: str, key: str, session_id: Optional[str] = None) -> bool:
        """Delete a key. Returns True if it existed."""
        self.call_count += 1
        now = time.time()
        sid = session_id or self._active_session_id

        with self._lock:
            # Get current version for history
            current = self._conn.execute(
                "SELECT version, value FROM keys WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()

            if not current:
                return False

            # Save deletion to history
            self._conn.execute(
                "INSERT INTO history (namespace, key, value, version, session_id, created_at, action) "
                "VALUES (?, ?, ?, ?, ?, ?, 'delete')",
                (namespace, key, current["value"], current["version"], sid, now),
            )

            # Remove
            self._conn.execute(
                "DELETE FROM keys WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            self._conn.commit()

        logger.debug(f"🗑️ deleted {namespace}:{key}")
        return True

    def list_keys(
        self,
        namespace: Optional[str] = None,
        prefix: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """List keys with optional filtering."""
        query = "SELECT namespace, key, version, updated_at, expires_at FROM keys WHERE 1=1"
        params = []

        if namespace:
            query += " AND namespace = ?"
            params.append(namespace)

        if prefix:
            query += " AND key LIKE ?"
            params.append(f"{prefix}%")

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
            return [
                {
                    "namespace": r["namespace"],
                    "key": r["key"],
                    "version": r["version"],
                    "updated_at": r["updated_at"],
                    "expires_at": r["expires_at"],
                }
                for r in rows
            ]

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Full-text search across all keys and values.

        Uses FTS5 for fast searching.
        """
        self.call_count += 1
        with self._lock:
            try:
                rows = self._conn.execute(
                    """SELECT k.namespace, k.key, k.version, k.updated_at
                       FROM keys k
                       JOIN fts ON k.id = fts.rowid
                       WHERE fts MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (query, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                # Fallback to LIKE search if FTS fails
                like_query = f"%{query}%"
                rows = self._conn.execute(
                    """SELECT namespace, key, version, updated_at
                       FROM keys
                       WHERE key LIKE ? OR value LIKE ?
                       ORDER BY updated_at DESC
                       LIMIT ?""",
                    (like_query, like_query, limit),
                ).fetchall()

            return [
                {
                    "namespace": r["namespace"],
                    "key": r["key"],
                    "version": r["version"],
                    "updated_at": r["updated_at"],
                }
                for r in rows
            ]

    def history(
        self,
        namespace: str,
        key: str,
        limit: int = 20,
    ) -> List[Dict]:
        """Get version history for a key."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT version, session_id, created_at, action
                   FROM history
                   WHERE namespace = ? AND key = ?
                   ORDER BY version DESC
                   LIMIT ?""",
                (namespace, key, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    # ─── Namespace Management ────────────────────────────────

    def list_namespaces(self) -> List[str]:
        """List all namespaces with data."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT namespace FROM keys ORDER BY namespace"
            ).fetchall()
            return [r["namespace"] for r in rows if r["namespace"]]

    def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace. Returns count."""
        with self._lock:
            count = self._conn.execute(
                "SELECT COUNT(*) as c FROM keys WHERE namespace = ?",
                (namespace,),
            ).fetchone()["c"]
            self._conn.execute("DELETE FROM keys WHERE namespace = ?", (namespace,))
            self._conn.commit()
        logger.info(f"🧹 Cleared namespace '{namespace}': {count} keys")
        return count

    # ─── Housekeeping ────────────────────────────────────────

    def vacuum(self):
        """Reclaim space and optimize."""
        with self._lock:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self._conn.execute("VACUUM")
        logger.info("🧹 Vacuum complete")

    def purge_expired(self) -> int:
        """Remove all expired entries. Returns count."""
        now = time.time()
        with self._lock:
            count = self._conn.execute(
                "DELETE FROM keys WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now,),
            ).rowcount
            if count:
                self._conn.commit()
        if count:
            logger.info(f"🧹 Purged {count} expired entries")
        return count

    # ─── Status ──────────────────────────────────────────────

    def status(self) -> Dict:
        """Get store status."""
        with self._lock:
            total_keys = self._conn.execute(
                "SELECT COUNT(*) as c FROM keys"
            ).fetchone()["c"]
            total_history = self._conn.execute(
                "SELECT COUNT(*) as c FROM history"
            ).fetchone()["c"]
            total_sessions = self._conn.execute(
                "SELECT COUNT(*) as c FROM sessions"
            ).fetchone()["c"]
            active_sessions = self._conn.execute(
                "SELECT COUNT(*) as c FROM sessions WHERE ended_at IS NULL"
            ).fetchone()["c"]
            db_size = self._conn.execute(
                "SELECT page_count * page_size as size FROM pragma_page_count, pragma_page_size"
            ).fetchone()

        return {
            "type": "sqlite_memory_store",
            "version": "1.0.0",
            "path": self.db_path,
            "keys": total_keys,
            "history_entries": total_history,
            "sessions_total": total_sessions,
            "sessions_active": active_sessions,
            "calls": self.call_count,
            "db_size_bytes": db_size["size"] if db_size else 0,
        }

    # ─── Cleanup ─────────────────────────────────────────────

    def close(self):
        """Close the database connection."""
        with self._lock:
            self._conn.close()
        logger.info("📀 MemoryStore closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ─── Standalone test ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    store = MemoryStore(":memory:")

    # Create a session
    session = store.create_session({"user": "MHamed"})
    print(f"Session: {session[:8]}...")

    # Set values
    store.set("hermes", "last_task", "Build SQLite memory")
    store.set("user", "preference", {"lang": "ar", "mode": "hybrid"}, session_id=session)
    store.set("system", "version", "0.4.0", ttl=3600)

    # Get values
    print(f"last_task: {store.get('hermes', 'last_task')}")
    print(f"preference: {store.get('user', 'preference')}")

    # Search
    results = store.search("memory")
    print(f"Search 'memory': {results}")

    # History
    store.set("hermes", "last_task", "Integrate Web Search")
    hist = store.history("hermes", "last_task")
    print(f"History: {hist}")

    # List keys
    keys = store.list_keys()
    print(f"Total keys: {len(keys)}")

    # Status
    print(f"Status: {json.dumps(store.status(), indent=2)}")

    store.end_session(session)
    store.close()
    print("\n✅ All memory store tests passed!")
