"""Smart background removal with validation & thread safety."""

from __future__ import annotations

import gc
import threading
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from PIL import Image
from rembg import remove as rembg_remove

from config.settings import BackgroundRemovalConfig
from utils.log_config import get_logger

log = get_logger(__name__)


@dataclass
class BGRemovalResult:
    success:      bool
    use_original: bool
    output_path:  Optional[Path]  = None
    stats:        Dict[str, Any]  = field(default_factory=dict)


class BackgroundRemover:
    """
    Serialises ``rembg`` calls through a lock (model is not
    guaranteed thread-safe) but allows the rest of the
    pipeline to run concurrently.
    """

    def __init__(self, cfg: BackgroundRemovalConfig) -> None:
        self.cfg = cfg
        self._lock = threading.Lock()

    def should_remove(self, query: str) -> bool:
        low = query.lower()
        return not any(kw in low for kw in self.cfg.scene_keywords)

    def remove(self, src: Path, dst: Path) -> BGRemovalResult:
        log.info("BG removal: %s", src.name)

        try:
            with Image.open(src) as orig:
                total_px = orig.width * orig.height

            with open(src, "rb") as fh:
                raw = fh.read()

            with self._lock:
                out_data = rembg_remove(raw)

            result = Image.open(BytesIO(out_data)).convert("RGBA")
            alpha = np.array(result)[:, :, 3]
            kept = int(np.sum(alpha > 10))
            ratio = kept / total_px

            log.info("BG removal kept %.1f%%", ratio * 100)

            c = self.cfg

            # too aggressive
            if ratio < c.min_retention:
                if ratio >= 0.01 and self._coherent(alpha):
                    result.save(dst, "PNG")
                    return BGRemovalResult(True, False, dst, {"ratio": ratio})
                return BGRemovalResult(False, True, stats={"ratio": ratio})

            # nothing removed
            if ratio > c.max_retention:
                return BGRemovalResult(False, True, stats={"ratio": ratio})

            # object too small
            coords = np.argwhere(alpha > 10)
            if len(coords):
                mn, mx = coords.min(0), coords.max(0)
                obj = (mx[1] - mn[1]) * (mx[0] - mn[0])
                if obj / (result.width * result.height) < c.min_object_ratio:
                    return BGRemovalResult(False, True, stats={"ratio": ratio})

            result.save(dst, "PNG")
            del alpha, result
            gc.collect()
            return BGRemovalResult(True, False, dst, {"ratio": ratio})

        except Exception as exc:
            log.error("BG removal error: %s", exc)
            return BGRemovalResult(False, True, stats={"error": str(exc)})

    def _coherent(self, alpha: np.ndarray) -> bool:
        mask = alpha > 10
        rows, cols = np.any(mask, 1), np.any(mask, 0)
        if not rows.any() or not cols.any():
            return False
        r0, r1 = np.where(rows)[0][[0, -1]]
        c0, c1 = np.where(cols)[0][[0, -1]]
        bbox = (r1 - r0 + 1) * (c1 - c0 + 1)
        filled = np.sum(mask[r0:r1 + 1, c0:c1 + 1])
        return (filled / bbox) >= self.cfg.min_fill_ratio