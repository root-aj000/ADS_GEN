# Ad Templates Documentation

## File: [`config/templates.py`](../../config/templates.py)

## Overview

The `templates.py` file defines **advertisement layouts** - how the final ad images will look. Each template specifies where to place the product image, text, discount, and call-to-action button.

## Real-World Analogy

Think of templates like **picture frame designs**:
- One frame might have the photo in the center
- Another might have the photo on the left side
- Another might be designed for Instagram Stories (tall and narrow)

Each template is like a different frame design that automatically arranges all elements in the right place.

---

## AdTemplate Data Class

```python
@dataclass(frozen=True)
class AdTemplate:
    name: str                          # Template identifier
    canvas_size: Tuple[int, int]       # Width, Height of final image
    product_max_size: Tuple[int, int]  # Max size for product image
    product_position_y: int            # Vertical position of product
    title_position_y: int              # Vertical position of title text
    title_max_width: int               # Max width for title text
    title_anchor_x: int                # Horizontal center point for title
    discount_y: int                    # Vertical position of discount text
    cta_y: int                         # Vertical position of CTA button
    cta_box: Tuple[int, int, int, int] # CTA button dimensions
    overlay_alpha: int                 # Darkness of background overlay
    title_font_size: int               # Font size for title
    discount_font_size: int            # Font size for discount
    cta_font_size: int                 # Font size for CTA button
```

---

## Available Templates

### 1. TEMPLATE_CENTERED (Default)

**Best for**: Instagram posts, general advertisements

```
┌─────────────────────────────────────┐
│           [TITLE TEXT]              │  ← Title at top
│                                     │
│                                     │
│          ┌─────────────┐            │
│          │             │            │
│          │   PRODUCT   │            │  ← Product centered
│          │    IMAGE    │            │
│          │             │            │
│          └─────────────┘            │
│                                     │
│           [DISCOUNT]                │  ← Discount below product
│        ┌───────────────┐            │
│        │  CALL TO ACT  │            │  ← CTA button at bottom
│        └───────────────┘            │
└─────────────────────────────────────┘
         1080 × 1080 pixels
```

**Configuration**:
| Property | Value |
|----------|-------|
| `canvas_size` | (1080, 1080) |
| `product_max_size` | (650, 650) |
| `product_position_y` | 220 |
| `title_position_y` | 50 |
| `title_font_size` | 70 |
| `discount_font_size` | 100 |
| `cta_font_size` | 60 |

---

### 2. TEMPLATE_LEFT_ALIGNED

**Best for**: Product catalogs, e-commerce

```
┌─────────────────────────────────────┐
│  [TITLE TEXT]                       │  ← Title on left
│                                     │
│  ┌──────────┐                       │
│  │          │                       │
│  │ PRODUCT  │                       │  ← Product on left
│  │  IMAGE   │                       │
│  │          │                       │
│  └──────────┘                       │
│                                     │
│  [DISCOUNT]                         │  ← Discount on left
│  ┌──────────────┐                   │
│  │ CALL TO ACT  │                   │  ← CTA on left
│  └──────────────┘                   │
└─────────────────────────────────────┘
         1080 × 1080 pixels
```

**Configuration**:
| Property | Value |
|----------|-------|
| `canvas_size` | (1080, 1080) |
| `product_max_size` | (500, 500) |
| `product_position_y` | 280 |
| `title_anchor_x` | 300 (left-aligned) |
| `title_font_size` | 60 |

---

### 3. TEMPLATE_FACEBOOK

**Best for**: Facebook feed ads

```
┌───────────────────────────────────────────────────┐
│                                    [TITLE TEXT]   │  ← Title on right
│                                                   │
│  ┌──────────┐                                    │
│  │          │                                    │
│  │ PRODUCT  │                                    │  ← Product on left
│  │  IMAGE   │                                    │
│  │          │                                    │
│  └──────────┘                                    │
│                                                   │
│                                    [DISCOUNT]     │  ← Discount on right
│                            ┌───────────────┐      │
│                            │  CALL TO ACT  │      │  ← CTA on right
│                            └───────────────┘      │
└───────────────────────────────────────────────────┘
                   1200 × 628 pixels
```

**Configuration**:
| Property | Value |
|----------|-------|
| `canvas_size` | (1200, 628) |
| `product_max_size` | (400, 400) |
| `title_anchor_x` | 900 (right side) |
| `title_font_size` | 50 |
| `discount_font_size` | 70 |

---

### 4. TEMPLATE_STORY

**Best for**: Instagram Stories, TikTok

```
┌─────────────────────────────────────┐
│           [TITLE TEXT]              │
│                                     │
│                                     │
│          ┌─────────────┐            │
│          │             │            │
│          │             │            │
│          │   PRODUCT   │            │  ← Larger product area
│          │    IMAGE    │            │
│          │             │            │
│          │             │            │
│          └─────────────┘            │
│                                     │
│                                     │
│           [DISCOUNT]                │
│        ┌───────────────┐            │
│        │  CALL TO ACT  │            │
│        └───────────────┘            │
│                                     │
└─────────────────────────────────────┘
         1080 × 1920 pixels
```

**Configuration**:
| Property | Value |
|----------|-------|
| `canvas_size` | (1080, 1920) |
| `product_max_size` | (800, 800) |
| `product_position_y` | 500 |
| `title_font_size` | 80 |
| `discount_font_size` | 120 |

---

## Template Registry

```python
ALL_TEMPLATES = {
    "centered": TEMPLATE_CENTERED,
    "left_aligned": TEMPLATE_LEFT_ALIGNED,
    "facebook": TEMPLATE_FACEBOOK,
    "story": TEMPLATE_STORY,
}

DEFAULT_TEMPLATE = "centered"
```

**Usage**:

```python
from config.templates import ALL_TEMPLATES, DEFAULT_TEMPLATE

# Get a specific template
template = ALL_TEMPLATES["facebook"]

# Use default template
default = ALL_TEMPLATES[DEFAULT_TEMPLATE]
```

---

## How Templates Connect to the Compositor

The [`AdCompositor`](../core/compositor.md) uses templates to position elements:

```
┌─────────────────────────────────────────────────────────────┐
│                      AdCompositor                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  compose(product_path, nobg_path, row, output, template_name)│
│                                                              │
│  1. Load template from ALL_TEMPLATES                         │
│     template = ALL_TEMPLATES.get(template_name, DEFAULT)     │
│                                                              │
│  2. Create canvas at template.canvas_size                    │
│                                                              │
│  3. Position product at template.product_position_y          │
│                                                              │
│  4. Draw title at template.title_position_y                  │
│                                                              │
│  5. Draw discount at template.discount_y                     │
│                                                              │
│  6. Draw CTA button using template.cta_box                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Creating a Custom Template

To add a new template:

```python
# In config/templates.py

TEMPLATE_CUSTOM = AdTemplate(
    name="custom",
    canvas_size=(800, 800),           # Custom size
    product_max_size=(400, 400),      # Smaller product
    product_position_y=150,           # Higher position
    title_position_y=30,
    title_max_width=700,
    title_anchor_x=400,
    discount_y=650,
    cta_y=700,
    cta_box=(200, 0, 600, 80),
    overlay_alpha=100,
    title_font_size=50,
    discount_font_size=70,
    cta_font_size=40,
)

# Add to registry
ALL_TEMPLATES["custom"] = TEMPLATE_CUSTOM
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    config/templates.py                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  AdTemplate (dataclass)                                      │
│  └── Defines layout properties                               │
│                                                              │
│  Pre-defined Templates:                                      │
│  ├── TEMPLATE_CENTERED (1080×1080)                          │
│  ├── TEMPLATE_LEFT_ALIGNED (1080×1080)                      │
│  ├── TEMPLATE_FACEBOOK (1200×628)                           │
│  └── TEMPLATE_STORY (1080×1920)                             │
│                                                              │
│  Registry:                                                   │
│  └── ALL_TEMPLATES = {"centered": ..., "facebook": ...}     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    core/compositor.py
                    ┌──────────────────────────┐
                    │ template = ALL_TEMPLATES  │
                    │     .get(template_name)   │
                    └──────────────────────────┘
```

---

## Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Define advertisement layouts |
| **Location** | `config/templates.py` |
| **Templates** | centered, left_aligned, facebook, story |
| **Default** | "centered" (1080×1080) |
| **Usage** | `from config.templates import ALL_TEMPLATES` |

**Think of it as**: A set of picture frames - each frame has a different design, but all hold the same content (product image, text, CTA).
