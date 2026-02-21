# FontManager

**File**: [`imaging/fonts.py`](imaging/fonts.py)  
**Purpose**: Manages font loading for ad text composition, with automatic downloading from Google Fonts CDN.

## 🎯 What It Does

The `FontManager` is like a typography specialist who ensures you always have the right fonts for your ad designs. It tries multiple sources to find fonts and automatically downloads them if missing.

Think of it as a **font librarian** who:
1. ✅ Checks if fonts are installed on your system
2. ✅ Looks in the local fonts directory
3. ✅ Downloads missing fonts from Google Fonts CDN
4. ✅ Falls back to PIL default font if all else fails
5. ✅ Caches loaded fonts for faster access

**Why is this important?**
- Professional ads need professional fonts
- Consistent text styling across all ads
- Automatic font management (no manual installation needed)

## 🔧 Class Structure

```python
# Google Fonts CDN URLs (free, no API key needed)
FONT_URLS = {
    "Roboto-Regular.ttf": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf",
    "Roboto-Bold.ttf": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
    "OpenSans-Regular.ttf": "https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Regular.ttf",
    "OpenSans-Bold.ttf": "https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Bold.ttf",
}

class FontManager:
    """Load fonts from local dir; download if missing."""
    
    def __init__(self, fonts_dir: Path) -> None:
        self.fonts_dir = fonts_dir          # Local font storage
        fonts_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, ImageFont.FreeTypeFont] = {}  # Loaded fonts
```

### Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| [`get()`](imaging/fonts.py:49) | Get a font (load, download, or fallback) | `ImageFont.FreeTypeFont` |
| [`_try_load()`](imaging/fonts.py:65) | Try loading from multiple sources | `ImageFont.FreeTypeFont` |
| [`_download()`](imaging/fonts.py:34) | Download font from CDN | `Optional[Path]` |

## 🔄 Font Loading Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  Font Loading Priority                      │
└─────────────────────────────────────────────────────────────┘

Request: get("Roboto-Bold.ttf", size=24)
                    │
                    ▼
         ┌─────────────────────┐
         │  Check Cache        │
         │  "Roboto-Bold:24"   │
         └──────────┬──────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
   In cache?               Not cached
        │                       │
        ▼                       ▼
   Return cached      ┌─────────────────────┐
                      │  Try System Fonts   │
                      │  (Roboto-Bold,      │
                      │   RobotoBold,       │
                      │   roboto)           │
                      └──────────┬──────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
              Found? No                Found? Yes
                    │                         │
                    ▼                         ▼
         ┌─────────────────────┐        Return font
         │  Try Local Dir      │
         │  fonts_dir/         │
         │  Roboto-Bold.ttf    │
         └──────────┬──────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
   Found? No                Found? Yes
        │                       │
        ▼                       ▼
┌─────────────────────┐    Return font
│  Download from CDN  │
│  Google Fonts       │
└──────────┬──────────┘
           │
           ▼
    ┌──────┴──────┐
    │             │
    ▼             ▼
 Success?     Failed
    │             │
    ▼             ▼
Return font  Try fallback
    │         fonts
    │             │
    ▼             ▼
         ┌─────────────────────┐
         │  PIL Default Font   │
         │  (Last resort)      │
         └─────────────────────┘
```

## 📚 Font Loading Priority

### 1. Cache Check
```python
key = f"{name}:{size}"
if key in self._cache:
    return self._cache[key]
```
Already loaded? Return immediately.

### 2. System Fonts
```python
# Try variations of the font name
for sys_name in (name, name.replace("-", ""), name.split("-")[0].lower()):
    try:
        f = ImageFont.truetype(sys_name, size)
        log.debug("Loaded system font: %s", sys_name)
        return f
    except OSError:
        continue
```

**Name variations tried**:
| Requested | Variations Tried |
|-----------|-----------------|
| `Roboto-Bold` | `Roboto-Bold`, `RobotoBold`, `roboto` |
| `OpenSans-Regular` | `OpenSans-Regular`, `OpenSansRegular`, `opensans` |

### 3. Local Fonts Directory
```python
local = self.fonts_dir / name
if local.exists():
    try:
        return ImageFont.truetype(str(local), size)
    except OSError:
        pass
```

Checks if the font file exists in the local `fonts/` directory.

### 4. Download from CDN
```python
downloaded = self._download(name)
if downloaded:
    try:
        return ImageFont.truetype(str(downloaded), size)
    except OSError:
        pass
```

Downloads from Google Fonts CDN:
```python
def _download(self, name: str) -> Optional[Path]:
    url = FONT_URLS.get(name)
    if not url:
        return None
    
    dest = self.fonts_dir / name
    if dest.exists():
        return dest  # Already downloaded
    
    try:
        log.info("Downloading font: %s", name)
        urllib.request.urlretrieve(url, str(dest))
        return dest
    except Exception as exc:
        log.warning("Font download failed: %s — %s", name, exc)
        return None
```

### 5. Fallback Fonts
```python
# Try any available font from the CDN
for fallback_name in FONT_URLS:
    fb = self._download(fallback_name)
    if fb:
        try:
            return ImageFont.truetype(str(fb), size)
        except OSError:
            continue
```

### 6. PIL Default (Last Resort)
```python
log.warning("All font loading failed — using PIL default")
return ImageFont.load_default()
```

## 🎨 Available Fonts

### Pre-configured CDN Fonts

| Font Name | Style | Best For |
|-----------|-------|----------|
| `Roboto-Regular.ttf` | Sans-serif, regular | Body text, descriptions |
| `Roboto-Bold.ttf` | Sans-serif, bold | Headlines, product names |
| `OpenSans-Regular.ttf` | Sans-serif, regular | Alternative body text |
| `OpenSans-Bold.ttf` | Sans-serif, bold | Alternative headlines |

**Why these fonts?**
- **Roboto**: Modern, clean, highly readable at all sizes
- **Open Sans**: Friendly, optimized for screens
- Free and open-source (Google Fonts)
- No API key required for download

### Adding Custom Fonts

To add your own fonts:

1. **Option 1**: Place TTF files in the fonts directory
```
data/
└── fonts/
    ├── Roboto-Regular.ttf
    ├── Roboto-Bold.ttf
    └── YourCustomFont.ttf  ← Add here
```

2. **Option 2**: Add to `FONT_URLS` dictionary
```python
FONT_URLS = {
    # ... existing fonts ...
    "YourCustomFont.ttf": "https://example.com/fonts/YourCustomFont.ttf",
}
```

## 🔗 Usage Examples

### Basic Usage
```python
from pathlib import Path
from imaging.fonts import FontManager

# Initialize with fonts directory
font_mgr = FontManager(Path("data/fonts"))

# Get a font
font = font_mgr.get("Roboto-Bold.ttf", size=32)

# Use with PIL
from PIL import Image, ImageDraw
img = Image.new("RGB", (800, 400), color="white")
draw = ImageDraw.Draw(img)
draw.text((50, 50), "SALE!", font=font, fill="red")
```

### Multiple Font Sizes
```python
# Each size is cached separately
title_font = font_mgr.get("Roboto-Bold.ttf", size=48)    # Headline
subtitle_font = font_mgr.get("Roboto-Regular.ttf", size=24)  # Subtitle
body_font = font_mgr.get("OpenSans-Regular.ttf", size=16)    # Body text
```

### Integration with AdCompositor
```python
# In core/compositor.py
class AdCompositor:
    def __init__(self, fonts_dir: Optional[Path] = None) -> None:
        self.font_mgr = FontManager(fonts_dir or Path("data/fonts"))
    
    def _text(self, img: Image.Image, row: pd.Series) -> None:
        draw = ImageDraw.Draw(img)
        
        # Product name (bold, large)
        name_font = self.font_mgr.get("Roboto-Bold.ttf", size=36)
        draw.text((50, 100), row["product_name"], font=name_font)
        
        # Price (regular, medium)
        price_font = self.font_mgr.get("Roboto-Regular.ttf", size=24)
        draw.text((50, 150), f"${row['price']}", font=price_font)
```

## 📁 File Structure

```
data/
└── fonts/                      # Local font storage
    ├── Roboto-Regular.ttf      # Downloaded on first use
    ├── Roboto-Bold.ttf         # Downloaded on first use
    ├── OpenSans-Regular.ttf    # Downloaded on first use
    └── OpenSans-Bold.ttf       # Downloaded on first use
```

**First run behavior**:
- Fonts directory is created automatically
- Fonts are downloaded on-demand when first requested
- Subsequent runs use cached fonts (no re-download)

## 🛡️ Error Handling

The font manager is designed to never fail:

```python
try:
    # Try each source in order
    font = self._try_load(name, size)
    self._cache[key] = font
    return font
except OSError:
    # All loading failed
    pass

# Should never reach here, but just in case
log.warning("All font loading failed — using PIL default")
return ImageFont.load_default()
```

**What happens if font loading fails?**
1. System fonts not found → try local
2. Local font not found → try download
3. Download fails → try fallback fonts
4. All fallbacks fail → use PIL default (always available)

## 📊 Caching Performance

```python
# Internal cache structure
self._cache: dict[str, ImageFont.FreeTypeFont] = {}

# Key format: "{font_name}:{size}"
# Example: "Roboto-Bold.ttf:32"

# First call: Loads from disk/download (slower)
font1 = font_mgr.get("Roboto-Bold.ttf", 32)  # ~50ms

# Subsequent calls: Returns from cache (instant)
font2 = font_mgr.get("Roboto-Bold.ttf", 32)  # ~0.1ms
font3 = font_mgr.get("Roboto-Bold.ttf", 32)  # ~0.1ms
```

---

**Related**: [Image Helpers](helpers.md) → Utility functions for image processing
