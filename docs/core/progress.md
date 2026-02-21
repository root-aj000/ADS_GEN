# Progress Manager Documentation

## File: [`core/progress.py`](../../core/progress.py)

## Overview

The `progress.py` file provides **progress tracking** with persistence. It remembers which rows have been processed, which have failed, and supports retrying failed items through a "dead-letter queue".

## Real-World Analogy

Think of the progress manager as a **bookmark in a book**:
- You can close the book (stop the program)
- When you open it again, you know exactly where you left off
- It also remembers which pages were difficult (failed) so you can try them again later

---

## ProgressManager Class

### Initialization

```python
class ProgressManager:
    def __init__(self, db_path: Path, max_retries: int = 2) -> None:
        self._db_path = db_path
        self._max_retries = max_retries
        self._local = threading.local()  # Thread-local connections
        self._init_lock = threading.Lock()
        self._ensure()  # Create database schema
```

**Parameters**:

| Parameter | Type | Source | Default | Description |
|-----------|------|--------|---------|-------------|
| `db_path` | `Path` | `cfg.paths.progress_db` | `data/temp/progress.db` | SQLite database file |
| `max_retries` | `int` | `cfg.dlq_retries` | 2 | Maximum retry attempts for failed rows |

---

### Database Schema

The progress is stored in a SQLite database with this structure:

```sql
CREATE TABLE IF NOT EXISTS progress (
    idx INTEGER PRIMARY KEY,      -- Row index from CSV
    status TEXT NOT NULL DEFAULT 'pending',  -- 'done', 'failed', 'pending'
    query TEXT,                   -- Search query used
    filename TEXT,                -- Output filename
    source TEXT,                  -- Search engine source
    error TEXT,                   -- Error message if failed
    retries INTEGER DEFAULT 0,    -- Number of retry attempts
    completed_at REAL,            -- Timestamp
    meta_json TEXT                -- Full metadata as JSON
);

CREATE INDEX IF NOT EXISTS idx_status ON progress(status);
```

---

### Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Not yet processed (initial state) |
| `done` | Successfully processed |
| `failed` | Processing failed (eligible for retry) |

---

## Public Methods

### is_done()

**Purpose**: Check if a row has been successfully processed.

```python
def is_done(self, idx: int) -> bool:
```

**Usage**:
```python
if not progress.is_done(42):
    # Process row 42
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `idx` | `int` | Row index to check |

**Returns**: `True` if row was successfully processed, `False` otherwise.

---

### mark_done()

**Purpose**: Mark a row as successfully completed.

```python
def mark_done(self, idx: int, meta: Dict[str, Any]) -> None:
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `idx` | `int` | Row index |
| `meta` | `Dict[str, Any]` | Metadata (query, filename, source, etc.) |

**Example**:
```python
progress.mark_done(42, {
    "query": "pizza slice",
    "filename": "ad_0043.jpg",
    "source": "google",
    "success": True
})
```

---

### mark_failed()

**Purpose**: Mark a row as failed (eligible for retry).

```python
def mark_failed(self, idx: int, meta: Dict[str, Any]) -> None:
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `idx` | `int` | Row index |
| `meta` | `Dict[str, Any]` | Metadata including error message |

**Example**:
```python
progress.mark_failed(42, {
    "query": "pizza slice",
    "error": "Connection timeout"
})
```

---

### get_dead_letters()

**Purpose**: Get list of failed rows eligible for retry.

```python
def get_dead_letters(self) -> List[int]:
```

**Returns**: List of row indices that failed and haven't exceeded max retries.

**Logic**:
```sql
SELECT idx FROM progress 
WHERE status = 'failed' 
AND retries < max_retries
```

**Usage**:
```python
failed_rows = progress.get_dead_letters()
# [5, 12, 23, 41, 55]  # These rows will be retried
```

---

### completed_count Property

**Purpose**: Get count of successfully processed rows.

```python
@property
def completed_count(self) -> int:
```

---

### stats() Method

**Purpose**: Get statistics about progress.

**Returns**: Dictionary with counts and timing information.

---

## Dead-Letter Queue (DLQ) Concept

The dead-letter queue is a pattern for handling failures:

```
┌─────────────────────────────────────────────────────────────┐
│                    Processing Flow                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Normal Processing                                        │
│     ├── Success → mark_done(idx)                            │
│     └── Failure → mark_failed(idx)                          │
│                                                              │
│  2. End of Run                                               │
│     └── Check dead-letter queue                             │
│         └── get_dead_letters() → [5, 12, 23, ...]           │
│                                                              │
│  3. Retry Failed Items                                       │
│     ├── For each failed index:                              │
│     │   ├── Retry count < max_retries? → Retry              │
│     │   └── Retry count >= max_retries? → Skip              │
│     └── Process again                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Example Timeline**:

```
Run 1:
- Process rows 0-99
- Rows 5, 12, 23 fail (retry count = 1)
- Save progress

Run 2 (Resume):
- Skip rows 0-99 (already done)
- Retry rows 5, 12, 23
- Row 5 succeeds, rows 12, 23 fail again (retry count = 2)

Run 3 (Resume):
- Skip completed rows
- Retry rows 12, 23 (retry count = 2, max reached)
- Row 12 succeeds, row 23 fails (give up)
```

---

## Thread Safety

The progress manager is designed for multi-threaded use:

```python
@property
def _conn(self) -> sqlite3.Connection:
    """Each thread gets its own connection."""
    conn = getattr(self._local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Concurrent access
        conn.execute("PRAGMA synchronous=NORMAL")
        self._local.conn = conn
    return conn
```

**Key Points**:
- Each thread gets its own database connection
- Uses WAL mode for concurrent read/write
- Thread-local storage prevents connection conflicts

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    ProgressManager                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input:                                                      │
│  └── db_path: data/temp/progress.db                         │
│                                                              │
│  Operations:                                                 │
│  ├── is_done(42) → True/False                               │
│  ├── mark_done(42, {"query": "...", "source": "google"})    │
│  ├── mark_failed(42, {"error": "timeout"})                  │
│  └── get_dead_letters() → [5, 12, 23]                       │
│                                                              │
│  Storage:                                                    │
│  └── SQLite database with WAL mode                          │
│                                                              │
│  Benefits:                                                   │
│  ├── Resume from interruption                               │
│  ├── Retry failed items                                     │
│  └── Track processing history                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Integration with Pipeline

```python
# In core/pipeline.py

# Check if row already done (resume mode)
if self.cfg.resume and self.progress.is_done(idx):
    continue  # Skip this row

# Process row...
try:
    # ... processing ...
    self.progress.mark_done(idx, meta)
except Exception as e:
    self.progress.mark_failed(idx, {"error": str(e)})

# At end of run, retry failed items
if self.cfg.enable_dlq:
    dlq = self.progress.get_dead_letters()
    if dlq:
        log.info("Retrying %d failed rows", len(dlq))
        self._run_indices(dlq)
```

---

## Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cfg.paths.progress_db` | Path | `data/temp/progress.db` | Database file location |
| `cfg.resume` | bool | `False` | Enable resume from last run |
| `cfg.enable_dlq` | bool | `True` | Enable dead-letter queue retry |
| `cfg.dlq_retries` | int | `2` | Maximum retry attempts |

---

## Connected Files

| File | Relationship |
|------|--------------|
| [`core/pipeline.py`](pipeline.md) | Uses progress tracking |
| [`config/settings.py`](../config/settings.md) | Provides configuration |

---

## Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Track processing progress and handle failures |
| **Storage** | SQLite database with WAL mode |
| **Key Features** | Resume capability, dead-letter queue, retry logic |
| **Thread Safety** | Per-thread connections |

**Think of it as**: A bookmark that not only remembers where you are in a book, but also notes which pages were confusing so you can re-read them later.
