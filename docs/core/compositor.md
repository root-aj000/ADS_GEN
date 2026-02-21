# Ad Compositor Documentation

## File: [`core/compositor.py`](../../core/compositor.py)

## Overview

The `compositor.py` file creates the **final advertisement images**. It takes a product image, optional background-removed version, and text from the CSV, then combines them into a polished 1080×1080 advertisement.

## Real-World Analogy

Think of the compositor as a **graphic designer** who:
1. Takes a product photo
2. Places it on a colored background
3. Adds a title at the top
4. Adds a discount/deal
5. Adds a "Call to Action" button
6. Exports the final design

---

## AdCompositor Class

### Initialization

```python
class AdCompositor:
    def __init__(self, fonts_dir: Optional[Path] = None) -> None:
        self.fonts_dir = fonts_dir
        self._load_fonts()
```

**Parameters**:

| Parameter | Type | Source | Description |
|-----------|------|--------|-------------|
| `fonts_dir` | `Optional[Path]` | `cfg.paths.fonts_dir` | Directory containing custom fonts |

**What happens during initialization**:
1. Loads font files for title, discount, and CTA text
2. Falls back through multiple font options if some aren't found
3. Uses system fonts as final fallback

---

### Font Loading

```python
def _load_fonts(self) -> None:
    """Load fonts with fallback chain."""
    title_fonts = ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "Roboto-Regular.ttf"]
    bold_fonts = ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "Roboto-Bold.ttf"]
    
    self.font_title = self._try_load_font(title_fonts, 70)     # Title: 70px
    self.font_discount = self._try_load_font(bold_fonts, 100)  # Discount: 100px
    self.font_cta = self._try_load_font(bold_fonts, 60)        # CTA: 60px
```

**Font Fallback Chain**:
```
1. Try custom fonts directory (cfg.paths.fonts_dir)
2. Try system fonts
3. Try common system paths (Windows/Linux/Mac)
4. Fall back to PIL default font
```

---

### compose() Method

**Purpose**: Creates the final advertisement image.

```python
def compose(
    self,
    product_path: Path,        # Path to product image
    nobg_path: Optional[Path], # Path to background-removed image
    use_original: bool,        # Use original or bg-removed?
    row: pd.Series,           # CSV row with text data
    output: Path,             # Where to save the result
    template_name: Optional[str] = None,  # Optional template
) -> Path:
```

**Step-by-Step Process**:

```
┌─────────────────────────────────────────────────────────────┐
│                    compose()                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. LOAD PRODUCT IMAGE                                       │
│     ├── use_original=True? → Load product_path              │
│     └── use_original=False? → Load nobg_path                │
│                                                              │
│  2. CREATE BACKGROUND                                        │
│     ├── Get dominant color from CSV or image                │
│     └── Create gradient from color to darker shade          │
│                                                              │
│  3. ADD OVERLAY                                              │
│     └── Add semi-transparent black layer (makes text pop)   │
│                                                              │
│  4. PLACE PRODUCT                                            │
│     ├── Resize to fit (max 650x650)                         │
│     ├── Center horizontally                                 │
│     ├── Position at y=220                                    │
│     └── Add drop shadow (if background removed)             │
│                                                              │
│  5. ADD TEXT                                                 │
│     ├── Title at top (from "text" column)                   │
│     ├── Discount (from "monetary_mention" column)           │
│     └── CTA button (from "call_to_action" column)           │
│                                                              │
│  6. SAVE OUTPUT                                              │
│     └── Save as JPEG with 95% quality                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Example Output**:

```
┌─────────────────────────────────────────┐
│           Delicious Pizza               │  ← Title (white, 70px)
│                                         │
│         ┌─────────────────┐             │
│         │                 │             │
│         │   [PRODUCT]     │             │  ← Product image centered
│         │                 │             │
│         │                 │             │
│         └─────────────────┘             │
│                                         │
│            $5.99 ONLY                   │  ← Discount (gold, 100px)
│        ┌─────────────────┐              │
│        │   ORDER NOW!    │              │  ← CTA button (white box)
│        └─────────────────┘              │
└─────────────────────────────────────────┘
          1080 × 1080 pixels
```

**Parameters**:

| Parameter | Type | Source | Description |
|-----------|------|--------|-------------|
| `product_path` | `Path` | Downloader | Original product image |
| `nobg_path` | `Optional[Path]` | BackgroundRemover | Background-removed image |
| `use_original` | `bool` | BackgroundRemover | Which image to use |
| `row` | `pd.Series` | CSV | Text data for the ad |
| `output` | `Path` | Pipeline | Output file path |
| `template_name` | `Optional[str]` | Config | Template to use |

**Returns**: Path to the saved image.

---

### placeholder() Method

**Purpose**: Creates a placeholder image when no suitable image is found.

```python
def placeholder(self, query: str, dest: Path) -> Path:
```

**What it does**:
1. Creates an 800×800 blue image
2. Writes the query text in the center
3. Saves as JPEG

**Example**:
```
┌─────────────────────────────┐
│                             │
│                             │
│        PIZZA SLICE          │  ← Query text centered
│                             │
│                             │
└─────────────────────────────┘
      800 × 800 pixels (blue background)
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | Search query (e.g., "pizza slice") |
| `dest` | `Path` | Where to save the placeholder |

---

## Internal Methods

### _pick_colour()

**Purpose**: Determines the background color for the ad.

```python
@staticmethod
def _pick_colour(row: pd.Series, product_path: Path) -> Tuple[int, int, int]:
```

**Logic**:
```
1. Check if CSV has "dominant_colour" column
   ├── Yes? Look up color in COLOR_MAP
   └── No? Extract dominant color from product image
2. Return RGB tuple
```

**Example**:
- CSV has `dominant_colour: "Blue"` → Returns `(0, 102, 204)`
- CSV has `dominant_colour: None` → Analyzes image, returns most common color

---

### _gradient()

**Purpose**: Creates a gradient background.

```python
@staticmethod
def _gradient(
    size: Tuple[int, int],       # Canvas size
    c1: Tuple[int, int, int],    # Top color
    c2: Tuple[int, int, int],    # Bottom color
) -> Image.Image:
```

**Visual Result**:
```
c1 (lighter blue)
        ↓
        ↓  Gradient transition
        ↓
c2 (darker blue)
```

---

### _shadow()

**Purpose**: Adds a drop shadow to the product image.

```python
@staticmethod
def _shadow(canvas: Image.Image, product: Image.Image, x: int, y: int) -> None:
```

**Visual Effect**:
```
Without shadow:          With shadow:
┌─────────┐              ┌─────────┐
│  ████   │              │  ▓▓▓▓   │ ← Shadow
│  ████   │              │  ████   │
│  ████   │              │  ████   │
└─────────┘              └─────────┘
```

This makes the product "float" above the background when the background has been removed.

---

### _text()

**Purpose**: Adds all text elements to the canvas.

```python
def _text(self, img: Image.Image, row: pd.Series) -> None:
```

**Text Elements**:

| Element | CSV Column | Style | Position |
|---------|------------|-------|----------|
| Title | `text` | White, 70px, with black outline | Top (y=50) |
| Discount | `monetary_mention` | Gold (#FFD700), 100px | Bottom area (y=900) |
| CTA Button | `call_to_action` | Black text on white rounded box | Bottom (y=920) |

**CSV Columns Used**:
```python
full = str(row.get("text", ""))               # Main ad text
money = str(row.get("monetary_mention", ""))  # Price/discount
cta = str(row.get("call_to_action", ""))      # Button text
```

---

### _wrap()

**Purpose**: Wraps text to fit within a maximum width.

```python
@staticmethod
def _wrap(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_w: int,
    draw: ImageDraw.ImageDraw,
) -> List[str]:
```

**Example**:
```
Input: "This is a very long product description that needs to be wrapped"
Max width: 500 pixels

Output:
[
    "This is a very long product",
    "description that needs to be",
    "wrapped"
]
```

---

## Canvas Constants

```python
CANVAS = (1080, 1080)  # Default output size (Instagram square)
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      AdCompositor                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Inputs:                                                     │
│  ├── product_path: data/temp/workers/w1/dl_42.jpg           │
│  ├── nobg_path: data/temp/workers/w1/nobg_42.png            │
│  ├── use_original: False                                     │
│  ├── row: {"text": "Delicious Pizza", "monetary_mention":   │
│  │         "$5.99", "call_to_action": "Order Now"}          │
│  └── output: data/output/images/ad_0043.jpg                 │
│                                                              │
│  Process:                                                    │
│  1. Load nobg_path (background-removed image)               │
│  2. Create blue gradient background                         │
│  3. Add semi-transparent overlay                            │
│  4. Place product with shadow                               │
│  5. Add "Delicious Pizza" title                             │
│  6. Add "$5.99" discount in gold                            │
│  7. Add "ORDER NOW" button                                  │
│                                                              │
│  Output:                                                     │
│  └── data/output/images/ad_0043.jpg (1080×1080)             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Connected Files

| File | Relationship |
|------|--------------|
| [`config/settings.py`](../config/settings.md) | Provides `COLOR_MAP` |
| [`config/templates.py`](../config/templates.md) | Provides layout templates |
| [`imaging/helpers.py`](../imaging/helpers.md) | Provides `dominant_colour()` |
| [`core/pipeline.py`](pipeline.md) | Calls `compose()` and `placeholder()` |

---

## Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Create final advertisement images |
| **Input** | Product image + text data |
| **Output** | 1080×1080 JPEG advertisement |
| **Key Method** | `compose()` - creates the final ad |
| **Fallback** | `placeholder()` - when no image found |

**Think of it as**: A graphic designer who takes your product photo and marketing text, and creates a professional-looking advertisement automatically.
