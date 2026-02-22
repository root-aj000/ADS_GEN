

## Yes — here's a full `Product3DEffect` class and integration

### 1. Save as `imaging/effects_3d.py`

```python
"""
3-D visual effects for flat product images.
Uses perspective transforms, reflections, and enhanced shadows
to make flat product shots look three-dimensional.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter


class Product3DEffect:
    """Transform flat product images into 3D-looking compositions."""

    # ── perspective maths ───────────────────────────────

    @staticmethod
    def _find_coeffs(
        source: List[Tuple[int, int]],
        target: List[Tuple[int, int]],
    ) -> List[float]:
        """
        8 coefficients for PIL's PERSPECTIVE transform.

        PIL maps *output* pixels → *input* pixels:
            x_src = (a·x_dst + b·y_dst + c) / (g·x_dst + h·y_dst + 1)
            y_src = (d·x_dst + e·y_dst + f) / (g·x_dst + h·y_dst + 1)

        Given 4 source corners and 4 target corners we solve
        the resulting 8×8 linear system.
        """
        A, B = [], []
        for (xs, ys), (xt, yt) in zip(source, target):
            A.append([xt, yt, 1, 0, 0, 0, -xs * xt, -xs * yt])
            A.append([0, 0, 0, xt, yt, 1, -ys * xt, -ys * yt])
            B.extend([xs, ys])
        return np.linalg.solve(
            np.array(A, dtype=np.float64),
            np.array(B, dtype=np.float64),
        ).tolist()

    @classmethod
    def _warp(
        cls,
        img: Image.Image,
        source: List[Tuple[int, int]],
        target: List[Tuple[int, int]],
        out_size: Optional[Tuple[int, int]] = None,
    ) -> Image.Image:
        coeffs = cls._find_coeffs(source, target)
        return img.transform(
            out_size or img.size,
            Image.Transform.PERSPECTIVE,
            coeffs,
            Image.Resampling.BICUBIC,
        )

    # ── individual effects ──────────────────────────────

    @classmethod
    def perspective_tilt(
        cls, img: Image.Image, strength: int = 12,
    ) -> Image.Image:
        """
        Viewed from slightly above — top edge shrinks inward.

        ┌──────────┐         ╱──────╲
        │          │   →    │        │
        │          │        │        │
        └──────────┘        └────────┘
        """
        w, h = img.size
        off = int(w * strength / 100)
        src = [(0, 0), (w, 0), (w, h), (0, h)]
        dst = [(off, 0), (w - off, 0), (w, h), (0, h)]
        return cls._warp(img, src, dst)

    @classmethod
    def rotate_y(
        cls, img: Image.Image, strength: int = 10,
    ) -> Image.Image:
        """
        Rotate around vertical axis — right side recedes.

        ┌──────────┐        ┌──────────╲
        │          │   →    │           |
        │          │        │           |
        └──────────┘        └──────────╱
        """
        w, h = img.size
        off = int(h * strength / 100)
        src = [(0, 0), (w, 0), (w, h), (0, h)]
        dst = [(0, 0), (w, off), (w, h - off), (0, h)]
        return cls._warp(img, src, dst)

    @classmethod
    def rotate_y_left(
        cls, img: Image.Image, strength: int = 10,
    ) -> Image.Image:
        """Mirror of rotate_y — left side recedes."""
        w, h = img.size
        off = int(h * strength / 100)
        src = [(0, 0), (w, 0), (w, h), (0, h)]
        dst = [(0, off), (w, 0), (w, h), (0, h - off)]
        return cls._warp(img, src, dst)

    @classmethod
    def hero_angle(
        cls, img: Image.Image, tilt: int = 8, rotation: int = 6,
    ) -> Image.Image:
        """Cinematic: combines tilt + subtle Y rotation."""
        w, h = img.size
        t = int(w * tilt / 100)
        r = int(h * rotation / 100)
        src = [(0, 0), (w, 0), (w, h), (0, h)]
        dst = [(t, 0), (w - t // 2, r), (w, h - r // 2), (0, h)]
        return cls._warp(img, src, dst)

    @classmethod
    def float_3d(
        cls, img: Image.Image, lift: int = 3,
    ) -> Image.Image:
        """Very subtle perspective — product feels 'lifted'."""
        w, h = img.size
        o = int(w * lift / 100)
        src = [(0, 0), (w, 0), (w, h), (0, h)]
        dst = [(o, o // 2), (w - o, o // 2), (w, h), (0, h)]
        return cls._warp(img, src, dst)

    @classmethod
    def isometric(
        cls, img: Image.Image, squeeze: int = 15,
    ) -> Image.Image:
        """
        Fake isometric / package-box angle.
        Top shrinks + right side recedes.
        """
        w, h = img.size
        tx = int(w * squeeze / 100)
        ty = int(h * squeeze / 200)
        src = [(0, 0), (w, 0), (w, h), (0, h)]
        dst = [(tx, 0), (w - tx // 2, ty), (w, h), (0, h - ty)]
        return cls._warp(img, src, dst)

    # ── reflection ──────────────────────────────────────

    @classmethod
    def add_reflection(
        cls,
        img: Image.Image,
        height_ratio: float = 0.3,
        start_opacity: float = 0.35,
        gap: int = 6,
    ) -> Image.Image:
        """Fading mirror-reflection below the product."""
        w, h = img.size
        ref_h = int(h * height_ratio)

        # flip & crop
        ref = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        ref = ref.crop((0, 0, w, ref_h))

        # fast gradient mask (numpy — no per-pixel loop)
        gradient = np.linspace(
            start_opacity * 255, 0, ref_h, dtype=np.uint8,
        )
        fade = np.tile(gradient[:, None], (1, w))
        fade_mask = Image.fromarray(fade, "L")

        # combine with existing alpha if RGBA
        if ref.mode == "RGBA":
            *rgb, a = ref.split()
            a_arr = np.array(a, dtype=np.float64)
            combined = (a_arr * fade.astype(np.float64) / 255).astype(np.uint8)
            ref.putalpha(Image.fromarray(combined, "L"))
        else:
            ref.putalpha(fade_mask)

        total_h = h + gap + ref_h
        result = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))
        result.paste(img, (0, 0), img if img.mode == "RGBA" else None)
        result.paste(ref, (0, h + gap), ref)
        return result

    # ── perspective shadow ──────────────────────────────

    @classmethod
    def perspective_shadow(
        cls,
        product: Image.Image,
        canvas: Image.Image,
        x: int,
        y: int,
        blur: int = 25,
        opacity: int = 100,
        offset_y: int = 30,
        spread: float = 1.15,
    ) -> None:
        """
        Paste a perspective-warped, blurred shadow onto *canvas*
        (modified in-place).  Much more realistic than a plain drop shadow.
        """
        try:
            alpha = product.split()[3]
        except IndexError:
            return

        w, h = product.size
        sw, sh = int(w * spread), int(h * 0.3)  # wider + squished

        # resize alpha into shadow dimensions
        a_resized = alpha.resize((sw, sh), Image.Resampling.LANCZOS)
        a_arr = (np.array(a_resized, dtype=np.float64) * opacity / 255)
        a_img = Image.fromarray(a_arr.astype(np.uint8), "L")

        shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        shadow.putalpha(a_img)

        # fan the shadow outward at the bottom
        off = int(sw * 0.08)
        src = [(0, 0), (sw, 0), (sw, sh), (0, sh)]
        dst = [(-off, 0), (sw + off, 0), (sw - off, sh), (off, sh)]
        coeffs = cls._find_coeffs(src, dst)
        shadow = shadow.transform(
            (sw, sh), Image.Transform.PERSPECTIVE,
            coeffs, Image.Resampling.BICUBIC,
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur))

        sx = x - (sw - w) // 2
        sy = y + h - sh // 2 + offset_y
        canvas.paste(shadow, (sx, sy), shadow)

    # ── dispatcher ──────────────────────────────────────

    @classmethod
    def apply(
        cls,
        img: Image.Image,
        effect_name: str = "perspective_tilt",
        **kwargs,
    ) -> Image.Image:
        effects = {
            "perspective_tilt": cls.perspective_tilt,
            "rotate_y":        cls.rotate_y,
            "rotate_y_left":   cls.rotate_y_left,
            "hero_angle":      cls.hero_angle,
            "float_3d":        cls.float_3d,
            "isometric":       cls.isometric,
            "reflection":      cls.add_reflection,
            "none":            lambda i, **kw: i,
        }
        fn = effects.get(effect_name, effects["none"])
        return fn(img, **kwargs)
```

---

### 2. Add to your `AdTemplate` dataclass

```python
@dataclass(frozen=True)
class AdTemplate:
    name:               str
    canvas_size:        Tuple[int, int]
    product_max_size:   Tuple[int, int]
    product_position_y: int
    title_position_y:   int
    title_max_width:    int
    title_anchor_x:     int
    discount_y:         int
    cta_y:              int
    cta_box:            Tuple[int, int, int, int]
    overlay_alpha:      int
    title_font_size:    int
    discount_font_size: int
    cta_font_size:      int
    # ── NEW ─────────────────────────────────
    effect_3d:          str  = "none"        # effect name
    effect_strength:    int  = 12            # passed as strength/tilt
    use_reflection:     bool = False         # add reflection below product
    use_3d_shadow:      bool = False         # perspective shadow instead of basic
```

Update your existing templates:

```python
TEMPLATE_CENTERED = AdTemplate(
    name="centered",
    # ... all existing fields stay the same ...
    effect_3d="perspective_tilt",
    effect_strength=10,
    use_reflection=False,
    use_3d_shadow=True,
)

TEMPLATE_HERO = AdTemplate(
    name="hero",
    canvas_size=(1080, 1080),
    product_max_size=(600, 600),
    product_position_y=250,
    title_position_y=50,
    title_max_width=1000,
    title_anchor_x=540,
    discount_y=900,
    cta_y=920,
    cta_box=(290, 0, 790, 100),
    overlay_alpha=80,
    title_font_size=70,
    discount_font_size=100,
    cta_font_size=60,
    effect_3d="hero_angle",
    effect_strength=10,
    use_reflection=True,
    use_3d_shadow=True,
)
```

---

### 3. Updated `compose()` — only changed lines marked

```python
def compose(
    self,
    product_path: Path,
    nobg_path: Optional[Path],
    use_original: bool,
    row: pd.Series,
    output: Path,
    template_name: Optional[str] = None,
) -> Path:
    from imaging.templates import ALL_TEMPLATES, DEFAULT_TEMPLATE
    from imaging.effects_3d import Product3DEffect          # ← NEW

    tpl = ALL_TEMPLATES.get(template_name or DEFAULT_TEMPLATE,
                            ALL_TEMPLATES[DEFAULT_TEMPLATE])

    src = product_path if use_original else (nobg_path or product_path)
    product = Image.open(src).convert("RGBA")
    bg_removed = not use_original and nobg_path is not None

    bg = self._pick_colour(row, product_path)
    canvas = self._gradient(tpl.canvas_size, bg,
                            tuple(max(0, c - 40) for c in bg))

    overlay = Image.new("RGBA", tpl.canvas_size,
                        (0, 0, 0, tpl.overlay_alpha))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)

    product.thumbnail(tpl.product_max_size, Image.Resampling.LANCZOS)

    # ── 3-D EFFECT (NEW) ───────────────────────────────
    if tpl.effect_3d != "none":
        product = Product3DEffect.apply(
            product,
            effect_name=tpl.effect_3d,
            strength=tpl.effect_strength,
        )

    if tpl.use_reflection:
        product = Product3DEffect.add_reflection(product)
    # ── END 3-D ────────────────────────────────────────

    x = (tpl.canvas_size[0] - product.width) // 2
    y = tpl.product_position_y

    # ── SHADOW (UPGRADED) ──────────────────────────────
    if bg_removed:
        if tpl.use_3d_shadow:
            Product3DEffect.perspective_shadow(
                product, canvas, x, y,
            )
        else:
            self._shadow(canvas, product, x, y)
    # ── END SHADOW ─────────────────────────────────────

    canvas.paste(product, (x, y), product)

    canvas = canvas.convert("RGB")
    self._text(canvas, row, tpl)
    canvas.save(output, "JPEG", quality=95)

    log.info("Composed [%s / %s] → %s",
             tpl.name, tpl.effect_3d, output.name)
    del product, canvas
    gc.collect()
    return output
```

---

### 4. Preview script — `preview_3d_effects.py`

```python
"""
Visualise every 3D effect on a single test image.
Run:  python preview_3d_effects.py [path/to/product.png]
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from imaging.effects_3d import Product3DEffect


EFFECTS = [
    ("none",             {}),
    ("perspective_tilt", {"strength": 12}),
    ("rotate_y",         {"strength": 10}),
    ("rotate_y_left",    {"strength": 10}),
    ("hero_angle",       {"tilt": 8, "rotation": 6}),
    ("float_3d",         {"lift": 4}),
    ("isometric",        {"squeeze": 15}),
    ("reflection",       {"height_ratio": 0.3}),
]


def _safe_font(size: int):
    for n in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _make_test_product(size: int = 400) -> Image.Image:
    """Create a dummy product image (coloured box with label)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # rounded-ish product shape
    margin = 40
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=30, fill=(70, 130, 180, 240),
        outline="white", width=3,
    )
    font = _safe_font(28)
    draw.text((size // 2, size // 2), "PRODUCT",
              font=font, fill="white", anchor="mm")
    return img


def preview(product_path: str | None = None) -> None:
    out_dir = Path("previews_3d")
    out_dir.mkdir(exist_ok=True)

    # load or create product image
    if product_path and Path(product_path).exists():
        original = Image.open(product_path).convert("RGBA")
        original.thumbnail((400, 400), Image.Resampling.LANCZOS)
    else:
        print("No image provided — using dummy product.")
        original = _make_test_product()

    cell_w, cell_h = 500, 600
    cols = 4
    rows = (len(EFFECTS) + cols - 1) // cols
    grid = Image.new("RGB",
                     (cols * cell_w, rows * cell_h),
                     (30, 30, 30))
    draw_grid = ImageDraw.Draw(grid)
    label_font = _safe_font(22)

    for idx, (name, kwargs) in enumerate(EFFECTS):
        col = idx % cols
        row = idx // cols
        cx = col * cell_w
        cy = row * cell_h

        # apply effect
        result = Product3DEffect.apply(original.copy(), name, **kwargs)

        # fit into cell
        result.thumbnail((cell_w - 40, cell_h - 80),
                         Image.Resampling.LANCZOS)
        px = cx + (cell_w - result.width) // 2
        py = cy + (cell_h - 80 - result.height) // 2 + 40

        # paste onto grid
        if result.mode == "RGBA":
            # dark cell background so alpha is visible
            cell_bg = Image.new("RGBA",
                                (result.width, result.height),
                                (50, 50, 50, 255))
            cell_bg = Image.alpha_composite(cell_bg, result)
            grid.paste(cell_bg.convert("RGB"), (px, py))
        else:
            grid.paste(result, (px, py))

        # label
        label = f"{name}"
        if kwargs:
            params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            label += f"\n({params})"
        draw_grid.text((cx + cell_w // 2, cy + 12), label,
                       font=label_font, fill="cyan", anchor="mt",
                       align="center")

        # cell border
        draw_grid.rectangle([cx, cy, cx + cell_w - 1, cy + cell_h - 1],
                            outline=(80, 80, 80), width=1)

        # also save individual
        individual = out_dir / f"effect_{name}.png"
        result.save(individual, "PNG")

    grid_path = out_dir / "all_effects_grid.jpg"
    grid.save(grid_path, "JPEG", quality=95)
    print(f"\n  ✓  Grid saved → {grid_path}")
    print(f"  ✓  Individual effects → {out_dir}/effect_*.png")
    print(f"\n  Open {grid_path} to compare all effects.\n")


if __name__ == "__main__":
    img_path = sys.argv[1] if len(sys.argv) > 1 else None
    preview(img_path)
```

---

### What each effect does visually

```
ORIGINAL              perspective_tilt       rotate_y             hero_angle
┌──────────┐             ╱────╲             ┌────────╲           ╱──────╲
│          │            │      │            │         |          │       ╲
│  FLAT    │   →        │      │     →      │         |    →     │        |
│          │            │      │            │         |          │        |
└──────────┘            └──────┘            └────────╱          └────────╱

float_3d               isometric            rotate_y_left       reflection
  ╱────────╲           ╱──────╲             ╱────────┐          ┌────────┐
 │          │         │       ╲            |         │          │        │
 │          │         │        |           |         │          │        │
 └──────────┘         └────────╱           ╱─────────┘          └────────┘
                                                                ░░░░░░░░░░
                                                                 ░░░░░░░░
                                                                  ░░░░░░
```

---

### Run the preview

```bash
# with your own product image
python preview_3d_effects.py data/product_images/shoe.png

# or with the built-in dummy
python preview_3d_effects.py
```

It produces `previews_3d/all_effects_grid.jpg` — one glance tells you which effect works best for your products before touching the 3000-image pipeline.