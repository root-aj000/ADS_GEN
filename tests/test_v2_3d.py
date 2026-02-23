"""
Test TRUE 3D effects.
Run:  python -m tests.test_3d [path/to/image.jpg]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from imaging.effects_3d import (
    Product3DEffect,
    EFFECT_CAMERAS,
    check_3d_status,
)


def _safe_font(size: int):
    for n in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _make_test_product(size: int = 400) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [40, 40, size - 40, size - 40],
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

    # Print engine status
    check_3d_status()

    # Load or create image
    if product_path and Path(product_path).exists():
        original = Image.open(product_path)
        if original.mode != "RGBA":
            print(f"  Converting {original.mode} → RGBA (PNG)")
            original = original.convert("RGBA")
        original.thumbnail((400, 400), Image.Resampling.LANCZOS)
        print(f"  Loaded: {product_path} → {original.size}")
    else:
        print("  No image — using dummy product.")
        original = _make_test_product()

    # Effects to test
    effects = list(EFFECT_CAMERAS.keys()) + ["reflection", "none"]
    print(f"\n  Engine:  {Product3DEffect.get_engine_name()}")
    print(f"  Effects: {len(effects)}")
    print()

    # Grid setup
    cell_w, cell_h = 550, 650
    cols = 4
    rows = (len(effects) + cols - 1) // cols
    grid = Image.new("RGB", (cols * cell_w, rows * cell_h), (30, 30, 30))
    draw_grid = ImageDraw.Draw(grid)
    label_font = _safe_font(18)
    small_font = _safe_font(14)

    total_time = 0

    for idx, effect_name in enumerate(effects):
        col = idx % cols
        row = idx // cols
        cx = col * cell_w
        cy = row * cell_h

        preset = EFFECT_CAMERAS.get(effect_name, {})
        rot = preset.get("rotation", (0, 0, 0))
        dep = preset.get("depth", 0)

        print(f"  [{idx + 1:2d}/{len(effects)}] {effect_name:20s}", end="  ")

        t0 = time.perf_counter()
        try:
            result = Product3DEffect.apply(original.copy(), effect_name, strength=10)
            elapsed = time.perf_counter() - t0
            total_time += elapsed
            status = f"✓ {elapsed:.2f}s"
        except Exception as e:
            elapsed = time.perf_counter() - t0
            result = original.copy()
            status = f"✗ {str(e)[:40]}"

        # Fit into cell
        result.thumbnail((cell_w - 40, cell_h - 110), Image.Resampling.LANCZOS)
        px = cx + (cell_w - result.width) // 2
        py = cy + (cell_h - 110 - result.height) // 2 + 60

        # Checkerboard background (shows transparency)
        checker = Image.new("RGB", (result.width, result.height))
        chk_draw = ImageDraw.Draw(checker)
        sq = 10
        for yy in range(0, result.height, sq):
            for xx in range(0, result.width, sq):
                c = (200, 200, 200) if (xx // sq + yy // sq) % 2 == 0 else (150, 150, 150)
                chk_draw.rectangle([xx, yy, xx + sq, yy + sq], fill=c)
        if result.mode == "RGBA":
            checker.paste(result, (0, 0), result)
        else:
            checker.paste(result, (0, 0))
        grid.paste(checker, (px, py))

        # Labels
        draw_grid.text((cx + cell_w // 2, cy + 8), effect_name,
                       font=label_font, fill="cyan", anchor="mt")
        if rot != (0, 0, 0):
            draw_grid.text(
                (cx + cell_w // 2, cy + 30),
                f"rot=({rot[0]:.0f},{rot[1]:.0f},{rot[2]:.0f})  depth={dep}",
                font=small_font, fill="yellow", anchor="mt",
            )

        # Border
        draw_grid.rectangle([cx, cy, cx + cell_w - 1, cy + cell_h - 1],
                            outline=(80, 80, 80), width=1)

        # Save individual
        result.save(out_dir / f"effect_{effect_name}.png", "PNG")
        print(status)

    # Save grid
    grid_path = out_dir / "all_effects_grid.jpg"
    grid.save(grid_path, "JPEG", quality=95)

    print(f"\n  {'=' * 55}")
    print(f"  ✓  Grid       → {grid_path}")
    print(f"  ✓  Individual → {out_dir}/effect_*.png")
    print(f"  ✓  Engine     : {Product3DEffect.get_engine_name()}")
    print(f"  ✓  Total time : {total_time:.2f}s")
    print(f"  ✓  Avg/effect : {total_time / max(len(effects), 1):.2f}s")
    print(f"  {'=' * 55}\n")


if __name__ == "__main__":
    img_path = sys.argv[1] if len(sys.argv) > 1 else None
    preview(img_path)