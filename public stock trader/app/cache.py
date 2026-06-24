"""SQLite-backed response cache.

Two jobs: (1) stay under free-tier rate limits by not re-fetching the same data,
and (2) make runs reproducible — the cache key includes the date, so the same
ticker analysed on the same day reuses the same upstream payloads.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from config import CACHE_TTL_SECONDS

_DB_PATH = Path(__file__).resolve().parent.parent / "cache.db"
_conn: Optional[sqlite3.Connection] = None


def _connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS cache ("
            "  key TEXT PRIMARY KEY,"
            "  value TEXT NOT NULL,"
            "  created_at REAL NOT NULL"
            ")"
        )
        _conn.commit()
    return _conn


def get(key: str) -> Optional[Any]:
    row = _connection().execute(
        "SELECT value, created_at FROM cache WHERE key = ?", (key,)
    ).fetchone()
    if row is None:
        return None
    value, created_at = row
    if time.time() - created_at > CACHE_TTL_SECONDS:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def set(key: str, value: Any) -> None:
    _connection().execute(
        "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
        (key, json.dumps(value), time.time()),
    )
    _connection().commit()
