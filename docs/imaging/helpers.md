# Image Helpers

**File**: [`imaging/helpers.py`](imaging/helpers.py)  
**Purpose**: Small utility functions shared across the imaging module for image validation and color extraction.

## 🎯 What It Does

The helpers module provides simple but essential image analysis functions used by the downloader and compositor. These are the "quick checks" that help validate and analyze images.

Think of it as your **image analysis toolkit** with:
1. ✅ Visual content detection (is this image blank/solid?)
2. ✅ Dominant color extraction (what's the main color?)

## 🔧 Functions

### has_visual_content()

**Purpose**: Detect if an image has actual visual content (not a blank image, progress bar, or solid color).

```python
def has_visual_content(
    image: Image.Image,
    min_std: float = 10.0,
    min_colours: int = 100,
) -> bool:
    """Return False if the image is blank / near-solid."""
    arr = np.array(image.convert("RGB"))
    
    # Check 1: Standard deviation (color variation)
    if np.std(arr) < min_std:
        return False
    
    # Check 2: Unique colors count
    uniq = len(np.unique(arr.reshape(-1, 3), axis=0))
    return uniq >= min_colours
```

**Parameters**:
| Parameter | Type | Default | Source |
|-----------|------|---------|--------|
| `image` | `Image.Image` | - | PIL image object |
| `min_std` | `float` | 10.0 | [`ImageQualityConfig.min_std_dev`](config/settings.py:823) |
| `min_colours` | `int` | 100 | [`ImageQualityConfig.min_unique_colours`](config/settings.py:824) |

**Returns**: `True` if image has visual content, `False` if blank/near-solid

#### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│              Visual Content Detection                       │
└─────────────────────────────────────────────────────────────┘

Input Image
    │
    ▼
Convert to RGB array
    │
    ├─── Calculate Standard Deviation
    │         │
    │         ▼
    │    Low std dev?
    │    (all pixels similar)
    │         │
    │    ┌────┴────┐
    │    │         │
    │   Yes       No
    │    │         │
    │    ▼         │
    │  Reject      │
    │              ▼
    │      Count unique colors
    │              │
    │              ▼
    │        Colors < 100?
    │              │
    │         ┌────┴────┐
    │         │         │
    │        Yes       No
    │         │         │
    │         ▼         ▼
    │      Reject    Accept
    │
    ▼
Final Result
```

#### Examples

**Good Image (accepted)**:
```python
# A photo with variety
img = Image.open("product_photo.jpg")
has_visual_content(img, min_std=10.0, min_colours=100)
# std_dev = 45.2, unique_colors = 15,432
# Returns: True ✅
```

**Blank Image (rejected)**:
```python
# A solid white image
img = Image.new("RGB", (800, 600), color="white")
has_visual_content(img, min_std=10.0, min_colours=100)
# std_dev = 0.0, unique_colors = 1
# Returns: False ❌
```

**Gradient Image (rejected)**:
```python
# A simple gradient
img = create_gradient_image()  # Smooth color transition
has_visual_content(img, min_std=10.0, min_colours=100)
# std_dev = 5.2, unique_colors = 200
# Returns: False (std_dev < 10) ❌
```

**Progress Bar (rejected)**:
```python
# A loading bar UI element
img = Image.open("progress_bar.png")
has_visual_content(img, min_std=10.0, min_colours=100)
# std_dev = 8.5, unique_colors = 45
# Returns: False (both checks fail) ❌
```

### dominant_colour()

**Purpose**: Extract the most prominent color from an image.

```python
def dominant_colour(path) -> Tuple[int, int, int]:
    """Get the dominant color from an image."""
    try:
        return ColorThief(str(path)).get_color(quality=1)
    except Exception:
        return (100, 100, 100)  # Default gray on failure
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `Path` or `str` | Path to image file |

**Returns**: `Tuple[int, int, int]` - RGB color values (0-255 each)

#### How It Works

Uses the `colorthief` library which:
1. Resizes image to reduce processing time
2. Creates a color palette using clustering
3. Returns the most dominant color

#### Examples

```python
# Product image with red shoes
dominant_colour("red_nike_shoes.jpg")
# Returns: (220, 45, 35) - Reddish color

# Product image with blue jeans
dominant_colour("blue_jeans.png")
# Returns: (35, 80, 180) - Bluish color

# Error case (file not found)
dominant_colour("missing_file.jpg")
# Returns: (100, 100, 100) - Default gray
```

#### Usage in Compositor

```python
# In core/compositor.py
def _pick_colour(self, query: str, img_path: Optional[Path]) -> Tuple[int, int, int]:
    """Pick background color based on product image."""
    if img_path and img_path.exists():
        # Use dominant color from image
        return dominant_colour(img_path)
    
    # Fallback to color based on query keywords
    query_lower = query.lower()
    if "red" in query_lower:
        return (255, 200, 200)  # Light red
    elif "blue" in query_lower:
        return (200, 200, 255)  # Light blue
    # ...
```

## 📊 Standard Deviation Calculation

The standard deviation measures how "spread out" the pixel values are:

```python
arr = np.array(image.convert("RGB"))
# Shape: (height, width, 3)
# Values: 0-255 for each R, G, B channel

std_dev = np.std(arr)
# High value = lots of color variation = complex image
# Low value = similar colors = simple/blank image
```

**Visual explanation**:

```
High std dev (varied image):     Low std dev (flat image):
┌─────────────────────────┐     ┌─────────────────────────┐
│ ██  ░░  ▓▓  ██  ░░  ▓▓  │     │ ░░  ░░  ░░  ░░  ░░  ░░  │
│ ▓▓  ██  ░░  ▓▓  ██  ░░  │     │ ░░  ░░  ░░  ░░  ░░  ░░  │
│ ░░  ▓▓  ██  ░░  ▓▓  ██  │     │ ░░  ░░  ░░  ░░  ░░  ░░  │
│ ██  ░░  ▓▓  ██  ░░  ▓▓  │     │ ░░  ░░  ░░  ░░  ░░  ░░  │
└─────────────────────────┘     └─────────────────────────┘
  std_dev = 85.3                  std_dev = 0.0
  ✅ Has visual content           ❌ No visual content
```

## 🔗 Where These Functions Are Used

### has_visual_content()

Used in [`imaging/downloader.py`](imaging/downloader.py:637):
```python
def _ok(self, img: Image.Image, raw: bytes) -> bool:
    # ... dimension checks ...
    
    return has_visual_content(img, c.min_std_dev, c.min_unique_colours)
```

**Purpose**: Reject downloaded images that are blank, solid-colored, or UI elements (progress bars, placeholders).

### dominant_colour()

Used in [`core/compositor.py`](core/compositor.py:165):
```python
@staticmethod
def _pick_colour(query: str, img_path: Optional[Path]) -> Tuple[int, int, int]:
    if img_path and img_path.exists():
        return dominant_colour(img_path)
    # ... fallback logic ...
```

**Purpose**: Choose a background color for the ad that complements the product image.

## 📈 Performance Notes

| Function | Complexity | Typical Time |
|----------|------------|--------------|
| `has_visual_content()` | O(n) where n = pixels | 5-20ms for 1000x1000 |
| `dominant_colour()` | O(n) with clustering | 10-50ms for 1000x1000 |

**Tips for performance**:
- Both functions are fast enough for real-time use
- `has_visual_content()` uses numpy vectorized operations
- `dominant_colour()` resizes internally for speed

---

**Previous**: [Font Manager](fonts.md)  
**Back to**: [Imaging Module Overview](overview.md)
