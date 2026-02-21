# Retry Decorator

**File**: [`utils/retry.py`](utils/retry.py)  
**Purpose**: Decorator that automatically retries failed operations with exponential backoff.

## 🎯 What It Does

The retry decorator wraps functions that might fail temporarily (like network requests) and automatically retries them with increasing delays between attempts.

Think of it as a **persistent assistant** who keeps trying to complete a task:
1. ✅ Tries the operation
2. ✅ If it fails, waits a bit
3. ✅ Tries again (up to max_attempts)
4. ✅ Gives up after all attempts exhausted

## 🔧 Function Definition

```python
from functools import wraps
import time
from typing import Callable, Type, Tuple

def retry(
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Retry decorator with exponential back-off.
    
    Args:
        max_attempts: Maximum number of tries (default: 3)
        backoff_base: Base seconds for exponential backoff (default: 1.0)
        exceptions: Tuple of exception types to catch (default: all)
    
    Returns:
        Decorated function that retries on failure
    """
```

## 🔄 How Exponential Backoff Works

```
┌─────────────────────────────────────────────────────────────┐
│              Exponential Backoff Timing                      │
└─────────────────────────────────────────────────────────────┘

Attempt 1: Execute immediately
    │
    ├─ Success → Return result
    │
    └─ Failure → Wait 1.0s (backoff_base × 2^0)

Attempt 2: Execute after 1.0s
    │
    ├─ Success → Return result
    │
    └─ Failure → Wait 2.0s (backoff_base × 2^1)

Attempt 3: Execute after 2.0s
    │
    ├─ Success → Return result
    │
    └─ Failure → Raise exception (max_attempts reached)
```

**Backoff calculation**:
```python
wait_time = backoff_base * (2 ** attempt_number)
```

| Attempt | Wait Before | Total Wait So Far |
|---------|-------------|-------------------|
| 1 | 0s | 0s |
| 2 | 1.0s | 1.0s |
| 3 | 2.0s | 3.0s |
| 4 | 4.0s | 7.0s |
| 5 | 8.0s | 15.0s |

## 📝 Implementation

```python
def retry(
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Retry decorator with exponential back-off."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_error = e
                    
                    if attempt < max_attempts - 1:
                        # Calculate wait time with exponential backoff
                        wait_time = backoff_base * (2 ** attempt)
                        log.warning(
                            "Attempt %d/%d failed: %s. Retrying in %.1fs",
                            attempt + 1, max_attempts, e, wait_time
                        )
                        time.sleep(wait_time)
                    else:
                        log.error(
                            "All %d attempts failed for %s",
                            max_attempts, func.__name__
                        )
            
            raise last_error
        
        return wrapper
    
    return decorator
```

## 🎯 Usage Examples

### Basic Usage

```python
from utils.retry import retry

@retry(max_attempts=3, backoff_base=1.0)
def fetch_data(url: str):
    return requests.get(url, timeout=10)

# Will try up to 3 times with 1s, 2s delays
result = fetch_data("https://api.example.com/data")
```

### Specific Exception Types

```python
from utils.retry import retry
import requests

@retry(
    max_attempts=3,
    backoff_base=0.5,
    exceptions=(requests.Timeout, requests.ConnectionError)
)
def download_image(url: str):
    return requests.get(url, timeout=10)

# Only retries on Timeout or ConnectionError
# Other exceptions (like 404) are raised immediately
```

### In the Codebase

**Used in [`imaging/downloader.py`](imaging/downloader.py:626)**:
```python
@retry(max_attempts=2, backoff_base=0.5, exceptions=(requests.RequestException,))
def _fetch(self, url: str) -> Optional[bytes]:
    """Fetch image data from URL."""
    resp = self.session.get(url, timeout=self.timeout, stream=True)
    if resp.status_code != 200:
        return None
    return resp.content
```

**Why retry here?**
- Network requests can fail temporarily
- Server might be briefly overloaded
- Connection might hiccup
- Second attempt often succeeds

## 📊 Retry Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Retry Flow                               │
└─────────────────────────────────────────────────────────────┘

                    Call decorated function
                          │
                          ▼
               ┌─────────────────────┐
               │  Attempt 1          │
               └──────────┬──────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
         Success                  Exception
              │                       │
              ▼                       ▼
         Return result    ┌─────────────────────┐
                          │ Matches exception   │
                          │ type filter?        │
                          └──────────┬──────────┘
                                     │
                         ┌───────────┴───────────┐
                         │                       │
                         ▼                       ▼
                       Yes                      No
                         │                       │
                         ▼                       ▼
              ┌─────────────────────┐   Raise immediately
              │ More attempts       │
              │ remaining?          │
              └──────────┬──────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
            Yes                    No
              │                     │
              ▼                     ▼
     Wait (exponential      Raise last exception
      backoff time)
              │
              ▼
         Next attempt
```

## ⚙️ Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_attempts` | `int` | 3 | Maximum tries before giving up |
| `backoff_base` | `float` | 1.0 | Base wait time in seconds |
| `exceptions` | `Tuple[Type[Exception], ...]` | `(Exception,)` | Which exceptions to catch |

### Choosing max_attempts

| Value | Use Case |
|-------|----------|
| 2 | Quick retry for flaky connections |
| 3 | Standard retry for most operations |
| 5 | Critical operations that must succeed |

### Choosing backoff_base

| Value | Use Case |
|-------|----------|
| 0.5 | Fast operations (image fetches) |
| 1.0 | Standard operations |
| 2.0 | API calls (be more patient) |

### Choosing exceptions

```python
# Catch only network errors
@retry(exceptions=(requests.Timeout, requests.ConnectionError))

# Catch all requests errors
@retry(exceptions=(requests.RequestException,))

# Catch any exception (use sparingly!)
@retry(exceptions=(Exception,))
```

## 🛡️ Best Practices

### ✅ Do

```python
# Retry specific, recoverable errors
@retry(exceptions=(requests.Timeout,))
def fetch_url(url):
    return requests.get(url)

# Use reasonable attempt counts
@retry(max_attempts=3)
def download_image(url):
    ...

# Add logging for debugging
@retry(max_attempts=2)
def operation():
    log.debug("Attempting operation...")
    ...
```

### ❌ Don't

```python
# Don't catch all exceptions blindly
@retry(exceptions=(Exception,))  # Too broad!
def important_operation():
    ...

# Don't retry infinitely
@retry(max_attempts=100)  # Too many!
def fetch_data():
    ...

# Don't retry non-recoverable errors
@retry(exceptions=(ValueError,))  # ValueError won't fix itself!
def parse_data(data):
    return int(data)  # "abc" will always fail
```

## 🔗 Where It's Used

| Location | max_attempts | backoff_base | exceptions |
|----------|--------------|--------------|------------|
| `imaging/downloader.py::_fetch` | 2 | 0.5 | `RequestException` |
| `search/base.py` (potential) | 3 | 1.0 | `RequestException` |

---

**Next**: [Logging](log-config.md) → Centralized logging setup
