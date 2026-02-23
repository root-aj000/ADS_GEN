# Imaging Module Overview

The `imaging/` module handles all image-related operations in the Ad Generator pipeline. It's responsible for downloading, validating, processing, caching, and verifying product images before they're composed into final ad creatives.

## 📁 Module Structure

```
imaging/
├── __init__.py       # Module exports
├── downloader.py     # Image downloading and validation
├── background.py     # Background removal using AI
├── helpers.py        # Image utility functions
├── cache.py          # SQLite-based image cache
├── scorer.py         # Multi-factor quality scoring
├── verifier.py       # CLIP/BLIP AI verification
├── fonts.py          # Font loading and management
└── effects_3d.py     # 3D mesh generation from 2D images
```

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IMAGING MODULE DATA FLOW                          │
└─────────────────────────────────────────────────────────────────────────────┘

                    Search Results (ImageResult list)
                              │
                              ▼
                    ┌─────────────────┐
                    │  ImageCache     │ ◄─── Check if query already processed
                    │  (cache.py)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ ImageQualityScorer │ ◄─── Score and rank candidates
                    │  (scorer.py)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ ImageDownloader │ ◄─── Download best candidate
                    │  (downloader.py) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  ImageVerifier  │ ◄─── AI verification (CLIP/BLIP)
                    │  (verifier.py)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ BackgroundRemover│ ◄─── Remove background if needed
                    │  (background.py) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  AdCompositor   │ ◄─── Compose final ad
                    │  (core/)         │
                    └─────────────────┘
```

## 🧩 Components at a Glance

| Component | File | Purpose | Thread-Safe |
|-----------|------|---------|-------------|
| **ImageDownloader** | [`downloader.py`](imaging/downloader.py) | Downloads images from URLs, validates quality | ✅ Yes |
| **BackgroundRemover** | [`background.py`](imaging/background.py) | Removes image backgrounds using AI | ✅ Yes (locked) |
| **ImageCache** | [`cache.py`](imaging/cache.py) | Caches downloaded images to avoid re-downloads | ✅ Yes |
| **ImageQualityScorer** | [`scorer.py`](imaging/scorer.py) | Scores image quality on multiple factors | ✅ Yes |
| **ImageVerifier** | [`verifier.py`](imaging/verifier.py) | AI-powered image-text verification | ✅ Yes (singleton) |
| **FontManager** | [`fonts.py`](imaging/fonts.py) | Loads and manages fonts for ad text | ✅ Yes |
| **Helper Functions** | [`helpers.py`](imaging/helpers.py) | Visual content detection, color extraction | ✅ Yes |
| **3DEffectsEngine** | [`effects_3d.py`](imaging/effects_3d.py) | Generates 3D meshes from 2D images | ✅ Yes |

## 🎯 Real-World Analogy

Think of the imaging module as a **professional photo studio**:

1. **ImageCache** = The archive of previously shot photos - check here first before shooting new ones
2. **ImageQualityScorer** = The casting director - evaluates which photo candidates are best
3. **ImageDownloader** = The photographer - goes out and captures the selected photo
4. **ImageVerifier** = The quality inspector - confirms the photo matches what was requested
5. **BackgroundRemover** = The photo editor - removes unwanted backgrounds
6. **FontManager** = The typography specialist - ensures text looks professional

## 📊 Key Data Structures

### ImageResult (from search module)
```python
@dataclass
class ImageResult:
    url: str              # URL of the image
    source: str           # Search engine (google/bing/duckduckgo)
    width: int            # Image width in pixels
    height: int           # Image height in pixels
    thumbnail: str        # Thumbnail URL
```

### DownloadResult
```python
@dataclass
class DownloadResult:
    success: bool                 # Was download successful?
    path: Optional[Path]          # Local file path
    source_url: Optional[str]     # Original URL
    info: Dict[str, Any]          # Metadata (width, height, hash, etc.)
```

### VerificationResult
```python
@dataclass
class VerificationResult:
    accepted: bool           # Should we accept this image?
    clip_score: float        # CLIP similarity (0.0-1.0)
    blip_score: float        # BLIP word overlap (0.0-1.0)
    combined_score: float    # Weighted combination
    blip_caption: str        # AI-generated caption
    reason: str              # Acceptance/rejection reason
```

### QualityReport
```python
@dataclass
class QualityReport:
    sharpness: float         # Image sharpness (0-10)
    contrast: float          # Contrast level (0-10)
    resolution: float        # Resolution score (0-10)
    source_trust: float      # Domain reputation (0-10)
    format_bonus: float      # PNG bonus for transparency
    penalty: float           # Penalties for small/thumbnail images
    final_score: float       # Weighted final score
```

## ⚙️ Configuration

The imaging module uses several configuration classes from [`config/settings.py`](config/settings.py):

### ImageQualityConfig
Controls image validation thresholds:
- `min_width`, `min_height` - Minimum dimensions (default: 100px)
- `min_file_bytes` - Minimum file size (default: 5000 bytes)
- `min_aspect`, `max_aspect` - Aspect ratio range (default: 0.3 to 3.0)
- `min_std_dev` - Minimum color variation (default: 10.0)
- `min_unique_colours` - Minimum unique colors (default: 100)

### BackgroundRemovalConfig
Controls background removal behavior:
- `scene_keywords` - Keywords to skip background removal (e.g., "scene", "landscape")
- `min_retention` - Minimum pixels to keep (default: 0.05 = 5%)
- `max_retention` - Maximum pixels before skipping (default: 0.98)
- `min_object_ratio` - Minimum object size ratio (default: 0.05)
- `min_fill_ratio` - Minimum fill within bounding box (default: 0.3)

### VerificationConfig
Controls AI verification:
- `use_clip` - Enable CLIP model (default: True)
- `use_blip` - Enable BLIP model (default: True)
- `clip_threshold` - Minimum CLIP score (default: 0.25)
- `blip_threshold` - Minimum BLIP score (default: 0.15)
- `combined_threshold` - Minimum combined score (default: 0.20)
- `device` - Compute device: "auto", "cuda", or "cpu"

## 🔗 Module Dependencies

```
imaging/
    ├── config/settings.py (ImageQualityConfig, BackgroundRemovalConfig, VerificationConfig)
    ├── search/base.py (ImageResult)
    ├── utils/concurrency.py (ThreadSafeSet)
    ├── utils/log_config.py (get_logger)
    └── utils/retry.py (retry decorator)

External Libraries:
    ├── PIL/Pillow (Image manipulation)
    ├── requests (HTTP downloads)
    ├── numpy (Array operations)
    ├── rembg (Background removal AI)
    ├── transformers (CLIP/BLIP models)
    ├── torch (Deep learning framework)
    └── colorthief (Color extraction)
```

## 🚀 Performance Considerations

1. **Thread Safety**: All components are designed for concurrent use in multi-threaded pipelines
2. **Memory Management**: Explicit garbage collection after image processing
3. **Caching**: SQLite cache prevents re-downloading identical queries
4. **Model Caching**: AI models loaded once as singletons
5. **Lazy Loading**: Fonts downloaded only when needed

---

## Next Steps

- **[Image Downloader](downloader.md)** - Detailed downloading and validation logic
- **[Image Cache](cache.md)** - SQLite-based caching system
- **[Image Scorer](scorer.md)** - Multi-factor quality scoring
- **[Image Verifier](verifier.md)** - CLIP/BLIP AI verification
- **[Background Removal](background.md)** - AI-powered background removal
- **[Font Manager](fonts.md)** - Font loading and management
- **[3D Effects Engine](effects-3d.md)** - AI-powered 3D mesh generation
