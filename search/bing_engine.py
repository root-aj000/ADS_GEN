"""Bing Images scraper."""

from __future__ import annotations

import re
import urllib.parse
from typing import List, Set

from bs4 import BeautifulSoup

from search.base import BaseSearchEngine, ImageResult
from utils.log_config import get_logger

log = get_logger(__name__)


class BingEngine(BaseSearchEngine):
    name = "bing"

    def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
        log.debug("Bing ← %s", query)
        adv = self.cfg.adv_search_term
        encoded = urllib.parse.quote(f"{query} ")
        url = (
            f'https://www.bing.com/images/search?q="{encoded}"'
            f'+"{adv}"&qft=+filterui:imagesize-large&form=IRFLTR'
        )

        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen: Set[str] = set()
        results: List[ImageResult] = []

        for anchor in soup.select("a.iusc"):
            m_json = anchor.get("m", "")
            match = re.search(r'"murl":"(.*?)"', m_json)
            if not match:
                continue
            img_url = match.group(1).replace("\\/", "/")
            if img_url.startswith("http") and img_url not in seen:
                seen.add(img_url)
                results.append(
                    ImageResult(
                        url=img_url,
                        source=self.name,
                        title=anchor.get("title", ""),
                    )
                )

        log.info("Bing → %d results", len(results))
        return results[:max_results]