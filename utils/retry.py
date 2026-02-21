"""Retry decorator with exponential back-off."""

from __future__ import annotations

import time
from functools import wraps
from typing import Tuple, Type

from utils.log_config import get_logger

log = get_logger(__name__)


def retry(
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
):
    """
    Decorator — retries the wrapped function up to *max_attempts*
    times with exponential back-off.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        delay = backoff_base * (2 ** (attempt - 1))
                        log.debug(
                            "Retry %d/%d for %s after %.1fs — %s",
                            attempt,
                            max_attempts,
                            func.__name__,
                            delay,
                            exc,
                        )
                        time.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator