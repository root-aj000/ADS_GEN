# BackgroundRemover

**File**: [`imaging/background.py`](imaging/background.py)  
**Purpose**: AI-powered background removal using the `rembg` library to isolate product images for cleaner ad composition.

## 🎯 What It Does

The `BackgroundRemover` is like a professional photo editor who carefully cuts out the subject from a photo, removing everything behind it. This makes product images look cleaner and more professional in final ads.

Think of it as a **digital scissors expert** who:
1. ✅ Detects the main subject in an image
2. ✅ Removes the background (makes it transparent)
3. ✅ Validates that the result is reasonable (not too aggressive)
4. ✅ Falls back to the original if removal fails

**Why remove backgrounds?**
- Product images look cleaner on solid/gradient backgrounds
- Consistent styling across all ads
- Removes distracting elements (store shelves, random people, etc.)

## 🔧 Class Structure

```python
@dataclass
class BGRemovalResult:
    """Result of background removal operation."""
    success: bool              # Was removal successful?
    use_original: bool         # Should we use original image instead?
    output_path: Optional[Path]  # Path to output PNG
    stats: Dict[str, Any]      # Statistics (ratio, etc.)

class BackgroundRemover:
    """
    Serializes `rembg` calls through a lock (model is not
    guaranteed thread-safe) but allows the rest of the
    pipeline to run concurrently.
    """
    
    def __init__(self, cfg: BackgroundRemovalConfig) -> None:
        self.cfg = cfg
        self._lock = threading.Lock()  # Thread safety for rembg
```

### Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| [`should_remove()`](imaging/background.py:41) | Check if BG removal is appropriate | `bool` |
| [`remove()`](imaging/background.py:45) | Remove background from image | `BGRemovalResult` |
| [`_coherent()`](imaging/background.py:95) | Check if result is coherent | `bool` |

## 🔄 Background Removal Flow

```
┌─────────────────────────────────────────────────────────────┐
│              Background Removal Flow                        │
└─────────────────────────────────────────────────────────────┘

Product Image + Query: "red nike shoes"
                    │
                    ▼
         ┌─────────────────────┐
         │  Check Query        │
         │                     │
         │  Does query contain │
         │  scene keywords?    │
         │  (landscape, scene, │
         │   room, etc.)       │
         └──────────┬──────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
   Has scene?              No scene?
   keywords?               (product)
        │                       │
        ▼                       ▼
┌───────────────┐      ┌───────────────┐
│ SKIP removal  │      │  Remove BG    │
│ Use original  │      │  with rembg   │
└───────────────┘      └───────┬───────┘
                               │
                               ▼
                    ┌───────────────────┐
                    │  Validate Result  │
                    │                   │
                    │  • Too aggressive?│
                    │    (< 5% kept)    │
                    │  • Nothing removed?│
                    │    (> 98% kept)   │
                    │  • Object too tiny?│
                    └─────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        Too aggressive   Nothing removed   Good result
        (< 5% kept)      (> 98% kept)     (5-98% kept)
              │               │               │
              ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Use      │    │ Use      │    │ Save PNG │
        │ original │    │ original │    │ with     │
        │ fallback │    │ fallback │    │ alpha    │
        └──────────┘    └──────────┘    └──────────┘
```

## 🔍 When to Remove Backgrounds

### Scene Keywords (Skip Removal)

```python
def should_remove(self, query: str) -> bool:
    low = query.lower()
    return not any(kw in low for kw in self.cfg.scene_keywords)
```

**Default scene keywords**:
```python
scene_keywords: Tuple[str, ...] = (
    "scene", "landscape", "room", "interior",
    "exterior", "background", "view", "panorama"
)
```

**Why skip these?**
- "Living room scene" → Keep the room as context
- "Mountain landscape" → The scene IS the subject
- "Kitchen interior" → Background is important

### Product Images (Remove Background)

For most products, background removal is appropriate:
- "red nike shoes" → Remove background
- "iPhone 15 Pro" → Remove background
- "wooden chair" → Remove background

## 📊 Validation Checks

### 1. Minimum Retention (Too Aggressive)

```python
# If less than 5% of pixels remain, removal was too aggressive
if ratio < c.min_retention:  # 0.05 = 5%
    if ratio >= 0.01 and self._coherent(alpha):
        # At least 1% and coherent - might be okay
        result.save(dst, "PNG")
        return BGRemovalResult(True, False, dst, {"ratio": ratio})
    # Otherwise, use original
    return BGRemovalResult(False, True, stats={"ratio": ratio})
```

**What this catches**:
- Model removed too much (thought everything was background)
- Image was mostly background to begin with
- Result would be a tiny speck

### 2. Maximum Retention (Nothing Removed)

```python
# If more than 98% of pixels remain, nothing was removed
if ratio > c.max_retention:  # 0.98 = 98%
    return BGRemovalResult(False, True, stats={"ratio": ratio})
```

**What this catches**:
- Image already had transparent background
- Model couldn't detect a subject
- No point in saving the same image

### 3. Minimum Object Size

```python
# Check if remaining object is too small
coords = np.argwhere(alpha > 10)
if len(coords):
    mn, mx = coords.min(0), coords.max(0)
    obj = (mx[1] - mn[1]) * (mx[0] - mn[0])
    if obj / (result.width * result.height) < c.min_object_ratio:
        return BGRemovalResult(False, True, stats={"ratio": ratio})
```

**What this catches**:
- Object bounding box is tiny compared to image
- Model only kept a small corner of the image

### 4. Coherence Check

```python
def _coherent(self, alpha: np.ndarray) -> bool:
    """Check if the remaining pixels form a coherent shape."""
    mask = alpha > 10
    rows, cols = np.any(mask, 1), np.any(mask, 0)
    
    if not rows.any() or not cols.any():
        return False
    
    # Find bounding box
    r0, r1 = np.where(rows)[0][[0, -1]]
    c0, c1 = np.where(cols)[0][[0, -1]]
    
    # Check fill ratio within bounding box
    bbox = (r1 - r0 + 1) * (c1 - c0 + 1)
    filled = np.sum(mask[r0:r1 + 1, c0:c1 + 1])
    
    return (filled / bbox) >= self.cfg.min_fill_ratio
```

**What this checks**:
- Do the remaining pixels form a solid shape?
- Or are they scattered random noise?

```
Coherent shape:          Incoherent noise:
┌─────────────────┐      ┌─────────────────┐
│     ████████    │      │   ██    ██      │
│   ██████████    │      │       ██   ██   │
│  ███████████    │      │   ██       ██   │
│   ██████████    │      │       ██        │
│     ████████    │      │   ██       ██   │
└─────────────────┘      └─────────────────┘
  fill ratio: 0.8          fill ratio: 0.2
  ✅ Coherent              ❌ Not coherent
```

## ⚙️ Configuration

From [`BackgroundRemovalConfig`](config/settings.py:829):

```python
@dataclass(frozen=True)
class BackgroundRemovalConfig:
    scene_keywords: Tuple[str, ...] = (
        "scene", "landscape", "room", "interior",
        "exterior", "background", "view", "panorama"
    )
    min_retention: float = 0.05      # Minimum 5% of pixels kept
    max_retention: float = 0.98      # Maximum 98% before skipping
    min_object_ratio: float = 0.05   # Minimum 5% bounding box
    min_fill_ratio: float = 0.3      # Minimum 30% fill in bbox
```

## 🔗 Thread Safety

```python
def remove(self, src: Path, dst: Path) -> BGRemovalResult:
    log.info("BG removal: %s", src.name)
    
    try:
        with Image.open(src) as orig:
            total_px = orig.width * orig.height
            
            with open(src, "rb") as fh:
                raw = fh.read()
            
            # CRITICAL: Lock protects rembg model
            with self._lock:
                out_data = rembg_remove(raw)
            
            # ... rest of processing ...
```

**Why a lock?**
- `rembg` uses a neural network internally
- The model may not be thread-safe
- Lock ensures only one removal at a time
- Other pipeline operations can still run concurrently

## 🎯 Real-World Example

### Scenario: Processing Product Images

```python
remover = BackgroundRemover(cfg)

# Example 1: Clear product image
result1 = remover.remove(
    Path("nike_shoes.jpg"),
    Path("nike_shoes_no_bg.png")
)
print(result1)
# BGRemovalResult(success=True, use_original=False, output_path=Path("nike_shoes_no_bg.png"))
# Ratio: 0.45 (45% of pixels kept)

# Example 2: Image already has transparent background
result2 = remover.remove(
    Path("already_transparent.png"),
    Path("output.png")
)
print(result2)
# BGRemovalResult(success=False, use_original=True)
# Ratio: 0.99 (99% kept - nothing removed)

# Example 3: Too aggressive removal
result3 = remover.remove(
    Path("complex_image.jpg"),
    Path("output.png")
)
print(result3)
# BGRemovalResult(success=False, use_original=True)
# Ratio: 0.02 (only 2% kept - too aggressive)
```

### Integration with Pipeline

```python
# In core/pipeline.py

# Check if we should remove background
if self.bg_remover and self.bg_remover.should_remove(query):
    bg_result = self.bg_remover.remove(image_path, output_path)
    
    if bg_result.success:
        # Use the image with removed background
        final_path = bg_result.output_path
    elif bg_result.use_original:
        # Removal failed or was unnecessary
        final_path = image_path  # Keep original
    else:
        # Some other issue
        final_path = image_path
```

## 📈 Memory Management

```python
# Explicit cleanup after processing
result.save(dst, "PNG")
del alpha, result
gc.collect()  # Force garbage collection
```

**Why explicit cleanup?**
- Image processing uses large memory buffers
- `rembg` model may cache data
- Explicit GC prevents memory buildup in long-running pipelines

## 🔍 Output Format

Background removal always outputs **PNG** format:

```python
result.save(dst, "PNG")
```

**Why PNG?**
- PNG supports alpha channel (transparency)
- Lossless compression (no quality loss)
- Standard format for transparent images

---

**Next**: [Font Manager](fonts.md) → Loading and managing fonts for ad text
