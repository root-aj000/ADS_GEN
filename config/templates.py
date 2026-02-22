"""
Multiple ad layout templates.
Each template defines text positions, product placement, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


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
    cta_box:            Tuple[int, int, int, int]   # left, top, right, bottom_offset
    overlay_alpha:      int
    title_font_size:    int
    discount_font_size: int
    cta_font_size:      int


# ── ready-made templates ────────────────────────────────────

TEMPLATE_CENTERED = AdTemplate(
    name="centered",
    canvas_size=(1080, 1080),
    product_max_size=(650, 650),
    product_position_y=220,
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
)

TEMPLATE_LEFT_ALIGNED = AdTemplate(
    name="left_aligned",
    canvas_size=(1080, 1080),
    product_max_size=(500, 500),
    product_position_y=280,
    title_position_y=50,
    title_max_width=500,
    title_anchor_x=300,
    discount_y=850,
    cta_y=920,
    cta_box=(50, 0, 450, 80),
    overlay_alpha=100,
    title_font_size=60,
    discount_font_size=80,
    cta_font_size=50,
)

TEMPLATE_FACEBOOK = AdTemplate(
    name="facebook",
    canvas_size=(1200, 628),
    product_max_size=(400, 400),
    product_position_y=114,
    title_position_y=30,
    title_max_width=700,
    title_anchor_x=900,
    discount_y=380,
    cta_y=600,
    cta_box=(700, 0, 1100, 70),
    overlay_alpha=90,
    title_font_size=50,
    discount_font_size=70,
    cta_font_size=40,
)

TEMPLATE_STORY = AdTemplate(
    name="story",
    canvas_size=(1080, 1920),
    product_max_size=(800, 800),
    product_position_y=500,
    title_position_y=100,
    title_max_width=900,
    title_anchor_x=540,
    discount_y=1400,
    cta_y=1550,
    cta_box=(240, 0, 840, 100),
    overlay_alpha=70,
    title_font_size=80,
    discount_font_size=120,
    cta_font_size=60,
)


TEMPLATE_MINIMAL = AdTemplate(
    name="minimal",
    canvas_size=(1080, 1080),
    product_max_size=(700, 700),
    product_position_y=300,       # product pushed lower
    title_position_y=30,          # title at very top
    title_max_width=900,
    title_anchor_x=540,           # centered horizontally
    discount_y=950,
    cta_y=1000,
    cta_box=(340, 0, 740, 70),    # narrower CTA button
    overlay_alpha=50,             # lighter overlay
    title_font_size=55,
    discount_font_size=90,
    cta_font_size=45,
)

TEMPLATE_PRODUCT_LEFT = AdTemplate(
    name="product_left",
    canvas_size=(1080, 1080),
    product_max_size=(450, 450),
    product_position_y=300,
    title_position_y=80,
    title_max_width=450,
    title_anchor_x=780,           # text on right half
    discount_y=600,
    cta_y=720,
    cta_box=(580, 0, 1000, 80),   # CTA on right side
    overlay_alpha=90,
    title_font_size=55,
    discount_font_size=75,
    cta_font_size=45,
)

# Register them
# ALL_TEMPLATES["minimal"] = TEMPLATE_MINIMAL
# ALL_TEMPLATES["product_left"] = TEMPLATE_PRODUCT_LEFT
# ALL_TEMPLATES["centered"] = TEMPLATE_CENTERED
# ALL_TEMPLATES["left_aligned"] = TEMPLATE_LEFT_ALIGNED
# ALL_TEMPLATES["facebook"] = TEMPLATE_FACEBOOK
# ALL_TEMPLATES["story"] = TEMPLATE_STORY


# ── registry ────────────────────────────────────────────────

ALL_TEMPLATES = {
    "centered":     TEMPLATE_CENTERED,
    "left_aligned": TEMPLATE_LEFT_ALIGNED,
    "facebook":     TEMPLATE_FACEBOOK,
    "story":        TEMPLATE_STORY,
    "minimal": TEMPLATE_MINIMAL,
    "product_left" : TEMPLATE_LEFT_ALIGNED,
    }
