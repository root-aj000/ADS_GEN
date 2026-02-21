# Pipeline Documentation

## File: [`core/pipeline.py`](../../core/pipeline.py)

## Overview

The `pipeline.py` file contains the **heart of the Ad Generator** - the `AdPipeline` class. This is the main orchestrator that coordinates all the work: reading CSV data, searching for images, downloading, processing, and creating final advertisements.

## Real-World Analogy

Think of the pipeline as a **factory assembly line**:

```
Raw Material (CSV Data)
        ↓
    Station 1: Read & Prepare Data
        ↓
    Station 2: Search for Images
        ↓
    Station 3: Download Best Image
        ↓
    Station 4: Remove Background
        ↓
    Station 5: Create Advertisement
        ↓
    Station 6: Save & Record
        ↓
    Finished Product (Ad Image)
```

Each "station" is handled by a different component, but the pipeline manages the entire flow.

---

## Classes and Functions

### 1. Stats Class

**Purpose**: Tracks processing statistics in real-time.

```python
class Stats:
    def __init__(self) -> None:
        self.total = AtomicCounter()        # Total processed
        self.success = AtomicCounter()      # Successfully created
        self.failed = AtomicCounter()       # Failed
        self.placeholder = AtomicCounter()  # Used placeholder image
        self.bg_removed = AtomicCounter()   # Backgrounds removed
        self.bg_skipped = AtomicCounter()   # Backgrounds kept
        self.skipped = AtomicCounter()      # Already done (resume)
        self.cache_hits = AtomicCounter()   # Cache hits
        self.dlq_retries = AtomicCounter()  # Dead-letter retries
        self.verified = AtomicCounter()     # CLIP verified
        self.verify_fails = AtomicCounter() # Verification failures
        self._t0 = time.monotonic()         # Start time
```

**Example Output** (from `report()` method):

```
============================================================
📊 PIPELINE REPORT
────────────────────────────────────────────────────────────
 Processed : 150
 Success : 142
 Failed : 8
 Placeholders : 3
 BG removed : 89
 BG skipped : 53
 Cache hits : 45
 DLQ retries : 2
 Verified (CLIP) : 130
 Verify rejects : 12
 Already done : 0
 Elapsed : 234.5s
 Throughput : 0.64 ads/s
============================================================
```

---

### 2. build_query() Function

**Purpose**: Creates a search query from CSV row data.

```python
def build_query(row: pd.Series, cfg: QueryConfig) -> str:
```

**How It Works**:

```
CSV Row:
┌─────────────────┬──────────────────┬─────────────────────┐
│ img_desc        │ keywords         │ text                │
├─────────────────┼──────────────────┼─────────────────────┤
│ "pizza slice"   │ "food, italian"  │ "Delicious pizza"   │
└─────────────────┴──────────────────┴─────────────────────┘
                ↓
        Try columns in order:
        1. img_desc → "pizza slice" ✓
                ↓
        Return: "pizza slice"
```

**Parameters**:

| Parameter | Type | Source | Description |
|-----------|------|--------|-------------|
| `row` | `pd.Series` | CSV row | One row from input CSV |
| `cfg` | `QueryConfig` | [`config/settings.py`](../config/settings.md) | Query configuration |

**Returns**: A cleaned search query string.

---

### 3. AdPipeline Class

**Purpose**: Main processing orchestrator.

#### Initialization

```python
class AdPipeline:
    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        cfg.paths.ensure()      # Create folders
        cfg.validate()          # Validate settings
        
        # Load CSV data
        self.df = pd.read_csv(cfg.paths.csv_input)
        
        # Initialize components
        self.search = SearchManager(cfg.search)
        self.scorer = ImageQualityScorer(cfg.quality)
        self.download = ImageDownloader(...)
        self.bg = BackgroundRemover(cfg.bg)
        self.comp = AdCompositor(cfg.paths.fonts_dir)
        self.progress = ProgressManager(cfg.paths.progress_db)
        self.stats = Stats()
        self.notifier = Notifier(cfg.notify)
        self.health = HealthMonitor() if cfg.enable_health else None
        self.cache = ImageCache(cfg.paths.cache_db) if cfg.enable_cache else None
        self.verifier = ImageVerifier(cfg.verify) if cfg.verify.use_clip else None
```

**Component Overview**:

| Component | Purpose | Documentation |
|-----------|---------|---------------|
| `SearchManager` | Search for images | [search/manager.md](../search/manager.md) |
| `ImageQualityScorer` | Score image quality | [imaging/scorer.md](../imaging/scorer.md) |
| `ImageDownloader` | Download images | [imaging/downloader.md](../imaging/downloader.md) |
| `BackgroundRemover` | Remove backgrounds | [imaging/background.md](../imaging/background.md) |
| `AdCompositor` | Create final ads | [compositor.md](compositor.md) |
| `ProgressManager` | Track progress | [progress.md](progress.md) |
| `Notifier` | Send notifications | [notifications/notifier.md](../notifications/notifier.md) |
| `HealthMonitor` | Monitor engine health | [health.md](health.md) |
| `ImageCache` | Cache downloaded images | [imaging/cache.md](../imaging/cache.md) |
| `ImageVerifier` | AI image verification | [imaging/verifier.md](../imaging/verifier.md) |

---

#### _process() Method

**Purpose**: Process a single CSV row (create one advertisement).

```python
def _process(self, idx: int) -> Dict[str, Any]:
```

**Step-by-Step Flow**:

```
┌─────────────────────────────────────────────────────────────┐
│                    _process(idx=42)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  0. CHECK CACHE                                              │
│     ├── Cache hit? → Use cached image                        │
│     └── Cache miss? → Continue to search                     │
│                                                              │
│  1. SEARCH + DOWNLOAD                                        │
│     ├── search.search(query) → List of image URLs            │
│     ├── download.download_best(results) → Downloaded image   │
│     ├── If failed, try fallback query                        │
│     └── If still failed, create placeholder                  │
│                                                              │
│  2. VERIFY (if enabled)                                      │
│     ├── CLIP: Check image matches query                      │
│     ├── BLIP: Generate caption, compare with query           │
│     └── Reject if score too low                              │
│                                                              │
│  3. BACKGROUND REMOVAL                                       │
│     ├── should_remove(query)? → Check if scene keyword       │
│     ├── Yes → Remove background                              │
│     └── No → Keep original                                   │
│                                                              │
│  4. COMPOSE                                                  │
│     └── comp.compose(...) → Create final 1080x1080 ad        │
│                                                              │
│  5. UPDATE DATA                                              │
│     ├── Save image path to DataFrame                         │
│     └── Mark progress as done                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `idx` | `int` | Row index in the DataFrame |

**Returns**:

```python
{
    "id": 42,
    "success": True,
    "query": "pizza slice",
    "filename": "ad_0043.jpg",
    "source": "google",
    "clip_score": 0.85,
    "blip_score": 0.72
}
```

---

#### run() Method

**Purpose**: Main entry point - process all rows.

```python
def run(self) -> None:
```

**Flow**:

```
┌─────────────────────────────────────────────────────────────┐
│                        run()                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Determine which rows to process                          │
│     ├── Get all indices                                      │
│     └── If resume mode, filter out completed rows            │
│                                                              │
│  2. Process in chunks (memory control)                       │
│     for chunk in range(0, len(indices), CHUNK_SIZE):         │
│         └── _run_indices(chunk)                              │
│                                                              │
│  3. Dead-letter queue (retry failures)                       │
│     └── _run_indices(failed_rows)                            │
│                                                              │
│  4. Final reports                                            │
│     ├── Save CSV                                             │
│     ├── Log health report                                    │
│     ├── Log cache stats                                      │
│     ├── Log progress stats                                   │
│     ├── Log pipeline report                                  │
│     └── Send notifications                                   │
│                                                              │
│  5. Cleanup                                                  │
│     └── Remove temp files                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Processing Flow Diagram

```
                        ┌──────────────┐
                        │   main.py    │
                        │   calls      │
                        │ pipeline.run()│
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │ Load CSV     │
                        │ (main.csv)   │
                        └──────┬───────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │ For each row in CSV (parallel) │
               └───────────────┬───────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │ Worker 1│           │ Worker 2│           │ Worker N│
   │ Row 0   │           │ Row 1   │           │ Row N   │
   └────┬────┘           └────┬────┘           └────┬────┘
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │ Search  │           │ Search  │           │ Search  │
   │ Images  │           │ Images  │           │ Images  │
   └────┬────┘           └────┬────┘           └────┬────┘
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │Download │           │Download │           │Download │
   │ Image   │           │ Image   │           │ Image   │
   └────┬────┘           └────┬────┘           └────┬────┘
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │ Verify  │           │ Verify  │           │ Verify  │
   │ (CLIP)  │           │ (CLIP)  │           │ (CLIP)  │
   └────┬────┘           └────┬────┘           └────┬────┘
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │ Remove  │           │ Remove  │           │ Remove  │
   │Background│          │Background│          │Background│
   └────┬────┘           └────┬────┘           └────┬────┘
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │ Compose │           │ Compose │           │ Compose │
   │   Ad    │           │   Ad    │           │   Ad    │
   └────┬────┘           └────┬────┘           └────┬────┘
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │ Save    │           │ Save    │           │ Save    │
   │ad_0001.jpg│         │ad_0002.jpg│         │ad_000N.jpg│
   └─────────┘           └─────────┘           └─────────┘
```

---

## Configuration Parameters Used

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cfg.paths.csv_input` | Path | `data/input/main.csv` | Input CSV file |
| `cfg.paths.csv_output` | Path | `data/output/ads_with_images.csv` | Output CSV file |
| `cfg.paths.images_dir` | Path | `data/output/images/` | Output images folder |
| `cfg.paths.temp_dir` | Path | `data/temp/workers/` | Temporary files folder |
| `cfg.pipeline.max_workers` | int | 4 | Number of parallel workers |
| `cfg.pipeline.csv_save_interval` | int | 5 | Save CSV every N ads |
| `cfg.pipeline.worker_timeout` | int | 300 | Worker timeout in seconds |
| `cfg.resume` | bool | False | Resume from last run |
| `cfg.dry_run` | bool | False | Skip compositing |
| `cfg.enable_cache` | bool | True | Use image cache |
| `cfg.enable_dlq` | bool | True | Retry failed rows |
| `cfg.chunk_size` | int | 50 | Rows per chunk |

---

## Thread Safety

The pipeline uses several thread-safe constructs:

| Component | Purpose |
|-----------|---------|
| `AtomicCounter` | Thread-safe counting |
| `threading.Lock` | Protects DataFrame writes |
| `threading.Event` | Graceful shutdown signal |

```python
# Example: Thread-safe CSV save
def _save_csv(self) -> None:
    with self._df_lock:  # Only one thread at a time
        tmp = self.cfg.paths.csv_output.with_suffix(".tmp")
        self.df.to_csv(tmp, index=False)
        tmp.replace(self.cfg.paths.csv_output)
```

---

## Graceful Shutdown

The pipeline handles Ctrl+C gracefully:

```python
def _on_signal(self, signum: int, _: Any) -> None:
    log.warning("Signal %d — shutting down gracefully", signum)
    self._shutdown.set()  # Signal all workers to stop
```

When you press Ctrl+C:
1. Workers finish their current task
2. No new tasks start
3. Progress is saved
4. Clean exit

---

## Connected Files

| File | Relationship |
|------|--------------|
| [`config/settings.py`](../config/settings.md) | Provides configuration |
| [`core/compositor.py`](compositor.md) | Creates final ads |
| [`core/progress.py`](progress.md) | Tracks progress |
| [`core/health.py`](health.md) | Monitors engine health |
| [`search/manager.py`](../search/manager.md) | Searches for images |
| [`imaging/downloader.py`](../imaging/downloader.md) | Downloads images |
| [`imaging/background.py`](../imaging/background.md) | Removes backgrounds |
| [`imaging/verifier.py`](../imaging/verifier.md) | Verifies images with AI |
| [`imaging/cache.py`](../imaging/cache.md) | Caches images |
| [`imaging/scorer.py`](../imaging/scorer.md) | Scores image quality |
| [`notifications/notifier.py`](../notifications/notifier.md) | Sends notifications |
| [`utils/concurrency.py`](../utils/concurrency.md) | Thread-safe utilities |

---

## Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Main orchestrator for ad generation |
| **Input** | CSV file with product data |
| **Output** | Generated advertisement images |
| **Key Method** | `run()` - processes all rows |
| **Parallelism** | Uses ThreadPoolExecutor with configurable workers |
| **Progress Tracking** | SQLite database with resume capability |

**Think of it as**: The conductor of an orchestra - it doesn't play any instruments itself, but it coordinates all the musicians (components) to create a symphony (advertisement).
