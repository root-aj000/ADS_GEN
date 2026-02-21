# """
# SQLite-backed image cache.
# Avoids re-downloading the same query across runs.
# """

# from __future__ import annotations

# import hashlib
# import sqlite3
# import threading
# import time
# from pathlib import Path
# from typing import Optional

# from utils.log_config import get_logger

# log = get_logger(__name__)

# _CREATE_SQL = """
# CREATE TABLE IF NOT EXISTS image_cache (
#     query_hash   TEXT PRIMARY KEY,
#     query        TEXT NOT NULL,
#     source_url   TEXT,
#     file_path    TEXT,
#     file_hash    TEXT,
#     width        INTEGER,
#     height       INTEGER,
#     file_size    INTEGER,
#     source_engine TEXT,
#     created_at   REAL,
#     hit_count    INTEGER DEFAULT 0
# );

# CREATE INDEX IF NOT EXISTS idx_query ON image_cache(query);
# CREATE INDEX IF NOT EXISTS idx_file_hash ON image_cache(file_hash);
# """


# class ImageCache:
#     """
#     Thread-safe SQLite cache for downloaded images.

#     Keyed by normalised query string so identical products
#     reuse the same downloaded image across rows.
#     """

#     def __init__(self, db_path: Path) -> None:
#         self._db_path = db_path
#         self._local = threading.local()
#         self._init_lock = threading.Lock()
#         self._ensure_schema()

#     # ── connection per thread ───────────────────────────────
#     @property
#     def _conn(self) -> sqlite3.Connection:
#         conn = getattr(self._local, "conn", None)
#         if conn is None:
#             conn = sqlite3.connect(str(self._db_path), timeout=10)
#             conn.row_factory = sqlite3.Row
#             conn.execute("PRAGMA journal_mode=WAL")
#             conn.execute("PRAGMA synchronous=NORMAL")
#             self._local.conn = conn
#         return conn

#     def _ensure_schema(self) -> None:
#         with self._init_lock:
#             conn = sqlite3.connect(str(self._db_path), timeout=10)
#             conn.executescript(_CREATE_SQL)
#             conn.close()

#     # ── helpers ─────────────────────────────────────────────
#     @staticmethod
#     def _hash_query(query: str) -> str:
#         normalised = " ".join(query.lower().strip().split())
#         return hashlib.sha256(normalised.encode()).hexdigest()[:16]

#     # ── public API ──────────────────────────────────────────
#     def get(self, query: str) -> Optional[dict]:
#         """Return cached entry or None."""
#         qh = self._hash_query(query)
#         row = self._conn.execute(
#             "SELECT * FROM image_cache WHERE query_hash = ?", (qh,)
#         ).fetchone()

#         if row is None:
#             return None

#         # check file still exists
#         fp = row["file_path"]
#         if fp and not Path(fp).exists():
#             log.debug("Cache stale (file missing): %s", query)
#             self._conn.execute(
#                 "DELETE FROM image_cache WHERE query_hash = ?", (qh,)
#             )
#             self._conn.commit()
#             return None

#         # bump hit count
#         self._conn.execute(
#             "UPDATE image_cache SET hit_count = hit_count + 1 WHERE query_hash = ?",
#             (qh,),
#         )
#         self._conn.commit()

#         log.info("Cache HIT for '%s' (hits=%d)", query, row["hit_count"] + 1)
#         return dict(row)

#     def put(
#         self,
#         query: str,
#         source_url: str,
#         file_path: str,
#         file_hash: str,
#         width: int,
#         height: int,
#         file_size: int,
#         source_engine: str,
#     ) -> None:
#         """Insert or replace a cache entry."""
#         qh = self._hash_query(query)
#         self._conn.execute(
#             """
#             INSERT OR REPLACE INTO image_cache
#                 (query_hash, query, source_url, file_path, file_hash,
#                  width, height, file_size, source_engine, created_at, hit_count)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
#             """,
#             (qh, query, source_url, file_path, file_hash,
#              width, height, file_size, source_engine, time.time()),
#         )
#         self._conn.commit()
#         log.debug("Cache PUT: '%s' → %s", query, file_path)

#     def stats(self) -> dict:
#         """Return cache statistics."""
#         row = self._conn.execute(
#             """
#             SELECT
#                 COUNT(*) as total,
#                 SUM(hit_count) as total_hits,
#                 SUM(file_size) as total_bytes
#             FROM image_cache
#             """
#         ).fetchone()
#         return dict(row) if row else {}

#     def clear(self) -> None:
#         self._conn.execute("DELETE FROM image_cache")
#         self._conn.commit()
#         log.info("Cache cleared")

"""
SQLite-backed image cache.
Thread-safe: uses a single shared connection with a lock,
not per-thread connections (which cause "database is locked").
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional, Dict

from utils.log_config import get_logger

log = get_logger(__name__)

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS image_cache (
    query_hash    TEXT PRIMARY KEY,
    query         TEXT NOT NULL,
    source_url    TEXT,
    file_path     TEXT,
    file_hash     TEXT,
    width         INTEGER,
    height        INTEGER,
    file_size     INTEGER,
    source_engine TEXT,
    created_at    REAL,
    hit_count     INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_query ON image_cache(query);
CREATE INDEX IF NOT EXISTS idx_file_hash ON image_cache(file_hash);
"""


class ImageCache:
    """
    Thread-safe SQLite cache.

    Uses ONE shared connection protected by a threading.Lock.
    This avoids "database is locked" errors that happen with
    per-thread connections.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create the single shared connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self._db_path),
                timeout=30,
                check_same_thread=False,  # Allow cross-thread usage (we use our own lock)
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA busy_timeout=10000")  # Wait 10s if busy
        return self._conn

    def _ensure_schema(self) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.executescript(_CREATE_SQL)
            conn.commit()

    @staticmethod
    def _hash_query(query: str) -> str:
        normalised = " ".join(query.lower().strip().split())
        return hashlib.sha256(normalised.encode()).hexdigest()[:16]

    def get(self, query: str) -> Optional[Dict]:
        """Return cached entry or None. Thread-safe."""
        qh = self._hash_query(query)

        with self._lock:
            try:
                conn = self._get_conn()
                row = conn.execute(
                    "SELECT * FROM image_cache WHERE query_hash = ?", (qh,)
                ).fetchone()

                if row is None:
                    return None

                # Check file still exists
                fp = row["file_path"]
                if fp and not Path(fp).exists():
                    log.debug("Cache stale (file missing): %s", query)
                    conn.execute(
                        "DELETE FROM image_cache WHERE query_hash = ?", (qh,)
                    )
                    conn.commit()
                    return None

                # Bump hit count
                conn.execute(
                    "UPDATE image_cache SET hit_count = hit_count + 1 WHERE query_hash = ?",
                    (qh,),
                )
                conn.commit()

                log.info("Cache HIT for '%s' (hits=%d)", query[:40], row["hit_count"] + 1)
                return dict(row)

            except sqlite3.Error as exc:
                log.warning("Cache get error: %s", exc)
                return None

    def put(
        self,
        query: str,
        source_url: str,
        file_path: str,
        file_hash: str,
        width: int,
        height: int,
        file_size: int,
        source_engine: str,
    ) -> None:
        """Insert or replace a cache entry. Thread-safe."""
        qh = self._hash_query(query)

        with self._lock:
            try:
                conn = self._get_conn()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO image_cache
                        (query_hash, query, source_url, file_path, file_hash,
                         width, height, file_size, source_engine, created_at, hit_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (qh, query, source_url, file_path, file_hash,
                     width, height, file_size, source_engine, time.time()),
                )
                conn.commit()
                log.debug("Cache PUT: '%s'", query[:40])

            except sqlite3.Error as exc:
                log.warning("Cache put error: %s", exc)

    def stats(self) -> Dict:
        """Return cache statistics. Thread-safe."""
        with self._lock:
            try:
                conn = self._get_conn()
                row = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        COALESCE(SUM(hit_count), 0) as total_hits,
                        COALESCE(SUM(file_size), 0) as total_bytes
                    FROM image_cache
                    """
                ).fetchone()
                return dict(row) if row else {"total": 0, "total_hits": 0, "total_bytes": 0}

            except sqlite3.Error as exc:
                log.warning("Cache stats error: %s", exc)
                return {"total": 0, "total_hits": 0, "total_bytes": 0}

    def clear(self) -> None:
        """Clear entire cache. Thread-safe."""
        with self._lock:
            try:
                conn = self._get_conn()
                conn.execute("DELETE FROM image_cache")
                conn.commit()
                log.info("Cache cleared")
            except sqlite3.Error as exc:
                log.warning("Cache clear error: %s", exc)

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None