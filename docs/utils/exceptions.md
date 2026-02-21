# Custom Exceptions

**File**: [`utils/exceptions.py`](utils/exceptions.py)  
**Purpose**: Custom exception hierarchy for specific error handling throughout the Ad Generator.

## 🎯 What It Does

The exceptions module provides specialized error types that make it easy to handle specific failure modes. Instead of catching generic `Exception`, you can catch specific errors and respond appropriately.

Think of them as **specialized error tickets** that tell you exactly what went wrong:
1. ✅ `AdGenError` - Base class for all project errors
2. ✅ `SearchExhaustedError` - All search engines failed
3. ✅ `ImageDownloadError` - Image download/validation failed
4. ✅ `BackgroundRemovalError` - Background removal processing failed
5. ✅ `ConfigurationError` - Invalid configuration

## 🔧 Exception Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    Exception Hierarchy                       │
└─────────────────────────────────────────────────────────────┘

Exception (Python built-in)
    │
    └── AdGenError (base for all project exceptions)
            │
            ├── SearchExhaustedError
            │   └── "All engines returned zero usable results"
            │
            ├── ImageDownloadError
            │   └── "Image could not be downloaded or failed validation"
            │
            ├── BackgroundRemovalError
            │   └── "rembg processing failed in a non-recoverable way"
            │
            └── ConfigurationError
                └── "Invalid or missing configuration"
```

## 📝 Class Definitions

```python
class AdGenError(Exception):
    """Base for every project exception."""
    pass


class SearchExhaustedError(AdGenError):
    """All engines returned zero usable results."""
    pass


class ImageDownloadError(AdGenError):
    """Image could not be downloaded or failed validation."""
    pass


class BackgroundRemovalError(AdGenError):
    """rembg processing failed in a non-recoverable way."""
    pass


class ConfigurationError(AdGenError):
    """Invalid or missing configuration."""
    pass
```

## 🔍 When Each Exception Is Raised

### SearchExhaustedError

**Raised when**: All search engines return no results for a query.

```python
# In search/manager.py
class SearchManager:
    def search(self, query: str, max_results: int) -> List[ImageResult]:
        all_results = []
        
        for engine_name in self.engine_order:
            try:
                results = engine.search(query, max_results)
                all_results.extend(results)
            except Exception:
                continue
        
        if not all_results:
            raise SearchExhaustedError(
                f"No results from any engine for query: {query}"
            )
        
        return all_results
```

**Handling**:
```python
try:
    results = search_manager.search(query)
except SearchExhaustedError:
    log.warning("No images found for: %s", query)
    # Create placeholder or skip product
```

### ImageDownloadError

**Raised when**: Image download fails or validation rejects all candidates.

```python
# In imaging/downloader.py
class ImageDownloader:
    def download_best(self, results: List[ImageResult], dest: Path):
        for r in results:
            try:
                # ... download and validate ...
            except Exception:
                continue
        
        # All candidates failed
        raise ImageDownloadError(
            f"No valid image found among {len(results)} candidates"
        )
```

**Handling**:
```python
try:
    result = downloader.download_best(results, dest)
except ImageDownloadError as e:
    log.error("Download failed: %s", e)
    # Create placeholder image
    compositor.placeholder(query, dest)
```

### BackgroundRemovalError

**Raised when**: Background removal processing fails critically.

```python
# In imaging/background.py
class BackgroundRemover:
    def remove(self, src: Path, dst: Path) -> BGRemovalResult:
        try:
            # ... rembg processing ...
        except Exception as exc:
            raise BackgroundRemovalError(
                f"Background removal failed: {exc}"
            )
```

**Handling**:
```python
try:
    result = bg_remover.remove(src, dst)
except BackgroundRemovalError:
    # Use original image without background removal
    shutil.copy(src, dst)
```

### ConfigurationError

**Raised when**: Configuration is missing or invalid.

```python
# In config/settings.py
class AppConfig:
    def validate(self) -> None:
        if not self.paths.input_file.exists():
            raise ConfigurationError(
                f"Input file not found: {self.paths.input_file}"
            )
        
        if self.search.requests_per_second <= 0:
            raise ConfigurationError(
                "requests_per_second must be positive"
            )
```

**Handling**:
```python
try:
    cfg = AppConfig()
    cfg.validate()
except ConfigurationError as e:
    log.error("Configuration error: %s", e)
    sys.exit(1)
```

## 🎯 Usage Patterns

### Pattern 1: Specific Exception Handling

```python
from utils.exceptions import (
    SearchExhaustedError,
    ImageDownloadError,
    BackgroundRemovalError,
)

def process_product(query: str):
    try:
        # Try to get image
        results = search_manager.search(query)
        download_result = downloader.download_best(results, dest)
        
        if bg_remover.should_remove(query):
            bg_remover.remove(download_result.path, output_path)
            
    except SearchExhaustedError:
        # No results - create placeholder
        compositor.placeholder(query, dest)
        
    except ImageDownloadError:
        # Download failed - create placeholder
        compositor.placeholder(query, dest)
        
    except BackgroundRemovalError:
        # BG removal failed - use original
        pass  # Already have downloaded image
```

### Pattern 2: Catch All Project Errors

```python
from utils.exceptions import AdGenError

def process_product(query: str):
    try:
        # ... process product ...
        pass
    except AdGenError as e:
        # Catch any project-specific error
        log.error("Processing failed: %s", e)
        stats.failed.increment()
```

### Pattern 3: Re-raise with Context

```python
from utils.exceptions import ImageDownloadError

def download_with_retry(url: str):
    try:
        return requests.get(url, timeout=10)
    except requests.Timeout as e:
        raise ImageDownloadError(f"Timeout downloading {url}") from e
    except requests.ConnectionError as e:
        raise ImageDownloadError(f"Connection failed for {url}") from e
```

## 📊 Exception Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              Exception Flow in Pipeline                      │
└─────────────────────────────────────────────────────────────┘

                    Process Product
                          │
                          ▼
               ┌─────────────────────┐
               │   Search for Image  │
               └──────────┬──────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
        Success              SearchExhaustedError
              │                       │
              ▼                       ▼
       Download Image         Create Placeholder
              │
              ├───────────────────────┐
              │                       │
              ▼                       ▼
        Success              ImageDownloadError
              │                       │
              ▼                       ▼
      Remove Background      Create Placeholder
              │
              ├───────────────────────┐
              │                       │
              ▼                       ▼
        Success          BackgroundRemovalError
              │                       │
              ▼                       ▼
          Compose Ad           Use Original Image
```

## 🔗 Where Exceptions Are Used

| Exception | Raised In | Caught In |
|-----------|-----------|-----------|
| `SearchExhaustedError` | `search/manager.py` | `core/pipeline.py` |
| `ImageDownloadError` | `imaging/downloader.py` | `core/pipeline.py` |
| `BackgroundRemovalError` | `imaging/background.py` | `core/pipeline.py` |
| `ConfigurationError` | `config/settings.py` | `main.py` |

## ✅ Benefits of Custom Exceptions

1. **Specific Handling**: Catch and handle specific error types differently
2. **Clear Code**: Exception names document what can go wrong
3. **Error Isolation**: Distinguish project errors from Python errors
4. **Graceful Degradation**: Continue processing other products when one fails

---

**Next**: [Retry Decorator](retry.md) → Automatic retry with backoff
