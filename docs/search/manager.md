# Search Manager Documentation

## File: [`search/manager.py`](../../search/manager.py)

## Overview

The `manager.py` file provides the **SearchManager** class that coordinates searching across multiple search engines. It handles priority ordering, deduplication, and fallback behavior.

## Real-World Analogy

Think of the SearchManager as a **shopping assistant**:
- You ask for a product ("pizza image")
- The assistant checks multiple stores (Google, Bing, DuckDuckGo)
- They start with your preferred store
- If the first store doesn't have enough results, they try the next
- They remove duplicates and return the best options

---

## Engine Registry

```python
ENGINE_REGISTRY: Dict[str, Type[BaseSearchEngine]] = {
    "google": GoogleEngine,
    "duckduckgo": DuckDuckGoEngine,
    "bing": BingEngine,
}
```

**Purpose**: Maps engine names to their implementing classes.

**Usage**:
```python
engine_class = ENGINE_REGISTRY["google"]  # Returns GoogleEngine class
```

---

## SearchManager Class

### Initialization

```python
class SearchManager:
    def __init__(self, cfg: SearchConfig) -> None:
        self.cfg = cfg
        self.engines: Dict[str, BaseSearchEngine] = {
            name: ENGINE_REGISTRY[name](cfg) 
            for name in cfg.priority
        }
        self.downloaded_hashes = ThreadSafeSet()  # For deduplication
```

**What happens during initialization**:

```
cfg.priority = ["google", "duckduckgo", "bing"]

        ↓ Initialize each engine

self.engines = {
    "google": GoogleEngine(cfg),
    "duckduckgo": DuckDuckGoEngine(cfg),
    "bing": BingEngine(cfg)
}

        ↓ Create shared deduplication set

self.downloaded_hashes = ThreadSafeSet()
```

**Parameters**:

| Parameter | Type | Source | Description |
|-----------|------|--------|-------------|
| `cfg` | `SearchConfig` | [`config/settings.py`](../config/settings.md) | Search configuration |

---

### search() Method

**Purpose**: Search across all configured engines and return combined results.

```python
def search(
    self,
    query: str,
    max_results: int = 100,
) -> List[ImageResult]:
```

**Flow**:

```
┌─────────────────────────────────────────────────────────────┐
│                    search(query)                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Initialize                                               │
│     ├── combined = []  (results from all engines)           │
│     └── seen_urls = set()  (for deduplication)              │
│                                                              │
│  2. For each engine in priority order:                       │
│     │                                                        │
│     │  2a. Call engine                                       │
│     │      results = engine.safe_search(query)               │
│     │                                                        │
│     │  2b. Add new results                                   │
│     │      for result in results:                            │
│     │          if result.url not in seen_urls:               │
│     │              seen_urls.add(result.url)                 │
│     │              combined.append(result)                   │
│     │                                                        │
│     │  2c. Check if enough results                           │
│     │      if len(combined) >= min_results_fallback:         │
│     │          break  # Don't try more engines               │
│     │                                                        │
│     │  2d. Wait between engines                              │
│     │      sleep(inter_engine_delay)                         │
│     │                                                        │
│  3. Return top results                                       │
│     return combined[:max_results]                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Example Execution**:

```
Query: "pizza slice"
Priority: ["google", "duckduckgo", "bing"]
min_results_fallback: 10

Step 1: Try Google
├── Google returns 45 results
├── Add all 45 to combined
├── 45 >= 10? Yes, but continue for more variety
└── Wait 0.5 seconds

Step 2: Try DuckDuckGo
├── DuckDuckGo returns 30 results
├── 15 are duplicates → Add 15 new results
├── Total: 60 results
└── Wait 0.5 seconds

Step 3: Try Bing (skipped - already enough results)
└── Return first 100 results
```

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | (required) | Search term |
| `max_results` | `int` | 100 | Maximum results to return |

**Returns**: `List[ImageResult]` - Combined and deduplicated results.

---

## Deduplication

### URL-Level Deduplication

```python
seen_urls: Set[str] = set()

for r in batch:
    if r.url not in seen_urls:
        seen_urls.add(r.url)
        combined.append(r)
```

**Why?** Different engines might find the same image URL. We only want each URL once.

### Hash-Level Deduplication (Cross-Run)

```python
self.downloaded_hashes = ThreadSafeSet()

# When downloading
if not self.hashes.add(hash):
    continue  # Skip - already downloaded this exact image
```

**Why?** Even if URLs differ, the actual image content might be identical. The hash prevents re-downloading the same image content.

---

## Configuration Parameters

From [`SearchConfig`](../config/settings.md):

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `priority` | `List[str]` | `["google", "duckduckgo", "bing"]` | Engine priority order |
| `adv_search_term` | `str` | `"product image"` | Added to query for better results |
| `min_results_fallback` | `int` | 10 | Minimum results before trying next engine |
| `inter_engine_delay` | `float` | 0.5 | Seconds to wait between engines |

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SearchManager                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input:                                                      │
│  └── query: "pizza slice"                                   │
│                                                              │
│  Process:                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Google Engine                                        │    │
│  │ ├── safe_search("pizza slice")                      │    │
│  │ └── Returns: [url1, url2, url3, ...]                │    │
│  └─────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ DuckDuckGo Engine                                    │    │
│  │ ├── safe_search("pizza slice")                      │    │
│  │ └── Returns: [url3, url4, url5, ...]                │    │
│  └─────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│  Deduplication:                                              │
│  ├── Remove duplicate URLs                                  │
│  └── Keep unique results only                               │
│                                                              │
│  Output:                                                     │
│  └── [ImageResult(url1), ImageResult(url2), ...]            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Integration with Pipeline

```python
# In core/pipeline.py

# Initialize
self.search = SearchManager(cfg.search)

# Use in processing
results = self.search.search(query)
dl = self.download.download_best(results, tmp_img)
```

---

## Thread Safety

The `downloaded_hashes` set is thread-safe:

```python
self.downloaded_hashes = ThreadSafeSet()

# Multiple workers can safely:
self.downloaded_hashes.add(hash)  # Returns True if new, False if duplicate
```

This prevents multiple workers from downloading the same image.

---

## Connected Files

| File | Relationship |
|------|--------------|
| [`search/base.py`](base.md) | Base class for engines |
| [`search/google_engine.py`](google_engine.md) | Google implementation |
| [`search/bing_engine.py`](bing_engine.md) | Bing implementation |
| [`search/duckduckgo_engine.py`](duckduckgo_engine.md) | DuckDuckGo implementation |
| [`core/pipeline.py`](../core/pipeline.md) | Uses SearchManager |
| [`imaging/downloader.py`](../imaging/downloader.md) | Uses downloaded_hashes |
| [`config/settings.py`](../config/settings.md) | Provides SearchConfig |
| [`utils/concurrency.py`](../utils/concurrency.md) | Provides ThreadSafeSet |

---

## Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Coordinate searching across multiple engines |
| **Key Feature** | Priority ordering with fallback |
| **Deduplication** | URL-level and hash-level |
| **Thread Safety** | ThreadSafeSet for cross-worker dedup |

**Think of it as**: A shopping assistant that checks multiple stores for you, starting with your favorite, and removes duplicates from the results.
