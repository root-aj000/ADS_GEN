# Health Monitor Documentation

## File: [`core/health.py`](../../core/health.py)

## Overview

The `health.py` file provides **real-time health tracking** for search engines. It monitors how well each search engine is performing - success rate, response time, and number of results returned.

## Real-World Analogy

Think of the health monitor as a **fitness tracker for search engines**:
- It records how fast each engine responds (like heart rate)
- It tracks success/failure rates (like steps taken)
- It can suggest which engine is "healthiest" to use first

---

## EngineMetrics Data Class

**Purpose**: Stores performance data for a single search engine.

```python
@dataclass
class EngineMetrics:
    total_calls: int = 0        # Total number of API calls
    total_results: int = 0      # Total images found
    successes: int = 0          # Successful calls
    failures: int = 0           # Failed calls
    total_latency: float = 0.0  # Total response time
    last_call: float = 0.0      # Timestamp of last call
    last_error: str = ""        # Last error message
```

### Computed Properties

```python
@property
def success_rate(self) -> float:
    """Percentage of successful calls (0.0 to 1.0)"""
    return self.successes / max(self.total_calls, 1)

@property
def avg_latency(self) -> float:
    """Average response time in seconds"""
    return self.total_latency / max(self.successes, 1)

@property
def avg_results(self) -> float:
    """Average number of results per call"""
    return self.total_results / max(self.successes, 1)
```

---

## HealthMonitor Class

### Initialization

```python
class HealthMonitor:
    """Thread-safe engine health tracker."""
    
    def __init__(self) -> None:
        self._metrics: Dict[str, EngineMetrics] = defaultdict(EngineMetrics)
        self._lock = threading.Lock()
```

---

### record_call() Method

**Purpose**: Record a search engine call result.

```python
def record_call(
    self,
    engine: str,           # Engine name ("google", "bing", "duckduckgo")
    success: bool,         # Did the call succeed?
    result_count: int = 0, # How many images found?
    latency: float = 0.0,  # Response time in seconds
    error: str = "",       # Error message if failed
) -> None:
```

**Example Usage**:
```python
# Successful call to Google
health.record_call(
    engine="google",
    success=True,
    result_count=45,
    latency=1.23
)

# Failed call to Bing
health.record_call(
    engine="bing",
    success=False,
    error="Connection timeout"
)
```

---

### get_report() Method

**Purpose**: Get a summary report of all engines.

```python
def get_report(self) -> Dict[str, Dict]:
```

**Returns**:
```python
{
    "google": {
        "calls": 50,
        "success_rate": "98.0%",
        "avg_latency": "1.23s",
        "avg_results": "42.5",
        "failures": 1,
        "last_error": ""
    },
    "duckduckgo": {
        "calls": 30,
        "success_rate": "100.0%",
        "avg_latency": "0.89s",
        "avg_results": "35.2",
        "failures": 0,
        "last_error": ""
    },
    "bing": {
        "calls": 10,
        "success_rate": "60.0%",
        "avg_latency": "2.50s",
        "failures": 4,
        "last_error": "Connection timeout"
    }
}
```

---

### log_report() Method

**Purpose**: Print a formatted health report to the log.

```python
def log_report(self) -> None:
```

**Example Output**:
```
─── Engine Health ───
 google       │ calls=50   │ success=98.0% │ latency=1.23s  │ avg_results=42.5  │ failures=1
 duckduckgo   │ calls=30   │ success=100.0%│ latency=0.89s  │ avg_results=35.2  │ failures=0
 bing         │ calls=10   │ success=60.0% │ latency=2.50s  │ avg_results=20.0  │ failures=4
────────────────────────────────────────────────────────────────────────────────────────
```

---

### suggest_priority() Method

**Purpose**: Suggest the best engine order based on performance.

```python
def suggest_priority(self) -> List[str]:
```

**Scoring Formula**:
```python
score = (
    success_rate * 50      # High success rate is good
    + avg_results * 2      # More results is good
    - avg_latency * 5      # Slower response is bad
)
```

**Returns**: List of engine names sorted by score (best first).

**Example**:
```python
suggested = health.suggest_priority()
# ["duckduckgo", "google", "bing"]  # DuckDuckGo performing best
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    HealthMonitor                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input:                                                      │
│  └── Search engine call results                             │
│                                                              │
│  Recording:                                                  │
│  record_call("google", success=True, result_count=45, ...)  │
│      ↓                                                       │
│  EngineMetrics["google"]                                     │
│      ├── total_calls += 1                                   │
│      ├── successes += 1                                     │
│      ├── total_results += 45                                │
│      └── total_latency += 1.23                              │
│                                                              │
│  Reporting:                                                  │
│  get_report() → {"google": {...}, "bing": {...}, ...}       │
│  log_report() → Pretty printed table                        │
│  suggest_priority() → ["duckduckgo", "google", "bing"]      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Integration with Pipeline

```python
# In core/pipeline.py

# Initialize health monitor
self.health = HealthMonitor() if cfg.enable_health else None

# Record search results
if self.health:
    t0 = time.monotonic()
    results = self.search.search(query)
    
    for eng_name in self.cfg.search.priority:
        eng_results = [r for r in results if r.source == eng_name]
        if eng_results:
            self.health.record_call(
                eng_name,
                True,
                len(eng_results),
                time.monotonic() - t0
            )

# At end of run
if self.health:
    self.health.log_report()
```

---

## Thread Safety

The health monitor uses a lock to ensure thread-safe updates:

```python
def record_call(self, engine: str, success: bool, ...) -> None:
    with self._lock:  # Only one thread at a time
        m = self._metrics[engine]
        m.total_calls += 1
        # ... update metrics ...
```

This prevents race conditions when multiple workers try to record metrics simultaneously.

---

## Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cfg.enable_health` | bool | `True` | Enable health monitoring |

---

## Connected Files

| File | Relationship |
|------|--------------|
| [`core/pipeline.py`](pipeline.md) | Records search engine calls |
| [`config/settings.py`](../config/settings.md) | Provides configuration |

---

## Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Track search engine performance |
| **Metrics** | Success rate, latency, result count |
| **Output** | Health reports, priority suggestions |
| **Thread Safety** | Lock-protected updates |

**Think of it as**: A performance dashboard that shows which search engines are working well and which might need attention.
