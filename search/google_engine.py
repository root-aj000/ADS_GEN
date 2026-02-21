"""Google Images scraper."""

from __future__ import annotations

import re
import urllib.parse
from typing import List, Set

from search.base import BaseSearchEngine, ImageResult
from utils.log_config import get_logger

log = get_logger(__name__)

_BLOCKED_DOMAINS = frozenset([
    "gstatic.com", "google.com", "googleapis.com",
    "ggpht.com", "googleusercontent.com", "encrypted-tbn",
])

_BLOCKED_PATTERNS = frozenset([
    "/thumb/", "/thumbs/", "thumbnail", "_thumb", "-thumb",
    "_small", "-small", "/small/", "_tiny", "/tiny/",
    "/icon", "favicon", "logo", "avatar", "emoji", "badge",
    "=s64", "=s72", "=s96", "=s128",
    "=w100", "=w150", "=h100", "=h150",
])


class GoogleEngine(BaseSearchEngine):
    name = "google"

    def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
        log.debug("Google ← %s", query)
        adv = self.cfg.adv_search_term
        encoded = urllib.parse.quote(f"'{query}'")
        url = (
            f"https://www.google.com/search?q={encoded}&tbm=isch&hl=en&tbs=isz:l"
            # f"&tbm=isch&hl=en&tbs=isz:l"
        )

        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        html = resp.text

        if len(html) < 50_000:
            log.warning("Google: response too small (%d B)", len(html))
            return []

        seen: Set[str] = set()
        results: List[ImageResult] = []

        # method 1: ["url", w, h]
        for m_url, w, h in re.findall(
            r'\["(https?://[^"]+\.(?:jpg|jpeg|png|webp|gif)[^"]*)"'
            r'[^\]]*?,\s*(\d+)\s*,\s*(\d+)\s*\]',
            html,
            re.I,
        ):
            clean = self._clean(m_url)
            wi, hi = int(w), int(h)
            if wi >= 300 and hi >= 300 and self._valid(clean) and clean not in seen:
                seen.add(clean)
                results.append(ImageResult(clean, self.name, width=wi, height=hi))

        # method 2: fallback regex
        if len(results) < 10:
            for m_url in re.findall(
                r'https://[^"\s<>\\]+\.(?:jpg|jpeg|png|webp|gif)[^"\s<>\\]*',
                html,
                re.I,
            ):
                clean = self._clean(m_url)
                if self._valid(clean) and clean not in seen:
                    seen.add(clean)
                    results.append(ImageResult(clean, self.name))

        results.sort(key=lambda r: r.width * r.height, reverse=True)
        log.info("Google → %d results", len(results))
        return results[:max_results]

    # ── helpers ─────────────────────────────────────────────
    @staticmethod
    def _clean(url: str) -> str:
        for old, new in (
            ("\\u003d", "="), ("\\u003D", "="),
            ("\\u0026", "&"), ("\\u002F", "/"),
            ("\\/", "/"), ("\\", ""),
        ):
            url = url.replace(old, new)
        return re.sub(r'[,\]\}\)]+$', "", url).strip()

    @staticmethod
    def _valid(url: str) -> bool:
        if not url or len(url) < 10 or not url.startswith("http"):
            return False
        low = url.lower()
        return (
            not any(d in low for d in _BLOCKED_DOMAINS)
            and not any(p in low for p in _BLOCKED_PATTERNS)
        )