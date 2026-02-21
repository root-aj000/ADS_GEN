# """
# Set-based progress tracker.

# Supports out-of-order completion from multiple threads and
# uses atomic writes (tmp → rename) to avoid corruption.
# """

# from __future__ import annotations

# import json
# import threading
# import time
# from pathlib import Path
# from typing import Any, Dict, List, Set

# from utils.log_config import get_logger

# log = get_logger(__name__)


# class ProgressManager:

#     def __init__(self, path: Path) -> None:
#         self._path = path
#         self._lock = threading.Lock()
#         self._completed: Set[int] = set()
#         self._metadata: List[Dict[str, Any]] = []
#         self._load()

#     # ── persistence ─────────────────────────────────────────
#     def _load(self) -> None:
#         if not self._path.exists():
#             return
#         try:
#             data = json.loads(self._path.read_text(encoding="utf-8"))
#             self._completed = set(data.get("completed_indices", []))
#             self._metadata = data.get("metadata", [])
#             log.info("Resumed progress — %d done", len(self._completed))
#         except Exception:
#             log.warning("Corrupt progress file — starting fresh")

#     def _flush(self) -> None:
#         tmp = self._path.with_suffix(".tmp")
#         payload = {
#             "completed_indices": sorted(self._completed),
#             "metadata": self._metadata,
#             "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
#         }
#         tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
#         tmp.replace(self._path)

#     # ── public ──────────────────────────────────────────────
#     def is_done(self, idx: int) -> bool:
#         with self._lock:
#             return idx in self._completed

#     def mark_done(self, idx: int, meta: Dict[str, Any]) -> None:
#         with self._lock:
#             self._completed.add(idx)
#             self._metadata.append(meta)
#             self._flush()

#     @property
#     def completed_count(self) -> int:
#         with self._lock:
#             return len(self._completed)

#     def reset(self) -> None:
#         with self._lock:
#             self._completed.clear()
#             self._metadata.clear()
#             if self._path.exists():
#                 self._path.unlink()


"""
SQLite-backed progress tracker with dead-letter queue.
Replaces JSON file — faster, atomic, concurrent-safe.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from utils.log_config import get_logger

log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS progress (
    idx          INTEGER PRIMARY KEY,
    status       TEXT NOT NULL DEFAULT 'pending',
    query        TEXT,
    filename     TEXT,
    source       TEXT,
    error        TEXT,
    retries      INTEGER DEFAULT 0,
    completed_at REAL,
    meta_json    TEXT
);

CREATE INDEX IF NOT EXISTS idx_status ON progress(status);
"""


class ProgressManager:
    """
    States: pending → processing → done | failed → (retry) → done
    Dead-letter: rows with status='failed' and retries < max
    """

    def __init__(self, db_path: Path, max_retries: int = 2) -> None:
        self._db_path = db_path
        self._max_retries = max_retries
        self._local = threading.local()
        self._init_lock = threading.Lock()
        self._ensure()

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self._db_path), timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return conn

    def _ensure(self) -> None:
        with self._init_lock:
            c = sqlite3.connect(str(self._db_path), timeout=10)
            c.executescript(_SCHEMA)
            c.close()

    # ── queries ─────────────────────────────────────────────
    def is_done(self, idx: int) -> bool:
        row = self._conn.execute(
            "SELECT status FROM progress WHERE idx = ?", (idx,)
        ).fetchone()
        return row is not None and row["status"] == "done"

    def mark_done(self, idx: int, meta: Dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO progress
                (idx, status, query, filename, source, error, completed_at, meta_json)
            VALUES (?, 'done', ?, ?, ?, NULL, ?, ?)
            """,
            (
                idx,
                meta.get("query", ""),
                meta.get("filename", ""),
                meta.get("source", ""),
                time.time(),
                json.dumps(meta),
            ),
        )
        self._conn.commit()

    def mark_failed(self, idx: int, meta: Dict[str, Any]) -> None:
        existing = self._conn.execute(
            "SELECT retries FROM progress WHERE idx = ?", (idx,)
        ).fetchone()
        retries = (existing["retries"] + 1) if existing else 1

        self._conn.execute(
            """
            INSERT OR REPLACE INTO progress
                (idx, status, query, filename, error, retries, completed_at, meta_json)
            VALUES (?, 'failed', ?, ?, ?, ?, ?, ?)
            """,
            (
                idx,
                meta.get("query", ""),
                meta.get("filename", ""),
                meta.get("error", ""),
                retries,
                time.time(),
                json.dumps(meta),
            ),
        )
        self._conn.commit()

    def get_dead_letters(self) -> List[int]:
        """Return indices eligible for retry."""
        rows = self._conn.execute(
            "SELECT idx FROM progress WHERE status = 'failed' AND retries < ?",
            (self._max_retries,),
        ).fetchall()
        return [r["idx"] for r in rows]

    @property
    def completed_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) as c FROM progress WHERE status = 'done'"
        ).fetchone()
        return row["c"] if row else 0

    @property
    def failed_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) as c FROM progress WHERE status = 'failed'"
        ).fetchone()
        return row["c"] if row else 0

    def stats(self) -> Dict[str, int]:
        rows = self._conn.execute(
            "SELECT status, COUNT(*) as c FROM progress GROUP BY status"
        ).fetchall()
        return {r["status"]: r["c"] for r in rows}

    def reset(self) -> None:
        self._conn.execute("DELETE FROM progress")
        self._conn.commit()
        log.info("Progress database reset")