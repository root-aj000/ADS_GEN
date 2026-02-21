# """
# Download VERIFIED human face images based on emotion + audience.

# Key difference from product downloader:
#     - Queries are heavily biased toward "portrait", "headshot", "face"
#     - Every downloaded image is verified to contain a human face
#     - CLIP verification asks "is this a photo of a person's face?"
#     - Falls back to placeholder silhouette if no real face found
# """

# from __future__ import annotations

# import gc
# import hashlib
# import random
# import threading
# from dataclasses import dataclass, field
# from io import BytesIO
# from pathlib import Path
# from typing import Any, Dict, List, Optional, TYPE_CHECKING

# import numpy as np
# import requests
# from PIL import Image, ImageDraw, ImageFilter, ImageFont

# from config.settings import DEFAULT_HEADERS, EmotionConfig, ImageQualityConfig
# from search.manager import SearchManager
# from utils.concurrency import ThreadSafeSet
# from utils.log_config import get_logger
# from utils.retry import retry

# if TYPE_CHECKING:
#     from imaging.verifier import ImageVerifier

# log = get_logger(__name__)


# @dataclass
# class FaceDownloadResult:
#     success:    bool
#     path:       Optional[Path]        = None
#     source_url: Optional[str]         = None
#     emotion:    str                    = ""
#     query_used: str                    = ""
#     is_placeholder: bool              = False
#     info:       Dict[str, Any]        = field(default_factory=dict)


# class FaceDownloader:
#     """
#     Downloads portrait photos matching an emotion.
    
#     Every candidate image is checked:
#         1. Basic size/aspect validation
#         2. Skin tone pixel ratio (simple heuristic)
#         3. CLIP verification: "is this a photo of a human face?"
    
#     Thread-safe: per-thread requests.Session.
#     """

#     # ── CLIP prompts for face verification ──────────────────
#     # These are compared against each candidate image
#     FACE_POSITIVE_PROMPTS = [
#         "a photo of a person's face",
#         "a portrait photograph of a human",
#         "a headshot of a person smiling",
#     ]
    
#     FACE_NEGATIVE_PROMPTS = [
#         "a photo of food",
#         "a photo of a product",
#         "a photo of an animal",
#         "a photo of a landscape",
#         "a photo of text or graphics",
#         "a photo of an object",
#     ]
    
#     # Minimum CLIP score for "this is a face"
#     FACE_CLIP_THRESHOLD = 0.20

#     # ── Emotion → search queries ────────────────────────────
#     # Every query MUST include face/portrait/headshot terms
#     EMOTION_QUERIES: Dict[str, List[str]] = {
#         "happy":      [
#             "happy smiling person portrait headshot stock photo",
#             "joyful human face close up professional photo",
#             "cheerful person headshot white background",
#         ],
#         "joy":        [
#             "joyful person laughing headshot portrait photo",
#             "happy face beaming smile studio portrait",
#         ],
#         "excited":    [
#             "excited person face portrait stock photo",
#             "thrilled happy human headshot professional",
#         ],
#         "love":       [
#             "loving warm smile person portrait headshot",
#             "affectionate person face close up photo",
#         ],
#         "trust":      [
#             "trustworthy professional person headshot photo",
#             "confident business person portrait stock photo",
#         ],
#         "surprise":   [
#             "surprised amazed person face portrait photo",
#             "astonished human face headshot stock photo",
#         ],
#         "sad":        [
#             "concerned thoughtful person portrait headshot",
#             "empathetic person face close up stock photo",
#         ],
#         "fear":       [
#             "worried concerned person face portrait photo",
#             "anxious person headshot stock photo",
#         ],
#         "anger":      [
#             "determined intense person portrait headshot",
#             "passionate focused person face stock photo",
#         ],
#         "neutral":    [
#             "professional person headshot neutral expression",
#             "calm person portrait stock photo white background",
#         ],
#         "calm":       [
#             "calm relaxed person portrait headshot photo",
#             "serene peaceful person face stock photo",
#         ],
#         "curious":    [
#             "curious interested person portrait headshot",
#             "intrigued person face stock photo",
#         ],
#         "proud":      [
#             "proud confident person headshot portrait photo",
#             "accomplished person face stock photo",
#         ],
#         "grateful":   [
#             "grateful thankful person smiling portrait photo",
#             "appreciative person headshot stock photo",
#         ],
#         "optimistic": [
#             "optimistic hopeful person portrait headshot",
#             "positive person smiling face stock photo",
#         ],
#         "default":    [
#             "friendly person smiling portrait headshot stock photo",
#             "approachable person face close up professional photo",
#             "warm smile human headshot white background photo",
#         ],
#     }

#     def __init__(
#         self,
#         emotion_cfg: EmotionConfig,
#         quality_cfg: ImageQualityConfig,
#         search_manager: SearchManager,
#         hashes: ThreadSafeSet,
#         verifier: Optional["ImageVerifier"] = None,
#         timeout: int = 10,
#     ) -> None:
#         self.emotion_cfg = emotion_cfg
#         self.quality_cfg = quality_cfg
#         self.search = search_manager
#         self.hashes = hashes
#         self.verifier = verifier
#         self.timeout = timeout
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

#     # ── Build search query ──────────────────────────────────

#     def _build_query(self, emotion: str, audience: str = "") -> str:
#         """
#         Build a face-specific search query.
        
#         Always includes "portrait", "headshot", "person face"
#         to avoid getting product/food images.
#         """
#         emotion_lower = emotion.strip().lower()

#         # Find matching emotion queries
#         queries = self.EMOTION_QUERIES.get(emotion_lower)
        
#         if not queries:
#             # Partial match
#             for key, vals in self.EMOTION_QUERIES.items():
#                 if key in emotion_lower or emotion_lower in key:
#                     queries = vals
#                     break
        
#         if not queries:
#             queries = self.EMOTION_QUERIES["default"]

#         # Pick random query for variety
#         base_query = random.choice(queries)

#         # Add audience refinement (but keep it minimal)
#         if audience and audience.lower() not in ("nan", "none", "", "unknown", "general"):
#             # Only take key demographic words
#             demo_words = self._extract_demographics(audience)
#             if demo_words:
#                 base_query = f"{demo_words} {base_query}"

#         log.info("Face query: emotion='%s' → '%s'", emotion, base_query)
#         return base_query

#     @staticmethod
#     def _extract_demographics(audience: str) -> str:
#         """
#         Extract demographic keywords from audience string.
#         Only keep words that help narrow face search.
#         """
#         useful_words = {
#             "young", "old", "elderly", "teen", "teenager", "child",
#             "adult", "senior", "middle-aged", "millennial",
#             "man", "woman", "male", "female", "boy", "girl",
#             "professional", "business", "casual",
#             "asian", "african", "european", "latin", "diverse",
#         }
        
#         words = audience.lower().split()
#         matched = [w for w in words if w in useful_words]
#         return " ".join(matched[:2])  # Max 2 demographic words

#     # ── Face validation ─────────────────────────────────────

#     def _is_face_image(self, img: Image.Image) -> bool:
#         """
#         Quick heuristic check if image likely contains a human face.
        
#         Checks:
#             1. Portrait-ish aspect ratio (not super wide)
#             2. Skin-tone pixel ratio (rough heuristic)
#             3. Not too uniform (not a solid color)
#         """
#         # Aspect ratio — faces are usually portrait or square
#         aspect = img.width / img.height
#         if aspect > 2.0:  # Too wide — probably not a face
#             return False

#         # Minimum size
#         if img.width < self.emotion_cfg.min_face_width:
#             return False
#         if img.height < self.emotion_cfg.min_face_height:
#             return False

#         # Skin tone heuristic
#         try:
#             small = img.copy()
#             small.thumbnail((100, 100), Image.Resampling.LANCZOS)
#             arr = np.array(small.convert("RGB"))

#             # Check for skin-like colors (very rough)
#             r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

#             # Common skin tone ranges (works across skin colors)
#             skin_mask = (
#                 (r > 50) & (g > 30) & (b > 15) &     # Not too dark
#                 (r < 255) & (g < 240) & (b < 230) &   # Not too bright
#                 (r > g) & (r > b) &                     # Red channel dominant (skin tones)
#                 (np.abs(r.astype(int) - g.astype(int)) < 80)  # R and G somewhat close
#             )

#             skin_ratio = np.sum(skin_mask) / skin_mask.size

#             # At least 10% skin-like pixels for a face image
#             if skin_ratio < 0.08:
#                 log.debug("Skin ratio too low: %.1f%%", skin_ratio * 100)
#                 return False

#             # Check it's not too uniform (solid color)
#             std = np.std(arr)
#             if std < 15:
#                 log.debug("Image too uniform (std=%.1f)", std)
#                 return False

#             return True

#         except Exception:
#             return True  # If analysis fails, give benefit of doubt

#     def _verify_face_with_clip(self, img: Image.Image) -> float:
#         """
#         Use CLIP to verify this is actually a human face.
        
#         Compares image against positive prompts (face/person)
#         and negative prompts (food/product/object).
        
#         Returns score 0.0–1.0 where higher = more likely a face.
#         """
#         if self.verifier is None or not self.verifier.is_available:
#             return 0.5  # Neutral — can't verify

#         try:
#             # Score against "is this a face?"
#             face_scores = []
#             for prompt in self.FACE_POSITIVE_PROMPTS:
#                 result = self.verifier.verify(img, prompt)
#                 face_scores.append(result.clip_score)
            
#             avg_face = sum(face_scores) / len(face_scores) if face_scores else 0

#             # Score against "is this NOT a face?"
#             non_face_scores = []
#             for prompt in self.FACE_NEGATIVE_PROMPTS:
#                 result = self.verifier.verify(img, prompt)
#                 non_face_scores.append(result.clip_score)
            
#             avg_non_face = sum(non_face_scores) / len(non_face_scores) if non_face_scores else 0

#             # Face score = how much more "face-like" than "non-face-like"
#             score = avg_face - avg_non_face + 0.5  # Center at 0.5
#             score = max(0.0, min(1.0, score))

#             log.debug(
#                 "Face CLIP: face_avg=%.3f non_face_avg=%.3f final=%.3f",
#                 avg_face, avg_non_face, score,
#             )

#             return score

#         except Exception as exc:
#             log.warning("Face CLIP verification error: %s", exc)
#             return 0.5

#     # ── Download ────────────────────────────────────────────

#     def download_face(
#         self,
#         emotion: str,
#         audience: str,
#         dest: Path,
#         max_candidates: int = 15,
#     ) -> FaceDownloadResult:
#         """
#         Search, download, and VERIFY a face image.
        
#         Every candidate goes through:
#             1. Size/aspect check
#             2. Skin tone heuristic
#             3. CLIP face verification
        
#         If no verified face found, returns a placeholder.
#         """
#         emotion_lower = emotion.strip().lower()
#         if emotion_lower in self.emotion_cfg.ignore_emotions:
#             emotion_lower = "default"

#         query = self._build_query(emotion_lower, audience)

#         # Search
#         results = self.search.search(query, max_results=50)
#         if not results:
#             log.warning("No face results for: '%s'", query)
#             return self._placeholder_result(emotion, dest)

#         # Track best candidate
#         best_score = -1.0
#         best_data = None
#         best_result = None
#         best_hash = ""
#         verified_count = 0

#         for r in results:
#             if verified_count >= max_candidates:
#                 break

#             try:
#                 # Download
#                 data = self._fetch(r.url)
#                 if data is None:
#                     continue

#                 h = hashlib.md5(data).hexdigest()
#                 if not self.hashes.add(h):
#                     continue

#                 img = Image.open(BytesIO(data))

#                 # Step 1: Basic validation
#                 if not self._is_face_image(img):
#                     log.debug("Face rejected (heuristic): %s", r.url[:50])
#                     continue

#                 verified_count += 1

#                 # Step 2: CLIP face verification
#                 clip_score = self._verify_face_with_clip(img)

#                 log.debug(
#                     "Face candidate %d: clip=%.3f url=%s",
#                     verified_count, clip_score, r.url[:60],
#                 )

#                 # Track best
#                 if clip_score > best_score:
#                     best_score = clip_score
#                     best_data = data
#                     best_result = r
#                     best_hash = h
#                     # Keep a copy of the best image
#                     if hasattr(self, '_best_img'):
#                         del self._best_img
#                     self._best_img = img.copy()

#                 # Accept if clearly a face
#                 if clip_score >= self.FACE_CLIP_THRESHOLD:
#                     saved = self._save(img, dest)
#                     log.info(
#                         "✅ Face accepted: %dx%d clip=%.3f from %s",
#                         img.width, img.height, clip_score, r.source,
#                     )
#                     del data, img
#                     gc.collect()
#                     return FaceDownloadResult(
#                         success=True,
#                         path=saved,
#                         source_url=r.url,
#                         emotion=emotion,
#                         query_used=query,
#                         info={
#                             "width": saved and Image.open(saved).width or 0,
#                             "height": saved and Image.open(saved).height or 0,
#                             "clip_face_score": clip_score,
#                             "source_engine": r.source,
#                             "hash": h,
#                         },
#                     )

#             except Exception as exc:
#                 log.debug("Face candidate error: %s", exc)
#                 continue

#         # Use best candidate if above minimum threshold
#         if best_score > 0.10 and best_data is not None:
#             log.info(
#                 "Using best face candidate (score=%.3f after %d checks)",
#                 best_score, verified_count,
#             )
#             img = Image.open(BytesIO(best_data))
#             saved = self._save(img, dest)
#             del best_data, img
#             gc.collect()
#             return FaceDownloadResult(
#                 success=True,
#                 path=saved,
#                 source_url=best_result.url if best_result else "",
#                 emotion=emotion,
#                 query_used=query,
#                 info={"clip_face_score": best_score},
#             )

#         # No good face found — use placeholder
#         log.warning("No verified face found for '%s' — using placeholder", emotion)
#         return self._placeholder_result(emotion, dest)

#     def _placeholder_result(self, emotion: str, dest: Path) -> FaceDownloadResult:
#         """Create and return a placeholder face result."""
#         path = self.create_placeholder_face(emotion, dest)
#         return FaceDownloadResult(
#             success=True,
#             path=path,
#             emotion=emotion,
#             is_placeholder=True,
#         )

#     # ── Internals ───────────────────────────────────────────

#     @retry(max_attempts=2, backoff_base=0.5, exceptions=(requests.RequestException,))
#     def _fetch(self, url: str) -> Optional[bytes]:
#         resp = self.session.get(url, timeout=self.timeout, stream=True)
#         if resp.status_code != 200:
#             return None
#         data = resp.content
#         return data if len(data) >= 20000 else None

#     @staticmethod
#     def _save(img: Image.Image, dest: Path) -> Path:
#         p = dest.with_suffix(".jpg")
#         img.convert("RGB").save(p, "JPEG", quality=95)
#         return p

#     # ── Placeholder face ────────────────────────────────────

#     @staticmethod
#     def create_placeholder_face(
#         emotion: str,
#         dest: Path,
#         size: int = 400,
#     ) -> Path:
#         """Create a stylized placeholder face silhouette."""
#         img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
#         draw = ImageDraw.Draw(img)

#         cx, cy = size // 2, size // 2

#         # Head circle
#         head_r = size // 3
#         draw.ellipse(
#             [cx - head_r, cy - head_r - 20, cx + head_r, cy + head_r - 20],
#             fill=(200, 200, 200, 220),
#         )

#         # Body/shoulders arc
#         body_w = size // 2 + 20
#         draw.ellipse(
#             [cx - body_w, cy + head_r - 20, cx + body_w, cy + head_r + 100],
#             fill=(180, 180, 180, 200),
#         )

#         # Eyes
#         eye_y = cy - 30
#         eye_r = 8
#         draw.ellipse([cx - 35 - eye_r, eye_y - eye_r, cx - 35 + eye_r, eye_y + eye_r], fill=(80, 80, 80))
#         draw.ellipse([cx + 35 - eye_r, eye_y - eye_r, cx + 35 + eye_r, eye_y + eye_r], fill=(80, 80, 80))

#         # Mouth based on emotion
#         emo = emotion.lower()
#         mouth_y = cy + 20
#         if emo in ("happy", "joy", "excited", "love", "grateful", "proud", "optimistic"):
#             draw.arc([cx - 30, mouth_y - 15, cx + 30, mouth_y + 15], 0, 180, fill=(80, 80, 80), width=3)
#         elif emo in ("sad", "fear"):
#             draw.arc([cx - 25, mouth_y + 5, cx + 25, mouth_y + 35], 180, 360, fill=(80, 80, 80), width=3)
#         elif emo in ("surprise",):
#             draw.ellipse([cx - 12, mouth_y - 5, cx + 12, mouth_y + 15], fill=(80, 80, 80))
#         else:
#             draw.line([cx - 20, mouth_y + 5, cx + 20, mouth_y + 5], fill=(80, 80, 80), width=3)

#         # Soften edges
#         img = img.filter(ImageFilter.GaussianBlur(1))

#         p = dest.with_suffix(".png")
#         img.save(p, "PNG")
#         return p