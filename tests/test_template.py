"""
Previews all ad templates with dummy data.
Run standalone:  python preview_templates.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.templates import ALL_TEMPLATES, AdTemplate


# ── dummy colours / fonts ───────────────────────────────────
BG_TOP    = (44, 62, 80)
BG_BOTTOM = (26, 42, 58)
PRODUCT_COLOR = (200, 200, 200, 220)   # grey box stands in for product
GOLD      = "#FFD700"
WHITE     = "white"
BLACK     = "black"

DUMMY_TITLE    = "Premium Wireless Headphones"
DUMMY_DISCOUNT = "30% OFF"
DUMMY_CTA      = "SHOP NOW"


def _safe_font(size: int) -> ImageFont.FreeTypeFont:
    for name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient(size, c1, c2) -> Image.Image:
    base = Image.new("RGB", size, c1)
    top  = Image.new("RGB", size, c2)
    mask = Image.new("L", size)
    data = []
    for y in range(size[1]):
        data.extend([int(255 * y / size[1])] * size[0])
    mask.putdata(data)
    base.paste(top, (0, 0), mask)
    return base


def render_preview(
    tpl: AdTemplate,
    output_dir: Path,
    show: bool = False,
) -> Path:
    """
    Renders one template with placeholder content 
    and annotated layout guides.
    """
    W, H = tpl.canvas_size

    # ── background ──────────────────────────────────────
    canvas = _gradient((W, H), BG_TOP, BG_BOTTOM).convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, tpl.overlay_alpha))
    canvas = Image.alpha_composite(canvas, overlay)

    draw = ImageDraw.Draw(canvas)

    # ── product placeholder (grey box with X) ───────────
    pw, ph = tpl.product_max_size
    px = (W - pw) // 2
    py = tpl.product_position_y

    # draw the product zone
    draw.rectangle([px, py, px + pw, py + ph],
                   fill=(180, 180, 180, 180),
                   outline="cyan", width=2)
    draw.line([(px, py), (px + pw, py + ph)], fill="cyan", width=1)
    draw.line([(px + pw, py), (px, py + ph)], fill="cyan", width=1)

    # label it
    small = _safe_font(20)
    draw.text((px + pw // 2, py + ph // 2),
              f"PRODUCT\n{pw}×{ph}",
              font=small, fill="cyan", anchor="mm", align="center")

    # ── title ───────────────────────────────────────────
    font_title = _safe_font(tpl.title_font_size)
    lines = _wrap(DUMMY_TITLE, font_title, tpl.title_max_width, draw)
    ty = tpl.title_position_y
    for line in lines:
        draw.text((tpl.title_anchor_x, ty), line,
                  font=font_title, fill=WHITE, anchor="mt",
                  stroke_width=2, stroke_fill=BLACK)
        ty += tpl.title_font_size + 10

    # draw title zone guide
    draw.rectangle(
        [tpl.title_anchor_x - tpl.title_max_width // 2,
         tpl.title_position_y - 5,
         tpl.title_anchor_x + tpl.title_max_width // 2,
         ty + 5],
        outline="lime", width=1,
    )
    draw.text((tpl.title_anchor_x - tpl.title_max_width // 2 + 5,
               tpl.title_position_y - 5),
              "TITLE ZONE", font=small, fill="lime")

    # ── discount ────────────────────────────────────────
    font_disc = _safe_font(tpl.discount_font_size)
    draw.text((tpl.title_anchor_x, tpl.discount_y),
              DUMMY_DISCOUNT, font=font_disc,
              fill=GOLD, anchor="mt",
              stroke_width=4, stroke_fill=BLACK)

    # guide
    bb = draw.textbbox((tpl.title_anchor_x, tpl.discount_y),
                       DUMMY_DISCOUNT, font=font_disc, anchor="mt")
    draw.rectangle(bb, outline="yellow", width=1)
    draw.text((bb[0], bb[1] - 18), "DISCOUNT", font=small, fill="yellow")

    # ── CTA button ──────────────────────────────────────
    cl, _, cr, ch = tpl.cta_box
    cta_top = tpl.cta_y
    cta_bottom = cta_top + ch

    draw.rounded_rectangle([cl, cta_top, cr, cta_bottom],
                           radius=ch // 2, fill=WHITE,
                           outline=BLACK, width=3)

    font_cta = _safe_font(tpl.cta_font_size)
    draw.text(((cl + cr) // 2, cta_top + ch // 2),
              DUMMY_CTA, font=font_cta,
              fill=BLACK, anchor="mm")

    # guide
    draw.rectangle([cl - 2, cta_top - 2, cr + 2, cta_bottom + 2],
                   outline="orange", width=1)
    draw.text((cl, cta_top - 20), "CTA", font=small, fill="orange")

    # ── template info label ─────────────────────────────
    info = f"{tpl.name}  |  {W}×{H}"
    draw.rectangle([0, H - 35, W, H], fill=(0, 0, 0, 160))
    draw.text((W // 2, H - 18), info,
              font=small, fill="white", anchor="mm")

    # ── safe-zone margin (50px from edges) ──────────────
    margin = 50
    draw.rectangle([margin, margin, W - margin, H - margin],
                   outline=(255, 255, 255, 60), width=1)

    # ── save ────────────────────────────────────────────
    canvas_rgb = canvas.convert("RGB")
    out_path = output_dir / f"preview_{tpl.name}.jpg"
    canvas_rgb.save(out_path, "JPEG", quality=95)
    print(f"  ✓  {tpl.name:20s}  →  {out_path}")

    if show:
        canvas_rgb.show()

    return out_path


def _wrap(text, font, max_w, draw):
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        try:
            bb = draw.textbbox((0, 0), test, font=font)
            width = bb[2] - bb[0]
        except Exception:
            width = len(test) * 10
        if width <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


# ── grid view: all templates side by side ───────────────────

def render_comparison_grid(output_dir: Path) -> Path:
    """Stitch all previews into one comparison image."""
    previews = []
    for tpl in ALL_TEMPLATES.values():
        p = render_preview(tpl, output_dir, show=False)
        previews.append(Image.open(p))

    # normalise heights to 600px for comparison
    TARGET_H = 600
    resized = []
    for img in previews:
        ratio = TARGET_H / img.height
        new_w = int(img.width * ratio)
        resized.append(img.resize((new_w, TARGET_H), Image.Resampling.LANCZOS))

    total_w = sum(r.width for r in resized) + 20 * (len(resized) - 1)
    grid = Image.new("RGB", (total_w, TARGET_H + 40), (30, 30, 30))

    x = 0
    for r in resized:
        grid.paste(r, (x, 20))
        x += r.width + 20

    grid_path = output_dir / "template_comparison.jpg"
    grid.save(grid_path, "JPEG", quality=95)
    print(f"\n  ★  Comparison grid  →  {grid_path}")
    return grid_path


# ── entry point ─────────────────────────────────────────────

if __name__ == "__main__":
    out = Path("previews")
    out.mkdir(exist_ok=True)

    print("Rendering individual previews...\n")
    for tpl in ALL_TEMPLATES.values():
        render_preview(tpl, out, show=False)

    print("\nRendering comparison grid...\n")
    render_comparison_grid(out)

    print("\nDone. Open the 'previews/' folder to inspect.")