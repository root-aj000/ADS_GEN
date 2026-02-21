# Technical Specification: API Specification
## Ad Generator System

---

## 1. Overview

This document specifies the programmatic interfaces of the Ad Generator system. While primarily a command-line application, the system exposes several internal APIs that allow for programmatic integration, extension, and testing.

---

## 2. System Interfaces

### 2.1 Command-Line Interface

#### 2.1.1 Entry Point
The main entry point is the `main.py` script executed from the command line.

**Usage:**
```bash
python main.py [--options]
```

**Note:** Currently, the system is configured through `config/settings.py` rather than command-line arguments.

#### 2.1.2 Configuration Interface
All configuration is managed through the `config/settings.py` file rather than CLI arguments.

**Configuration Options:**
- Feature flags (booleans)
- Numeric parameters (integers, floats)
- List parameters (priority orders, ignore lists)
- Path configurations (directories, files)

### 2.2 Python Module Interface

#### 2.2.1 Main Module
**Module:** `main.py`
**Purpose:** Entry point and initialization

**Functions:**
```python
def main() -> None:
    """
    Main entry point for the Ad Generator application.
    
    Initializes configuration, sets up logging, creates pipeline,
    and starts processing.
    """
    pass
```

**Usage Example:**
```python
from main import main

if __name__ == "__main__":
    main()
```

#### 2.2.2 Configuration Module
**Module:** `config/settings.py`
**Purpose:** Centralized configuration management

**Classes:**
```python
class AppConfig:
    """Top-level configuration aggregator."""
    paths: PathConfig
    quality: ImageQualityConfig
    bg: BackgroundRemovalConfig
    search: SearchConfig
    query: QueryConfig
    verify: VerificationConfig
    proxy: ProxyConfig
    notify: NotificationConfig
    output: OutputConfig
    pipeline: PipelineConfig
    
    # Feature flags
    resume: bool
    dry_run: bool
    verbose: bool
    # ... other flags

class PathConfig:
    """File system path configuration."""
    root: Path
    csv_input: Path
    csv_output: Path
    images_dir: Path
    temp_dir: Path
    progress_db: Path
    cache_db: Path
    log_file: Path
    fonts_dir: Path
    proxy_file: Path
    models_dir: Path

class ImageQualityConfig:
    """Image validation parameters."""
    min_width: int
    min_height: int
    min_file_bytes: int
    max_search_results: int
    min_aspect: float
    max_aspect: float
    min_unique_colours: int
    min_std_dev: float
    # ... quality scoring weights

class SearchConfig:
    """Search engine configuration."""
    priority: List[str]
    adv_search_term: str
    min_results_fallback: int
    # ... timing and rate limiting

class QueryConfig:
    """CSV column mapping and query configuration."""
    priority_columns: Tuple[str, ...]
    text_column: str
    monetary_column: str
    cta_column: str
    color_column: str
    max_query_words: int
    ignore_values: Tuple[str, ...]
    strip_suffixes: Tuple[str, ...]

# ... other configuration classes
```

#### 2.2.3 Core Pipeline Module
**Module:** `core/pipeline.py`
**Purpose:** Orchestration of the advertisement generation workflow

**Classes:**
```python
class AdPipeline:
    """Main orchestrator for advertisement generation."""
    
    def __init__(self, cfg: AppConfig) -> None:
        """
        Initialize the pipeline with configuration.
        
        Args:
            cfg: Application configuration
        """
        pass
    
    def run(self) -> None:
        """
        Execute the advertisement generation pipeline.
        
        Processes all products in the input CSV according to
        configuration settings.
        """
        pass

class Stats:
    """Processing statistics collector."""
    
    def __init__(self) -> None:
        """Initialize counters."""
        pass
    
    def report(self) -> str:
        """
        Generate human-readable statistics report.
        
        Returns:
            Formatted statistics report
        """
        pass
```

**Functions:**
```python
def build_query(row: pd.Series, cfg: QueryConfig) -> str:
    """
    Build search query from CSV row using configured column priority.
    
    Args:
        row: DataFrame row containing product data
        cfg: Query configuration
        
    Returns:
        Cleaned search query string
    """
    pass
```

#### 2.2.4 Search Modules
**Modules:** `search/*.py`
**Purpose:** Image search functionality across multiple engines

**Base Class:**
```python
class BaseSearchEngine(ABC):
    """Abstract base class for search engines."""
    
    def __init__(self, delay: float = 1.0) -> None:
        """
        Initialize search engine with request delay.
        
        Args:
            delay: Delay between requests in seconds
        """
        pass
    
    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> List[ImageResult]:
        """
        Search for images matching the query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of image search results
        """
        pass
```

**Implementation Classes:**
```python
class GoogleSearchEngine(BaseSearchEngine):
    """Google Images search implementation."""
    pass

class BingSearchEngine(BaseSearchEngine):
    """Bing Images search implementation."""
    pass

class DuckDuckGoSearchEngine(BaseSearchEngine):
    """DuckDuckGo Images search implementation."""
    pass

class SearchManager:
    """Coordinates multiple search engines with fallback."""
    
    def __init__(self, cfg: SearchConfig) -> None:
        """
        Initialize with search configuration.
        
        Args:
            cfg: Search configuration
        """
        pass
    
    def search(self, query: str) -> List[ImageResult]:
        """
        Search using configured engine priority.
        
        Args:
            query: Search query string
            
        Returns:
            Ranked list of image results
        """
        pass
```

**Data Classes:**
```python
@dataclass
class ImageResult:
    """Represents a single image search result."""
    url: str
    width: int
    height: int
    source: str
    thumbnail: Optional[str] = None
```

#### 2.2.5 Imaging Modules
**Modules:** `imaging/*.py`
**Purpose:** Image processing, validation, and enhancement

**Downloader:**
```python
class ImageDownloader:
    """Downloads and validates images."""
    
    def __init__(
        self,
        cfg: ImageQualityConfig,
        hashes: ThreadSafeSet,
        timeout: int = 10,
        scorer: Optional[ImageQualityScorer] = None,
        verifier: Optional[ImageVerifier] = None,
        verify_cfg: Optional[VerificationConfig] = None,
    ) -> None:
        """Initialize with configuration and dependencies."""
        pass
    
    def download_best(
        self,
        results: List[ImageResult],
        dest: Path,
        query: str = "",
        skip: int = 0,
    ) -> DownloadResult:
        """
        Download the best matching image from search results.
        
        Args:
            results: Search results to try
            dest: Save destination
            query: Search query for verification
            skip: Number of valid images to skip
            
        Returns:
            Download result with success status
        """
        pass

@dataclass
class DownloadResult:
    """Result of image download attempt."""
    success: bool
    path: Optional[Path] = None
    source_url: Optional[str] = None
    info: Dict[str, Any] = field(default_factory=dict)
    verification: Optional[Dict] = None
```

**Quality Scorer:**
```python
class ImageQualityScorer:
    """Scores image candidates by quality factors."""
    
    def __init__(self, cfg: ImageQualityConfig) -> None:
        """Initialize with configuration."""
        pass
    
    def score_result(self, result: ImageResult) -> float:
        """
        Calculate quality score for search result.
        
        Args:
            result: Image search result
            
        Returns:
            Quality score (higher is better)
        """
        pass
```

**Verifier:**
```python
class ImageVerifier:
    """Verifies image relevance using AI models."""
    
    def __init__(self, cfg: VerificationConfig) -> None:
        """Initialize with configuration and load models."""
        pass
    
    def verify(self, image: Image.Image, query: str) -> VerificationResult:
        """
        Verify image relevance to query using CLIP and BLIP.
        
        Args:
            image: PIL Image to verify
            query: Search query string
            
        Returns:
            Verification result with scores
        """
        pass

@dataclass
class VerificationResult:
    """Result of image verification."""
    clip_score: float
    blip_score: float
    combined_score: float
    blip_caption: str
    accepted: bool
    reason: str
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        pass
```

**Background Remover:**
```python
class BackgroundRemover:
    """Removes image backgrounds using AI."""
    
    def __init__(self, cfg: BackgroundRemovalConfig) -> None:
        """Initialize with configuration."""
        pass
    
    def should_remove(self, query: str) -> bool:
        """
        Determine if background should be removed for query.
        
        Args:
            query: Search query
            
        Returns:
            True if background removal should be applied
        """
        pass
    
    def remove(self, src: Path, dst: Path) -> BackgroundRemovalResult:
        """
        Remove background from image.
        
        Args:
            src: Source image path
            dst: Destination path for result
            
        Returns:
            Background removal result
        """
        pass
```

#### 2.2.6 Composition Module
**Module:** `core/compositor.py`
**Purpose:** Advertisement image creation

**Classes:**
```python
class AdCompositor:
    """Creates advertisement images from product data."""
    
    def __init__(self, fonts_dir: Path) -> None:
        """
        Initialize with fonts directory.
        
        Args:
            fonts_dir: Directory containing font files
        """
        pass
    
    def compose(
        self,
        product_path: Path,
        nobg_path: Optional[Path],
        use_original: bool,
        row: pd.Series,
        output: Path,
        template_name: str = "default",
    ) -> None:
        """
        Compose advertisement image.
        
        Args:
            product_path: Path to product image
            nobg_path: Path to background-removed image
            use_original: Whether to use original image
            row: Product data from CSV
            output: Output path for advertisement
            template_name: Template to use
        """
        pass
    
    def placeholder(self, query: str, dest: Path) -> Path:
        """
        Generate placeholder image for failed products.
        
        Args:
            query: Search query
            dest: Destination path
            
        Returns:
            Path to generated placeholder
        """
        pass
```

#### 2.2.7 Utility Modules
**Modules:** `utils/*.py`
**Purpose:** Shared utilities and cross-cutting concerns

**Concurrency Utilities:**
```python
class AtomicCounter:
    """Thread-safe integer counter."""
    
    def __init__(self, initial: int = 0) -> None:
        """Initialize with initial value."""
        pass
    
    def increment(self, delta: int = 1) -> int:
        """
        Atomically increment counter.
        
        Args:
            delta: Amount to increment by
            
        Returns:
            New counter value
        """
        pass
    
    @property
    def value(self) -> int:
        """Get current counter value."""
        pass

class ThreadSafeSet:
    """Thread-safe set implementation."""
    
    def __init__(self) -> None:
        """Initialize empty set."""
        pass
    
    def add(self, item: Hashable) -> bool:
        """
        Add item to set if not present.
        
        Args:
            item: Item to add
            
        Returns:
            True if item was added, False if already present
        """
        pass
```

**Rate Limiting:**
```python
class RateLimiter:
    """Rate limiter using token bucket algorithm."""
    
    def __init__(self, rate_per_second: float) -> None:
        """
        Initialize with target rate.
        
        Args:
            rate_per_second: Maximum requests per second
        """
        pass
    
    def acquire(self) -> None:
        """Block until permission is granted."""
        pass
```

**Circuit Breaker:**
```python
class CircuitBreaker:
    """Circuit breaker for failure detection."""
    
    def __init__(self, threshold: int, cooldown: float) -> None:
        """
        Initialize with failure threshold and cooldown period.
        
        Args:
            threshold: Number of failures before opening
            cooldown: Seconds to stay open before half-open
        """
        pass
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Any exception raised by func
        """
        pass
```

**Retry Decorator:**
```python
def retry(
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator for automatic retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        backoff_base: Base for exponential backoff calculation
        exceptions: Exception types to retry on
        
    Returns:
        Decorator function
    """
    pass
```

---

## 3. Data Models

### 3.1 Input Models

#### 3.1.1 Product Data
**Source:** CSV file
**Format:** Pandas DataFrame

**Columns (Configurable):**
- Search query columns (priority order)
- Text content columns
- Pricing/discount information
- Call-to-action text
- Color information

#### 3.1.2 Configuration Data
**Source:** `config/settings.py`
**Format:** Python dataclasses

**Structure:**
- Nested configuration objects
- Type annotations for validation
- Default values for all parameters
- Immutable after initialization

### 3.2 Processing Models

#### 3.2.1 Search Results
```python
@dataclass
class ImageResult:
    url: str
    width: int
    height: int
    source: str
    thumbnail: Optional[str] = None
```

#### 3.2.2 Download Results
```python
@dataclass
class DownloadResult:
    success: bool
    path: Optional[Path] = None
    source_url: Optional[str] = None
    info: Dict[str, Any] = field(default_factory=dict)
    verification: Optional[Dict] = None
```

#### 3.2.3 Verification Results
```python
@dataclass
class VerificationResult:
    clip_score: float
    blip_score: float
    combined_score: float
    blip_caption: str
    accepted: bool
    reason: str
```

### 3.3 Output Models

#### 3.3.1 Advertisement Images
**Format:** JPEG files
**Naming:** `ad_{index:04d}.jpg`
**Location:** Configurable output directory

#### 3.3.2 Updated CSV
**Format:** CSV file with added `image_path` column
**Location:** Configurable output path

#### 3.3.3 Metadata
**Format:** SQLite databases
**Content:** Cache entries, progress tracking, statistics

---

## 4. Error Models

### 4.1 Exception Hierarchy
```python
class AdGenError(Exception):
    """Base exception for Ad Generator errors."""
    pass

class SearchExhaustedError(AdGenError):
    """Raised when no suitable images found."""
    pass

class ImageDownloadError(AdGenError):
    """Raised when image download fails."""
    pass

class BackgroundRemovalError(AdGenError):
    """Raised when background removal fails."""
    pass

class VerificationError(AdGenError):
    """Raised when image verification fails."""
    pass

class ConfigurationError(AdGenError):
    """Raised when configuration is invalid."""
    pass
```

### 4.2 Error Responses
**For recoverable errors:**
- Return failure status in result objects
- Log detailed error information
- Continue processing other products

**For unrecoverable errors:**
- Raise appropriate exceptions
- Provide clear error messages
- Exit gracefully with error codes

---

## 5. Extension Points

### 5.1 Search Engine Extensions
**Interface:** `BaseSearchEngine`
**Registration:** `SearchManager.ENGINE_REGISTRY`

**Requirements:**
- Implement `search()` method
- Handle rate limiting internally
- Return standardized `ImageResult` objects

### 5.2 Template Extensions
**Interface:** Template definitions in `config/templates.py`
**Registration:** Template registry in `AdCompositor`

**Requirements:**
- Define layout parameters
- Specify text placement rules
- Support dynamic sizing

### 5.3 Notification Extensions
**Interface:** `Notifier` class in `notifications/notifier.py`
**Registration:** Direct method extensions

**Requirements:**
- Implement notification channels
- Handle delivery failures
- Support multiple message formats

---

## 6. Integration Guidelines

### 6.1 Library Usage
The system can be used as a library by importing modules directly:

```python
from config.settings import cfg
from core.pipeline import AdPipeline

# Customize configuration
cfg.paths.csv_input = Path("custom_input.csv")
cfg.pipeline.max_workers = 8

# Run pipeline
pipeline = AdPipeline(cfg)
pipeline.run()
```

### 6.2 Testing Integration
The system provides interfaces for testing:

```python
from imaging.downloader import ImageDownloader
from imaging.scorer import ImageQualityScorer

# Mock dependencies for testing
mock_cfg = Mock()
mock_hashes = Mock()

# Test specific components
downloader = ImageDownloader(mock_cfg, mock_hashes)
result = downloader.download_best(test_results, temp_path)
```

### 6.3 Monitoring Integration
Components expose metrics for monitoring:

```python
from core.pipeline import Stats

stats = Stats()
# ... processing occurs ...
report = stats.report()  # Get formatted metrics
```

---

## 7. Performance Considerations

### 7.1 API Response Times
- Configuration loading: < 100ms
- Component initialization: < 500ms
- Individual product processing: ~3-5 seconds
- Bulk operations: Parallelizable

### 7.2 Memory Usage
- Per-worker memory: ~300MB
- Shared state: < 50MB
- Peak usage scales linearly with worker count

### 7.3 Concurrency
- Thread-safe operations where needed
- Shared-nothing architecture for workers
- Database connection pooling

---

## 8. Security Considerations

### 8.1 Input Validation
- Strict type checking on configuration
- Sanitization of file paths
- Validation of network URLs

### 8.2 Data Handling
- Secure temporary file management
- Proper cleanup of intermediate data
- No storage of sensitive information

### 8.3 Network Security
- HTTPS enforcement where possible
- User agent rotation
- Request timeout enforcement

---

*Document Version: 1.0*
*Last Updated: February 18, 2026*