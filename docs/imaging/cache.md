# ImageCache

**File**: [`imaging/cache.py`](imaging/cache.py)  
**Purpose**: SQLite-backed cache that prevents re-downloading the same query across multiple pipeline runs.

## 🎯 What It Does

The `ImageCache` is like a smart filing cabinet that remembers every product image you've ever downloaded. Before downloading a new image, the system checks if we already have one for that product.

Think of it as a **photo archive librarian** who:
1. ✅ Records every downloaded image with its search query
2. ✅ Quickly finds existing images for repeated queries
3. ✅ Tracks how often each image is reused ("hit count")
4. ✅ Detects and removes stale entries (when files are deleted)
5. ✅ Provides statistics on cache performance

## 🔧 Class Structure

```python
class ImageCache:
    """
    Thread-safe SQLite cache for downloaded images.
    
    Keyed by normalised query string so identical products
    reuse the same downloaded image across rows.
    """
    
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path           # Path to SQLite file
        self._local = threading.local()   # Per-thread connections
        self._init_lock = threading.Lock() # Schema initialization lock
        self._ensure_schema()
```

### Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| [`get()`](imaging/cache.py:78) | Retrieve cached entry by query | `Optional[dict]` |
| [`put()`](imaging/cache.py:108) | Store new entry in cache | `None` |
| [`stats()`](imaging/cache.py:134) | Get cache statistics | `dict` |
| [`clear()`](imaging/cache.py:147) | Remove all entries | `None` |

## 🔄 How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    ImageCache Flow                          │
└─────────────────────────────────────────────────────────────┘

Product Query: "red nike shoes" ────────┐
                                        │
                                        ▼
                         ┌─────────────────────────┐
                         │   Normalize Query       │
                         │  "red nike shoes" →     │
                         │  hash: "a1b2c3d4e5f6"   │
                         └──────────┬──────────────┘
                                    │
                                    ▼
                         ┌─────────────────────────┐
                         │   Check SQLite Cache    │
                         └──────────┬──────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
            ┌───────────────┐               ┌───────────────┐
            │  CACHE HIT    │               │  CACHE MISS   │
            │               │               │               │
            │ • Verify file │               │ • Download    │
            │   exists      │               │ • Save image  │
            │ • Bump hit    │               │ • Store entry │
            │   count       │               │   in cache    │
            │ • Return path │               │               │
            └───────────────┘               └───────────────┘
```

## 📊 Database Schema

```sql
CREATE TABLE image_cache (
    query_hash TEXT PRIMARY KEY,   -- SHA256 of normalized query (first 16 chars)
    query TEXT NOT NULL,           -- Original search query
    source_url TEXT,               -- URL where image was downloaded from
    file_path TEXT,                -- Local path to saved image
    file_hash TEXT,                -- MD5 hash of image data
    width INTEGER,                 -- Image width in pixels
    height INTEGER,                -- Image height in pixels
    file_size INTEGER,             -- File size in bytes
    source_engine TEXT,            -- Which search engine provided it
    created_at REAL,               -- Unix timestamp when cached
    hit_count INTEGER DEFAULT 0    -- How many times reused
);

CREATE INDEX idx_query ON image_cache(query);
CREATE INDEX idx_file_hash ON image_cache(file_hash);
```

## 🔍 Key Operations

### Query Normalization and Hashing

```python
@staticmethod
def _hash_query(query: str) -> str:
    normalised = " ".join(query.lower().strip().split())
    return hashlib.sha256(normalised.encode()).hexdigest()[:16]
```

**Why normalize?**
- "Red Nike Shoes" and "red nike shoes" should match the same cache entry
- Extra whitespace is removed
- Case-insensitive matching

**Example**:
```python
# These all produce the same hash:
_hash_query("Red Nike Shoes")     # "a1b2c3d4e5f6g7h8"
_hash_query("red nike shoes")     # "a1b2c3d4e5f6g7h8"
_hash_query("  red   nike  shoes  ")  # "a1b2c3d4e5f6g7h8"
```

### Getting Cached Images

```python
def get(self, query: str) -> Optional[dict]:
    """Return cached entry or None."""
    qh = self._hash_query(query)
    row = self._conn.execute(
        "SELECT * FROM image_cache WHERE query_hash = ?", (qh,)
    ).fetchone()
    
    if row is None:
        return None
    
    # Check file still exists (detect stale cache)
    fp = row["file_path"]
    if fp and not Path(fp).exists():
        log.debug("Cache stale (file missing): %s", query)
        self._conn.execute(
            "DELETE FROM image_cache WHERE query_hash = ?", (qh,)
        )
        self._conn.commit()
        return None
    
    # Bump hit count
    self._conn.execute(
        "UPDATE image_cache SET hit_count = hit_count + 1 WHERE query_hash = ?",
        (qh,),
    )
    self._conn.commit()
    
    log.info("Cache HIT for '%s' (hits=%d)", query, row["hit_count"] + 1)
    return dict(row)
```

**What happens on cache hit**:
1. ✅ Query is hashed
2. ✅ Database is queried
3. ✅ If found, verify file still exists on disk
4. ✅ If file missing, delete stale entry and return None
5. ✅ If valid, increment hit count and return entry

### Storing New Entries

```python
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
    """Insert or replace a cache entry."""
    qh = self._hash_query(query)
    self._conn.execute(
        """
        INSERT OR REPLACE INTO image_cache
        (query_hash, query, source_url, file_path, file_hash,
         width, height, file_size, source_engine, created_at, hit_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (qh, query, source_url, file_path, file_hash,
         width, height, file_size, source_engine, time.time()),
    )
    self._conn.commit()
```

**Parameters passed from**:
- `query` - The product search query
- `source_url` - URL from [`ImageResult.url`](search/base.py)
- `file_path` - Local path where image was saved
- `file_hash` - MD5 hash from downloader
- `width`, `height` - Image dimensions from PIL
- `file_size` - File size in bytes
- `source_engine` - Which search engine (google/bing/duckduckgo)

## 🔗 Thread Safety

### Per-Thread Database Connections

```python
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
```

**Why per-thread connections?**
- SQLite connections are not thread-safe
- Each thread gets its own connection
- WAL mode allows concurrent reads
- `synchronous=NORMAL` for better performance

### Schema Initialization Lock

```python
def _ensure_schema(self) -> None:
    with self._init_lock:
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.executescript(_CREATE_SQL)
        conn.close()
```

**Why a lock?**
- Multiple threads might try to create schema simultaneously
- Lock ensures schema is created exactly once
- Separate connection for initialization (closed after)

## 📈 Statistics

```python
def stats(self) -> dict:
    """Return cache statistics."""
    row = self._conn.execute(
        """
        SELECT
            COUNT(*) as total,
            SUM(hit_count) as total_hits,
            SUM(file_size) as total_bytes
        FROM image_cache
        """
    ).fetchone()
    return dict(row) if row else {}
```

**Returns**:
```python
{
    "total": 150,           # Total cached images
    "total_hits": 423,      # Total cache hits (reuses)
    "total_bytes": 52428800 # Total bytes saved in cache
}
```

## 🎯 Real-World Example

### Scenario: Processing a CSV with Duplicate Products

```python
# CSV contains:
# Row 1: "Red Nike Shoes", $99.99
# Row 2: "Red Nike Shoes", $89.99 (same product, different price)
# Row 3: "Blue Nike Shoes", $79.99 (different product)

cache = ImageCache(Path("data/cache.db"))

# Process Row 1: "Red Nike Shoes"
entry = cache.get("Red Nike Shoes")  # None (cache miss)
# ... download image, save to disk ...
cache.put(
    query="Red Nike Shoes",
    source_url="https://example.com/shoes.jpg",
    file_path="data/output/images/ad_0001.jpg",
    file_hash="abc123",
    width=800, height=600,
    file_size=45000,
    source_engine="google"
)

# Process Row 2: "Red Nike Shoes" (same query!)
entry = cache.get("Red Nike Shoes")
# Returns: {
#     "query": "Red Nike Shoes",
#     "file_path": "data/output/images/ad_0001.jpg",
#     "hit_count": 1,  # Incremented!
#     ...
# }
# NO RE-DOWNLOAD NEEDED! Use cached image.

# Process Row 3: "Blue Nike Shoes"
entry = cache.get("Blue Nike Shoes")  # None (different product)
# ... download new image ...
```

**Result**:
- Row 1: Downloaded and cached
- Row 2: Cache HIT, reused image (saved time + bandwidth)
- Row 3: Cache MISS, downloaded new image

## 🔄 Integration with Pipeline

```python
# In core/pipeline.py

# Check cache before searching
cached = self.cache.get(query)
if cached:
    log.info("Using cached image for: %s", query)
    # Use cached file_path directly
    return {"path": cached["file_path"], "cached": True}

# Not in cache - search and download
results = self.search_manager.search(query)
download_result = self.downloader.download_best(results, dest)

# Store in cache for future use
if download_result.success:
    self.cache.put(
        query=query,
        source_url=download_result.source_url,
        file_path=str(download_result.path),
        file_hash=download_result.info["hash"],
        width=download_result.info["width"],
        height=download_result.info["height"],
        file_size=download_result.info["file_size"],
        source_engine=download_result.info["source_engine"]
    )
```

## 📁 File Location

The cache database is typically stored at:
```
data/
└── .image_cache.db    # SQLite database file
```

**Why a hidden file?** The dot prefix keeps it out of the way and indicates it's internal data.

---

**Next**: [Image Scorer](scorer.md) → Multi-factor quality scoring for image selection
