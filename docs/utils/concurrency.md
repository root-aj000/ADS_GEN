# Concurrency Utilities

**File**: [`utils/concurrency.py`](utils/concurrency.py)  
**Purpose**: Thread-safe primitives for concurrent/parallel processing in the Ad Generator pipeline.

## 🎯 What It Does

The concurrency module provides thread-safe data structures that enable multiple threads to work together safely. When the pipeline processes multiple products simultaneously, these utilities prevent race conditions and data corruption.

Think of them as **traffic controllers** for your data:
1. ✅ `AtomicCounter` - Safe counting across threads
2. ✅ `ThreadSafeSet` - Deduplication without races
3. ✅ `RateLimiter` - Control request speed
4. ✅ `CircuitBreaker` - Fail-fast after repeated errors

## 🔧 Classes Overview

```
┌─────────────────────────────────────────────────────────────┐
│                 Concurrency Utilities                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐  ┌─────────────────┐
│  AtomicCounter  │  │  ThreadSafeSet  │
│                 │  │                 │
│ • increment()   │  │ • add()         │
│ • value         │  │ • __contains__  │
│                 │  │ • __len__       │
└─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐
│   RateLimiter   │ │  CircuitBreaker │
│                 │  │                 │
│ • wait()        │  │ • record_success│
│                 │  │ • record_failure│
│                 │  │ • is_open       │
└─────────────────┘  └─────────────────┘
```

---

## 1. AtomicCounter

**Purpose**: Thread-safe integer counter for tracking progress across multiple threads.

### Class Definition

```python
class AtomicCounter:
    """Thread-safe integer counter."""
    
    def __init__(self, initial: int = 0) -> None:
        self._value = initial
        self._lock = threading.Lock()
    
    def increment(self, n: int = 1) -> int:
        """Add n to counter. Returns new value."""
        with self._lock:
            self._value += n
            return self._value
    
    @property
    def value(self) -> int:
        """Get current value."""
        with self._lock:
            return self._value
```

### Why Thread-Safe?

**Without AtomicCounter (race condition)**:
```python
# Two threads try to increment at the same time
counter = 0

# Thread 1: reads counter = 0
# Thread 2: reads counter = 0  
# Thread 1: writes counter = 1
# Thread 2: writes counter = 1  # Should be 2!

print(counter)  # 1 (WRONG - should be 2)
```

**With AtomicCounter (correct)**:
```python
counter = AtomicCounter(0)

# Thread 1: counter.increment() → 1
# Thread 2: counter.increment() → 2

print(counter.value)  # 2 (CORRECT)
```

### Usage in Pipeline

```python
# In core/pipeline.py
class Stats:
    def __init__(self):
        self.processed = AtomicCounter(0)
        self.success = AtomicCounter(0)
        self.failed = AtomicCounter(0)

def _process(idx: int) -> Dict[str, Any]:
    stats.processed.increment()
    try:
        # ... process product ...
        stats.success.increment()
    except Exception:
        stats.failed.increment()
        raise
```

### Real-World Analogy

Think of `AtomicCounter` like a **ticket dispenser** at a deli counter. Only one person can take a ticket at a time, ensuring each number is given out exactly once in the correct order.

---

## 2. ThreadSafeSet

**Purpose**: Thread-safe string set for deduplication across threads.

### Class Definition

```python
class ThreadSafeSet:
    """Thread-safe ``set[str]`` for deduplication."""
    
    def __init__(self) -> None:
        self._data: Set[str] = set()
        self._lock = threading.Lock()
    
    def add(self, item: str) -> bool:
        """Add item. Returns True if it was NEW."""
        with self._lock:
            if item in self._data:
                return False  # Already exists
            self._data.add(item)
            return True  # Added successfully
    
    def __contains__(self, item: str) -> bool:
        with self._lock:
            return item in self._data
    
    def __len__(self) -> int:
        with self._lock:
            return len(self._data)
```

### Key Method: add()

Returns `True` if the item was **new** (added), `False` if it **already existed**:

```python
hashes = ThreadSafeSet()

# First time - returns True (item was new)
hashes.add("abc123")  # True

# Second time - returns False (already exists)
hashes.add("abc123")  # False

# Different hash - returns True
hashes.add("def456")  # True

print(len(hashes))  # 2
```

### Usage in Downloader

```python
# In imaging/downloader.py
class ImageDownloader:
    def __init__(self, cfg, hashes: ThreadSafeSet):
        self.hashes = hashes  # Shared across all threads
    
    def download_best(self, results, dest):
        for r in results:
            data = self._fetch(r.url)
            h = hashlib.md5(data).hexdigest()
            
            # Check for duplicate (thread-safe!)
            if not self.hashes.add(h):
                continue  # Already downloaded, skip
            
            # Process new image...
```

### Real-World Analogy

Think of `ThreadSafeSet` like a **guest list at an exclusive club**. The bouncer checks if someone is already on the list before letting them in. Multiple bouncers (threads) can check the list, but only one can write on it at a time.

---

## 3. RateLimiter

**Purpose**: Token-bucket rate limiter to control request speed.

### Class Definition

```python
class RateLimiter:
    """Token-bucket rate limiter shared across threads."""
    
    def __init__(self, calls_per_second: float = 2.0) -> None:
        self._interval = 1.0 / calls_per_second
        self._last = 0.0
        self._lock = threading.Lock()
    
    def wait(self) -> None:
        """Block until rate limit allows next call."""
        with self._lock:
            now = time.monotonic()
            gap = now - self._last
            
            if gap < self._interval:
                # Too soon - sleep for remaining time
                time.sleep(self._interval - gap)
            
            self._last = time.monotonic()
```

### How It Works

```
Rate: 2 calls per second (interval = 0.5s)

Timeline:
────────────────────────────────────────────────────────►
     │                    │                    │
     │                    │                    │
   Call 1              Call 2              Call 3
     │                    │                    │
     │    0.5s wait       │    0.3s wait       │
     │◄──────────────────►│◄──────────────────►│
                          │                    │
                       Allowed             Must wait
                       immediately         0.2s more
```

### Usage in Search Engines

```python
# In search/base.py
class BaseSearchEngine:
    def __init__(self, cfg: SearchConfig):
        self.rates = RateLimiter(cfg.requests_per_second)
    
    def safe_search(self, query: str, max_results: int):
        self.rates.wait()  # Block if too fast
        return self.search(query, max_results)
```

### Real-World Analogy

Think of `RateLimiter` like a **traffic light** that turns green at fixed intervals. You have to wait for the green light before proceeding, ensuring a steady flow of traffic.

---

## 4. CircuitBreaker

**Purpose**: Fail-fast after repeated errors (prevents cascading failures).

### Class Definition

```python
class CircuitBreaker:
    """
    After *threshold* consecutive failures the engine is
    disabled for *cooldown* seconds.
    """
    
    def __init__(
        self,
        threshold: int = 5,      # Failures before opening
        cooldown: float = 120.0,  # Seconds to wait before retry
    ) -> None:
        self._threshold = threshold
        self._cooldown = cooldown
        self._failures = 0
        self._opened_at: Optional[float] = None
        self._lock = threading.Lock()
    
    def record_success(self) -> None:
        """Reset failure count."""
        with self._lock:
            self._failures = 0
            self._opened_at = None
    
    def record_failure(self) -> None:
        """Increment failure count, open if threshold reached."""
        with self._lock:
            self._failures += 1
            if self._failures >= self._threshold:
                self._opened_at = time.monotonic()
                log.warning("Circuit breaker OPEN (failures=%d)", self._failures)
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is currently open (failing fast)."""
        with self._lock:
            if self._opened_at is None:
                return False  # Closed - operating normally
            
            # Check if cooldown period has passed
            if time.monotonic() - self._opened_at > self._cooldown:
                log.info("Circuit breaker half-open — allowing retry")
                self._opened_at = None
                self._failures = 0
                return False  # Half-open - allowing one retry
            
            return True  # Open - failing fast
```

### Circuit States

```
┌─────────────────────────────────────────────────────────────┐
│                    Circuit Breaker States                   │
└─────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │     CLOSED      │
                    │  (operating)    │
                    │                 │
                    │  failures = 0   │
                    │  Normal flow    │
                    └────────┬────────┘
                             │
                    failures >= threshold
                             │
                             ▼
                    ┌─────────────────┐
                    │      OPEN       │
                    │  (failing fast) │
                    │                 │
                    │  Fail immediately│
                    │  No API calls   │
                    └────────┬────────┘
                             │
                    cooldown expires
                             │
                             ▼
                    ┌─────────────────┐
                    │   HALF-OPEN     │
                    │  (testing)      │
                    │                 │
                    │  Allow 1 retry  │
                    │  → success: close│
                    │  → failure: open│
                    └─────────────────┘
```

### Usage in Search Engines

```python
# In search/base.py
class BaseSearchEngine:
    def __init__(self, cfg: SearchConfig):
        self.breaker = CircuitBreaker(threshold=5, cooldown=60.0)
    
    def safe_search(self, query: str, max_results: int):
        # Check circuit breaker first
        if self.breaker.is_open:
            log.warning("Circuit breaker open, skipping search")
            return []
        
        try:
            results = self.search(query, max_results)
            self.breaker.record_success()
            return results
        except Exception as e:
            self.breaker.record_failure()
            raise
```

### Real-World Analogy

Think of `CircuitBreaker` like an **electrical fuse** in your house. If too many appliances overload the circuit, the fuse trips (opens) to prevent a fire. After fixing the problem and waiting, you reset the fuse (close) to restore power.

---

## 📊 Comparison Table

| Feature | AtomicCounter | ThreadSafeSet | RateLimiter | CircuitBreaker |
|---------|---------------|---------------|-------------|----------------|
| **Purpose** | Count items | Deduplicate | Limit speed | Fail fast |
| **Thread-safe?** | ✅ | ✅ | ✅ | ✅ |
| **Blocking?** | No | No | Yes (wait) | No (check only) |
| **Used in** | Pipeline stats | Downloader | Search engines | Search engines |
| **Analogy** | Ticket dispenser | Guest list | Traffic light | Electrical fuse |

## 🔗 Where Each Is Used

```
AtomicCounter:
    └── core/pipeline.py (Stats class)
        ├── processed count
        ├── success count
        └── failed count

ThreadSafeSet:
    └── core/pipeline.py → imaging/downloader.py
        └── Image hash deduplication

RateLimiter:
    └── search/base.py
        └── API request throttling

CircuitBreaker:
    └── search/base.py
        └── Engine failure protection
```

---

**Next**: [Exceptions](exceptions.md) → Custom error types
