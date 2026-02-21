"""
Orchestrates searches across all engines with priority,
circuit-breakers, and cross-engine deduplication.
"""

from __future__ import annotations

import time
from typing import Dict, List, Set, Type

from config.settings import SearchConfig
from search.base import BaseSearchEngine, ImageResult
from search.bing_engine import BingEngine
from search.duckduckgo_engine import DuckDuckGoEngine
from search.google_engine import GoogleEngine
from utils.concurrency import ThreadSafeSet
from utils.log_config import get_logger

log = get_logger(__name__)

ENGINE_REGISTRY: Dict[str, Type[BaseSearchEngine]] = {
    "google":     GoogleEngine,
    "duckduckgo": DuckDuckGoEngine,
    "bing":       BingEngine,
}


class SearchManager:
    """
    Instantiate once → reuse across threads.
    ``downloaded_hashes`` is shared for cross-row dedup.
    """

    def __init__(self, cfg: SearchConfig) -> None:
        self.cfg = cfg
        self.engines: Dict[str, BaseSearchEngine] = {
            name: ENGINE_REGISTRY[name](cfg) for name in cfg.priority
        }
        self.downloaded_hashes = ThreadSafeSet()

    def search(
        self,
        query: str,
        max_results: int = 100,
    ) -> List[ImageResult]:
        combined: List[ImageResult] = []
        seen_urls: Set[str] = set()

        for name in self.cfg.priority:
            engine = self.engines.get(name)
            if engine is None:
                continue

            batch = engine.safe_search(query, max_results)
            for r in batch:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    combined.append(r)

            if len(combined) >= self.cfg.min_results_fallback:
                log.debug(
                    "Got %d after %s — skipping remaining engines",
                    len(combined),
                    name,
                )
                break

            time.sleep(self.cfg.inter_engine_delay)

        log.info("Total unique results: %d", len(combined))
        return combined[:max_results]