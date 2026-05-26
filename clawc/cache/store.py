from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .dedup import make_ref_token, sha256_hex

SCHEMA_VERSION = 1

_PRAGMAS = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;
"""

_DDL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    started_at   INTEGER NOT NULL DEFAULT (unixepoch()),
    project_cwd  TEXT,
    model        TEXT
);

CREATE TABLE IF NOT EXISTS cache_entries (
    content_hash   TEXT PRIMARY KEY,
    original_len   INTEGER NOT NULL,
    compressed     TEXT NOT NULL,
    compressed_len INTEGER NOT NULL,
    ref_token      TEXT NOT NULL,
    tool_name      TEXT NOT NULL,
    simhash        INTEGER,
    created_at     INTEGER NOT NULL DEFAULT (unixepoch()),
    last_seen_at   INTEGER NOT NULL DEFAULT (unixepoch()),
    hit_count      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS compressions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id        TEXT NOT NULL,
    tool_name         TEXT NOT NULL,
    tool_use_id       TEXT,
    content_hash      TEXT,
    original_tokens   INTEGER NOT NULL,
    compressed_tokens INTEGER NOT NULL,
    stages_applied    TEXT NOT NULL DEFAULT '[]',
    was_cache_hit     INTEGER NOT NULL DEFAULT 0,
    was_safe_mode     INTEGER NOT NULL DEFAULT 0,
    created_at        INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS deltas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    base_hash    TEXT NOT NULL,
    new_hash     TEXT NOT NULL,
    simhash_dist INTEGER NOT NULL,
    patch        TEXT NOT NULL,
    created_at   INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE VIRTUAL TABLE IF NOT EXISTS cache_fts USING fts5(
    content_hash UNINDEXED,
    compressed,
    content='cache_entries',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS cache_entries_ai AFTER INSERT ON cache_entries BEGIN
    INSERT INTO cache_fts(rowid, content_hash, compressed)
    VALUES (new.rowid, new.content_hash, new.compressed);
END;

CREATE TRIGGER IF NOT EXISTS cache_entries_ad AFTER DELETE ON cache_entries BEGIN
    INSERT INTO cache_fts(cache_fts, rowid, content_hash, compressed)
    VALUES ('delete', old.rowid, old.content_hash, old.compressed);
END;
"""


def _default_db_path() -> Path:
    env_path = os.environ.get("CLAWC_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path.home() / ".clawc" / "sessions.db"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_PRAGMAS)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < SCHEMA_VERSION:
        conn.executescript(_DDL)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()


class CacheStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @classmethod
    def open(cls, db_path: Path | None = None) -> "CacheStore":
        return cls(_connect(db_path or _default_db_path()))

    def close(self) -> None:
        self._conn.close()

    def ensure_session(self, session_id: str, cwd: str = "", model: str = "") -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO sessions (session_id, project_cwd, model) VALUES (?, ?, ?)",
            (session_id, cwd, model),
        )
        self._conn.commit()

    def lookup(self, content_hash: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM cache_entries WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        return dict(row) if row else None

    def lookup_by_ref(self, ref_token: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM cache_entries WHERE ref_token = ?", (ref_token,)
        ).fetchone()
        return dict(row) if row else None

    def record_hit(self, content_hash: str) -> None:
        self._conn.execute(
            "UPDATE cache_entries SET hit_count = hit_count + 1, last_seen_at = unixepoch() "
            "WHERE content_hash = ?",
            (content_hash,),
        )
        self._conn.commit()

    def store(
        self,
        content_hash: str,
        original: str,
        compressed: str,
        tool_name: str,
        simhash_val: int | None = None,
    ) -> str:
        ref = make_ref_token(content_hash)
        self._conn.execute(
            """INSERT OR REPLACE INTO cache_entries
               (content_hash, original_len, compressed, compressed_len, ref_token,
                tool_name, simhash, created_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, unixepoch(), unixepoch())""",
            (content_hash, len(original), compressed, len(compressed), ref, tool_name, simhash_val),
        )
        self._conn.commit()
        return ref

    def record_compression(
        self,
        session_id: str,
        tool_name: str,
        content_hash: str | None,
        original_tokens: int,
        compressed_tokens: int,
        stages_applied: list[str],
        was_cache_hit: bool = False,
        was_safe_mode: bool = False,
        tool_use_id: str = "",
    ) -> None:
        self._conn.execute(
            """INSERT INTO compressions
               (session_id, tool_name, tool_use_id, content_hash,
                original_tokens, compressed_tokens, stages_applied,
                was_cache_hit, was_safe_mode)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                tool_name,
                tool_use_id,
                content_hash,
                original_tokens,
                compressed_tokens,
                json.dumps(stages_applied),
                int(was_cache_hit),
                int(was_safe_mode),
            ),
        )
        self._conn.commit()

    def stats(self, session_id: str | None = None) -> dict[str, Any]:
        where = "WHERE session_id = ?" if session_id else ""
        params = (session_id,) if session_id else ()
        row = self._conn.execute(
            f"""SELECT
                COUNT(*) AS total_compressions,
                COALESCE(SUM(original_tokens), 0) AS total_original_tokens,
                COALESCE(SUM(compressed_tokens), 0) AS total_compressed_tokens,
                COALESCE(SUM(was_cache_hit), 0) AS cache_hits,
                COALESCE(SUM(was_safe_mode), 0) AS safe_mode_passes
               FROM compressions {where}""",
            params,
        ).fetchone()
        d = dict(row) if row else {}
        orig = d.get("total_original_tokens", 0)
        comp = d.get("total_compressed_tokens", 0)
        d["tokens_saved"] = max(0, orig - comp)
        d["reduction_pct"] = round((orig - comp) / orig * 100, 1) if orig else 0.0
        return d

    def recent_entries(self, limit: int = 200) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT content_hash, simhash, compressed FROM cache_entries "
            "WHERE simhash IS NOT NULL "
            "ORDER BY last_seen_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def store_delta(self, base_hash: str, new_hash: str, dist: int, patch: str) -> None:
        self._conn.execute(
            "INSERT INTO deltas (base_hash, new_hash, simhash_dist, patch) VALUES (?, ?, ?, ?)",
            (base_hash, new_hash, dist, patch),
        )
        self._conn.commit()

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT content_hash, compressed FROM cache_fts WHERE cache_fts MATCH ? LIMIT ?",
            (query, limit),
        ).fetchall()
        return [dict(r) for r in rows]
