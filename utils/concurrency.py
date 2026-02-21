"""Thread-safe primitives used across the project."""

from __future__ import annotations

import threading
import time
from typing import Optional, Set

from utils.log_config import get_logger

log = get_logger(__name__)


class AtomicCounter:
    """Thread-safe integer counter."""

    def __init__(self, initial: int = 0) -> None:
        self._value = initial
        self._lock = threading.Lock()

    def increment(self, n: int = 1) -> int:
        with self._lock:
            self._value += n
            return self._value

    @property
    def value(self) -> int:
        with self._lock:
            return self._value

    def __repr__(self) -> str:
        return f"AtomicCounter({self.value})"


class ThreadSafeSet:
    """Thread-safe ``set[str]`` for deduplication."""

    def __init__(self) -> None:
        self._data: Set[str] = set()
        self._lock = threading.Lock()

    def add(self, item: str) -> bool:
        """Add *item*.  Returns ``True`` if it was **new**."""
        with self._lock:
            if item in self._data:
                return False
            self._data.add(item)
            return True

    def __contains__(self, item: str) -> bool:
        with self._lock:
            return item in self._data

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


class RateLimiter:
    """Token-bucket rate limiter shared across threads."""

    def __init__(self, calls_per_second: float = 2.0) -> None:
        self._interval = 1.0 / calls_per_second
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            gap = now - self._last
            if gap < self._interval:
                time.sleep(self._interval - gap)
            self._last = time.monotonic()


class CircuitBreaker:
    """
    After *threshold* consecutive failures the engine is
    disabled for *cooldown* seconds.
    """

    def __init__(
        self,
        threshold: int = 5,
        cooldown: float = 120.0,
    ) -> None:
        self._threshold = threshold
        self._cooldown = cooldown
        self._failures = 0
        self._opened_at: Optional[float] = None
        self._lock = threading.Lock()

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self._threshold:
                self._opened_at = time.monotonic()
                log.warning(
                    "Circuit breaker OPEN  (failures=%d)", self._failures,
                )

    @property
    def is_open(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return False
            if time.monotonic() - self._opened_at > self._cooldown:
                log.info("Circuit breaker half-open — allowing retry")
                self._opened_at = None
                self._failures = 0
                return False
            return True