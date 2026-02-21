# # """Download, validate and persist a single product image."""

# # from __future__ import annotations

# # import gc
# # import hashlib
# # import threading
# # from dataclasses import dataclass, field
# # from io import BytesIO
# # from pathlib import Path
# # from typing import Any, Dict, List, Optional

# # import requests
# # from PIL import Image

# # from config.settings import DEFAULT_HEADERS, ImageQualityConfig
# # from imaging.helpers import has_visual_content
# # from search.base import ImageResult
# # from utils.concurrency import ThreadSafeSet
# # from utils.log_config import get_logger
# # from utils.retry import retry

# # log = get_logger(__name__)


# # @dataclass
# # class DownloadResult:
# #     success:    bool
# #     path:       Optional[Path]        = None
# #     source_url: Optional[str]         = None
# #     info:       Dict[str, Any]        = field(default_factory=dict)


# # class ImageDownloader:
# #     """Thread-safe: each thread gets its own ``requests.Session``."""

# #     def __init__(
# #         self,
# #         cfg: ImageQualityConfig,
# #         hashes: ThreadSafeSet,
# #         timeout: int = 10,
# #     ) -> None:
# #         self.cfg = cfg
# #         self.hashes = hashes
# #         self.timeout = timeout
# #         self._local = threading.local()

# #     @property
# #     def session(self) -> requests.Session:
# #         s = getattr(self._local, "session", None)
# #         if s is None:
# #             s = requests.Session()
# #             s.headers.update({
# #                 "User-Agent": DEFAULT_HEADERS["User-Agent"],
# #                 "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
# #             })
# #             self._local.session = s
# #         return s

# #     # ── public ──────────────────────────────────────────────
# #     def download_best(
# #         self,
# #         results: List[ImageResult],
# #         dest: Path,
# #         skip: int = 0,
# #     ) -> DownloadResult:
# #         ranked = sorted(results, key=self._score, reverse=True)
# #         valid = 0

# #         for r in ranked:
# #             try:
# #                 data = self._fetch(r.url)
# #                 if data is None:
# #                     continue

# #                 h = hashlib.md5(data).hexdigest()
# #                 if not self.hashes.add(h):
# #                     continue

# #                 img = Image.open(BytesIO(data))
# #                 if not self._ok(img, data):
# #                     continue

# #                 if valid < skip:
# #                     valid += 1
# #                     continue

# #                 saved = self._save(img, dest)
# #                 info = {
# #                     "width": img.width,
# #                     "height": img.height,
# #                     "file_size": len(data),
# #                     "source_engine": r.source,
# #                     "hash": h,
# #                 }
# #                 log.info(
# #                     "Downloaded %dx%d from %s",
# #                     img.width, img.height, r.source,
# #                 )
# #                 del data, img
# #                 gc.collect()
# #                 return DownloadResult(True, saved, r.url, info)

# #             except Exception:
# #                 continue

# #         log.warning("No image passed validation (%d candidates)", len(ranked))
# #         return DownloadResult(False)

# #     # ── internals ───────────────────────────────────────────
# #     @retry(max_attempts=2, backoff_base=0.5, exceptions=(requests.RequestException,))
# #     def _fetch(self, url: str) -> Optional[bytes]:
# #         resp = self.session.get(url, timeout=self.timeout, stream=True)
# #         if resp.status_code != 200:
# #             return None
# #         cl = resp.headers.get("content-length")
# #         if cl and int(cl) < self.cfg.min_file_bytes:
# #             return None
# #         data = resp.content
# #         return data if len(data) >= self.cfg.min_file_bytes else None

# #     def _ok(self, img: Image.Image, raw: bytes) -> bool:
# #         c = self.cfg
# #         if img.width < c.min_width or img.height < c.min_height:
# #             return False
# #         ar = img.width / img.height
# #         if ar < c.min_aspect or ar > c.max_aspect:
# #             return False
# #         return has_visual_content(img, c.min_std_dev, c.min_unique_colours)

# #     @staticmethod
# #     def _save(img: Image.Image, dest: Path) -> Path:
# #         if img.mode == "RGBA":
# #             p = dest.with_suffix(".png")
# #             img.save(p, "PNG")
# #         else:
# #             p = dest.with_suffix(".jpg")
# #             img.convert("RGB").save(p, "JPEG", quality=95)
# #         return p

# #     @staticmethod
# #     def _score(r: ImageResult) -> float:
# #         s = 0.0
# #         low = r.url.lower()
# #         if ".png" in low:
# #             s += 10
# #         for d in (
# #             "shutterstock", "istockphoto", "gettyimages",
# #             "adobe", "amazon", "pngtree", "freepik", "unsplash",
# #         ):
# #             if d in low:
# #                 s += 5
# #         if any(x in low for x in ("thumb", "small", "icon", "tiny", "mini")):
# #             s -= 10
# #         s += {"duckduckgo": 3, "bing": 2, "google": 1}.get(r.source, 0)
# #         s += (r.width * r.height) / 1_000_000
# #         return s

# """Download, validate and persist a single product image."""

# from __future__ import annotations

# import gc
# import hashlib
# import threading
# from dataclasses import dataclass, field
# from io import BytesIO
# from pathlib import Path
# from typing import Any, Dict, List, Optional, TYPE_CHECKING

# import requests
# from PIL import Image

# from config.settings import DEFAULT_HEADERS, ImageQualityConfig
# from imaging.helpers import has_visual_content
# from search.base import ImageResult
# from utils.concurrency import ThreadSafeSet
# from utils.log_config import get_logger
# from utils.retry import retry

# if TYPE_CHECKING:
#     from imaging.scorer import ImageQualityScorer

# log = get_logger(__name__)


# @dataclass
# class DownloadResult:
#     success:    bool
#     path:       Optional[Path]        = None
#     source_url: Optional[str]         = None
#     info:       Dict[str, Any]        = field(default_factory=dict)


# class ImageDownloader:
#     """Thread-safe: each thread gets its own ``requests.Session``."""

#     def __init__(
#         self,
#         cfg: ImageQualityConfig,
#         hashes: ThreadSafeSet,
#         timeout: int = 10,
#         scorer: Optional["ImageQualityScorer"] = None,
#     ) -> None:
#         self.cfg = cfg
#         self.hashes = hashes
#         self.timeout = timeout
#         self.scorer = scorer
#         self._local = threading.local()

#     @property
#     def session(self) -> requests.Session:
#         s = getattr(self._local, "session", None)
#         if s is None:
#             s = requests.Session()
#             s.headers.update({
#                 "User-Agent": DEFAULT_HEADERS["User-Agent"],
#                 "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
#             })
#             self._local.session = s
#         return s

#     # ── public ──────────────────────────────────────────────
#     def download_best(
#         self,
#         results: List[ImageResult],
#         dest: Path,
#         skip: int = 0,
#     ) -> DownloadResult:
#         # Use scorer if available, otherwise fallback to simple scoring
#         if self.scorer:
#             ranked = sorted(
#                 results,
#                 key=lambda r: self.scorer.score_result(r),
#                 reverse=True,
#             )
#         else:
#             ranked = sorted(results, key=self._score, reverse=True)

#         valid = 0

#         for r in ranked:
#             try:
#                 data = self._fetch(r.url)
#                 if data is None:
#                     continue

#                 h = hashlib.md5(data).hexdigest()
#                 if not self.hashes.add(h):
#                     continue

#                 img = Image.open(BytesIO(data))
#                 if not self._ok(img, data):
#                     continue

#                 if valid < skip:
#                     valid += 1
#                     continue

#                 saved = self._save(img, dest)
#                 info = {
#                     "width": img.width,
#                     "height": img.height,
#                     "file_size": len(data),
#                     "source_engine": r.source,
#                     "hash": h,
#                 }
#                 log.info(
#                     "Downloaded %dx%d from %s",
#                     img.width, img.height, r.source,
#                 )
#                 del data, img
#                 gc.collect()
#                 return DownloadResult(True, saved, r.url, info)

#             except Exception as exc:
#                 log.debug("Download failed for %s: %s", r.url[:50], exc)
#                 continue

#         log.warning("No image passed validation (%d candidates)", len(ranked))
#         return DownloadResult(False)

#     # ── internals ───────────────────────────────────────────
#     @retry(max_attempts=2, backoff_base=0.5, exceptions=(requests.RequestException,))
#     def _fetch(self, url: str) -> Optional[bytes]:
#         resp = self.session.get(url, timeout=self.timeout, stream=True)
#         if resp.status_code != 200:
#             return None
#         cl = resp.headers.get("content-length")
#         if cl and int(cl) < self.cfg.min_file_bytes:
#             return None
#         data = resp.content
#         return data if len(data) >= self.cfg.min_file_bytes else None

#     def _ok(self, img: Image.Image, raw: bytes) -> bool:
#         c = self.cfg
#         if img.width < c.min_width or img.height < c.min_height:
#             return False
#         ar = img.width / img.height
#         if ar < c.min_aspect or ar > c.max_aspect:
#             return False
#         return has_visual_content(img, c.min_std_dev, c.min_unique_colours)

#     @staticmethod
#     def _save(img: Image.Image, dest: Path) -> Path:
#         if img.mode == "RGBA":
#             p = dest.with_suffix(".png")
#             img.save(p, "PNG")
#         else:
#             p = dest.with_suffix(".jpg")
#             img.convert("RGB").save(p, "JPEG", quality=95)
#         return p

#     @staticmethod
#     def _score(r: ImageResult) -> float:
#         """Simple fallback scoring when no scorer is provided."""
#         s = 0.0
#         low = r.url.lower()
#         if ".png" in low:
#             s += 10
#         for d in (
#             "shutterstock", "istockphoto", "gettyimages",
#             "adobe", "amazon", "pngtree", "freepik", "unsplash",
#         ):
#             if d in low:
#                 s += 5
#         if any(x in low for x in ("thumb", "small", "icon", "tiny", "mini")):
#             s -= 10
#         s += {"duckduckgo": 3, "bing": 2, "google": 1}.get(r.source, 0)
#         s += (r.width * r.height) / 1_000_000
#         return s


"""Download, validate, VERIFY, and persist a single product image."""

from __future__ import annotations

import gc
import hashlib
import threading
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import requests
from PIL import Image

from config.settings import DEFAULT_HEADERS, ImageQualityConfig, VerificationConfig
from imaging.helpers import has_visual_content
from search.base import ImageResult
from utils.concurrency import ThreadSafeSet
from utils.log_config import get_logger
from utils.retry import retry

if TYPE_CHECKING:
    from imaging.scorer import ImageQualityScorer
    from imaging.verifier import ImageVerifier

log = get_logger(__name__)


@dataclass
class DownloadResult:
    success:          bool
    path:             Optional[Path]        = None
    source_url:       Optional[str]         = None
    info:             Dict[str, Any]        = field(default_factory=dict)
    verification:     Optional[Dict]        = None


class ImageDownloader:
    """
    Thread-safe image downloader with CLIP+BLIP verification.
    
    Flow for each candidate:
        1. Download raw bytes
        2. Check file size, dimensions, aspect ratio
        3. Check visual content (not blank)
        4. CLIP+BLIP verification against query
        5. Accept or reject → try next candidate
    """

    def __init__(
        self,
        cfg: ImageQualityConfig,
        hashes: ThreadSafeSet,
        timeout: int = 10,
        scorer: Optional["ImageQualityScorer"] = None,
        verifier: Optional["ImageVerifier"] = None,
        verify_cfg: Optional[VerificationConfig] = None,
    ) -> None:
        self.cfg = cfg
        self.hashes = hashes
        self.timeout = timeout
        self.scorer = scorer
        self.verifier = verifier
        self.verify_cfg = verify_cfg
        self._local = threading.local()

    @property
    def session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update({
                "User-Agent": DEFAULT_HEADERS["User-Agent"],
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            })
            self._local.session = s
        return s

    # ── public ──────────────────────────────────────────────
    def download_best(
        self,
        results: List[ImageResult],
        dest: Path,
        query: str = "",
        skip: int = 0,
    ) -> DownloadResult:
        """
        Download the best matching image from search results.
        
        With verification enabled:
            - Tries up to max_verify_candidates images
            - Each image scored by CLIP+BLIP
            - Accepts first image above threshold
            - If none pass, uses best-scoring one
        
        Args:
            results: Search results to try
            dest: Save path
            query: Original search query (for verification)
            skip: Skip this many valid images
            
        Returns:
            DownloadResult with success status and info
        """
        # Rank by quality score
        if self.scorer:
            ranked = sorted(
                results,
                key=lambda r: self.scorer.score_result(r),
                reverse=True,
            )
        else:
            ranked = sorted(results, key=self._score, reverse=True)

        valid = 0
        
        # Track best candidate for fallback
        best_candidate: Optional[Dict] = None
        best_score: float = -1.0
        
        verified_count = 0
        max_verify = (
            self.verify_cfg.max_verify_candidates
            if self.verify_cfg else 10
        )

        for r in ranked:
            # Stop if we've verified enough candidates
            if self.verifier and verified_count >= max_verify:
                log.info(
                    "Checked %d candidates, using best (score=%.3f)",
                    verified_count, best_score,
                )
                break
            
            try:
                # Step 1: Download
                data = self._fetch(r.url)
                if data is None:
                    continue

                # Step 2: Hash dedup
                h = hashlib.md5(data).hexdigest()
                if not self.hashes.add(h):
                    continue

                # Step 3: Basic validation
                img = Image.open(BytesIO(data))
                if not self._ok(img, data):
                    continue

                # Step 4: Skip logic
                if valid < skip:
                    valid += 1
                    continue

                # ═══════════════════════════════════════════
                # Step 5: CLIP + BLIP VERIFICATION
                # ═══════════════════════════════════════════
                if self.verifier and query:
                    verified_count += 1
                    
                    verify_result = self.verifier.verify(img, query)
                    
                    log.info(
                        "  Candidate %d: %s",
                        verified_count,
                        verify_result.summary(),
                    )
                    
                    # Track best candidate
                    if verify_result.combined_score > best_score:
                        best_score = verify_result.combined_score
                        best_candidate = {
                            "data": data,
                            "image": img.copy(),
                            "result": r,
                            "hash": h,
                            "verification": verify_result,
                        }
                    
                    # Accept if above threshold
                    if verify_result.accepted:
                        return self._save_and_return(
                            img, data, r, h, dest, verify_result,
                        )
                    
                    # Check if we should try more
                    min_before_best = (
                        self.verify_cfg.min_candidates_before_best
                        if self.verify_cfg else 3
                    )
                    if verified_count < min_before_best:
                        continue
                    
                    # After min candidates, accept best if reasonable
                    combined_reject = (
                        self.verify_cfg.combined_reject
                        if self.verify_cfg else 0.12
                    )
                    if best_score > combined_reject:
                        log.info(
                            "Using best candidate after %d checks (score=%.3f)",
                            verified_count, best_score,
                        )
                        bc = best_candidate
                        return self._save_and_return(
                            bc["image"], bc["data"], bc["result"],
                            bc["hash"], dest, bc["verification"],
                        )
                    
                    continue
                
                # No verifier — accept directly
                return self._save_and_return(img, data, r, h, dest)

            except Exception as exc:
                log.debug("Candidate failed: %s", exc)
                continue
        
        # ── After all candidates exhausted ──
        # Use best candidate if we have one
        if best_candidate and best_score > 0:
            combined_reject = (
                self.verify_cfg.combined_reject
                if self.verify_cfg else 0.12
            )
            if best_score >= combined_reject:
                log.info(
                    "Using best from %d candidates (score=%.3f)",
                    verified_count, best_score,
                )
                bc = best_candidate
                return self._save_and_return(
                    bc["image"], bc["data"], bc["result"],
                    bc["hash"], dest, bc["verification"],
                )
            else:
                log.warning(
                    "Best candidate score %.3f below threshold %.3f — rejecting all",
                    best_score, combined_reject,
                )

        log.warning("No image passed validation (%d candidates)", len(ranked))
        return DownloadResult(False)

    # ── save helper ─────────────────────────────────────────
    def _save_and_return(
        self,
        img: Image.Image,
        data: bytes,
        result: ImageResult,
        img_hash: str,
        dest: Path,
        verification=None,
    ) -> DownloadResult:
        """Save image and return DownloadResult."""
        saved = self._save(img, dest)
        
        info = {
            "width": img.width,
            "height": img.height,
            "file_size": len(data),
            "source_engine": result.source,
            "hash": img_hash,
        }
        
        verify_info = None
        if verification:
            verify_info = {
                "clip_score": verification.clip_score,
                "blip_score": verification.blip_score,
                "combined_score": verification.combined_score,
                "blip_caption": verification.blip_caption,
                "accepted": verification.accepted,
                "reason": verification.reason,
            }
            info["verification"] = verify_info
        
        log.info(
            "Downloaded %dx%d from %s%s",
            img.width, img.height, result.source,
            f" (verified={verification.combined_score:.3f})" if verification else "",
        )
        
        del data
        gc.collect()
        
        return DownloadResult(True, saved, result.url, info, verify_info)

    # ── internals ───────────────────────────────────────────
    @retry(max_attempts=2, backoff_base=0.5, exceptions=(requests.RequestException,))
    def _fetch(self, url: str) -> Optional[bytes]:
        resp = self.session.get(url, timeout=self.timeout, stream=True)
        if resp.status_code != 200:
            return None
        cl = resp.headers.get("content-length")
        if cl and int(cl) < self.cfg.min_file_bytes:
            return None
        data = resp.content
        return data if len(data) >= self.cfg.min_file_bytes else None

    def _ok(self, img: Image.Image, raw: bytes) -> bool:
        c = self.cfg
        if img.width < c.min_width or img.height < c.min_height:
            return False
        ar = img.width / img.height
        if ar < c.min_aspect or ar > c.max_aspect:
            return False
        return has_visual_content(img, c.min_std_dev, c.min_unique_colours)

    @staticmethod
    def _save(img: Image.Image, dest: Path) -> Path:
        if img.mode == "RGBA":
            p = dest.with_suffix(".png")
            img.save(p, "PNG")
        else:
            p = dest.with_suffix(".jpg")
            img.convert("RGB").save(p, "JPEG", quality=95)
        return p

    @staticmethod
    def _score(r: ImageResult) -> float:
        """Fallback scoring when no scorer provided."""
        s = 0.0
        low = r.url.lower()
        if ".png" in low:
            s += 10
        for d in (
            "shutterstock", "istockphoto", "gettyimages",
            "adobe", "amazon", "pngtree", "freepik", "unsplash",
        ):
            if d in low:
                s += 5
        if any(x in low for x in ("thumb", "small", "icon", "tiny", "mini")):
            s -= 10
        s += {"duckduckgo": 3, "bing": 2, "google": 1}.get(r.source, 0)
        s += (r.width * r.height) / 1_000_000
        return s