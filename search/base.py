"""Abstract base class every search engine inherits from."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import List, Optional

import requests

from config.settings import DEFAULT_HEADERS, SearchConfig
from utils.concurrency import CircuitBreaker, RateLimiter
from utils.log_config import get_logger

log = get_logger(__name__)


@dataclass
class ImageResult:
    """One image hit from any engine."""

    url:    str
    source: str
    title:  str = ""
    width:  int = 0
    height: int = 0


class BaseSearchEngine:
    """
    Subclass must set ``name`` and implement ``search()``.
    """

    name: str = "base"

    def __init__(self, cfg: SearchConfig) -> None:
        self.cfg = cfg
        self.limiter = RateLimiter(cfg.rate_limit_per_sec)
        self.breaker = CircuitBreaker(
            threshold=cfg.breaker_threshold,
            cooldown=cfg.breaker_cooldown,
        )
        self._local = threading.local()

    # ── thread-local session (connection pooling) ───────────
    @property
    def session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update(DEFAULT_HEADERS)
            self._local.session = s
        return s

    # ── override in subclass ────────────────────────────────
    def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
        raise NotImplementedError

    # ── wrapper with circuit-breaker + rate-limit ───────────
    def safe_search(
        self,
        query: str,
        max_results: int = 50,
    ) -> List[ImageResult]:
        if self.breaker.is_open:
            log.debug("Skipping %s — circuit breaker open", self.name)
            return []
        self.limiter.wait()
        try:
            results = self.search(query, max_results)
            if results:
                self.breaker.record_success()
            return results
        except Exception as exc:
            self.breaker.record_failure()
            log.warning("%s search failed: %s", self.name, exc)
            return []