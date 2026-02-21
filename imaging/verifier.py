# # """
# # CLIP + BLIP image-text cross-verification.

# # Ensures downloaded images actually match the search query.

# # Flow:
# #     1. CLIP: Compute cosine similarity between image embedding & text embedding
# #     2. BLIP: Generate caption for image, compare caption words with query words
# #     3. Combine scores with configurable weights
# #     4. Accept / reject based on thresholds

# # Thread Safety:
# #     - Models loaded once (singleton)
# #     - Inference protected by threading.Lock
# #     - Multiple threads share the same model instance
# # """

# # from __future__ import annotations

# # import threading
# # import time
# # from dataclasses import dataclass
# # from io import BytesIO
# # from typing import Dict, List, Optional, Set, Tuple

# # from PIL import Image

# # from config.settings import VerificationConfig
# # from utils.log_config import get_logger

# # log = get_logger(__name__)


# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # #  RESULT TYPES
# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # @dataclass
# # class VerificationResult:
# #     """Result of verifying one image against a query."""
    
# #     accepted:        bool
# #     clip_score:      float  = 0.0
# #     blip_score:      float  = 0.0
# #     combined_score:  float  = 0.0
# #     blip_caption:    str    = ""
# #     reason:          str    = ""
    
# #     def summary(self) -> str:
# #         status = "✅ ACCEPT" if self.accepted else "❌ REJECT"
# #         parts = [f"{status} (combined={self.combined_score:.3f}"]
# #         if self.clip_score > 0:
# #             parts.append(f"clip={self.clip_score:.3f}")
# #         if self.blip_score > 0:
# #             parts.append(f"blip={self.blip_score:.3f}")
# #         if self.blip_caption:
# #             parts.append(f"caption='{self.blip_caption[:50]}'")
# #         parts.append(f"reason='{self.reason}'")
# #         return " | ".join(parts) + ")"


# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # #  TEXT SIMILARITY HELPER
# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # def _word_overlap_score(text_a: str, text_b: str) -> float:
# #     """
# #     Compute word-level overlap between two texts.
    
# #     Returns 0.0–1.0 based on Jaccard-like similarity.
# #     Ignores common stop words.
# #     """
# #     stop_words: Set[str] = {
# #         "a", "an", "the", "is", "are", "was", "were", "be",
# #         "been", "being", "have", "has", "had", "do", "does",
# #         "did", "will", "would", "could", "should", "may",
# #         "might", "shall", "can", "need", "dare", "ought",
# #         "used", "to", "of", "in", "for", "on", "with", "at",
# #         "by", "from", "as", "into", "through", "during",
# #         "before", "after", "above", "below", "between",
# #         "and", "but", "or", "not", "no", "nor", "so", "yet",
# #         "it", "its", "this", "that", "these", "those",
# #         "i", "me", "my", "we", "our", "you", "your",
# #         "he", "him", "his", "she", "her", "they", "them",
# #         "image", "photo", "picture", "showing", "featuring",
# #         "with", "very", "really", "quite", "just",
# #     }
    
# #     words_a = {
# #         w.lower().strip(".,!?;:'\"()[]{}") 
# #         for w in text_a.split() 
# #         if len(w) > 1
# #     } - stop_words
    
# #     words_b = {
# #         w.lower().strip(".,!?;:'\"()[]{}") 
# #         for w in text_b.split() 
# #         if len(w) > 1
# #     } - stop_words
    
# #     if not words_a or not words_b:
# #         return 0.0
    
# #     intersection = words_a & words_b
# #     union = words_a | words_b
    
# #     # Weighted: how much of the QUERY appears in the CAPTION
# #     query_coverage = len(intersection) / len(words_a) if words_a else 0
# #     jaccard = len(intersection) / len(union) if union else 0
    
# #     # Blend: 70% query coverage + 30% jaccard
# #     return 0.7 * query_coverage + 0.3 * jaccard


# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # #  IMAGE VERIFIER
# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # class ImageVerifier:
# #     """
# #     Singleton that loads CLIP and BLIP models once,
# #     then verifies images against text queries.
    
# #     Thread-safe: uses locks around model inference.
    
# #     Usage:
# #         verifier = ImageVerifier(cfg)
# #         result = verifier.verify(image, "red nike shoes")
# #         if result.accepted:
# #             # use image
# #         else:
# #             # try next candidate
# #     """
    
# #     _instance: Optional["ImageVerifier"] = None
# #     _init_lock = threading.Lock()
    
# #     def __new__(cls, cfg: VerificationConfig):
# #         """Singleton: one instance shared across all threads."""
# #         with cls._init_lock:
# #             if cls._instance is None:
# #                 cls._instance = super().__new__(cls)
# #                 cls._instance._initialized = False
# #             return cls._instance
    
# #     def __init__(self, cfg: VerificationConfig) -> None:
# #         if self._initialized:
# #             return
        
# #         self.cfg = cfg
# #         self._clip_model = None
# #         self._clip_processor = None
# #         self._blip_model = None
# #         self._blip_processor = None
# #         self._device = None
# #         self._clip_lock = threading.Lock()
# #         self._blip_lock = threading.Lock()
# #         self._load_count = 0
        
# #         self._setup_device()
# #         self._load_models()
# #         self._initialized = True
    
# #     # ── device setup ────────────────────────────────────────
# #     def _setup_device(self) -> None:
# #         """Determine compute device."""
# #         import torch
        
# #         if self.cfg.device == "auto":
# #             if torch.cuda.is_available():
# #                 self._device = "cuda"
# #                 gpu_name = torch.cuda.get_device_name(0)
# #                 gpu_mem = torch.cuda.get_device_properties(0).total_mem / 1e9
# #                 log.info("Using GPU: %s (%.1f GB)", gpu_name, gpu_mem)
# #             else:
# #                 self._device = "cpu"
# #                 log.info("Using CPU (no GPU detected)")
# #         else:
# #             self._device = self.cfg.device
# #             log.info("Using device: %s", self._device)
    
# #     # ── model loading ───────────────────────────────────────
# #     def _load_models(self) -> None:
# #         """Load CLIP and/or BLIP models."""
        
# #         if self.cfg.use_clip:
# #             self._load_clip()
        
# #         if self.cfg.use_blip:
# #             self._load_blip()
    
# #     def _load_clip(self) -> None:
# #         """Load CLIP model and processor."""
# #         try:
# #             from transformers import CLIPProcessor, CLIPModel
            
# #             log.info("Loading CLIP model: %s ...", self.cfg.clip_model)
# #             t0 = time.monotonic()
            
# #             self._clip_processor = CLIPProcessor.from_pretrained(
# #                 self.cfg.clip_model
# #             )
# #             self._clip_model = CLIPModel.from_pretrained(
# #                 self.cfg.clip_model
# #             ).to(self._device)
# #             self._clip_model.eval()
            
# #             elapsed = time.monotonic() - t0
# #             log.info("CLIP loaded in %.1fs on %s", elapsed, self._device)
            
# #         except ImportError:
# #             log.error("transformers not installed! Run: pip install transformers torch")
# #             self.cfg = self.cfg.__class__(
# #                 **{**self.cfg.__dict__, "use_clip": False}
# #             )
# #         except Exception as exc:
# #             log.error("Failed to load CLIP: %s", exc)
    
# #     def _load_blip(self) -> None:
# #         """Load BLIP model and processor."""
# #         try:
# #             from transformers import BlipProcessor, BlipForConditionalGeneration
            
# #             log.info("Loading BLIP model: %s ...", self.cfg.blip_model)
# #             t0 = time.monotonic()
            
# #             self._blip_processor = BlipProcessor.from_pretrained(
# #                 self.cfg.blip_model
# #             )
# #             self._blip_model = BlipForConditionalGeneration.from_pretrained(
# #                 self.cfg.blip_model
# #             ).to(self._device)
# #             self._blip_model.eval()
            
# #             elapsed = time.monotonic() - t0
# #             log.info("BLIP loaded in %.1fs on %s", elapsed, self._device)
            
# #         except ImportError:
# #             log.error("transformers not installed! Run: pip install transformers torch")
# #         except Exception as exc:
# #             log.error("Failed to load BLIP: %s", exc)
    
# #     # ── CLIP scoring ────────────────────────────────────────
# #     def _clip_score(self, image: Image.Image, query: str) -> float:
# #         """
# #         Compute CLIP cosine similarity between image and text.
# #         Returns 0.0–1.0
# #         """
# #         if self._clip_model is None or self._clip_processor is None:
# #             return 0.0
        
# #         try:
# #             import torch
            
# #             with self._clip_lock:
# #                 # Prepare inputs
# #                 inputs = self._clip_processor(
# #                     text=[query],
# #                     images=image,
# #                     return_tensors="pt",
# #                     padding=True,
# #                     truncation=True,
# #                     max_length=77,
# #                 )
# #                 inputs = {k: v.to(self._device) for k, v in inputs.items()}
                
# #                 # Forward pass
# #                 with torch.no_grad():
# #                     outputs = self._clip_model(**inputs)
                
# #                 # Cosine similarity (already normalized in CLIP)
# #                 logits = outputs.logits_per_image
                
# #                 # Convert to 0–1 range
# #                 # CLIP logits are typically in range 15–35
# #                 # Normalize: (logit / 100) gives ~0.15–0.35
# #                 score = logits.item() / 100.0
                
# #                 return max(0.0, min(1.0, score))
        
# #         except Exception as exc:
# #             log.warning("CLIP scoring failed: %s", exc)
# #             return 0.0
    
# #     # ── BLIP captioning ─────────────────────────────────────
# #     def _blip_caption(self, image: Image.Image) -> str:
# #         """
# #         Generate image caption using BLIP.
# #         Returns caption string.
# #         """
# #         if self._blip_model is None or self._blip_processor is None:
# #             return ""
        
# #         try:
# #             import torch
            
# #             with self._blip_lock:
# #                 inputs = self._blip_processor(
# #                     images=image,
# #                     return_tensors="pt",
# #                 )
# #                 inputs = {k: v.to(self._device) for k, v in inputs.items()}
                
# #                 with torch.no_grad():
# #                     output_ids = self._blip_model.generate(
# #                         **inputs,
# #                         max_new_tokens=50,
# #                         num_beams=3,
# #                     )
                
# #                 caption = self._blip_processor.decode(
# #                     output_ids[0],
# #                     skip_special_tokens=True,
# #                 )
                
# #                 return caption.strip()
        
# #         except Exception as exc:
# #             log.warning("BLIP captioning failed: %s", exc)
# #             return ""
    
# #     def _blip_score(self, image: Image.Image, query: str) -> Tuple[float, str]:
# #         """
# #         Generate caption with BLIP, then compute word overlap with query.
# #         Returns (score, caption).
# #         """
# #         caption = self._blip_caption(image)
# #         if not caption:
# #             return 0.0, ""
        
# #         score = _word_overlap_score(query, caption)
# #         return score, caption
    
# #     # ── main verification ───────────────────────────────────
# #     def verify(self, image: Image.Image, query: str) -> VerificationResult:
# #         """
# #         Verify if an image matches the given text query.
        
# #         Uses CLIP and/or BLIP depending on configuration.
# #         Returns VerificationResult with accept/reject decision.
        
# #         Args:
# #             image: PIL Image to verify
# #             query: Search query text
            
# #         Returns:
# #             VerificationResult with scores and decision
# #         """
# #         cfg = self.cfg
# #         result = VerificationResult(accepted=False)
        
# #         # Ensure image is RGB
# #         if image.mode != "RGB":
# #             image = image.convert("RGB")
        
# #         # Resize for faster inference (models don't need full resolution)
# #         verify_image = image.copy()
# #         verify_image.thumbnail((384, 384), Image.Resampling.LANCZOS)
        
# #         scores: Dict[str, float] = {}
        
# #         # ── CLIP ──
# #         if cfg.use_clip and self._clip_model is not None:
# #             t0 = time.monotonic()
# #             result.clip_score = self._clip_score(verify_image, query)
# #             scores["clip"] = result.clip_score
# #             log.debug(
# #                 "CLIP score: %.3f (%.0fms)",
# #                 result.clip_score,
# #                 (time.monotonic() - t0) * 1000,
# #             )
            
# #             # Quick decision if CLIP is very confident
# #             if result.clip_score >= cfg.clip_accept_threshold:
# #                 result.accepted = True
# #                 result.reason = "clip_high"
# #                 result.combined_score = result.clip_score
# #                 log.info("CLIP auto-accept: %.3f", result.clip_score)
# #                 return result
            
# #             if result.clip_score < cfg.clip_reject_threshold:
# #                 result.reason = "clip_low"
# #                 result.combined_score = result.clip_score
# #                 log.info("CLIP auto-reject: %.3f", result.clip_score)
# #                 return result
        
# #         # ── BLIP ──
# #         if cfg.use_blip and self._blip_model is not None:
# #             t0 = time.monotonic()
# #             result.blip_score, result.blip_caption = self._blip_score(
# #                 verify_image, query,
# #             )
# #             scores["blip"] = result.blip_score
# #             log.debug(
# #                 "BLIP score: %.3f caption='%s' (%.0fms)",
# #                 result.blip_score,
# #                 result.blip_caption[:40],
# #                 (time.monotonic() - t0) * 1000,
# #             )
        
# #         # ── Combined score ──
# #         if scores:
# #             total_weight = 0.0
# #             weighted_sum = 0.0
            
# #             if "clip" in scores:
# #                 weighted_sum += scores["clip"] * cfg.clip_weight
# #                 total_weight += cfg.clip_weight
            
# #             if "blip" in scores:
# #                 weighted_sum += scores["blip"] * cfg.blip_weight
# #                 total_weight += cfg.blip_weight
            
# #             result.combined_score = weighted_sum / total_weight if total_weight > 0 else 0
            
# #             # Decision
# #             if result.combined_score >= cfg.combined_accept:
# #                 result.accepted = True
# #                 result.reason = "combined_pass"
# #             else:
# #                 result.reason = "combined_fail"
            
# #             log.info(
# #                 "Verify: %s (combined=%.3f, clip=%.3f, blip=%.3f, caption='%s')",
# #                 "✅" if result.accepted else "❌",
# #                 result.combined_score,
# #                 result.clip_score,
# #                 result.blip_score,
# #                 result.blip_caption[:30],
# #             )
# #         else:
# #             # No models available — fallback
# #             if cfg.accept_on_model_failure:
# #                 result.accepted = True
# #                 result.reason = "no_models_fallback"
# #                 log.warning("No verification models — accepting by default")
# #             else:
# #                 result.reason = "no_models_reject"
        
# #         del verify_image
# #         return result
    
# #     @property
# #     def is_available(self) -> bool:
# #         """Check if at least one model is loaded."""
# #         return (self._clip_model is not None) or (self._blip_model is not None)
    
# #     def stats(self) -> Dict:
# #         """Return model status info."""
# #         return {
# #             "clip_loaded": self._clip_model is not None,
# #             "blip_loaded": self._blip_model is not None,
# #             "device": self._device,
# #         }

# """
# CLIP + BLIP image-text cross-verification.

# Models are downloaded and cached in ./data/models/ (not ~/.cache/).
# """

# from __future__ import annotations

# import os
# import threading
# import time
# from dataclasses import dataclass
# from pathlib import Path
# from typing import Any, Dict, Optional, Set, Tuple

# from PIL import Image

# from config.settings import VerificationConfig
# from utils.log_config import get_logger

# log = get_logger(__name__)

# # Lazy imports
# _torch = None
# _CLIPProcessor = None
# _CLIPModel = None
# _BlipProcessor = None
# _BlipForConditionalGeneration = None


# def _import_deps() -> bool:
#     """Import torch + transformers. Returns True if successful."""
#     global _torch, _CLIPProcessor, _CLIPModel
#     global _BlipProcessor, _BlipForConditionalGeneration

#     try:
#         import torch as t
#         _torch = t
#     except ImportError:
#         log.error(
#             "PyTorch not installed!\n"
#             "  CPU:  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu\n"
#             "  GPU:  pip install torch torchvision"
#         )
#         return False

#     try:
#         from transformers import (
#             CLIPProcessor,
#             CLIPModel,
#             BlipProcessor,
#             BlipForConditionalGeneration,
#         )
#         _CLIPProcessor = CLIPProcessor
#         _CLIPModel = CLIPModel
#         _BlipProcessor = BlipProcessor
#         _BlipForConditionalGeneration = BlipForConditionalGeneration
#         return True
#     except ImportError as exc:
#         log.error("transformers not installed: %s\n  Run: pip install transformers", exc)
#         return False


# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# #  RESULT
# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# @dataclass
# class VerificationResult:
#     accepted:       bool
#     clip_score:     float = 0.0
#     blip_score:     float = 0.0
#     combined_score: float = 0.0
#     blip_caption:   str   = ""
#     reason:         str   = ""

#     def summary(self) -> str:
#         status = "✅ ACCEPT" if self.accepted else "❌ REJECT"
#         parts = [f"{status} (combined={self.combined_score:.3f}"]
#         if self.clip_score > 0:
#             parts.append(f"clip={self.clip_score:.3f}")
#         if self.blip_score > 0:
#             parts.append(f"blip={self.blip_score:.3f}")
#         if self.blip_caption:
#             parts.append(f"caption='{self.blip_caption[:50]}'")
#         parts.append(f"reason='{self.reason}'")
#         return " | ".join(parts) + ")"


# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# #  TEXT SIMILARITY
# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# _STOP_WORDS: Set[str] = {
#     "a", "an", "the", "is", "are", "was", "were", "be", "been",
#     "being", "have", "has", "had", "do", "does", "did", "will",
#     "would", "could", "should", "may", "might", "shall", "can",
#     "to", "of", "in", "for", "on", "with", "at", "by", "from",
#     "as", "into", "through", "during", "before", "after", "above",
#     "below", "between", "and", "but", "or", "not", "no", "so",
#     "it", "its", "this", "that", "these", "those", "i", "me",
#     "my", "we", "our", "you", "your", "he", "him", "his", "she",
#     "her", "they", "them", "image", "photo", "picture", "showing",
#     "featuring", "very", "really", "quite", "just",
# }


# def _word_overlap(query: str, caption: str) -> float:
#     def _extract(text: str) -> Set[str]:
#         return {
#             w.lower().strip(".,!?;:'\"()[]{}") for w in text.split() if len(w) > 1
#         } - _STOP_WORDS

#     wq = _extract(query)
#     wc = _extract(caption)
#     if not wq or not wc:
#         return 0.0
#     inter = wq & wc
#     coverage = len(inter) / len(wq)
#     jaccard = len(inter) / len(wq | wc)
#     return 0.7 * coverage + 0.3 * jaccard


# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# #  VERIFIER
# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# class ImageVerifier:
#     """
#     Singleton — loads CLIP + BLIP once into ./data/models/.
#     Thread-safe via locks around inference.
#     """

#     _instance: Optional["ImageVerifier"] = None
#     _creation_lock = threading.Lock()

#     def __new__(cls, cfg: VerificationConfig, models_dir: Optional[Path] = None) -> "ImageVerifier":
#         with cls._creation_lock:
#             if cls._instance is None:
#                 obj = super().__new__(cls)
#                 obj._initialized = False
#                 cls._instance = obj
#             return cls._instance

#     def __init__(self, cfg: VerificationConfig, models_dir: Optional[Path] = None) -> None:
#         if self._initialized:
#             return

#         self.cfg = cfg
#         self._models_dir = models_dir
#         self._clip_model: Any = None
#         self._clip_processor: Any = None
#         self._blip_model: Any = None
#         self._blip_processor: Any = None
#         self._device: str = "cpu"
#         self._clip_lock = threading.Lock()
#         self._blip_lock = threading.Lock()
#         self._deps_ok = False

#         # Ensure models directory exists
#         if self._models_dir:
#             self._models_dir.mkdir(parents=True, exist_ok=True)
#             log.info("Models directory: %s", self._models_dir)

#         # Import dependencies
#         self._deps_ok = _import_deps()

#         if self._deps_ok:
#             # Set HuggingFace cache to our models directory
#             self._set_cache_dir()
#             self._setup_device()
#             self._load_models()

#         self._initialized = True

#     # ── force HuggingFace to use our directory ──────────────
#     def _set_cache_dir(self) -> None:
#         """
#         Override HuggingFace's default cache to ./data/models/.
        
#         Without this, models go to:
#           Windows: C:\\Users\\<user>\\.cache\\huggingface\\
#           Linux:   ~/.cache/huggingface/
        
#         With this, models go to:
#           ./data/models/clip/
#           ./data/models/blip/
#         """
#         if self._models_dir:
#             cache_str = str(self._models_dir)
            
#             # Set ALL HuggingFace cache environment variables
#             os.environ["TRANSFORMERS_CACHE"] = cache_str
#             os.environ["HF_HOME"] = cache_str
#             os.environ["HF_HUB_CACHE"] = cache_str
#             os.environ["HUGGINGFACE_HUB_CACHE"] = cache_str
            
#             log.info("HuggingFace cache → %s", cache_str)

#     # ── device ──────────────────────────────────────────────
#     def _setup_device(self) -> None:
#         if self.cfg.device == "auto":
#             self._device = "cuda" if _torch.cuda.is_available() else "cpu"
#         else:
#             self._device = self.cfg.device

#         if self._device == "cuda":
#             name = _torch.cuda.get_device_name(0)
#             mem = _torch.cuda.get_device_properties(0).total_mem / 1e9
#             log.info("GPU: %s (%.1f GB)", name, mem)
#         else:
#             log.info("Device: CPU")

#     # ── model loading ───────────────────────────────────────
#     def _load_models(self) -> None:
#         if self.cfg.use_clip:
#             self._load_clip()
#         if self.cfg.use_blip:
#             self._load_blip()

#     def _get_local_path(self, model_name: str, subfolder: str) -> Tuple[str, Optional[str]]:
#         """
#         Check if model exists locally. If yes, return local path.
#         If no, return HuggingFace name + cache_dir for download.
        
#         Directory structure:
#             ./data/models/
#                 clip/
#                     openai--clip-vit-base-patch32/
#                         config.json
#                         model.safetensors
#                         ...
#                 blip/
#                     Salesforce--blip-image-captioning-base/
#                         config.json
#                         ...
#         """
#         if not self._models_dir:
#             return model_name, None

#         # Create subfolder
#         sub_dir = self._models_dir / subfolder
#         sub_dir.mkdir(parents=True, exist_ok=True)

#         # Check if already downloaded locally
#         local_name = model_name.replace("/", "--")
#         local_path = sub_dir / local_name

#         if local_path.exists() and any(local_path.iterdir()):
#             # Model exists locally
#             log.info("Found local model: %s", local_path)
#             return str(local_path), None
#         else:
#             # Will download to this directory
#             log.info("Model will download to: %s", sub_dir)
#             return model_name, str(sub_dir)

#     def _load_clip(self) -> None:
#         model_name = self.cfg.clip_model
#         log.info("Loading CLIP: %s", model_name)
#         t0 = time.monotonic()

#         try:
#             source, cache_dir = self._get_local_path(model_name, "clip")

#             log.info("CLIP source: %s (cache: %s)", source, cache_dir or "local")

#             self._clip_processor = _CLIPProcessor.from_pretrained(
#                 source,
#                 cache_dir=cache_dir,
#             )
#             self._clip_model = _CLIPModel.from_pretrained(
#                 source,
#                 cache_dir=cache_dir,
#             ).to(self._device)
#             self._clip_model.eval()

#             # Save locally for next run (if downloaded from HuggingFace)
#             if cache_dir and self._models_dir:
#                 self._save_model_locally(
#                     self._clip_processor, self._clip_model,
#                     model_name, "clip",
#                 )

#             elapsed = time.monotonic() - t0
#             log.info("✅ CLIP loaded in %.1fs on %s", elapsed, self._device)

#             # Log model size
#             self._log_model_size("clip")

#         except Exception as exc:
#             log.error("❌ CLIP failed: %s", exc, exc_info=True)
#             self._clip_model = None
#             self._clip_processor = None

#     def _load_blip(self) -> None:
#         model_name = self.cfg.blip_model
#         log.info("Loading BLIP: %s", model_name)
#         t0 = time.monotonic()

#         try:
#             source, cache_dir = self._get_local_path(model_name, "blip")

#             log.info("BLIP source: %s (cache: %s)", source, cache_dir or "local")

#             self._blip_processor = _BlipProcessor.from_pretrained(
#                 source,
#                 cache_dir=cache_dir,
#             )
#             self._blip_model = _BlipForConditionalGeneration.from_pretrained(
#                 source,
#                 cache_dir=cache_dir,
#             ).to(self._device)
#             self._blip_model.eval()

#             # Save locally
#             if cache_dir and self._models_dir:
#                 self._save_model_locally(
#                     self._blip_processor, self._blip_model,
#                     model_name, "blip",
#                 )

#             elapsed = time.monotonic() - t0
#             log.info("✅ BLIP loaded in %.1fs on %s", elapsed, self._device)

#             self._log_model_size("blip")

#         except Exception as exc:
#             log.error("❌ BLIP failed: %s", exc, exc_info=True)
#             self._blip_model = None
#             self._blip_processor = None

#     def _save_model_locally(self, processor, model, model_name: str, subfolder: str) -> None:
#         """Save downloaded model to local directory for offline use."""
#         if not self._models_dir:
#             return

#         local_name = model_name.replace("/", "--")
#         save_path = self._models_dir / subfolder / local_name

#         try:
#             save_path.mkdir(parents=True, exist_ok=True)

#             # Check if already saved
#             if (save_path / "config.json").exists():
#                 log.debug("Model already saved locally: %s", save_path)
#                 return

#             log.info("Saving model locally: %s", save_path)
#             processor.save_pretrained(str(save_path))
#             model.save_pretrained(str(save_path))
#             log.info("✅ Model saved: %s", save_path)

#         except Exception as exc:
#             log.warning("Could not save model locally: %s", exc)

#     def _log_model_size(self, subfolder: str) -> None:
#         """Log the disk size of downloaded model."""
#         if not self._models_dir:
#             return

#         model_dir = self._models_dir / subfolder
#         if not model_dir.exists():
#             return

#         total_bytes = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
#         size_mb = total_bytes / (1024 * 1024)
#         log.info("Model disk size (%s): %.1f MB", subfolder, size_mb)

#     # ── CLIP score ──────────────────────────────────────────
#     def _clip_score(self, image: Image.Image, query: str) -> float:
#         if self._clip_model is None:
#             return 0.0
#         try:
#             with self._clip_lock:
#                 inputs = self._clip_processor(
#                     text=[query], images=image,
#                     return_tensors="pt", padding=True,
#                     truncation=True, max_length=77,
#                 )
#                 inputs = {k: v.to(self._device) for k, v in inputs.items()}
#                 with _torch.no_grad():
#                     outputs = self._clip_model(**inputs)
#                 score = outputs.logits_per_image.item() / 100.0
#                 return max(0.0, min(1.0, score))
#         except Exception as exc:
#             log.warning("CLIP error: %s", exc)
#             return 0.0

#     # ── BLIP caption ────────────────────────────────────────
#     def _blip_caption(self, image: Image.Image) -> str:
#         if self._blip_model is None:
#             return ""
#         try:
#             with self._blip_lock:
#                 inputs = self._blip_processor(images=image, return_tensors="pt")
#                 inputs = {k: v.to(self._device) for k, v in inputs.items()}
#                 with _torch.no_grad():
#                     ids = self._blip_model.generate(
#                         **inputs, max_new_tokens=50, num_beams=3,
#                     )
#                 return self._blip_processor.decode(ids[0], skip_special_tokens=True).strip()
#         except Exception as exc:
#             log.warning("BLIP error: %s", exc)
#             return ""

#     def _blip_score(self, image: Image.Image, query: str) -> Tuple[float, str]:
#         caption = self._blip_caption(image)
#         if not caption:
#             return 0.0, ""
#         return _word_overlap(query, caption), caption

#     # ── main verify ─────────────────────────────────────────
#     def verify(self, image: Image.Image, query: str) -> VerificationResult:
#         cfg = self.cfg
#         result = VerificationResult(accepted=False)

#         if not self.is_available:
#             if cfg.accept_on_model_failure:
#                 result.accepted = True
#                 result.reason = "no_models_fallback"
#             else:
#                 result.reason = "no_models_reject"
#             return result

#         img = image.convert("RGB")
#         img.thumbnail((384, 384), Image.Resampling.LANCZOS)

#         scores: Dict[str, float] = {}

#         # CLIP
#         if cfg.use_clip and self._clip_model is not None:
#             t0 = time.monotonic()
#             result.clip_score = self._clip_score(img, query)
#             scores["clip"] = result.clip_score
#             log.debug("CLIP: %.3f (%.0fms)", result.clip_score, (time.monotonic() - t0) * 1000)

#             if result.clip_score >= cfg.clip_accept_threshold:
#                 result.accepted = True
#                 result.combined_score = result.clip_score
#                 result.reason = "clip_high"
#                 return result
#             if result.clip_score < cfg.clip_reject_threshold:
#                 result.combined_score = result.clip_score
#                 result.reason = "clip_low"
#                 return result

#         # BLIP
#         if cfg.use_blip and self._blip_model is not None:
#             t0 = time.monotonic()
#             result.blip_score, result.blip_caption = self._blip_score(img, query)
#             scores["blip"] = result.blip_score
#             log.debug("BLIP: %.3f '%s' (%.0fms)", result.blip_score, result.blip_caption[:40], (time.monotonic() - t0) * 1000)

#         # Combined
#         if scores:
#             ws, wt = 0.0, 0.0
#             if "clip" in scores:
#                 ws += scores["clip"] * cfg.clip_weight
#                 wt += cfg.clip_weight
#             if "blip" in scores:
#                 ws += scores["blip"] * cfg.blip_weight
#                 wt += cfg.blip_weight
#             result.combined_score = ws / wt if wt > 0 else 0.0
#             result.accepted = result.combined_score >= cfg.combined_accept
#             result.reason = "combined_pass" if result.accepted else "combined_fail"

#             log.info(
#                 "Verify: %s combined=%.3f clip=%.3f blip=%.3f caption='%s'",
#                 "✅" if result.accepted else "❌",
#                 result.combined_score, result.clip_score,
#                 result.blip_score, result.blip_caption[:40],
#             )
#         else:
#             if cfg.accept_on_model_failure:
#                 result.accepted = True
#                 result.reason = "no_scores_fallback"

#         del img
#         return result

#     @property
#     def is_available(self) -> bool:
#         return (self._clip_model is not None) or (self._blip_model is not None)

#     def stats(self) -> Dict[str, Any]:
#         return {
#             "deps_installed": self._deps_ok,
#             "clip_loaded": self._clip_model is not None,
#             "blip_loaded": self._blip_model is not None,
#             "device": self._device,
#             "models_dir": str(self._models_dir) if self._models_dir else "default_cache",
#             "clip_model": self.cfg.clip_model if self._clip_model else "NOT LOADED",
#             "blip_model": self.cfg.blip_model if self._blip_model else "NOT LOADED",
#         }
"""
CLIP + BLIP image-text cross-verification.

Two stages:
    Stage 1 (verify):           Download check — strict thresholds
    Stage 2 (verify_composed):  Post-compose check — relaxed thresholds
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from PIL import Image

from config.settings import VerificationConfig
from utils.log_config import get_logger

log = get_logger(__name__)

_torch = None
_CLIPProcessor = None
_CLIPModel = None
_BlipProcessor = None
_BlipForConditionalGeneration = None


def _import_deps() -> bool:
    global _torch, _CLIPProcessor, _CLIPModel
    global _BlipProcessor, _BlipForConditionalGeneration
    try:
        import torch as t
        _torch = t
    except ImportError:
        log.error("PyTorch not installed! pip install torch")
        return False
    try:
        from transformers import (
            CLIPProcessor, CLIPModel,
            BlipProcessor, BlipForConditionalGeneration,
        )
        _CLIPProcessor = CLIPProcessor
        _CLIPModel = CLIPModel
        _BlipProcessor = BlipProcessor
        _BlipForConditionalGeneration = BlipForConditionalGeneration
        return True
    except ImportError as exc:
        log.error("transformers not installed: %s", exc)
        return False


_STOP_WORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "and", "but", "or", "not", "no", "so",
    "it", "its", "this", "that", "these", "those", "i", "me",
    "my", "we", "our", "you", "your", "he", "him", "his", "she",
    "her", "they", "them", "image", "photo", "picture", "showing",
    "featuring", "very", "really", "quite", "just",
}


def _word_overlap(query: str, caption: str) -> float:
    def _extract(text: str) -> Set[str]:
        return {
            w.lower().strip(".,!?;:'\"()[]{}") for w in text.split() if len(w) > 1
        } - _STOP_WORDS
    wq = _extract(query)
    wc = _extract(caption)
    if not wq or not wc:
        return 0.0
    inter = wq & wc
    coverage = len(inter) / len(wq)
    jaccard = len(inter) / len(wq | wc)
    return 0.7 * coverage + 0.3 * jaccard


@dataclass
class VerificationResult:
    accepted:       bool
    clip_score:     float = 0.0
    blip_score:     float = 0.0
    combined_score: float = 0.0
    blip_caption:   str   = ""
    reason:         str   = ""
    stage:          str   = "download"   # "download" or "compose"

    def summary(self) -> str:
        status = "✅ ACCEPT" if self.accepted else "❌ REJECT"
        tag = f"[{self.stage.upper()}]"
        parts = [f"{tag} {status} (combined={self.combined_score:.3f}"]
        if self.clip_score > 0:
            parts.append(f"clip={self.clip_score:.3f}")
        if self.blip_score > 0:
            parts.append(f"blip={self.blip_score:.3f}")
        if self.blip_caption:
            parts.append(f"caption='{self.blip_caption[:50]}'")
        parts.append(f"reason='{self.reason}'")
        return " | ".join(parts) + ")"


class ImageVerifier:
    """
    Singleton — CLIP + BLIP loaded once.
    
    Two verification methods:
        verify()          — Stage 1: Download check (strict)
        verify_composed() — Stage 2: Post-compose check (relaxed)
    """

    _instance: Optional["ImageVerifier"] = None
    _creation_lock = threading.Lock()

    def __new__(cls, cfg: VerificationConfig, models_dir: Optional[Path] = None) -> "ImageVerifier":
        with cls._creation_lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._initialized = False
                cls._instance = obj
            return cls._instance

    def __init__(self, cfg: VerificationConfig, models_dir: Optional[Path] = None) -> None:
        if self._initialized:
            return
        self.cfg = cfg
        self._models_dir = models_dir
        self._clip_model: Any = None
        self._clip_processor: Any = None
        self._blip_model: Any = None
        self._blip_processor: Any = None
        self._device: str = "cpu"
        self._clip_lock = threading.Lock()
        self._blip_lock = threading.Lock()
        self._deps_ok = False

        if self._models_dir:
            self._models_dir.mkdir(parents=True, exist_ok=True)

        self._deps_ok = _import_deps()
        if self._deps_ok:
            self._set_cache_dir()
            self._setup_device()
            self._load_models()
        self._initialized = True

    def _set_cache_dir(self) -> None:
        if self._models_dir:
            cache_str = str(self._models_dir)
            os.environ["TRANSFORMERS_CACHE"] = cache_str
            os.environ["HF_HOME"] = cache_str
            os.environ["HF_HUB_CACHE"] = cache_str

    def _setup_device(self) -> None:
        if self.cfg.device == "auto":
            self._device = "cuda" if _torch.cuda.is_available() else "cpu"
        else:
            self._device = self.cfg.device
        log.info("Verifier device: %s", self._device)

    def _load_models(self) -> None:
        if self.cfg.use_clip:
            self._load_clip()
        if self.cfg.use_blip:
            self._load_blip()

    def _get_local_path(self, model_name: str, subfolder: str) -> Tuple[str, Optional[str]]:
        if not self._models_dir:
            return model_name, None
        sub_dir = self._models_dir / subfolder
        sub_dir.mkdir(parents=True, exist_ok=True)
        local_name = model_name.replace("/", "--")
        local_path = sub_dir / local_name
        if local_path.exists() and any(local_path.iterdir()):
            return str(local_path), None
        return model_name, str(sub_dir)

    def _load_clip(self) -> None:
        model_name = self.cfg.clip_model
        log.info("Loading CLIP: %s", model_name)
        t0 = time.monotonic()
        try:
            source, cache_dir = self._get_local_path(model_name, "clip")
            self._clip_processor = _CLIPProcessor.from_pretrained(source, cache_dir=cache_dir)
            self._clip_model = _CLIPModel.from_pretrained(source, cache_dir=cache_dir).to(self._device)
            self._clip_model.eval()
            if cache_dir and self._models_dir:
                self._save_local(self._clip_processor, self._clip_model, model_name, "clip")
            log.info("✅ CLIP loaded in %.1fs", time.monotonic() - t0)
        except Exception as exc:
            log.error("❌ CLIP failed: %s", exc, exc_info=True)
            self._clip_model = None

    def _load_blip(self) -> None:
        model_name = self.cfg.blip_model
        log.info("Loading BLIP: %s", model_name)
        t0 = time.monotonic()
        try:
            source, cache_dir = self._get_local_path(model_name, "blip")
            self._blip_processor = _BlipProcessor.from_pretrained(source, cache_dir=cache_dir)
            self._blip_model = _BlipForConditionalGeneration.from_pretrained(
                source, cache_dir=cache_dir
            ).to(self._device)
            self._blip_model.eval()
            if cache_dir and self._models_dir:
                self._save_local(self._blip_processor, self._blip_model, model_name, "blip")
            log.info("✅ BLIP loaded in %.1fs", time.monotonic() - t0)
        except Exception as exc:
            log.error("❌ BLIP failed: %s", exc, exc_info=True)
            self._blip_model = None

    def _save_local(self, processor, model, model_name: str, subfolder: str) -> None:
        if not self._models_dir:
            return
        local_name = model_name.replace("/", "--")
        save_path = self._models_dir / subfolder / local_name
        try:
            save_path.mkdir(parents=True, exist_ok=True)
            if not (save_path / "config.json").exists():
                processor.save_pretrained(str(save_path))
                model.save_pretrained(str(save_path))
        except Exception as exc:
            log.warning("Could not save model: %s", exc)

    # ── Core scoring methods ────────────────────────────────

    def _clip_score(self, image: Image.Image, query: str) -> float:
        if self._clip_model is None:
            return 0.0
        try:
            with self._clip_lock:
                inputs = self._clip_processor(
                    text=[query], images=image,
                    return_tensors="pt", padding=True,
                    truncation=True, max_length=77,
                )
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
                with _torch.no_grad():
                    outputs = self._clip_model(**inputs)
                return max(0.0, min(1.0, outputs.logits_per_image.item() / 100.0))
        except Exception as exc:
            log.warning("CLIP error: %s", exc)
            return 0.0

    def _blip_caption(self, image: Image.Image) -> str:
        if self._blip_model is None:
            return ""
        try:
            with self._blip_lock:
                inputs = self._blip_processor(images=image, return_tensors="pt")
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
                with _torch.no_grad():
                    ids = self._blip_model.generate(**inputs, max_new_tokens=50, num_beams=3)
                return self._blip_processor.decode(ids[0], skip_special_tokens=True).strip()
        except Exception as exc:
            log.warning("BLIP error: %s", exc)
            return ""

    def _blip_score(self, image: Image.Image, query: str) -> Tuple[float, str]:
        caption = self._blip_caption(image)
        if not caption:
            return 0.0, ""
        return _word_overlap(query, caption), caption

    # ── Generic verify with custom thresholds ───────────────

    def _verify_with_thresholds(
        self,
        image: Image.Image,
        query: str,
        clip_accept: float,
        clip_reject: float,
        blip_accept: float,
        blip_reject: float,
        combined_accept: float,
        combined_reject: float,
        stage: str,
    ) -> VerificationResult:
        """
        Internal: run CLIP + BLIP with given thresholds.
        Used by both verify() and verify_composed().
        """
        cfg = self.cfg
        result = VerificationResult(accepted=False, stage=stage)

        if not self.is_available:
            if cfg.accept_on_model_failure:
                result.accepted = True
                result.reason = "no_models_fallback"
            else:
                result.reason = "no_models_reject"
            return result

        img = image.convert("RGB")
        img.thumbnail((384, 384), Image.Resampling.LANCZOS)

        scores: Dict[str, float] = {}

        # CLIP
        if cfg.use_clip and self._clip_model is not None:
            t0 = time.monotonic()
            result.clip_score = self._clip_score(img, query)
            scores["clip"] = result.clip_score
            log.debug(
                "[%s] CLIP: %.3f (%.0fms)",
                stage, result.clip_score, (time.monotonic() - t0) * 1000,
            )

            if result.clip_score >= clip_accept:
                result.accepted = True
                result.combined_score = result.clip_score
                result.reason = f"{stage}_clip_high"
                log.info("[%s] CLIP auto-accept: %.3f", stage, result.clip_score)
                return result

            if result.clip_score < clip_reject:
                result.combined_score = result.clip_score
                result.reason = f"{stage}_clip_low"
                log.info("[%s] CLIP auto-reject: %.3f", stage, result.clip_score)
                return result

        # BLIP
        if cfg.use_blip and self._blip_model is not None:
            t0 = time.monotonic()
            result.blip_score, result.blip_caption = self._blip_score(img, query)
            scores["blip"] = result.blip_score
            log.debug(
                "[%s] BLIP: %.3f '%s' (%.0fms)",
                stage, result.blip_score, result.blip_caption[:40],
                (time.monotonic() - t0) * 1000,
            )

        # Combined
        if scores:
            ws, wt = 0.0, 0.0
            if "clip" in scores:
                ws += scores["clip"] * cfg.clip_weight
                wt += cfg.clip_weight
            if "blip" in scores:
                ws += scores["blip"] * cfg.blip_weight
                wt += cfg.blip_weight
            result.combined_score = ws / wt if wt > 0 else 0.0

            result.accepted = result.combined_score >= combined_accept
            result.reason = f"{stage}_combined_{'pass' if result.accepted else 'fail'}"

            log.info(
                "[%s] %s combined=%.3f clip=%.3f blip=%.3f caption='%s'",
                stage,
                "✅" if result.accepted else "❌",
                result.combined_score, result.clip_score,
                result.blip_score, result.blip_caption[:40],
            )
        else:
            if cfg.accept_on_model_failure:
                result.accepted = True
                result.reason = f"{stage}_no_scores_fallback"

        del img
        return result

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STAGE 1: DOWNLOAD VERIFICATION (STRICT)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def verify(self, image: Image.Image, query: str) -> VerificationResult:
        """
        Stage 1: Verify downloaded image matches query.
        Uses STRICT thresholds.
        """
        cfg = self.cfg
        return self._verify_with_thresholds(
            image=image,
            query=query,
            clip_accept=cfg.clip_accept_threshold,
            clip_reject=cfg.clip_reject_threshold,
            blip_accept=cfg.blip_accept_threshold,
            blip_reject=cfg.blip_reject_threshold,
            combined_accept=cfg.combined_accept,
            combined_reject=cfg.combined_reject,
            stage="download",
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STAGE 2: POST-COMPOSE VERIFICATION (RELAXED)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def verify_composed(self, image: Image.Image, query: str) -> VerificationResult:
        """
        Stage 2: Verify composed ad still contains the product.
        Uses RELAXED thresholds because:
          - Text overlays change the image
          - Gradient backgrounds alter colors
          - Drop shadows add visual noise
          - BG removal may have changed proportions
        """
        if not self.cfg.use_post_compose:
            return VerificationResult(
                accepted=True,
                reason="post_compose_disabled",
                stage="compose",
            )

        cfg = self.cfg
        return self._verify_with_thresholds(
            image=image,
            query=query,
            clip_accept=cfg.post_clip_accept,
            clip_reject=cfg.post_clip_reject,
            blip_accept=cfg.post_blip_accept,
            blip_reject=cfg.post_blip_reject,
            combined_accept=cfg.post_combined_accept,
            combined_reject=cfg.post_combined_reject,
            stage="compose",
        )

    @property
    def is_available(self) -> bool:
        return (self._clip_model is not None) or (self._blip_model is not None)

    def stats(self) -> Dict[str, Any]:
        return {
            "deps_installed": self._deps_ok,
            "clip_loaded": self._clip_model is not None,
            "blip_loaded": self._blip_model is not None,
            "device": self._device,
            "models_dir": str(self._models_dir) if self._models_dir else "default",
            "post_compose": self.cfg.use_post_compose,
        }