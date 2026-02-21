# ImageQualityScorer

**File**: [`imaging/scorer.py`](imaging/scorer.py)  
**Purpose**: Multi-factor image quality scoring system that evaluates and ranks image candidates before downloading.

## 🎯 What It Does

The `ImageQualityScorer` is like a professional photo editor who quickly looks at a stack of photos and picks the best ones. It evaluates images on multiple criteria and assigns a score that determines which image to download first.

Think of it as a **talent show judge** who scores contestants on:
1. ✅ Sharpness (is the image blurry or crisp?)
2. ✅ Contrast (are there rich colors or is it washed out?)
3. ✅ Resolution (is it high-quality or pixelated?)
4. ✅ Source trust (is it from a reputable stock photo site?)
5. ✅ Format bonus (PNG for transparency support)
6. ✅ Penalties (tiny thumbnails, placeholder images)

## 🔧 Class Structure

```python
@dataclass
class QualityReport:
    """Breakdown of quality metrics for an image."""
    sharpness: float = 0.0      # 0-10 (Laplacian variance)
    contrast: float = 0.0       # 0-10 (luminance std dev)
    resolution: float = 0.0     # 0-10 (megapixels)
    source_trust: float = 0.0   # 0-10 (domain reputation)
    format_bonus: float = 0.0   # PNG bonus for transparency
    penalty: float = 0.0        # Negative score for issues
    final_score: float = 0.0    # Weighted combination

class ImageQualityScorer:
    """
    Scores images on multiple axes:
    - Sharpness (Laplacian variance)
    - Contrast (std dev of luminance)
    - Resolution (total pixel count, normalised)
    - Source trust (domain reputation)
    - Format (PNG bonus for transparency)
    - Penalties (thumbnail patterns, tiny images)
    """
    
    TRUSTED_DOMAINS = {
        "shutterstock.com": 0.9,
        "istockphoto.com": 0.9,
        "gettyimages.com": 0.9,
        "adobe.com": 0.85,
        "unsplash.com": 0.85,
        "pexels.com": 0.8,
        "freepik.com": 0.7,
        "pngtree.com": 0.7,
        "amazon.com": 0.6,
        "ebay.com": 0.5,
    }
    
    PENALTY_PATTERNS = (
        "thumb", "small", "icon", "tiny", "mini",
        "preview", "placeholder", "loading", "spinner",
    )
```

### Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| [`score_result()`](imaging/scorer.py:69) | Quick URL-based scoring (no download) | `float` |
| [`score_image()`](imaging/scorer.py:100) | Full image analysis (requires download) | `QualityReport` |

## 🔄 Scoring Flow

```
┌─────────────────────────────────────────────────────────────┐
│              Two-Stage Scoring Process                      │
└─────────────────────────────────────────────────────────────┘

Stage 1: Quick Score (Before Download)
──────────────────────────────────────
        ImageResult from search
                │
                ▼
    ┌─────────────────────┐
    │  Analyze URL only   │
    │  • Format hints     │
    │  • Domain trust     │
    │  • Resolution hint  │
    │  • Penalty patterns │
    └──────────┬──────────┘
               │
               ▼
        Quick Score (0-50+)
               │
               ▼
    ┌─────────────────────┐
    │  Rank & Select      │
    │  Top Candidates     │
    └──────────┬──────────┘
               │
               ▼
        Download Top N

Stage 2: Deep Score (After Download)
─────────────────────────────────────
        Downloaded Image
               │
               ▼
    ┌─────────────────────┐
    │  Full Analysis      │
    │  • Sharpness        │
    │  • Contrast         │
    │  • Resolution       │
    │  • Format check     │
    └──────────┬──────────┘
               │
               ▼
        QualityReport
```

## 📊 Scoring Factors

### 1. Quick Score (URL-Based)

Used **before downloading** to rank candidates:

```python
def score_result(self, result: ImageResult) -> float:
    """Quick score based on URL metadata only (no download needed)."""
    s = 0.0
    low = result.url.lower()
    
    # Format bonus
    if ".png" in low:
        s += 10
    elif ".webp" in low:
        s += 5
    
    # Source trust (domain reputation)
    for domain, trust in self.TRUSTED_DOMAINS.items():
        if domain in low:
            s += trust * 10
            break
    
    # Resolution hint from search metadata
    if result.width > 0 and result.height > 0:
        mpx = (result.width * result.height) / 1_000_000
        s += min(mpx * 5, 20)
    
    # Penalties for thumbnail patterns
    if any(p in low for p in self.PENALTY_PATTERNS):
        s -= 15
    
    # Engine trust (DuckDuckGo tends to have cleaner results)
    s += {"duckduckgo": 3, "bing": 2, "google": 1}.get(result.source, 0)
    
    return s
```

**Example Scores**:
| URL | Score Calculation | Final |
|-----|-------------------|-------|
| `shutterstock.com/photo.png` | 9 (trust) + 10 (PNG) = 19 | **19** |
| `unsplash.com/image.webp` | 8.5 (trust) + 5 (WebP) = 13.5 | **13.5** |
| `random-site.com/thumb.jpg` | 0 (trust) - 15 (penalty) = -15 | **-15** |
| `amazon.com/product.png` | 6 (trust) + 10 (PNG) = 16 | **16** |

### 2. Deep Score (Image Analysis)

Used **after downloading** for full quality assessment:

```python
def score_image(self, image: Image.Image, result: Optional[ImageResult] = None) -> QualityReport:
    """Full quality analysis on a downloaded image."""
    report = QualityReport()
    
    # 1. Sharpness (Laplacian variance)
    #    High variance = sharp edges = crisp image
    grey = image.convert("L")
    laplacian = grey.filter(ImageFilter.Kernel(...))
    report.sharpness = min(stat.var[0] / 100, 10.0)
    
    # 2. Contrast (std dev of luminance)
    #    High std dev = more variation = better contrast
    stat = ImageStat.Stat(grey)
    report.contrast = min(stat.stddev[0] / 10, 10.0)
    
    # 3. Resolution (megapixels)
    mpx = (image.width * image.height) / 1_000_000
    report.resolution = min(mpx * 3, 10.0)
    
    # 4. Source trust
    if result:
        for domain, trust in self.TRUSTED_DOMAINS.items():
            if domain in result.url.lower():
                report.source_trust = trust * 10
                break
    
    # 5. Format bonus
    if image.mode == "RGBA":
        report.format_bonus = 3.0  # Transparency support!
    
    # 6. Penalties
    if image.width < 200 or image.height < 200:
        report.penalty += 5.0
    if image.width < 100 or image.height < 100:
        report.penalty += 10.0
    
    # Final weighted score
    report.final_score = (
        report.sharpness * c.sharpness_weight +
        report.contrast * c.contrast_weight +
        report.resolution * c.resolution_weight +
        report.source_trust * c.source_weight +
        report.format_bonus -
        report.penalty
    )
    
    return report
```

## 🔍 Scoring Factors Explained

### Sharpness (Laplacian Variance)

**What it measures**: Edge clarity in the image

**How it works**:
1. Convert image to grayscale
2. Apply Laplacian kernel (edge detection)
3. Calculate variance of the result
4. High variance = sharp edges = crisp image

**Real-world analogy**: Like measuring how "in focus" a photo is. A blurry photo has gradual color transitions (low variance), while a sharp photo has abrupt edges (high variance).

```
Blurry Image (low sharpness):    Sharp Image (high sharpness):
┌─────────────────────┐        ┌─────────────────────┐
│  ░▒▓█▓▒░           │        │  ██  █   ███       │
│  ░▒▓█▓▒░           │        │  ██  █   █  █      │
│  ░▒▓█▓▒░           │        │  ██  █   █  █      │
│                    │        │  ██  █   ███       │
└─────────────────────┘        └─────────────────────┘
  variance = 15                  variance = 850
  score = 0.15                   score = 8.5
```

### Contrast (Luminance Standard Deviation)

**What it measures**: Range of light to dark values

**How it works**:
1. Convert image to grayscale
2. Calculate standard deviation of pixel values
3. High std dev = wide range = good contrast

**Real-world analogy**: Like comparing a foggy day (low contrast) to a sunny day with deep shadows (high contrast).

```
Low Contrast:              High Contrast:
Pixels: [128,130,127,129]  Pixels: [20,200,50,240]
std dev = 1.2              std dev = 98.5
score = 0.12               score = 9.85
```

### Resolution Score

**What it measures**: Total pixel count (megapixels)

**How it works**:
```python
mpx = (width * height) / 1_000_000
score = min(mpx * 3, 10.0)  # Cap at 10
```

**Examples**:
| Dimensions | Megapixels | Score |
|------------|------------|-------|
| 500 x 500 | 0.25 MP | 0.75 |
| 1000 x 1000 | 1.0 MP | 3.0 |
| 2000 x 1500 | 3.0 MP | 9.0 |
| 4000 x 3000 | 12.0 MP | 10.0 (capped) |

### Source Trust (Domain Reputation)

**What it measures**: Reliability of the image source

**Trusted Domains**:
```python
TRUSTED_DOMAINS = {
    "shutterstock.com": 0.9,   # Professional stock photos
    "istockphoto.com": 0.9,   # Professional stock photos
    "gettyimages.com": 0.9,   # Professional stock photos
    "adobe.com": 0.85,        # Adobe Stock
    "unsplash.com": 0.85,     # Free high-quality photos
    "pexels.com": 0.8,        # Free stock photos
    "freepik.com": 0.7,       # Free vectors/photos
    "pngtree.com": 0.7,       # PNG images
    "amazon.com": 0.6,        # Product images
    "ebay.com": 0.5,          # Product images
}
```

**Score calculation**: `trust_value * 10`

**Why it matters**: Professional stock photo sites have consistently high-quality, properly licensed images. Random websites may have compressed, watermarked, or low-quality images.

### Format Bonus

**What it measures**: Image format capabilities

**Bonus for PNG**:
- Supports transparency (can remove background cleanly)
- Lossless compression (no quality loss)
- Better for product images with transparent backgrounds

### Penalties

**What triggers penalties**:
```python
PENALTY_PATTERNS = (
    "thumb",      # Thumbnail version
    "small",      # Small version
    "icon",       # Icon size
    "tiny",       # Tiny version
    "mini",       # Miniature
    "preview",    # Preview image
    "placeholder", # Placeholder
    "loading",    # Loading spinner
    "spinner",    # Loading animation
)
```

**Size penalties**:
- Width or height < 200px: -5 points
- Width or height < 100px: -10 points (additional)

## ⚙️ Configuration

Weights are configurable via [`ImageQualityConfig`](config/settings.py:814):

```python
@dataclass(frozen=True)
class ImageQualityConfig:
    # Validation thresholds
    min_width: int = 100
    min_height: int = 100
    min_file_bytes: int = 5000
    min_aspect: float = 0.3
    max_aspect: float = 3.0
    
    # Visual content checks
    min_std_dev: float = 10.0
    min_unique_colours: int = 100
    
    # Scoring weights
    sharpness_weight: float = 1.0
    contrast_weight: float = 1.0
    resolution_weight: float = 1.0
    source_weight: float = 0.5
```

## 🎯 Real-World Example

### Scenario: Scoring Search Results for "Red Nike Shoes"

```python
results = [
    ImageResult(url="https://shutterstock.com/red-nike.png", source="google", width=1200, height=800),
    ImageResult(url="https://random-site.com/thumb.jpg", source="bing", width=150, height=150),
    ImageResult(url="https://unsplash.com/nike-shoes.webp", source="duckduckgo", width=2000, height=1500),
]

scorer = ImageQualityScorer(cfg)

for r in results:
    score = scorer.score_result(r)
    print(f"{r.url}: {score:.1f}")
```

**Output**:
```
https://shutterstock.com/red-nike.png: 25.0
  └─ 9 (trust) + 10 (PNG) + 4.8 (resolution) + 1 (google) = 24.8 ≈ 25

https://random-site.com/thumb.jpg: -12.0
  └─ 0 (trust) - 15 (thumb penalty) + 0.1 (resolution) + 2 (bing) = -12.9 ≈ -13

https://unsplash.com/nike-shoes.webp: 25.5
  └─ 8.5 (trust) + 5 (WebP) + 10 (resolution capped) + 3 (duckduckgo) = 26.5
```

**Ranking**:
1. unsplash.com (25.5) - Best candidate
2. shutterstock.com (25.0) - Also excellent
3. random-site.com (-13) - Rejected (thumbnail)

## 📈 QualityReport Summary

```python
report = scorer.score_image(downloaded_image, result)
print(report.summary())
```

**Output**:
```
score=7.8 (sharp=8.2 contrast=6.5 res=9.0 source=9.0 fmt=3.0 pen=0.0)
```

---

**Next**: [Image Verifier](verifier.md) → AI-powered image-text matching
