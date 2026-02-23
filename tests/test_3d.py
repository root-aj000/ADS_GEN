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
                # label — draw line by line (anchor not supported for multiline)
        label_line1 = name
        draw_grid.text((cx + cell_w // 2, cy + 12), label_line1,
                       font=label_font, fill="cyan", anchor="mt")

        if kwargs:
            params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            label_line2 = f"({params})"
            draw_grid.text((cx + cell_w // 2, cy + 38), label_line2,
                           font=label_font, fill="yellow", anchor="mt")

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
