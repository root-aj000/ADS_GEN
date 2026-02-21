# Utils Module Overview

The `utils/` module provides shared utility functions and classes used across the entire Ad Generator project. These are the building blocks that enable thread-safe operations, error handling, logging, and text processing.

## 📁 Module Structure

```
utils/
├── __init__.py         # Module exports
├── exceptions.py       # Custom exception hierarchy
├── concurrency.py      # Thread-safe primitives
├── log_config.py       # Centralized logging setup
├── retry.py            # Retry decorator with backoff
└── text_cleaner.py     # Text cleaning utilities
```

## 🎯 Purpose

The utils module provides the "glue" that holds the application together:

| Component | Purpose | Used By |
|-----------|---------|---------|
| **Exceptions** | Custom error types for specific failure modes | All modules |
| **Concurrency** | Thread-safe data structures for parallel processing | Pipeline, Search, Imaging |
| **Logging** | Centralized logging configuration | All modules |
| **Retry** | Automatic retry with exponential backoff | Downloader, Search |
| **Text Cleaner** | Query sanitization and cleaning | Pipeline, Search |

## 🔄 How Utils Connects to Other Modules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           UTILS MODULE CONNECTIONS                          │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │    utils/       │
                              └────────┬────────┘
                                   │
       ┌───────────────────────────┼───────────────────────────┐
       │                           │                           │
       ▼                           ▼                           ▼
┌─────────────┐           ┌─────────────┐           ┌─────────────┐
│ exceptions  │           │ concurrency │           │ log_config  │
│             │           │             │           │             │
│ • AdGenError│           │ • AtomicCntr│           │ • setup_root│
│ • SearchErr │           │ • ThreadSet │           │ • get_logger│
│ • DownloadErr│          │ • RateLimit │           │             │
│ • BGError   │           │ • CircuitBrk│           │             │
│ • ConfigErr │           │             │           │             │
└──────┬──────┘           └──────┬──────┘           └──────┬──────┘
       │                         │                         │
       │         ┌───────────────┼───────────────┐         │
       │         │               │               │         │
       ▼         ▼               ▼               ▼         ▼
┌─────────────────────────────────────────────────────────────────┐
│                        core/pipeline.py                         │
│  Uses: exceptions, AtomicCounter, ThreadSafeSet, get_logger    │
└─────────────────────────────────────────────────────────────────┘
       │
       ├──────────────────────┬──────────────────────┐
       ▼                      ▼                      ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   search/   │       │  imaging/   │       │     core/   │
│             │       │             │       │             │
│ RateLimiter │       │ ThreadSet   │       │ All utils   │
│ CircuitBrk  │       │ get_logger  │       │             │
│ retry       │       │ retry       │       │             │
└─────────────┘       └─────────────┘       └─────────────┘
```

## 🧩 Components at a Glance

### 1. Exceptions (`exceptions.py`)

Custom exception hierarchy for specific error handling:

```python
AdGenError (base)
├── SearchExhaustedError    # All search engines failed
├── ImageDownloadError      # Download/validation failed
├── BackgroundRemovalError  # rembg processing failed
└── ConfigurationError      # Invalid config
```

**Usage**:
```python
from utils.exceptions import SearchExhaustedError, ImageDownloadError

try:
    results = search_manager.search(query)
    if not results:
        raise SearchExhaustedError(f"No results for: {query}")
except SearchExhaustedError:
    # Handle gracefully
    pass
```

### 2. Concurrency (`concurrency.py`)

Thread-safe primitives for parallel processing:

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| `AtomicCounter` | Thread-safe integer counter | `increment()`, `value` |
| `ThreadSafeSet` | Thread-safe string set for deduplication | `add()`, `__contains__` |
| `RateLimiter` | Token-bucket rate limiting | `wait()` |
| `CircuitBreaker` | Fail-fast after repeated errors | `record_success()`, `record_failure()`, `is_open` |

### 3. Logging (`log_config.py`)

Centralized logging with consistent format:

```python
from utils.log_config import get_logger, setup_root

# Setup at application start
setup_root(Path("logs/adgen.log"), verbose=False)

# Use in any module
log = get_logger(__name__)
log.info("Processing product: %s", product_name)
```

**Log Format**:
```
14:32:15 │ INFO    │ ThreadPool-1   │ core.pipeline     │ Processing row 42
```

### 4. Retry (`retry.py`)

Automatic retry with exponential backoff:

```python
from utils.retry import retry

@retry(max_attempts=3, backoff_base=1.0, exceptions=(RequestException,))
def fetch_url(url: str):
    return requests.get(url)
```

### 5. Text Cleaner (`text_cleaner.py`)

Query sanitization for better search results:

```python
from utils.text_cleaner import clean_query, is_valid_query

query = clean_query("  RED  NIKE  SHOES!!!  ", ignore_values=("N/A", "NULL"))
# Returns: "red nike shoes"

if is_valid_query(query, ignore_values=("N/A", "NULL")):
    # Proceed with search
```

## ⚡ Quick Reference

### Common Patterns

#### Thread-Safe Counter
```python
from utils.concurrency import AtomicCounter

processed = AtomicCounter(0)

def worker():
    # ... process item ...
    count = processed.increment()
    print(f"Processed {count} items")
```

#### Deduplication Set
```python
from utils.concurrency import ThreadSafeSet

seen_hashes = ThreadSafeSet()

def process_image(image_data):
    h = hashlib.md5(image_data).hexdigest()
    if not seen_hashes.add(h):  # Returns False if already exists
        return  # Skip duplicate
    # Process new image...
```

#### Rate Limiting
```python
from utils.concurrency import RateLimiter

limiter = RateLimiter(calls_per_second=2.0)

for url in urls:
    limiter.wait()  # Blocks if called too fast
    fetch(url)
```

#### Circuit Breaker
```python
from utils.concurrency import CircuitBreaker

breaker = CircuitBreaker(threshold=5, cooldown=60.0)

def call_api():
    if breaker.is_open:
        raise Exception("Circuit breaker open - too many failures")
    
    try:
        result = api.request()
        breaker.record_success()
        return result
    except Exception:
        breaker.record_failure()
        raise
```

#### Retry with Backoff
```python
from utils.retry import retry

@retry(max_attempts=3, backoff_base=0.5, exceptions=(ConnectionError,))
def download_with_retry(url):
    return requests.get(url, timeout=10)
```

## 📊 Module Dependencies

```
utils/
    ├── No internal dependencies (standalone)
    └── External: threading, time, logging, hashlib

Used by:
    ├── config/ (get_logger)
    ├── core/ (all utils)
    ├── search/ (RateLimiter, CircuitBreaker, retry, get_logger)
    ├── imaging/ (ThreadSafeSet, retry, get_logger)
    └── notifications/ (get_logger)
```

---

**Next**: [Exceptions](exceptions.md) → Custom error types
