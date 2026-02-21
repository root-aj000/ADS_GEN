# Search Base Documentation

## File: [`search/base.py`](../../search/base.py)

## Overview

The `base.py` file defines the **foundation** for all search engines. It provides an abstract base class that every search engine (Google, Bing, DuckDuckGo) inherits from, along with common infrastructure for rate limiting and circuit breaking.

## Real-World Analogy

Think of the base class as a **template for a store**:
- Every store must have certain features (search capability)
- Every store has the same safety features (rate limiting, circuit breaker)
- But each store can implement things differently (Google vs Bing vs DuckDuckGo)

---

## ImageResult Data Class

**Purpose**: Represents a single image search result.

```python
@dataclass
class ImageResult:
    url: str           # Direct URL to the image
    source: str        # Which engine found it ("google", "bing", etc.)
    title: str = ""    # Image title/alt text
    width: int = 0     # Image width (if known)
    height: int = 0    # Image height (if known)
```

**Example**:
```python
result = ImageResult(
    url="https://example.com/images/pizza.jpg",
    source="google",
    title="Delicious Pizza Slice",
    width=1920,
    height=1080
)
```

---

## BaseSearchEngine Class

**Purpose**: Abstract base class that all search engines inherit from.

### Initialization

```python
class BaseSearchEngine:
    name: str = "base"  # Override in subclass
    
    def __init__(self, cfg: SearchConfig) -> None:
        self.cfg = cfg
        self.limiter = RateLimiter(cfg.rate_limit_per_sec)
        self.breaker = CircuitBreaker(
            threshold=cfg.breaker_threshold,
            cooldown=cfg.breaker_cooldown
        )
        self._local = threading.local()  # Thread-local storage
```

**Components**:

| Component | Purpose |
|-----------|---------|
| `limiter` | Prevents making too many requests too fast |
| `breaker` | Stops using engine if it fails repeatedly |
| `_local` | Thread-local storage for HTTP sessions |

---

### session Property

**Purpose**: Provides a thread-local HTTP session for connection pooling.

```python
@property
def session(self) -> requests.Session:
    s = getattr(self._local, "session", None)
    if s is None:
        s = requests.Session()
        s.headers.update(DEFAULT_HEADERS)
        self._local.session = s
    return s
```

**Why Thread-Local?**

Each worker thread gets its own session:
```
Thread 1 → Session 1 → HTTP connections
Thread 2 → Session 2 → HTTP connections
Thread 3 → Session 3 → HTTP connections
```

This prevents connection conflicts and improves performance.

---

### search() Method (Abstract)

**Purpose**: Must be implemented by each search engine.

```python
def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
    raise NotImplementedError  # Subclass must implement
```

**Subclasses must implement this method** to return a list of image URLs for the given query.

---

### safe_search() Method

**Purpose**: Wrapper that adds safety features around search.

```python
def safe_search(
    self,
    query: str,
    max_results: int = 50,
) -> List[ImageResult]:
```

**Flow**:
```
┌─────────────────────────────────────────────────────────────┐
│                     safe_search()                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Check circuit breaker                                    │
│     └── Is breaker open? → Return empty list (skip engine)  │
│                                                              │
│  2. Rate limit                                                │
│     └── Wait if necessary to respect rate limit             │
│                                                              │
│  3. Call search()                                            │
│     └── Subclass implementation                             │
│                                                              │
│  4. Handle result                                            │
│     ├── Success? → Record success, return results           │
│     └── Failure? → Record failure, return empty list        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Rate Limiting Concept

**Purpose**: Prevent making too many requests too quickly.

```python
class RateLimiter:
    def __init__(self, calls_per_second: float = 2.0) -> None:
        self._interval = 1.0 / calls_per_second  # 0.5 seconds between calls
        self._last = 0.0
        self._lock = threading.Lock()
    
    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            gap = now - self._last
            if gap < self._interval:
                time.sleep(self._interval - gap)  # Wait before proceeding
            self._last = time.monotonic()
```

**Example**:

If `rate_limit_per_sec = 2.0`:
```
Request 1 → Immediate (0.00s)
Request 2 → Wait (0.50s)
Request 3 → Wait (0.50s)
Request 4 → Wait (0.50s)
```

---

## Circuit Breaker Concept

**Purpose**: Stop using a failing engine to prevent wasting time.

```python
class CircuitBreaker:
    def __init__(
        self,
        threshold: int = 5,       # Failures before opening
        cooldown: float = 120.0,  # Seconds to wait before retry
    ) -> None:
        self._threshold = threshold
        self._cooldown = cooldown
        self._failures = 0
        self._opened_at: Optional[float] = None
        self._lock = threading.Lock()
```

**States**:

```
                    ┌──────────────┐
                    │    CLOSED    │  ← Normal operation
                    │  (working)   │
                    └──────┬───────┘
                           │
                    5 consecutive failures
                           │
                           ▼
                    ┌──────────────┐
                    │     OPEN     │  ← Not accepting requests
                    │  (broken)    │
                    └──────┬───────┘
                           │
                    Wait 120 seconds
                           │
                           ▼
                    ┌──────────────┐
                    │  HALF-OPEN   │  ← Try one request
                    │  (testing)   │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
         Success                    Failure
              │                         │
              ▼                         ▼
        Close circuit              Open circuit
```

**Why Use Circuit Breaker?**

Imagine Bing is down:
1. Without circuit breaker: Every request waits 30 seconds and times out
2. With circuit breaker: After 5 failures, skip Bing entirely for 2 minutes

---

## Configuration Parameters

From [`SearchConfig`](../config/settings.md):

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rate_limit_per_sec` | float | 2.0 | Maximum requests per second |
| `breaker_threshold` | int | 5 | Failures before circuit opens |
| `breaker_cooldown` | float | 120.0 | Seconds to wait before retrying |

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    BaseSearchEngine                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input:                                                      │
│  └── SearchConfig (rate limit, circuit breaker settings)    │
│                                                              │
│  Initialize:                                                 │
│  ├── RateLimiter(2.0 calls/sec)                             │
│  └── CircuitBreaker(5 failures, 120s cooldown)              │
│                                                              │
│  Subclass Implements:                                        │
│  └── search(query) → List[ImageResult]                      │
│                                                              │
│  Safety Wrapper:                                             │
│  safe_search(query)                                          │
│      ├── Check circuit breaker                              │
│      ├── Rate limit (wait if needed)                        │
│      ├── Call search(query)                                 │
│      └── Handle success/failure                             │
│                                                              │
│  Output:                                                     │
│  └── List[ImageResult] with URLs to download                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Inheritance Example

```python
# In search/google_engine.py
class GoogleEngine(BaseSearchEngine):
    name = "google"
    
    def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
        # Google-specific implementation
        url = f"https://www.google.com/search?q={query}&tbm=isch"
        resp = self.session.get(url)
        # ... parse response ...
        return results

# In search/bing_engine.py
class BingEngine(BaseSearchEngine):
    name = "bing"
    
    def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
        # Bing-specific implementation
        # ...
```

---

## Connected Files

| File | Relationship |
|------|--------------|
| [`search/manager.py`](manager.md) | Uses base class and subclasses |
| [`search/google_engine.py`](google_engine.md) | Inherits from BaseSearchEngine |
| [`search/bing_engine.py`](bing_engine.md) | Inherits from BaseSearchEngine |
| [`search/duckduckgo_engine.py`](duckduckgo_engine.md) | Inherits from BaseSearchEngine |
| [`config/settings.py`](../config/settings.md) | Provides SearchConfig |
| [`utils/concurrency.py`](../utils/concurrency.md) | Provides RateLimiter, CircuitBreaker |

---

## Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Define interface for all search engines |
| **Key Class** | `BaseSearchEngine` - abstract base class |
| **Safety Features** | Rate limiting, circuit breaker |
| **Thread Safety** | Thread-local sessions |

**Think of it as**: A blueprint for building search engines - every engine must follow this design, but can implement the details differently.
