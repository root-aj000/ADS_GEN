

## What needs to change in `compose` and `_text`

Only **two methods** need modification. Every hardcoded number gets replaced by a template lookup:

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

    # ── pick template ───────────────────────────────────
    from imaging.templates import ALL_TEMPLATES, DEFAULT_TEMPLATE

    tpl = ALL_TEMPLATES.get(template_name or DEFAULT_TEMPLATE,
                            ALL_TEMPLATES[DEFAULT_TEMPLATE])

    src = product_path if use_original else (nobg_path or product_path)
    product = Image.open(src).convert("RGBA")
    bg_removed = not use_original and nobg_path is not None

    bg = self._pick_colour(row, product_path)
    canvas_size = tpl.canvas_size
    canvas = self._gradient(canvas_size, bg,
                            tuple(max(0, c - 40) for c in bg))

    overlay = Image.new("RGBA", canvas_size, (0, 0, 0, tpl.overlay_alpha))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)

    product.thumbnail(tpl.product_max_size, Image.Resampling.LANCZOS)
    x = (canvas_size[0] - product.width) // 2
    y = tpl.product_position_y

    if bg_removed:
        self._shadow(canvas, product, x, y)
    canvas.paste(product, (x, y), product)

    canvas = canvas.convert("RGB")
    self._text(canvas, row, tpl)          # ← pass template
    canvas.save(output, "JPEG", quality=95)

    log.info("Composed [%s] → %s", tpl.name, output.name)
    del product, canvas
    gc.collect()
    return output
```

```python
def _text(self, img: Image.Image, row: pd.Series, tpl) -> None:
    draw = ImageDraw.Draw(img)

    # ── load fonts at template sizes ────────────────────
    bold_fonts = ["arialbd.ttf", "Arial Bold.ttf",
                  "DejaVuSans-Bold.ttf", "Roboto-Bold.ttf"]
    title_fonts = ["arial.ttf", "Arial.ttf",
                   "DejaVuSans.ttf", "Roboto-Regular.ttf"]

    font_title    = self._try_load_font(title_fonts, tpl.title_font_size)
    font_discount = self._try_load_font(bold_fonts, tpl.discount_font_size)
    font_cta      = self._try_load_font(bold_fonts, tpl.cta_font_size)

    # ── extract text parts ──────────────────────────────
    full  = str(row.get("text", ""))
    money = (str(row.get("monetary_mention", ""))
             if pd.notna(row.get("monetary_mention")) else "")
    cta   = (str(row.get("call_to_action", ""))
             if pd.notna(row.get("call_to_action")) else "")

    main = full.replace(money, "").replace(cta, "").strip()

    # ── title lines ─────────────────────────────────────
    y = tpl.title_position_y
    for line in self._wrap(main[:80], font_title, tpl.title_max_width, draw):
        draw.text((tpl.title_anchor_x, y), line,
                  font=font_title, fill="white", anchor="mt",
                  stroke_width=2, stroke_fill="black")
        y += tpl.title_font_size + 10

    # ── discount ────────────────────────────────────────
    dy = tpl.discount_y
    cy = tpl.cta_y

    if money and money.lower() != "nan" and money.strip():
        draw.text((tpl.title_anchor_x, dy), money,
                  font=font_discount, fill="#FFD700", anchor="mt",
                  stroke_width=4, stroke_fill="black")
        bb = draw.textbbox((tpl.title_anchor_x, dy), money,
                           font=font_discount, anchor="mt")
        cy = dy + (bb[3] - bb[1]) + 30

    # ── CTA button ──────────────────────────────────────
    if cta and cta.lower() != "nan" and cta.strip():
        cl, _, cr, ch = tpl.cta_box
        draw.rounded_rectangle([cl, cy, cr, cy + ch],
                               radius=ch // 2, fill="white",
                               outline="black", width=3)
        draw.text(((cl + cr) // 2, cy + ch // 2), cta.upper(),
                  font=font_cta, fill="black", anchor="mm")
```

---

## What changed (nothing else)

| Before (hardcoded) | After (from template) |
|---|---|
| `CANVAS` → `(1080, 1080)` | `tpl.canvas_size` |
| `(650, 650)` thumbnail | `tpl.product_max_size` |
| `y = 220` product | `tpl.product_position_y` |
| `(0,0,0, 80)` overlay | `(0,0,0, tpl.overlay_alpha)` |
| `y = 50` title start | `tpl.title_position_y` |
| `540` anchor x | `tpl.title_anchor_x` |
| `1000` wrap width | `tpl.title_max_width` |
| `900 / 920` discount/cta y | `tpl.discount_y / tpl.cta_y` |
| `[290, ..., 790, 100]` CTA box | `tpl.cta_box` |
| Font sizes `70/100/60` | `tpl.*_font_size` |

---

## Your existing calling code stays the same

```python
# Without template (uses "centered" default) — all 3000 images work as before
compositor.compose(product_path, nobg_path, use_original, row, output)

# With a specific template
compositor.compose(product_path, nobg_path, use_original, row, output,
                   template_name="story")
```

No loop over template names needed. Each image just gets composed with whichever template you pass (or the default). Your 3000-image pipeline doesn't change at all — it only changes if you **want** a different layout for specific rows.