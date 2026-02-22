# # 


# """Renders the final 1080×1080 ad image."""

# from __future__ import annotations

# import gc
# from pathlib import Path
# from typing import List, Optional, Tuple

# import pandas as pd
# from PIL import Image, ImageDraw, ImageFilter, ImageFont

# from config.settings import COLOR_MAP
# from imaging.helpers import dominant_colour
# from utils.log_config import get_logger

# log = get_logger(__name__)

# CANVAS = (1080, 1080)


# class AdCompositor:

#     def __init__(self, fonts_dir: Optional[Path] = None) -> None:
#         """
#         Initialize compositor with optional fonts directory.
        
#         Args:
#             fonts_dir: Path to custom fonts directory. If None, uses system fonts.
#         """
#         self.fonts_dir = fonts_dir
#         self._load_fonts()

#     def _load_fonts(self) -> None:
#         """Load fonts with fallback chain."""
#         # Font names to try in order
#         title_fonts = ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "Roboto-Regular.ttf"]
#         bold_fonts = ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "Roboto-Bold.ttf"]

#         self.font_title = self._try_load_font(title_fonts, 70)
#         self.font_discount = self._try_load_font(bold_fonts, 100)
#         self.font_cta = self._try_load_font(bold_fonts, 60)

#     def _try_load_font(self, font_names: List[str], size: int) -> ImageFont.FreeTypeFont:
#         """Try loading fonts from multiple sources."""
#         # 1. Try custom fonts directory
#         if self.fonts_dir and self.fonts_dir.exists():
#             for name in font_names:
#                 font_path = self.fonts_dir / name
#                 if font_path.exists():
#                     try:
#                         return ImageFont.truetype(str(font_path), size)
#                     except OSError:
#                         continue

#         # 2. Try system fonts
#         for name in font_names:
#             try:
#                 return ImageFont.truetype(name, size)
#             except OSError:
#                 continue

#         # 3. Try common system paths (Windows, Linux, Mac)
#         system_paths = [
#             Path("C:/Windows/Fonts"),
#             Path("/usr/share/fonts/truetype"),
#             Path("/usr/share/fonts/TTF"),
#             Path("/Library/Fonts"),
#             Path.home() / ".fonts",
#         ]
        
#         for sys_path in system_paths:
#             if sys_path.exists():
#                 for name in font_names:
#                     font_path = sys_path / name
#                     if font_path.exists():
#                         try:
#                             return ImageFont.truetype(str(font_path), size)
#                         except OSError:
#                             continue

#         # 4. Fallback to PIL default
#         log.warning("Could not load any fonts, using PIL default")
#         return ImageFont.load_default()

#     # ── public ──────────────────────────────────────────────
#     def compose(
#         self,
#         product_path: Path,
#         nobg_path: Optional[Path],
#         use_original: bool,
#         row: pd.Series,
#         output: Path,
#         template_name: Optional[str] = None,
#     ) -> Path:
#         """
#         Compose the final ad image.
        
#         Args:
#             product_path: Path to the product image
#             nobg_path: Path to background-removed image (optional)
#             use_original: Whether to use original or bg-removed image
#             row: DataFrame row with ad text data
#             output: Output path for the composed ad
#             template_name: Optional template name for different layouts
        
#         Returns:
#             Path to the saved ad image
#         """
#         src = product_path if use_original else (nobg_path or product_path)
#         product = Image.open(src).convert("RGBA")
#         bg_removed = not use_original and nobg_path is not None

#         bg = self._pick_colour(row, product_path)
#         canvas = self._gradient(CANVAS, bg, tuple(max(0, c - 40) for c in bg))

#         overlay = Image.new("RGBA", CANVAS, (0, 0, 0, 80))
#         canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)

#         product.thumbnail((650, 650), Image.Resampling.LANCZOS)
#         x = (CANVAS[0] - product.width) // 2
#         y = 220

#         if bg_removed:
#             self._shadow(canvas, product, x, y)
#         canvas.paste(product, (x, y), product)

#         canvas = canvas.convert("RGB")
#         self._text(canvas, row)
#         canvas.save(output, "JPEG", quality=95)

#         log.info("Composed → %s", output.name)
#         del product, canvas
#         gc.collect()
#         return output

#     # ── placeholder ─────────────────────────────────────────
#     def placeholder(self, query: str, dest: Path) -> Path:
#         """Create a placeholder image when download fails."""
#         img = Image.new("RGB", (800, 800), (70, 130, 180))
#         draw = ImageDraw.Draw(img)
        
#         # Use smaller font for placeholder
#         font = self._try_load_font(["arial.ttf", "Arial.ttf"], 50)
        
#         # Draw text centered
#         text = query.upper()[:20]
#         try:
#             bbox = draw.textbbox((0, 0), text, font=font)
#             text_width = bbox[2] - bbox[0]
#             text_height = bbox[3] - bbox[1]
#             x = (800 - text_width) // 2
#             y = (800 - text_height) // 2
#             draw.text((x, y), text, fill="white", font=font)
#         except Exception:
#             draw.text((400, 400), text, fill="white", font=font, anchor="mm")
        
#         img.save(dest, "JPEG")
#         log.info("Created placeholder → %s", dest.name)
#         return dest

#     # ── internals ───────────────────────────────────────────
#     @staticmethod
#     def _pick_colour(
#         row: pd.Series,
#         product_path: Path,
#     ) -> Tuple[int, int, int]:
#         name = str(row.get("dominant_colour", ""))
#         if pd.notna(row.get("dominant_colour")) and name in COLOR_MAP:
#             return COLOR_MAP[name]
#         return dominant_colour(product_path)

#     @staticmethod
#     def _gradient(
#         size: Tuple[int, int],
#         c1: Tuple[int, int, int],
#         c2: Tuple[int, int, int],
#     ) -> Image.Image:
#         base = Image.new("RGB", size, c1)
#         top = Image.new("RGB", size, c2)
#         mask = Image.new("L", size)
#         data = []
#         for yy in range(size[1]):
#             data.extend([int(255 * yy / size[1])] * size[0])
#         mask.putdata(data)
#         base.paste(top, (0, 0), mask)
#         return base

#     @staticmethod
#     def _shadow(canvas: Image.Image, product: Image.Image, x: int, y: int) -> None:
#         try:
#             alpha = product.split()[3]
#             shd = Image.new("RGBA", (product.width + 40, product.height + 40),
#                             (0, 0, 0, 0))
#             shd.paste((0, 0, 0, 120), (20, 20), alpha)
#             shd = shd.filter(ImageFilter.GaussianBlur(20))
#             canvas.paste(shd, (x - 20, y - 10), shd)
#         except Exception:
#             pass

#     def _text(self, img: Image.Image, row: pd.Series) -> None:
#         draw = ImageDraw.Draw(img)

#         full  = str(row.get("text", ""))
#         money = str(row.get("monetary_mention", "")) if pd.notna(row.get("monetary_mention")) else ""
#         cta   = str(row.get("call_to_action", ""))   if pd.notna(row.get("call_to_action"))   else ""

#         main = full.replace(money, "").replace(cta, "").strip()

#         y = 50
#         for line in self._wrap(main[:80], self.font_title, 1000, draw):
#             draw.text((540, y), line, font=self.font_title, fill="white",
#                       anchor="mt", stroke_width=2, stroke_fill="black")
#             y += 80

#         dy, cy = 900, 920
#         if money and money.lower() != "nan" and money.strip():
#             draw.text((540, dy), money, font=self.font_discount,
#                       fill="#FFD700", anchor="mt",
#                       stroke_width=4, stroke_fill="black")
#             bb = draw.textbbox((540, dy), money,
#                                font=self.font_discount, anchor="mt")
#             cy = dy + (bb[3] - bb[1]) + 30

#         if cta and cta.lower() != "nan" and cta.strip():
#             h = 100
#             draw.rounded_rectangle([290, cy, 790, cy + h],
#                                    radius=40, fill="white",
#                                    outline="black", width=3)
#             draw.text((540, cy + h // 2), cta.upper(),
#                       font=self.font_cta, fill="black", anchor="mm")

#     @staticmethod
#     def _wrap(
#         text: str,
#         font: ImageFont.FreeTypeFont,
#         max_w: int,
#         draw: ImageDraw.ImageDraw,
#     ) -> List[str]:
#         words = text.split()
#         lines: List[str] = []
#         cur: List[str] = []
#         for w in words:
#             test = " ".join(cur + [w])
#             try:
#                 bb = draw.textbbox((0, 0), test, font=font)
#                 width = bb[2] - bb[0]
#             except Exception:
#                 width = len(test) * 10
#             if width <= max_w:
#                 cur.append(w)
#             else:
#                 if cur:
#                     lines.append(" ".join(cur))
#                 cur = [w]
#         if cur:
#             lines.append(" ".join(cur))
#         return lines

"""Renders the final 1080×1080 ad image."""

from __future__ import annotations

import gc
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config.settings import COLOR_MAP
from imaging.helpers import dominant_colour
from utils.log_config import get_logger

log = get_logger(__name__)

CANVAS = (1080, 1080)


class AdCompositor:

    def __init__(self, fonts_dir: Optional[Path] = None) -> None:
        """
        Initialize compositor with optional fonts directory.
        
        Args:
            fonts_dir: Path to custom fonts directory. If None, uses system fonts.
        """
        self.fonts_dir = fonts_dir
        self._load_fonts()

    def _load_fonts(self) -> None:
        """Load fonts with fallback chain."""
        # Font names to try in order
        title_fonts = ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "Roboto-Regular.ttf"]
        bold_fonts = ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "Roboto-Bold.ttf"]

        self.font_title = self._try_load_font(title_fonts, 70)
        self.font_discount = self._try_load_font(bold_fonts, 100)
        self.font_cta = self._try_load_font(bold_fonts, 60)

    def _try_load_font(self, font_names: List[str], size: int) -> ImageFont.FreeTypeFont:
        """Try loading fonts from multiple sources."""
        # 1. Try custom fonts directory
        if self.fonts_dir and self.fonts_dir.exists():
            for name in font_names:
                font_path = self.fonts_dir / name
                if font_path.exists():
                    try:
                        return ImageFont.truetype(str(font_path), size)
                    except OSError:
                        continue

        # 2. Try system fonts
        for name in font_names:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue

        # 3. Try common system paths (Windows, Linux, Mac)
        system_paths = [
            Path("C:/Windows/Fonts"),
            Path("/usr/share/fonts/truetype"),
            Path("/usr/share/fonts/TTF"),
            Path("/Library/Fonts"),
            Path.home() / ".fonts",
        ]
        
        for sys_path in system_paths:
            if sys_path.exists():
                for name in font_names:
                    font_path = sys_path / name
                    if font_path.exists():
                        try:
                            return ImageFont.truetype(str(font_path), size)
                        except OSError:
                            continue

        # 4. Fallback to PIL default
        log.warning("Could not load any fonts, using PIL default")
        return ImageFont.load_default()

    # ── public ──────────────────────────────────────────────
    # def compose(
    #     self,
    #     product_path: Path,
    #     nobg_path: Optional[Path],
    #     use_original: bool,
    #     row: pd.Series,
    #     output: Path,
    #     template_name: Optional[str] = None,
    # ) -> Path:
    #     """
    #     Compose the final ad image.
        
    #     Args:
    #         product_path: Path to the product image
    #         nobg_path: Path to background-removed image (optional)
    #         use_original: Whether to use original or bg-removed image
    #         row: DataFrame row with ad text data
    #         output: Output path for the composed ad
    #         template_name: Optional template name for different layouts
        
    #     Returns:
    #         Path to the saved ad image
    #     """
    #     src = product_path if use_original else (nobg_path or product_path)
    #     product = Image.open(src).convert("RGBA")
    #     bg_removed = not use_original and nobg_path is not None

    #     bg = self._pick_colour(row, product_path)
    #     canvas = self._gradient(CANVAS, bg, tuple(max(0, c - 40) for c in bg))

    #     overlay = Image.new("RGBA", CANVAS, (0, 0, 0, 80))
    #     canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)

    #     product.thumbnail((650, 650), Image.Resampling.LANCZOS)
    #     x = (CANVAS[0] - product.width) // 2
    #     y = 220

    #     if bg_removed:
    #         self._shadow(canvas, product, x, y)
    #     canvas.paste(product, (x, y), product)

    #     canvas = canvas.convert("RGB")
    #     self._text(canvas, row)
    #     canvas.save(output, "JPEG", quality=95)

    #     log.info("Composed → %s", output.name)
    #     del product, canvas
    #     gc.collect()
    #     return output


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
        from config.templates import ALL_TEMPLATES, DEFAULT_TEMPLATE

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
         # ── placeholder ─────────────────────────────────────────
    def placeholder(self, query: str, dest: Path) -> Path:
        """Create a placeholder image when download fails."""
        img = Image.new("RGB", (800, 800), (70, 130, 180))
        draw = ImageDraw.Draw(img)
        
        # Use smaller font for placeholder
        font = self._try_load_font(["arial.ttf", "Arial.ttf"], 50)
        
        # Draw text centered
        text = query.upper()[:20]
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (800 - text_width) // 2
            y = (800 - text_height) // 2
            draw.text((x, y), text, fill="white", font=font)
        except Exception:
            draw.text((400, 400), text, fill="white", font=font, anchor="mm")
        
        img.save(dest, "JPEG")
        log.info("Created placeholder → %s", dest.name)
        return dest

    # ── internals ───────────────────────────────────────────
    @staticmethod
    def _pick_colour(
        row: pd.Series,
        product_path: Path,
    ) -> Tuple[int, int, int]:
        name = str(row.get("dominant_colour", ""))
        if pd.notna(row.get("dominant_colour")) and name in COLOR_MAP:
            return COLOR_MAP[name]
        return dominant_colour(product_path)

    @staticmethod
    def _gradient(
        size: Tuple[int, int],
        c1: Tuple[int, int, int],
        c2: Tuple[int, int, int],
    ) -> Image.Image:
        base = Image.new("RGB", size, c1)
        top = Image.new("RGB", size, c2)
        mask = Image.new("L", size)
        data = []
        for yy in range(size[1]):
            data.extend([int(255 * yy / size[1])] * size[0])
        mask.putdata(data)
        base.paste(top, (0, 0), mask)
        return base

    @staticmethod
    def _shadow(canvas: Image.Image, product: Image.Image, x: int, y: int) -> None:
        try:
            alpha = product.split()[3]
            shd = Image.new("RGBA", (product.width + 40, product.height + 40),
                            (0, 0, 0, 0))
            shd.paste((0, 0, 0, 120), (20, 20), alpha)
            shd = shd.filter(ImageFilter.GaussianBlur(20))
            canvas.paste(shd, (x - 20, y - 10), shd)
        except Exception:
            pass

    # def _text(self, img: Image.Image, row: pd.Series) -> None:
    #     draw = ImageDraw.Draw(img)

    #     full  = str(row.get("text", ""))
    #     money = str(row.get("monetary_mention", "")) if pd.notna(row.get("monetary_mention")) else ""
    #     cta   = str(row.get("call_to_action", ""))   if pd.notna(row.get("call_to_action"))   else ""

    #     main = full.replace(money, "").replace(cta, "").strip()

    #     y = 50
    #     for line in self._wrap(main[:80], self.font_title, 1000, draw):
    #         draw.text((540, y), line, font=self.font_title, fill="white",
    #                   anchor="mt", stroke_width=2, stroke_fill="black")
    #         y += 80

    #     dy, cy = 900, 920
    #     if money and money.lower() != "nan" and money.strip():
    #         draw.text((540, dy), money, font=self.font_discount,
    #                   fill="#FFD700", anchor="mt",
    #                   stroke_width=4, stroke_fill="black")
    #         bb = draw.textbbox((540, dy), money,
    #                            font=self.font_discount, anchor="mt")
    #         cy = dy + (bb[3] - bb[1]) + 30

    #     if cta and cta.lower() != "nan" and cta.strip():
    #         h = 100
    #         draw.rounded_rectangle([290, cy, 790, cy + h],
    #                                radius=40, fill="white",
    #                                outline="black", width=3)
    #         draw.text((540, cy + h // 2), cta.upper(),
    #                   font=self.font_cta, fill="black", anchor="mm")


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
    
    @staticmethod
    def _wrap(
        text: str,
        font: ImageFont.FreeTypeFont,
        max_w: int,
        draw: ImageDraw.ImageDraw,
    ) -> List[str]:
        words = text.split()
        lines: List[str] = []
        cur: List[str] = []
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