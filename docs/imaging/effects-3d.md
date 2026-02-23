# 3D Effects Engine - Documentation

## Overview

The [`imaging/effects_3d.py`](../../imaging/effects_3d.py) module provides true 3D mesh generation from 2D product images using AI-powered models. It supports multiple backends with automatic fallback.

## Quick Start

```bash
# Check engine status
python -m imaging.effects_3d --status

# Download all enabled models
python -m imaging.effects_3d --download

# Run test preview
python tests/test_3d.py
```

## Available Engines

| Engine | Status | Size | Speed | Quality |
|--------|--------|------|-------|---------|
| **TripoSR** | ✅ Recommended | ~1.7 GB | ~5-10s GPU | Highest |
| **Shap-E** | ⚠️ Optional | ~2 GB | ~10-120s | Good |
| **Stable Fast 3D** | ⚠️ Optional | ~2 GB | ~1s GPU | Good |
| **NumPy Fallback** | ✅ Always available | 0 MB | ~0.5s | Basic |

## Configuration

Toggle engines at the top of [`effects_3d.py`](../../imaging/effects_3d.py:47-50):

```python
USE_TRIPOSR: bool = True           # Primary engine (recommended)
USE_SHAP_E: bool = False           # OpenAI's diffusion model
USE_STABLE_FAST_3D: bool = False   # Fastest engine
USE_NUMPY_FALLBACK: bool = True    # Always available fallback
```

## Usage

### Basic Usage

```python
from PIL import Image
from imaging.effects_3d import Product3DEffect

# Load product image
img = Image.open("product.png").convert("RGBA")

# Apply 3D effect
result = Product3DEffect.apply(img, effect_name="hero_angle", strength=10)
result.save("output_3d.png")
```

### Available Effects

| Effect Name | Description | Best For |
|-------------|-------------|----------|
| `perspective_tilt` | Subtle forward tilt | Product cards |
| `rotate_y` | Rotate right (~30°) | Showing side depth |
| `rotate_y_left` | Rotate left (~30°) | Alternative angle |
| `hero_angle` | Dramatic angle (20°, 15°) | Hero images |
| `float_3d` | Subtle lift effect | Floating products |
| `isometric` | Isometric view (35°, 45°) | Technical presentations |
| `product_showcase` | Balanced showcase angle | E-commerce |
| `dramatic_tilt` | Extreme tilt (30°, 20°) | Dynamic compositions |
| `box_view` | Full 3D box perspective | Package design |
| `card_stand` | Minimal depth, upright | Card mockups |
| `front` | Direct front view | Flat presentation |
| `top_down` | Overhead view | Layout planning |
| `reflection` | Adds floor reflection | Polish effect |
| `none` | No effect passthrough | Original image |

### Effect Parameters

```python
# Custom strength (1-10 scale)
result = Product3DEffect.apply(img, "hero_angle", strength=8)

# Reflection effect
result = Product3DEffect.add_reflection(img, height_ratio=0.35)
```

## Installation

### Required Dependencies

```bash
pip install huggingface_hub torch trimesh pyvista rembg scipy numpy Pillow
```

### Engine-Specific Dependencies

#### TripoSR (Recommended)
```bash
pip install torch einops omegaconf transformers trimesh PyMCubes tsr
```

#### Shap-E
```bash
pip install git+https://github.com/openai/shap-e.git
```

#### Stable Fast 3D
```bash
pip install git+https://github.com/Stability-AI/stable-fast-3d.git
```

## Model Storage

Models are downloaded and cached locally:

```
data/
├── models/
│   ├── TripoSR/              # TripoSR weights + code
│   │   ├── model.ckpt        # Model weights
│   │   ├── config.yaml       # Configuration
│   │   └── code/tsr/         # Source code
│   ├── shap-e/               # Shap-E weights
│   └── stable-fast-3d/       # SF3D weights
└── cache/
    └── meshes/               # Generated mesh cache (.obj files)
```

## API Reference

### Product3DEffect Class

#### `apply(img, effect_name, strength=10, **kwargs)`

Apply a 3D effect to an image.

**Parameters:**
- `img` (PIL.Image): Input RGBA image
- `effect_name` (str): Effect preset name
- `strength` (int): Effect intensity (1-10)
- `**kwargs`: Additional engine-specific options

**Returns:** PIL.Image with applied 3D effect

#### `add_reflection(img, height_ratio=0.3, start_opacity=0.35, gap=6)`

Add a reflection below the product.

**Parameters:**
- `img` (PIL.Image): Input image
- `height_ratio` (float): Reflection height relative to image
- `start_opacity` (float): Opacity at top of reflection
- `gap` (int): Pixel gap between image and reflection

**Returns:** PIL.Image with reflection added

#### `perspective_shadow(product, canvas, x, y, blur=25, opacity=100, offset_y=30, spread=1.15)`

Add perspective shadow to a product on a canvas.

#### `list_effects()`

Return list of available effect names.

#### `get_engine_name()`

Return the currently active engine name.

### TripoSRGenerator Class

```python
from imaging.effects_3d import TripoSRGenerator

# Check if ready
if TripoSRGenerator.is_available():
    mesh = TripoSRGenerator.generate_mesh(img)
    rendered = TripoSRGenerator.render(img, rotation=(15, 20, 0))

# Manual download
TripoSRGenerator.download(force=False)

# Check dependencies
deps = TripoSRGenerator.check_deps()
TripoSRGenerator.install_deps()
```

### MeshRenderer Class

Renders 3D meshes to 2D images:

```python
from imaging.effects_3d import MeshRenderer

# Render mesh with custom camera
image = MeshRenderer.render(
    mesh,
    rotation=(15, 20, 0),  # (rx, ry, rz) in degrees
    size=(1024, 1024),     # Output resolution
    zoom=1.3               # Camera zoom
)
```

## Camera Presets

Camera configurations in [`EFFECT_CAMERAS`](../../imaging/effects_3d.py:1167-1180):

```python
EFFECT_CAMERAS = {
    "perspective_tilt": {"rotation": (25, 0, 0), "depth": 30, "zoom": 1.3},
    "rotate_y": {"rotation": (5, 30, 0), "depth": 30, "zoom": 1.2},
    "hero_angle": {"rotation": (20, 15, 3), "depth": 40, "zoom": 1.2},
    # ... etc
}
```

## Troubleshooting

### Error: `extract_mesh() got an unexpected keyword argument 'texture'`

**Issue:** TripoSR's `extract_mesh()` method signature may vary between versions.

**Fix:** The code uses `texture=True` as a keyword argument. If your version doesn't support this:

```python
# Line 709 in effects_3d.py
# Change from:
meshes = model.extract_mesh(scene_codes, texture=True, resolution=resolution)

# To (positional argument):
meshes = model.extract_mesh(scene_codes, True, resolution=resolution)
```

### Error: Missing dependencies

Run the dependency checker:

```python
from imaging.effects_3d import TripoSRGenerator
TripoSRGenerator.install_deps()
```

### Models not downloading

Check HuggingFace authentication for rate limits:

```bash
# Set HF token for faster downloads
export HF_TOKEN=your_token_here
```

### No GPU available

The engine automatically falls back to CPU. Performance will be slower but functional. Ensure `torch` is installed with CPU support.

## Performance Benchmarks

| Engine | GPU Time | CPU Time | Quality |
|--------|----------|----------|---------|
| TripoSR | ~5-8s | ~30-60s | ⭐⭐⭐⭐⭐ |
| Shap-E | ~10-15s | ~60-120s | ⭐⭐⭐⭐ |
| Stable Fast 3D | ~1-2s | ~10-20s | ⭐⭐⭐⭐ |
| NumPy Fallback | ~0.5s | ~0.5s | ⭐⭐ |

## Testing

```bash
# Visual test of all effects
python tests/test_3d.py

# With custom image
python tests/test_3d.py path/to/product.png
```

Output: `previews_3d/all_effects_grid.jpg`

## Related Documentation

- [Imaging Overview](overview.md) - Main imaging module
- [Background Removal](background.md) - AI background removal
- [Image Cache](cache.md) - Image caching system
- [Quality Scorer](scorer.md) - Image quality assessment

## References

- TripoSR: [stabilityai/TripoSR](https://huggingface.co/stabilityai/TripoSR)
- TripoSR Code: [VAST-AI-Research/TripoSR](https://github.com/VAST-AI-Research/TripoSR)
- Shap-E: [openai/shap-e](https://huggingface.co/openai/shap-e)
- Stable Fast 3D: [stabilityai/stable-fast-3d](https://huggingface.co/stabilityai/stable-fast-3d)
