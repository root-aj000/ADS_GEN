"""Small image utilities shared by downloader & compositor."""

from __future__ import annotations

from typing import Tuple

import numpy as np
from colorthief import ColorThief
from PIL import Image

from utils.log_config import get_logger

log = get_logger(__name__)


def has_visual_content(
    image: Image.Image,
    min_std: float = 10.0,
    min_colours: int = 100,
) -> bool:
    """Return False if the image is blank / near-solid."""
    arr = np.array(image.convert("RGB"))
    if np.std(arr) < min_std:
        return False
    uniq = len(np.unique(arr.reshape(-1, 3), axis=0))
    return uniq >= min_colours


def dominant_colour(path) -> Tuple[int, int, int]:
    try:
        return ColorThief(str(path)).get_color(quality=1)
    except Exception:
        return (100, 100, 100)