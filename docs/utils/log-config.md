# Logging Configuration

**File**: [`utils/log_config.py`](utils/log_config.py)  
**Purpose**: Centralized logging setup with consistent formatting across all modules.

## 🎯 What It Does

The logging module provides a unified logging system for the entire Ad Generator. Every module uses the same log format and outputs to both console and file.

Think of it as a **central diary system** where:
1. ✅ All modules write to the same format
2. ✅ Logs go to both screen and file
3. ✅ Third-party libraries are silenced
4. ✅ Thread names are tracked for debugging

## 🔧 Functions

### setup_root()

Initialize logging at application startup:

```python
def setup_root(log_file: Path, verbose: bool = False) -> None:
    """Call once at startup to wire console + file handlers."""
```

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `log_file` | `Path` | Required | Path to log file |
| `verbose` | `bool` | `False` | Enable DEBUG level logging |

### get_logger()

Get a logger for a specific module:

```python
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger. Typical usage: log = get_logger(__name__)"""
```

**Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | `None` | Module name (usually `__name__`) |

## 📝 Log Format

```
%(asctime)s │ %(levelname)-7s │ %(threadName)-14s │ %(name)-22s │ %(message)s
```

**Example Output**:
```
14:32:15 │ INFO    │ ThreadPool-1   │ core.pipeline     │ Processing row 42
14:32:15 │ DEBUG   │ ThreadPool-2   │ imaging.download  │ Fetching https://example.com/img.jpg
14:32:16 │ WARNING │ MainThread     │ search.manager    │ No results from google for query: xyz
14:32:17 │ ERROR   │ ThreadPool-3   │ imaging.verifier  │ Image rejected: low CLIP score
```

### Format Components

| Component | Description | Example |
|-----------|-------------|---------|
| `asctime` | Time of log | `14:32:15` |
| `levelname` | Log level | `INFO`, `DEBUG`, `WARNING`, `ERROR` |
| `threadName` | Thread that logged | `ThreadPool-1`, `MainThread` |
| `name` | Module name | `core.pipeline` |
| `message` | Log message | `Processing row 42` |

## 🔄 Setup Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Logging Setup Flow                        │
└─────────────────────────────────────────────────────────────┘

Application Start (main.py)
          │
          ▼
┌─────────────────────┐
│  setup_root()       │
│  called once        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Create log file    │
│  directory          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Configure handlers │
│  • Console (stdout) │
│  • File (.log)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Silence noisy      │
│  third-party logs   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Ready!             │
│  All modules can    │
│  use get_logger()   │
└─────────────────────┘
```

## 🎯 Usage Examples

### In main.py

```python
from pathlib import Path
from utils.log_config import setup_root

def main():
    # Setup logging FIRST
    setup_root(
        log_file=Path("data/adgen.log"),
        verbose=False  # Set True for debug output
    )
    
    # Now other modules can log
    ...
```

### In Any Module

```python
from utils.log_config import get_logger

log = get_logger(__name__)

def process_item(item):
    log.info("Processing item: %s", item)
    
    try:
        result = do_something(item)
        log.debug("Result: %s", result)
    except Exception as e:
        log.error("Failed to process %s: %s", item, e)
```

### Log Level Examples

```python
log = get_logger(__name__)

# Debug (only shown with verbose=True)
log.debug("Variable x = %d", x)

# Info (normal operation)
log.info("Processing %d items", len(items))

# Warning (something unexpected but recoverable)
log.warning("No images found for query: %s", query)

# Error (operation failed)
log.error("Download failed: %s", error_message)

# Critical (application-level failure)
log.critical("Database connection lost!")
```

## 🔇 Silenced Third-Party Loggers

The following libraries are silenced (set to WARNING level) to reduce noise:

### Network/HTTP
- `urllib3`, `requests`, `httpx`, `httpcore`
- `h11`, `h2`, `hyper`

### Image Processing
- `PIL`, `PIL.Image`, `PIL.PngImagePlugin`

### AI/ML
- `rembg`, `onnxruntime`

### Search
- `duckduckgo_search`

### Other
- `asyncio`, `concurrent`, `chardet`

**Why silence them?**
- These libraries can produce thousands of log lines
- Their DEBUG/INFO messages are rarely useful
- WARNING and ERROR still show through

## 📁 Log File Location

```
data/
└── adgen.log    # Default log file location
```

**Log rotation**: Not built-in. For production, consider:
- Using `logging.handlers.RotatingFileHandler`
- External log rotation (logrotate on Linux)

## 🔍 Log Analysis

### Finding Errors
```bash
grep "ERROR" data/adgen.log
```

### Finding Warnings
```bash
grep "WARNING" data/adgen.log
```

### Thread Activity
```bash
# See what ThreadPool-1 is doing
grep "ThreadPool-1" data/adgen.log
```

### Specific Module
```bash
# See only pipeline logs
grep "core.pipeline" data/adgen.log
```

## 📊 Log Levels

| Level | When to Use | Visible By Default |
|-------|-------------|-------------------|
| DEBUG | Detailed diagnostic info | No (verbose=True) |
| INFO | Normal operation events | Yes |
| WARNING | Unexpected but recoverable | Yes |
| ERROR | Operation failed | Yes |
| CRITICAL | Application failure | Yes |

## 🎯 Best Practices

### ✅ Do

```python
# Use module name for logger
log = get_logger(__name__)

# Use % formatting (not f-strings) for lazy evaluation
log.info("Processing %d items", len(items))

# Include context in messages
log.error("Failed to download %s: %s", url, error)

# Use appropriate levels
log.debug("Variable state: %r", var)  # Only with verbose
log.info("Starting process")           # Normal operation
log.warning("Retry %d/%d", attempt, max)  # Recoverable issue
log.error("Failed: %s", reason)        # Failure
```

### ❌ Don't

```python
# Don't use print()
print("Processing...")  # Use log.info() instead

# Don't use f-strings (eager evaluation)
log.info(f"Processing {len(items)} items")  # Slow if log disabled

# Don't log sensitive data
log.info("User password: %s", password)  # SECURITY RISK!

# Don't over-log in loops
for item in items:
    log.debug("Item: %s", item)  # Too verbose for production
```

## 🔗 Integration Example

```python
# main.py
from utils.log_config import setup_root

setup_root(Path("data/adgen.log"), verbose=False)

# core/pipeline.py
from utils.log_config import get_logger
log = get_logger(__name__)

class AdPipeline:
    def run(self):
        log.info("Starting pipeline with %d items", len(self.df))
        # ...
        log.info("Completed: %d success, %d failed", stats.success, stats.failed)

# imaging/downloader.py
from utils.log_config import get_logger
log = get_logger(__name__)

class ImageDownloader:
    def download_best(self, results, dest):
        log.debug("Downloading from %d candidates", len(results))
        # ...
        log.info("Downloaded %dx%d from %s", width, height, source)
```

---

**Next**: [Text Cleaner](text-cleaner.md) → Query sanitization utilities
