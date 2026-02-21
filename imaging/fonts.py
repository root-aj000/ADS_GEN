"""
Font manager — auto-download missing fonts.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Optional

from PIL import ImageFont

from utils.log_config import get_logger

log = get_logger(__name__)

# Google Fonts CDN URLs (free, no API key needed)
FONT_URLS = {
    "Roboto-Regular.ttf": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf",
    "Roboto-Bold.ttf": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
    "OpenSans-Regular.ttf": "https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Regular.ttf",
    "OpenSans-Bold.ttf": "https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Bold.ttf",
}


class FontManager:
    """Load fonts from local dir; download if missing."""

    def __init__(self, fonts_dir: Path) -> None:
        self.fonts_dir = fonts_dir
        fonts_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, ImageFont.FreeTypeFont] = {}

    def _download(self, name: str) -> Optional[Path]:
        url = FONT_URLS.get(name)
        if not url:
            return None
        dest = self.fonts_dir / name
        if dest.exists():
            return dest
        try:
            log.info("Downloading font: %s", name)
            urllib.request.urlretrieve(url, str(dest))
            return dest
        except Exception as exc:
            log.warning("Font download failed: %s — %s", name, exc)
            return None

    def get(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        """
        Try loading in order:
          1. System font
          2. Local fonts_dir
          3. Download from CDN
          4. PIL default fallback
        """
        key = f"{name}:{size}"
        if key in self._cache:
            return self._cache[key]

        font = self._try_load(name, size)
        self._cache[key] = font
        return font

    def _try_load(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        # 1. system
        for sys_name in (name, name.replace("-", ""), name.split("-")[0].lower()):
            try:
                f = ImageFont.truetype(sys_name, size)
                log.debug("Loaded system font: %s", sys_name)
                return f
            except OSError:
                continue

        # 2. local dir
        local = self.fonts_dir / name
        if local.exists():
            try:
                return ImageFont.truetype(str(local), size)
            except OSError:
                pass

        # 3. download
        downloaded = self._download(name)
        if downloaded:
            try:
                return ImageFont.truetype(str(downloaded), size)
            except OSError:
                pass

        # 4. fallback to any available Roboto
        for fallback_name in FONT_URLS:
            fb = self._download(fallback_name)
            if fb:
                try:
                    return ImageFont.truetype(str(fb), size)
                except OSError:
                    continue

        log.warning("All font loading failed — using PIL default")
        return ImageFont.load_default()