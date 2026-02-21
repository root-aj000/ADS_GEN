"""DuckDuckGo Images search."""

from __future__ import annotations

import time
from typing import List

from duckduckgo_search import DDGS

from search.base import BaseSearchEngine, ImageResult
from utils.log_config import get_logger

log = get_logger(__name__)


class DuckDuckGoEngine(BaseSearchEngine):
    name = "duckduckgo"

    def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
        log.debug("DuckDuckGo ← %s", query)
        adv = self.cfg.adv_search_term
        results: List[ImageResult] = []

        queries = [
            f'"{query}" ',
            # f"{query} product PNG transparent",
        ]

        for sq in queries:
            try:
                with DDGS() as ddgs:
                    raw = list(
                        ddgs.images(
                            keywords=sq,
                            region="wt-wt",
                            safesearch="off",
                            size="Large",
                            type_image="photo",
                            max_results=max_results // len(queries),
                        )
                    )
                for r in raw:
                    results.append(
                        ImageResult(
                            url=r["image"],
                            source=self.name,
                            title=r.get("title", ""),
                        )
                    )
                time.sleep(self.cfg.per_request_delay)
            except Exception:
                continue

        log.info("DuckDuckGo → %d results", len(results))
        return results[:max_results]