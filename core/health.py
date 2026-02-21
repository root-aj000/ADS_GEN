"""
Real-time health tracking for search engines.
Collects latency, success rate, result counts.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from utils.log_config import get_logger

log = get_logger(__name__)


@dataclass
class EngineMetrics:
    total_calls:   int   = 0
    total_results: int   = 0
    successes:     int   = 0
    failures:      int   = 0
    total_latency: float = 0.0
    last_call:     float = 0.0
    last_error:    str   = ""

    @property
    def success_rate(self) -> float:
        return self.successes / max(self.total_calls, 1)

    @property
    def avg_latency(self) -> float:
        return self.total_latency / max(self.successes, 1)

    @property
    def avg_results(self) -> float:
        return self.total_results / max(self.successes, 1)


class HealthMonitor:
    """Thread-safe engine health tracker."""

    def __init__(self) -> None:
        self._metrics: Dict[str, EngineMetrics] = defaultdict(EngineMetrics)
        self._lock = threading.Lock()

    def record_call(
        self,
        engine: str,
        success: bool,
        result_count: int = 0,
        latency: float = 0.0,
        error: str = "",
    ) -> None:
        with self._lock:
            m = self._metrics[engine]
            m.total_calls += 1
            m.last_call = time.monotonic()
            if success:
                m.successes += 1
                m.total_results += result_count
                m.total_latency += latency
            else:
                m.failures += 1
                m.last_error = error

    def get_report(self) -> Dict[str, Dict]:
        with self._lock:
            report = {}
            for name, m in self._metrics.items():
                report[name] = {
                    "calls":        m.total_calls,
                    "success_rate": f"{m.success_rate:.1%}",
                    "avg_latency":  f"{m.avg_latency:.2f}s",
                    "avg_results":  f"{m.avg_results:.1f}",
                    "failures":     m.failures,
                    "last_error":   m.last_error[:50] if m.last_error else "",
                }
            return report

    def log_report(self) -> None:
        report = self.get_report()
        log.info("─── Engine Health ───")
        for name, data in report.items():
            log.info(
                "  %-12s │ calls=%-4d │ success=%-5s │ latency=%-6s │ avg_results=%-5s │ failures=%d",
                name,
                data["calls"],
                data["success_rate"],
                data["avg_latency"],
                data["avg_results"],
                data["failures"],
            )
        log.info("─" * 60)

    def suggest_priority(self) -> List[str]:
        """Suggest engine order based on actual performance."""
        with self._lock:
            scored = []
            for name, m in self._metrics.items():
                score = (
                    m.success_rate * 50
                    + m.avg_results * 2
                    - m.avg_latency * 5
                )
                scored.append((name, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [name for name, _ in scored]