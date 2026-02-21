"""
Multi-factor image quality scoring.
Replaces the simple _score() method with a proper scorer.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter, ImageStat

from config.settings import ImageQualityConfig
from search.base import ImageResult
from utils.log_config import get_logger

log = get_logger(__name__)


@dataclass
class QualityReport:
    """Breakdown of quality metrics for an image."""
    sharpness:       float = 0.0
    contrast:        float = 0.0
    resolution:      float = 0.0
    source_trust:    float = 0.0
    format_bonus:    float = 0.0
    penalty:         float = 0.0
    final_score:     float = 0.0

    def summary(self) -> str:
        return (
            f"score={self.final_score:.1f} "
            f"(sharp={self.sharpness:.1f} contrast={self.contrast:.1f} "
            f"res={self.resolution:.1f} source={self.source_trust:.1f} "
            f"fmt={self.format_bonus:.1f} pen={self.penalty:.1f})"
        )


class ImageQualityScorer:
    """
    Scores images on multiple axes:
      - Sharpness   (Laplacian variance)
      - Contrast    (std dev of luminance)
      - Resolution  (total pixel count, normalised)
      - Source trust (domain reputation)
      - Format      (PNG bonus for transparency)
      - Penalties   (thumbnail patterns, tiny images)
    """

    TRUSTED_DOMAINS = {
        "shutterstock.com": 0.9, "istockphoto.com": 0.9,
        "gettyimages.com": 0.9, "adobe.com": 0.85,
        "unsplash.com": 0.85, "pexels.com": 0.8,
        "freepik.com": 0.7, "pngtree.com": 0.7,
        "amazon.com": 0.6, "ebay.com": 0.5,
    }

    PENALTY_PATTERNS = (
        "thumb", "small", "icon", "tiny", "mini",
        "preview", "placeholder", "loading", "spinner",
    )

    def __init__(self, cfg: ImageQualityConfig) -> None:
        self.cfg = cfg

    def score_result(self, result: ImageResult) -> float:
        """Quick score based on URL metadata only (no download needed)."""
        s = 0.0
        low = result.url.lower()

        # format
        if ".png" in low:
            s += 10
        elif ".webp" in low:
            s += 5

        # source trust
        for domain, trust in self.TRUSTED_DOMAINS.items():
            if domain in low:
                s += trust * 10
                break

        # resolution hint from search metadata
        if result.width > 0 and result.height > 0:
            mpx = (result.width * result.height) / 1_000_000
            s += min(mpx * 5, 20)

        # penalties
        if any(p in low for p in self.PENALTY_PATTERNS):
            s -= 15

        # engine trust
        s += {"duckduckgo": 3, "bing": 2, "google": 1}.get(result.source, 0)

        return s

    def score_image(
        self,
        image: Image.Image,
        result: Optional[ImageResult] = None,
    ) -> QualityReport:
        """
        Full quality analysis on a downloaded image.
        More expensive — call only on top candidates.
        """
        report = QualityReport()
        c = self.cfg

        # 1. Sharpness (Laplacian variance)
        try:
            grey = image.convert("L")
            laplacian = grey.filter(ImageFilter.Kernel(
                size=(3, 3),
                kernel=[-1, -1, -1, -1, 8, -1, -1, -1, -1],
                scale=1, offset=128,
            ))
            stat = ImageStat.Stat(laplacian)
            # variance of laplacian
            report.sharpness = min(stat.var[0] / 100, 10.0)
        except Exception:
            report.sharpness = 5.0

        # 2. Contrast (std dev of luminance)
        try:
            grey = image.convert("L")
            stat = ImageStat.Stat(grey)
            report.contrast = min(stat.stddev[0] / 10, 10.0)
        except Exception:
            report.contrast = 5.0

        # 3. Resolution
        mpx = (image.width * image.height) / 1_000_000
        report.resolution = min(mpx * 3, 10.0)

        # 4. Source trust
        if result:
            low = result.url.lower()
            for domain, trust in self.TRUSTED_DOMAINS.items():
                if domain in low:
                    report.source_trust = trust * 10
                    break

        # 5. Format bonus
        if image.mode == "RGBA":
            report.format_bonus = 3.0

        # 6. Penalties
        if image.width < 200 or image.height < 200:
            report.penalty += 5.0
        if image.width < 100 or image.height < 100:
            report.penalty += 10.0

        # Weighted final
        report.final_score = (
            report.sharpness   * c.sharpness_weight
            + report.contrast  * c.contrast_weight
            + report.resolution * c.resolution_weight
            + report.source_trust * c.source_weight
            + report.format_bonus
            - report.penalty
        )

        return report