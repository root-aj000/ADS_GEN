# Configuration Settings Documentation

## File: [`config/settings.py`](../../config/settings.py)

## Overview

The `settings.py` file is the **control center** of the Ad Generator application. It contains ALL the configuration options that control how the application behaves. Think of it as the "settings menu" for the entire system.

## Real-World Analogy

Imagine a factory control panel with many switches and knobs:
- Some switches turn features ON or OFF (Feature Flags)
- Some knobs control speed or quantity (Numeric Settings)
- Some settings define where things go (Paths)

This file is that control panel. Change a value here, and the entire application adjusts its behavior.

---

## Feature Flags (On/Off Switches)

These are boolean (True/False) settings that enable or disable features:

| Flag Name | Default | What It Does |
|-----------|---------|--------------|
| `RESUME_FROM_PROGRESS` | `False` | If `True`, continue from where the last run stopped. If `False`, start fresh. |
| `DRY_RUN` | `False` | If `True`, only search and download images - don't create final ads. Like a "test mode". |
| `VERBOSE_LOGGING` | `True` | If `True`, shows detailed debug messages. If `False`, shows only important messages. |
| `REMOVE_TEMP_ON_FINISH` | `True` | If `True`, deletes temporary files after processing. Saves disk space. |
| `START_INDEX` | `None` | Which row to start from. `None` = start from beginning (row 0). |
| `END_INDEX` | `None` | Which row to stop at. `None` = process all rows. |
| `ENABLE_IMAGE_CACHE` | `True` | Remember downloaded images to avoid re-downloading same images. |
| `ENABLE_PROXY_ROTATION` | `False` | Rotate through proxy servers for each request. |
| `ENABLE_NOTIFICATIONS` | `False` | Send notifications (email/webhook) when complete. |
| `ENABLE_MULTI_SIZE` | `False` | Generate multiple ad sizes (Instagram, Facebook, etc.). |
| `ENABLE_WATERMARK` | `False` | Add watermark text to generated images. |
| `ENABLE_ASYNC_DOWNLOAD` | `True` | Download multiple images at once (faster). |
| `ENABLE_HEALTH_MONITOR` | `True` | Track search engine health and performance. |
| `ENABLE_DEAD_LETTER` | `True` | Retry failed rows at the end of a run. |
| `DEAD_LETTER_MAX_RETRIES` | `2` | How many times to retry failed rows. |
| `CHUNK_SIZE` | `50` | Process N rows at a time (controls memory usage). |
| `ENABLE_CLIP_VERIFICATION` | `True` | Use AI to verify image matches the search query. |
| `ENABLE_BLIP_VERIFICATION` | `True` | Use AI to generate image captions for verification. |

---

## Configuration Classes

The settings are organized into **dataclasses** - think of these as "groups of related settings".

### 1. VerificationConfig

**Purpose**: Controls AI-powered image verification (CLIP + BLIP).

**What it does**: When you search for "red shoes", the AI checks if the downloaded image actually shows red shoes.

```python
@dataclass(frozen=True)
class VerificationConfig:
    use_clip: bool = True           # Enable CLIP image-text matching
    use_blip: bool = True           # Enable BLIP caption verification
    clip_model: str = "openai/clip-vit-base-patch32"
    blip_model: str = "Salesforce/blip-image-captioning-base"
    clip_accept_threshold: float = 0.25   # Score above this = accept
    clip_reject_threshold: float = 0.15   # Score below this = reject
    blip_accept_threshold: float = 0.30
    blip_reject_threshold: float = 0.10
    combined_accept: float = 0.25
    combined_reject: float = 0.12
    clip_weight: float = 0.6        # CLIP score weight (60%)
    blip_weight: float = 0.4        # BLIP score weight (40%)
    max_verify_candidates: int = 10 # Max images to check before giving up
    device: str = "auto"            # "auto", "cuda", or "cpu"
    batch_size: int = 1
    accept_on_model_failure: bool = True  # Accept if AI crashes
    min_candidates_before_best: int = 3   # Try at least 3 images
```

**Example for Non-Technical Readers**:
- Imagine you asked someone to find a photo of a "blue car"
- CLIP looks at the image and says "This looks 80% like a blue car" (score: 0.80)
- BLIP generates a caption: "A blue sedan parked on street"
- The combined score determines if we keep or reject the image

---

### 2. QueryConfig

**Purpose**: Defines which columns in your CSV to use for searching images.

```python
@dataclass(frozen=True)
class QueryConfig:
    priority_columns: Tuple[str, ...] = (
        "img_desc",        # First try this column
        "keywords",        # Then try this
        "object_detected", # Then this
        "product_name",    # Then this
        "description",     # Then this
        "text",            # Finally try this
    )
    text_column: str = "text"
    monetary_column: str = "monetary_mention"
    cta_column: str = "call_to_action"
    color_column: str = "dominant_colour"
    max_query_words: int = 0        # 0 = no word limit
    ignore_values: Tuple[str, ...] = (
        "nan", "none", "", "general", "food",
        "automotive", "object", "unknown", "null",
    )
    strip_suffixes: Tuple[str, ...] = (
        "filetype png", "filetype jpg", "filetype jpeg",
        "filetype webp", "site:", "inurl:",
    )
```

**How It Works**:

Your CSV might look like this:

| img_desc | keywords | text |
|----------|----------|------|
| "pizza slice" | "food, italian" | "Delicious pizza for $5" |
| "red sneakers" | "shoes, nike" | "Best running shoes" |

The system tries columns in order:
1. First looks at `img_desc` → "pizza slice"
2. If empty or invalid, tries `keywords` → "food, italian"
3. If still no luck, tries `text` → "Delicious pizza for $5"

---

### 3. PathConfig

**Purpose**: Defines where all files are stored.

```python
@dataclass(frozen=True)
class PathConfig:
    root: Path = DATA_DIR
    csv_input: Path = DATA_DIR / "input" / "main.csv"
    csv_output: Path = DATA_DIR / "output" / "ads_with_images.csv"
    images_dir: Path = DATA_DIR / "output" / "images"
    temp_dir: Path = DATA_DIR / "temp" / "workers"
    progress_db: Path = DATA_DIR / "temp" / "progress.db"
    cache_db: Path = DATA_DIR / "cache" / "images.db"
    log_file: Path = DATA_DIR / "logs" / "ad_generator.log"
    fonts_dir: Path = DATA_DIR / "fonts"
    proxy_file: Path = DATA_DIR / "config" / "proxies.txt"
    models_dir: Path = DATA_DIR / "models"

    def ensure(self) -> None:
        # Creates all necessary folders
        for d in (self.images_dir, self.temp_dir, ...):
            d.mkdir(parents=True, exist_ok=True)
```

**Directory Structure**:
```
data/
├── input/
│   └── main.csv          ← Your input file (csv_input)
├── output/
│   ├── ads_with_images.csv  ← Output CSV (csv_output)
│   └── images/           ← Generated ads (images_dir)
├── temp/
│   └── workers/          ← Temporary files (temp_dir)
│   └── progress.db       ← Progress tracking (progress_db)
├── cache/
│   └── images.db         ← Image cache (cache_db)
├── logs/
│   └── ad_generator.log  ← Log file (log_file)
├── fonts/                ← Custom fonts (fonts_dir)
└── models/               ← AI models (models_dir)
```

---

### 4. ImageQualityConfig

**Purpose**: Sets minimum quality requirements for downloaded images.

```python
@dataclass(frozen=True)
class ImageQualityConfig:
    min_width: int = 60           # Minimum width in pixels
    min_height: int = 60          # Minimum height in pixels
    min_file_bytes: int = 30_000  # Minimum file size (30 KB)
    max_search_results: int = 100 # Maximum images to consider
    min_aspect: float = 0.3       # Min width/height ratio
    max_aspect: float = 3.0       # Max width/height ratio
    min_unique_colours: int = 100 # Min different colors
    min_std_dev: float = 10.0     # Min color variation
    sharpness_weight: float = 0.3 # Weight for sharpness score
    contrast_weight: float = 0.2  # Weight for contrast score
    resolution_weight: float = 0.3 # Weight for resolution score
    source_weight: float = 0.2    # Weight for source reputation
```

**What This Means**:

Imagine you're buying a photo from a store:
- Must be at least 60x60 pixels (minimum size)
- Must be at least 30 KB in file size (not a tiny thumbnail)
- Must have at least 100 different colors (not a solid block)
- Must not be too stretched (aspect ratio between 0.3 and 3.0)

---

### 5. BackgroundRemovalConfig

**Purpose**: Controls how the system removes backgrounds from images.

```python
@dataclass(frozen=True)
class BackgroundRemovalConfig:
    min_retention: float = 0.05    # Keep at least 5% of pixels
    max_retention: float = 0.95    # If 95% remains, nothing removed
    min_object_ratio: float = 0.10 # Object must be 10% of image
    min_fill_ratio: float = 0.15   # Object must be 15% filled
    
    scene_keywords: Tuple[str, ...] = (
        "highway", "road", "street", "city", "landscape",
        "beach", "mountain", "forest", "park", "building",
        "room", "interior", "outdoor", "sky", "sunset",
        ...
    )
```

**How Background Removal Decides**:

```
Query: "pizza slice"
↓
Contains scene keyword? NO → Try to remove background
↓
Result: Product image with transparent background

Query: "car on highway"
↓
Contains scene keyword? YES → Keep original background
↓
Result: Full image with background intact
```

---

### 6. SearchConfig

**Purpose**: Controls how images are searched across different engines.

```python
@dataclass(frozen=True)
class SearchConfig:
    priority: List[str] = field(default_factory=lambda: [
        "google", "duckduckgo", "bing"
    ])
    adv_search_term: str = "product image"
    min_results_fallback: int = 10   # Min results before trying next engine
    inter_engine_delay: float = 0.5  # Wait between engines (seconds)
    per_request_delay: float = 0.3   # Wait between requests (seconds)
    rate_limit_per_sec: float = 2.0  # Max requests per second
    breaker_threshold: int = 5       # Failures before stopping
    breaker_cooldown: float = 120.0  # Wait time after failures (seconds)
```

**Search Flow**:

```
User Query: "red shoes"
↓
1. Try Google Images
   ├── Success? Return results
   └── Fail? Continue to next engine
↓
2. Try DuckDuckGo
   ├── Success? Return results
   └── Fail? Continue to next engine
↓
3. Try Bing
   └── Return whatever found
```

---

### 7. ProxyConfig

**Purpose**: Configure proxy server rotation (if enabled).

```python
@dataclass(frozen=True)
class ProxyConfig:
    enabled: bool = ENABLE_PROXY_ROTATION
    rotation_mode: str = "round_robin"  # "round_robin" | "random" | "least_used"
    max_failures: int = 3
    test_url: str = "https://httpbin.org/ip"
    test_timeout: int = 5
```

---

### 8. NotificationConfig

**Purpose**: Configure email/webhook notifications.

```python
@dataclass(frozen=True)
class NotificationConfig:
    enabled: bool = ENABLE_NOTIFICATIONS
    webhook_url: str = ""          # Slack/Discord webhook URL
    email_to: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    notify_on: Tuple[str, ...] = ("completion", "failure", "milestone")
    milestone_every: int = 100     # Notify every N successful ads
```

---

### 9. OutputConfig

**Purpose**: Configure output image settings.

```python
@dataclass(frozen=True)
class OutputConfig:
    primary_size: Tuple[int, int] = (1080, 1080)  # Main output size
    jpeg_quality: int = 95                         # JPEG quality (1-100)
```

---

### 10. PipelineConfig

**Purpose**: Control the main processing pipeline behavior.

```python
@dataclass(frozen=True)
class PipelineConfig:
    max_workers: int = 4            # Parallel workers (threads)
    inter_ad_delay: float = 0.5     # Wait between ads (seconds)
    csv_save_interval: int = 5      # Save CSV every N ads
    download_timeout: int = 10      # Download timeout (seconds)
    worker_timeout: int = 300       # Worker timeout (seconds)
```

---

### 11. AppConfig (Main Configuration)

**Purpose**: Combines all configuration classes into one main object.

```python
@dataclass
class AppConfig:
    paths: PathConfig = field(default_factory=PathConfig)
    quality: ImageQualityConfig = field(default_factory=ImageQualityConfig)
    bg: BackgroundRemovalConfig = field(default_factory=BackgroundRemovalConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    query: QueryConfig = field(default_factory=QueryConfig)
    verify: VerificationConfig = field(default_factory=VerificationConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    notify: NotificationConfig = field(default_factory=NotificationConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    # Flags
    resume: bool = RESUME_FROM_PROGRESS
    dry_run: bool = DRY_RUN
    verbose: bool = VERBOSE_LOGGING
    remove_temp: bool = REMOVE_TEMP_ON_FINISH
    start_index: int | None = START_INDEX
    end_index: int | None = END_INDEX
    enable_cache: bool = ENABLE_IMAGE_CACHE
    enable_async: bool = ENABLE_ASYNC_DOWNLOAD
    enable_health: bool = ENABLE_HEALTH_MONITOR
    enable_dlq: bool = ENABLE_DEAD_LETTER
    dlq_retries: int = DEAD_LETTER_MAX_RETRIES
    chunk_size: int = CHUNK_SIZE
    multi_size: bool = ENABLE_MULTI_SIZE
    watermark: bool = ENABLE_WATERMARK

    def validate(self) -> None:
        # Validates all configuration
        if not self.paths.csv_input.exists():
            raise FileNotFoundError(f"Input CSV missing: {self.paths.csv_input}")
        if self.pipeline.max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        for eng in self.search.priority:
            if eng not in ("google", "duckduckgo", "bing"):
                raise ValueError(f"Unknown engine: {eng}")
```

---

## Constants

### COLOR_MAP

Defines standard RGB color values for background colors:

```python
COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
    "Red": (220, 20, 60),
    "Blue": (0, 102, 204),
    "Green": (34, 139, 34),
    "Yellow": (255, 193, 7),
    "Orange": (255, 102, 0),
    "Pink": (255, 105, 180),
    "Purple": (128, 0, 128),
    "Black": (45, 45, 45),
    "White": (255, 255, 255),
    "Brown": (139, 69, 19),
    "Grey": (128, 128, 128),
}
```

**Usage**: When your CSV has `dominant_colour: "Blue"`, the compositor uses `(0, 102, 204)` as the background color.

---

### DEFAULT_HEADERS

HTTP headers used for all web requests:

```python
DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
    "Accept": "text/html,application/xhtml+xml,...",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}
```

**Purpose**: Makes the scraper look like a real web browser to avoid being blocked.

---

## How to Modify Settings

### Example 1: Change Number of Workers

```python
# In config/settings.py
class PipelineConfig:
    max_workers: int = 8  # Changed from 4 to 8
```

**Effect**: Processes 8 ads at once instead of 4 (faster, but uses more memory).

---

### Example 2: Skip Background Removal for All Images

```python
# In config/settings.py
class BackgroundRemovalConfig:
    scene_keywords: Tuple[str, ...] = ()  # Empty tuple
```

**Effect**: All images will try to have their backgrounds removed.

---

### Example 3: Use Only DuckDuckGo

```python
# In config/settings.py
class SearchConfig:
    priority: List[str] = field(default_factory=lambda: ["duckduckgo"])
```

**Effect**: Only uses DuckDuckGo for image search.

---

## Singleton Instance

```python
cfg = AppConfig()
```

This creates a single instance that all modules import:

```python
from config.settings import cfg

# Access settings
print(cfg.pipeline.max_workers)  # 4
print(cfg.search.priority)       # ["google", "duckduckgo", "bing"]
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    config/settings.py                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Feature Flags                                               │
│  ├── RESUME_FROM_PROGRESS = False                           │
│  ├── VERBOSE_LOGGING = True                                  │
│  └── ENABLE_IMAGE_CACHE = True                               │
│                                                              │
│  Configuration Classes                                       │
│  ├── PathConfig          → cfg.paths                         │
│  ├── SearchConfig        → cfg.search                        │
│  ├── QueryConfig         → cfg.query                         │
│  ├── PipelineConfig      → cfg.pipeline                      │
│  ├── ImageQualityConfig  → cfg.quality                       │
│  ├── VerificationConfig  → cfg.verify                        │
│  ├── BackgroundRemovalConfig → cfg.bg                        │
│  ├── NotificationConfig  → cfg.notify                        │
│  ├── ProxyConfig         → cfg.proxy                         │
│  └── OutputConfig        → cfg.output                        │
│                                                              │
│  Main Config                                                 │
│  └── AppConfig           → cfg                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    Imported by all modules
                    ┌──────────────────────┐
                    │ from config.settings │
                    │ import cfg            │
                    └──────────────────────┘
```

---

## Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Central configuration hub for the entire application |
| **Location** | `config/settings.py` |
| **Usage** | `from config.settings import cfg` |
| **Customization** | Change values directly in the file |
| **Validation** | `cfg.validate()` checks if settings are valid |

**Think of it as**: The "control room" of the factory - every setting you change here affects how the entire system operates.
