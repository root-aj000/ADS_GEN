# ImageDownloader

**File**: [`imaging/downloader.py`](imaging/downloader.py)  
**Purpose**: Downloads images from URLs, validates them rigorously, and saves them locally for ad composition.

## 🎯 What It Does

The `ImageDownloader` is like a demanding photo curator at a gallery. It doesn't just download any image—it carefully inspects each candidate, checks its quality, ensures it hasn't been seen before, and only accepts the very best photos for display.

Think of it as your personal photo quality inspector who:
1. ✅ Downloads images from URLs (with retry logic)
2. ✅ Validates dimensions, aspect ratio, file size
3. ✅ Checks for visual content (rejects blank images)
4. ✅ Deduplicates by hash (no duplicates allowed!)
5. ✅ Uses intelligent scoring to pick the best candidate
6. ✅ Saves in optimal format (PNG for transparency, JPEG otherwise)

## 🔧 Class Structure

```python
class ImageDownloader:
    """Thread-safe: each thread gets its own requests.Session."""
    
    def __init__(
        self,
        cfg: ImageQualityConfig,
        hashes: ThreadSafeSet,
        timeout: int = 10,
        scorer: Optional[ImageQualityScorer] = None,
    ) -> None:
        self.cfg = cfg              # Quality configuration
        self.hashes = hashes         # Deduplication set
        self.timeout = timeout       # HTTP timeout (seconds)
        self.scorer = scorer         # Optional quality scorer
        self._local = threading.local()  # Per-thread session storage
```

### Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| [`download_best()`](imaging/downloader.py:414) | Download best image from candidates | `DownloadResult` |
| [`_fetch()`](imaging/downloader.py:626) | Fetch URL with retry logic | `Optional[bytes]` |
| [`_ok()`](imaging/downloader.py:637) | Validate image quality | `bool` |
| [`_save()`](imaging/downloader.py:646) | Save image to disk | `Path` |
| [`_score()`](imaging/downloader.py:656) | Score candidate images | `float` |

## 🔄 Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│             ImageDownloader Workflow                        │
└─────────────────────────────────────────────────────────────┘

Search Results (List[ImageResult]) ─────┐
                                         │
                                         ▼
                         ┌─────────────────────────┐
                         │  Rank by Quality Score  │
                         │  (scorer OR simple score)│
                         └──────────┬──────────────┘
                                    │
                                    ▼
                         ┌─────────────────────────┐
                         │ For Each Candidate...    │
                         └──────────┬──────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  1. Fetch with Retry Logic    │
                    │  2. Check File Size           │
                    │  3. Load Image                │
                    │  4. Check Dimensions          │
                    │  5. Check Aspect Ratio        │
                    │  6. Check Visual Content      │
                    │  7. Deduplicate by Hash       │
                    │  8. Save If Valid             │
                    └─────────────┬─────────────────┘
                                  │
                         ┌────────▼────────┐
                         │ Return Success  │
                         │ (or Failure)    │
                         └─────────────────┘
```

## 🏁 How Components Connect

**Parameters and Their Sources**:

| Parameter | Source | Purpose |
|-----------|--------|---------|
| `cfg: ImageQualityConfig` | [`config/settings.py`](config/settings.py:814) | Validation thresholds |
| `hashes: ThreadSafeSet` | [`core/pipeline.py`](core/pipeline.py) | Deduplication across pipeline |
| `timeout: int` | Default: 10 | HTTP request timeout |
| `scorer: ImageQualityScorer` | [`imaging/scorer.py`](imaging/scorer.py) | Quality scoring (optional) |
| `results: List[ImageResult]` | [`search/base.py`](search/base.py) | Search results from engines |
| `dest: Path` | Pipeline worker | Where to save image |

**Data Flow**:

1. **Pipeline** → calls `download_best()` with search results
2. **ImageDownloader** → ranks results by quality score
3. **For each candidate** → fetches image from URL
4. **Quality Check** → validates dimensions, aspect ratio, visual content
5. **Deduplication** → checks hash against shared ThreadSafeSet
6. **Return** → DownloadResult with success status and file path

## 🔍 Detailed Validation Process

### 1. HTTP Fetch (with Retry)
```python
@retry(max_attempts=2, backoff_base=0.5)
def _fetch(self, url: str) -> Optional[bytes]:
    resp = self.session.get(url, timeout=self.timeout, stream=True)
    if resp.status_code != 200:
        return None
    cl = resp.headers.get("content-length")
    if cl and int(cl) < self.cfg.min_file_bytes:
        return None
    data = resp.content
    return data if len(data) >= self.cfg.min_file_bytes else None
```

**Validation Steps**:
- ✅ Status code must be 200
- ✅ Content-Length header ≥ `min_file_bytes` (5KB by default)
- ✅ Actual file size ≥ `min_file_bytes`

**Retry Logic**: If fetch fails, waits 0.5 seconds and tries again (max 2 attempts)

### 2. Deduplication Check
```python
h = hashlib.md5(data).hexdigest()
if not self.hashes.add(h):
    continue  # Already downloaded!
```

**How it works**: 
- Compute MD5 hash of image data
- Add to `ThreadSafeSet` (shared across all threads)
- Returns `False` if hash already exists (image already downloaded)

**Why it matters**: Prevents downloading the same product image multiple times across different products

### 3. Image Loading and Validation
```python
def _ok(self, img: Image.Image, raw: bytes) -> bool:
    c = self.cfg
    if img.width < c.min_width or img.height < c.min_height:
        return False
    ar = img.width / img.height
    if ar < c.min_aspect or ar > c.max_aspect:
        return False
    return has_visual_content(img, c.min_std_dev, c.min_unique_colours)
```

**Checks**:
- ✅ Width ≥ `min_width` (100px)
- ✅ Height ≥ `min_height` (100px)
- ✅ Aspect ratio between `min_aspect` (0.3) and `max_aspect` (3.0)
- ✅ Visual content detection (not a blank/progress bar/UI element)

### 4. Save With Optimal Format
```python
@staticmethod
def _save(img: Image.Image, dest: Path) -> Path:
    if img.mode == "RGBA":  # Has transparency
        p = dest.with_suffix(".png")
        img.save(p, "PNG")
    else:  # No transparency
        p = dest.with_suffix(".jpg")
        img.convert("RGB").save(p, "JPEG", quality=95)
    return p
```

**Format Selection**:
- **PNG**: If image has transparency (RGBA mode)
- **JPEG**: If image has no transparency (convert RGB)
- **High quality**: JPEG quality=95 for best visual fidelity

## 📊 Quality Scoring

### Simple Scoring (fallback)
```python
def _score(r: ImageResult) -> float:
    s = 0.0
    low = r.url.lower()
    
    # Format bonuses
    if ".png" in low:
        s += 10
    for d in ("shutterstock", "istockphoto", "gettyimages", "adobe"):
        if d in low:
            s += 5
    
    # Penalties
    if any(x in low for x in ("thumb", "small", "icon")):
        s -= 10
        
    # Engine trust
    s += {"duckduckgo": 3, "bing": 2, "google": 1}.get(r.source, 0)
    
    # Size bonus
    s += (r.width * r.height) / 1_000_000
    
    return s
```

### Advanced Scoring (with ImageQualityScorer)
When a scorer is provided, it uses multi-factor analysis including sharpness, contrast, and source reputation.

## 🛡️ Error Handling

### Graceful Degradation
```python
try:
    data = self._fetch(r.url)
    if data is None:
        continue  # Try next candidate
    
    # ... validation ...
    
    return DownloadResult(True, saved_path, r.url, metadata)
    
except Exception as exc:
    log.debug("Download failed for %s: %s", r.url[:50], exc)
    continue  # Try next candidate

log.warning("No image passed validation (%d candidates)", len(ranked))
return DownloadResult(False)  # All failed
```

**What happens**:
- If URL is unreachable → try next candidate
- If image too small → try next candidate
- If validation fails → try next candidate
- If all candidates fail → return failure result

## 🔗 Thread Safety

### Per-Thread Sessions
```python
@property
def session(self) -> requests.Session:
    s = getattr(self._local, "session", None)
    if s is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": DEFAULT_HEADERS["User-Agent"],
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        })
        self._local.session = s
    return s
```

**Why it matters**: 
- `requests.Session` is not thread-safe
- Each thread gets its own session
- Custom headers for image requests
- Better performance through connection pooling per thread

## 📈 Logging Output

**Success**:
```
INFO: Downloaded 800x600 from google (saved to: ad_0001.png)
```

**Validation Failures** (DEBUG level):
```
DEBUG: Download failed for https://example.com/img.jpg: Timeout
DEBUG: Image too small (50x50 < 100x100 min)
DEBUG: Aspect ratio 0.2 < 0.3 minimum
DEBUG: No visual content detected (std_dev: 3.2 < 10.0)
DEBUG: Duplicate image detected (hash: abc123)
```

**All Failed**:
```
WARNING: No image passed validation (15 candidates)
```

## 🎯 Real-World Example

### Scenario: Downloading a "Red Nike Shoes" Image

```python
search_results = [
    ImageResult(url="https://google.com/img1.jpg", source="google", width=800, height=600),
    ImageResult(url="https://bing.com/img2.png", source="bing", width=1200, height=800),
    ImageResult(url="https://small-thumb.jpg", source="google", width=50, height=50),
]

hashes = ThreadSafeSet()  # Shared across threads
downloader = ImageDownloader(cfg, hashes, timeout=10)

result = downloader.download_best(search_results, dest=Path("ad_0001.png"))
```

**What Happens**:

1. **Score candidates**:
   - img1.jpg: 12 points (JPEG, 800x600 = 0.48MP)
   - img2.png: 22 points (PNG +10, 1200x800 = 0.96MP)
   - small-thumb.jpg: -5 points (50x50 tiny, "thumb" keyword)

2. **Try img2.png first** (highest score):
   - ✅ Download successful
   - ✅ Dimensions: 1200x800 (pass)
   - ✅ Aspect ratio: 1.5 (pass)
   - ✅ Visual content: Yes (std_dev: 45.2)
   - ✅ Hash: new (not seen before)
   - ✅ Save as PNG (has transparency)
   - **SUCCESS!** → Return DownloadResult(True, path, url, metadata)

**Result Metadata**:
```python
DownloadResult(
    success=True,
    path=Path("output/images/ad_0001.png"),
    source_url="https://bing.com/img2.png",
    info={
        "width": 1200,
        "height": 800,
        "file_size": 245_832,
        "source_engine": "bing",
        "hash": "abc123def456"
    }
)
```

---

**Next**: [Image Cache](cache.md) → Avoid re-downloading images across product batches
