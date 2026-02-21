"""
Proxy rotation manager.
Supports round-robin, random, and least-used strategies.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import requests

from config.settings import ProxyConfig
from utils.log_config import get_logger

log = get_logger(__name__)


@dataclass
class ProxyEntry:
    url:        str
    failures:   int   = 0
    uses:       int   = 0
    last_used:  float = 0.0
    is_alive:   bool  = True


class ProxyRotator:
    """
    Thread-safe proxy rotation with health tracking.

    Load proxies from a text file (one per line):
        http://user:pass@host:port
        socks5://host:port
    """

    def __init__(self, cfg: ProxyConfig, proxy_file: Path) -> None:
        self.cfg = cfg
        self._lock = threading.Lock()
        self._index = 0
        self._proxies: List[ProxyEntry] = []

        if cfg.enabled and proxy_file.exists():
            self._load(proxy_file)
            log.info("Loaded %d proxies", len(self._proxies))
        elif cfg.enabled:
            log.warning("Proxy enabled but file not found: %s", proxy_file)

    def _load(self, path: Path) -> None:
        for line in path.read_text().strip().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                self._proxies.append(ProxyEntry(url=line))

    @property
    def available(self) -> bool:
        with self._lock:
            return any(p.is_alive for p in self._proxies)

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Return next proxy dict for requests, or None."""
        if not self.cfg.enabled or not self._proxies:
            return None

        with self._lock:
            alive = [p for p in self._proxies if p.is_alive]
            if not alive:
                log.warning("All proxies dead — falling back to direct")
                return None

            if self.cfg.rotation_mode == "random":
                entry = random.choice(alive)
            elif self.cfg.rotation_mode == "least_used":
                entry = min(alive, key=lambda p: p.uses)
            else:  # round_robin
                entry = alive[self._index % len(alive)]
                self._index += 1

            entry.uses += 1
            entry.last_used = time.monotonic()

        return {"http": entry.url, "https": entry.url}

    def report_success(self, proxy_dict: Optional[Dict]) -> None:
        if not proxy_dict:
            return
        url = proxy_dict.get("http", "")
        with self._lock:
            for p in self._proxies:
                if p.url == url:
                    p.failures = 0
                    break

    def report_failure(self, proxy_dict: Optional[Dict]) -> None:
        if not proxy_dict:
            return
        url = proxy_dict.get("http", "")
        with self._lock:
            for p in self._proxies:
                if p.url == url:
                    p.failures += 1
                    if p.failures >= self.cfg.max_failures:
                        p.is_alive = False
                        log.warning("Proxy disabled: %s", url[:40])
                    break

    def health_check(self) -> Dict[str, int]:
        """Test all proxies and return stats."""
        alive = dead = 0
        for p in self._proxies:
            try:
                resp = requests.get(
                    self.cfg.test_url,
                    proxies={"http": p.url, "https": p.url},
                    timeout=self.cfg.test_timeout,
                )
                p.is_alive = resp.status_code == 200
            except Exception:
                p.is_alive = False

            if p.is_alive:
                alive += 1
            else:
                dead += 1

        log.info("Proxy health: %d alive, %d dead", alive, dead)
        return {"alive": alive, "dead": dead}