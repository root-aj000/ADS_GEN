# # # # """
# # # # All configuration lives here.
# # # # Change flags / knobs in this single file — nothing is CLI-driven.
# # # # """

# # # # from __future__ import annotations

# # # # from dataclasses import dataclass, field
# # # # from pathlib import Path
# # # # from typing import Dict, List, Tuple

# # # # # ── project root (two levels up from this file) ────────────
# # # # ROOT_DIR = Path(__file__).resolve().parent.parent
# # # # DATA_DIR = ROOT_DIR / "data"


# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # # #  FLAGS  —  toggle behaviour without touching any other file
# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # # RESUME_FROM_PROGRESS   = True     # False → start from scratch
# # # # DRY_RUN                = False    # True → search & download only, skip compositing
# # # # VERBOSE_LOGGING        = True     # True → DEBUG level
# # # # REMOVE_TEMP_ON_FINISH  = True     # cleanup worker dirs after run
# # # # START_INDEX            = None     # None → 0
# # # # END_INDEX              = None     # None → len(df)


# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # # #  DATACLASS CONFIGS
# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# # # # @dataclass(frozen=True)
# # # # class PathConfig:
# # # #     """Every filesystem path the pipeline touches."""

# # # #     root:         Path = DATA_DIR
# # # #     csv_input:    Path = DATA_DIR / "input" / "main.csv"
# # # #     csv_output:   Path = DATA_DIR / "output" / "ads_with_images.csv"
# # # #     images_dir:   Path = DATA_DIR / "output" / "images"
# # # #     temp_dir:     Path = DATA_DIR / "temp" / "workers"
# # # #     progress:     Path = DATA_DIR / "temp" / "progress.json"
# # # #     log_file:     Path = DATA_DIR / "logs" / "ad_generator.log"

# # # #     def ensure(self) -> None:
# # # #         for d in (
# # # #             self.images_dir,
# # # #             self.temp_dir,
# # # #             self.csv_output.parent,
# # # #             self.progress.parent,
# # # #             self.log_file.parent,
# # # #         ):
# # # #             d.mkdir(parents=True, exist_ok=True)


# # # # @dataclass(frozen=True)
# # # # class ImageQualityConfig:
# # # #     min_width:          int   = 60
# # # #     min_height:         int   = 60
# # # #     min_file_bytes:     int   = 30_000
# # # #     max_search_results: int   = 100
# # # #     min_aspect:         float = 0.3
# # # #     max_aspect:         float = 3.0
# # # #     min_unique_colours: int   = 100
# # # #     min_std_dev:        float = 10.0


# # # # @dataclass(frozen=True)
# # # # class BackgroundRemovalConfig:
# # # #     min_retention:    float = 0.05
# # # #     max_retention:    float = 0.95
# # # #     min_object_ratio: float = 0.10
# # # #     min_fill_ratio:   float = 0.15
# # # #     scene_keywords:   Tuple[str, ...] = (
# # # #         "highway", "road", "street", "city", "landscape", "beach",
# # # #         "mountain", "forest", "park", "building", "house", "room",
# # # #         "interior", "outdoor", "sky", "sunset", "sunrise", "driving",
# # # #         "parking", "traffic", "accident", "breakdown", "crowd", "group",
# # # #         "family", "restaurant", "dining", "concert", "festival",
# # # #         "wedding", "ceremony", "meeting", "party", "office", "store",
# # # #         "shop", "mall", "gym", "stadium", "arena",
# # # #     )


# # # # @dataclass(frozen=True)
# # # # class SearchConfig:
# # # #     priority:             List[str] = field(default_factory=lambda: [
# # # #         "google", "duckduckgo", "bing",
# # # #     ])
# # # #     adv_search_term:      str   = " "
# # # #     min_results_fallback: int   = 10
# # # #     inter_engine_delay:   float = 0.5
# # # #     per_request_delay:    float = 0.3
# # # #     rate_limit_per_sec:   float = 2.0
# # # #     breaker_threshold:    int   = 5
# # # #     breaker_cooldown:     float = 120.0


# # # # @dataclass(frozen=True)
# # # # class PipelineConfig:
# # # #     max_workers:       int   = 4
# # # #     inter_ad_delay:    float = 0.5
# # # #     csv_save_interval: int   = 5
# # # #     download_timeout:  int   = 10
# # # #     worker_timeout:    int   = 300


# # # # @dataclass
# # # # class AppConfig:
# # # #     paths:    PathConfig              = field(default_factory=PathConfig)
# # # #     quality:  ImageQualityConfig      = field(default_factory=ImageQualityConfig)
# # # #     bg:       BackgroundRemovalConfig = field(default_factory=BackgroundRemovalConfig)
# # # #     search:   SearchConfig            = field(default_factory=SearchConfig)
# # # #     pipeline: PipelineConfig          = field(default_factory=PipelineConfig)

# # # #     # flags (copied from module-level for convenience)
# # # #     resume:             bool = RESUME_FROM_PROGRESS
# # # #     dry_run:            bool = DRY_RUN
# # # #     verbose:            bool = VERBOSE_LOGGING
# # # #     remove_temp:        bool = REMOVE_TEMP_ON_FINISH
# # # #     start_index:        int | None = START_INDEX
# # # #     end_index:          int | None = END_INDEX

# # # #     def validate(self) -> None:
# # # #         if not self.paths.csv_input.exists():
# # # #             raise FileNotFoundError(
# # # #                 f"Input CSV not found: {self.paths.csv_input}"
# # # #             )
# # # #         if self.pipeline.max_workers < 1:
# # # #             raise ValueError("max_workers must be >= 1")
# # # #         for eng in self.search.priority:
# # # #             if eng not in ("google", "duckduckgo", "bing"):
# # # #                 raise ValueError(f"Unknown search engine: {eng}")


# # # # # ── singleton ───────────────────────────────────────────────
# # # # cfg = AppConfig()


# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # # #  SHARED CONSTANTS
# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # # COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
# # # #     "Red":    (220,  20,  60),
# # # #     "Blue":   (  0, 102, 204),
# # # #     "Green":  ( 34, 139,  34),
# # # #     "Yellow": (255, 193,   7),
# # # #     "Orange": (255, 102,   0),
# # # #     "Pink":   (255, 105, 180),
# # # #     "Purple": (128,   0, 128),
# # # #     "Black":  ( 45,  45,  45),
# # # #     "White":  (255, 255, 255),
# # # #     "Brown":  (139,  69,  19),
# # # #     "Grey":   (128, 128, 128),
# # # # }

# # # # DEFAULT_HEADERS: Dict[str, str] = {
# # # #     "User-Agent": (
# # # #         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
# # # #         "AppleWebKit/537.36 (KHTML, like Gecko) "
# # # #         "Chrome/120.0.0.0 Safari/537.36"
# # # #     ),
# # # #     "Accept": (
# # # #         "text/html,application/xhtml+xml,application/xml;"
# # # #         "q=0.9,image/webp,*/*;q=0.8"
# # # #     ),
# # # #     "Accept-Language": "en-US,en;q=0.9",
# # # #     "DNT": "1",
# # # #     "Connection": "keep-alive",
# # # #     "Upgrade-Insecure-Requests": "1",
# # # # }

# # # """
# # # All configuration — flags, knobs, feature toggles.
# # # Edit THIS file to change any behaviour.
# # # """

# # # from __future__ import annotations

# # # import os
# # # from dataclasses import dataclass, field
# # # from pathlib import Path
# # # from typing import Dict, List, Optional, Tuple

# # # ROOT_DIR = Path(__file__).resolve().parent.parent
# # # DATA_DIR = ROOT_DIR / "data"

# # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # #  FLAGS — toggle without touching other files
# # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # RESUME_FROM_PROGRESS    = False
# # # DRY_RUN                 = False
# # # VERBOSE_LOGGING         = True
# # # REMOVE_TEMP_ON_FINISH   = True
# # # START_INDEX: int | None = None
# # # END_INDEX:   int | None = None

# # # # ── NEW feature flags ──
# # # ENABLE_IMAGE_CACHE      = False      # cache downloaded images to skip re-downloads
# # # ENABLE_PROXY_ROTATION   = False     # rotate proxies across requests
# # # ENABLE_NOTIFICATIONS    = False     # send webhook on completion/failure
# # # ENABLE_MULTI_SIZE       = False     # generate multiple output sizes
# # # ENABLE_WATERMARK        = False     # add brand watermark
# # # ENABLE_ASYNC_DOWNLOAD   = True      # use async I/O for downloads
# # # ENABLE_HEALTH_MONITOR   = True      # track search engine health metrics
# # # ENABLE_DEAD_LETTER      = True      # retry failed rows at end of run
# # # DEAD_LETTER_MAX_RETRIES = 2         # how many times to retry failed rows
# # # CHUNK_SIZE              = 50        # process N rows per chunk (memory control)


# # # @dataclass(frozen=True)
# # # class PathConfig:
# # #     root:         Path = DATA_DIR
# # #     csv_input:    Path = DATA_DIR / "input" / "main.csv"
# # #     csv_output:   Path = DATA_DIR / "output" / "Train.csv"
# # #     images_dir:   Path = DATA_DIR / "output" / "images"
# # #     temp_dir:     Path = DATA_DIR / "temp" / "workers"
# # #     progress_db:  Path = DATA_DIR / "temp" / "progress.db"
# # #     cache_db:     Path = DATA_DIR / "cache" / "images.db"
# # #     log_file:     Path = DATA_DIR / "logs" / "ad_generator.log"
# # #     fonts_dir:    Path = DATA_DIR / "fonts"
# # #     proxy_file:   Path = DATA_DIR / "config" / "proxies.txt"

# # #     def ensure(self) -> None:
# # #         for d in (
# # #             self.images_dir, self.temp_dir,
# # #             self.csv_output.parent, self.progress_db.parent,
# # #             self.cache_db.parent, self.log_file.parent,
# # #             self.fonts_dir,
# # #         ):
# # #             d.mkdir(parents=True, exist_ok=True)


# # # @dataclass(frozen=True)
# # # class ImageQualityConfig:
# # #     min_width:          int   = 60
# # #     min_height:         int   = 60
# # #     min_file_bytes:     int   = 30_000
# # #     max_search_results: int   = 100
# # #     min_aspect:         float = 0.3
# # #     max_aspect:         float = 3.0
# # #     min_unique_colours: int   = 100
# # #     min_std_dev:        float = 10.0

# # #     # NEW — advanced quality scoring weights
# # #     sharpness_weight:   float = 0.3
# # #     contrast_weight:    float = 0.2
# # #     resolution_weight:  float = 0.3
# # #     source_weight:      float = 0.2


# # # @dataclass(frozen=True)
# # # class BackgroundRemovalConfig:
# # #     min_retention:    float = 0.05
# # #     max_retention:    float = 0.95
# # #     min_object_ratio: float = 0.10
# # #     min_fill_ratio:   float = 0.15
# # #     scene_keywords:   Tuple[str, ...] = (
# # #         "highway", "road", "street", "city", "landscape", "beach",
# # #         "mountain", "forest", "park", "building", "house", "room",
# # #         "interior", "outdoor", "sky", "sunset", "sunrise", "driving",
# # #         "parking", "traffic", "accident", "breakdown", "crowd", "group",
# # #         "family", "restaurant", "dining", "concert", "festival",
# # #         "wedding", "ceremony", "meeting", "party", "office", "store",
# # #         "shop", "mall", "gym", "stadium", "arena",
# # #     )


# # # @dataclass(frozen=True)
# # # class SearchConfig:
# # #     priority:             List[str] = field(default_factory=lambda: [
# # #         "google", "duckduckgo", "bing",
# # #     ])
# # #     adv_search_term:      str   = "original+image"
# # #     min_results_fallback: int   = 10
# # #     inter_engine_delay:   float = 0.5
# # #     per_request_delay:    float = 0.3
# # #     rate_limit_per_sec:   float = 2.0
# # #     breaker_threshold:    int   = 5
# # #     breaker_cooldown:     float = 120.0


# # # @dataclass(frozen=True)
# # # class ProxyConfig:
# # #     enabled:          bool  = ENABLE_PROXY_ROTATION
# # #     rotation_mode:    str   = "round_robin"    # "round_robin" | "random" | "least_used"
# # #     max_failures:     int   = 3
# # #     test_url:         str   = "https://httpbin.org/ip"
# # #     test_timeout:     int   = 5


# # # @dataclass(frozen=True)
# # # class NotificationConfig:
# # #     enabled:       bool = ENABLE_NOTIFICATIONS
# # #     webhook_url:   str  = ""                    # Slack / Discord webhook
# # #     email_to:      str  = ""
# # #     smtp_host:     str  = ""
# # #     smtp_port:     int  = 587
# # #     smtp_user:     str  = ""
# # #     smtp_pass:     str  = ""
# # #     notify_on:     Tuple[str, ...] = ("completion", "failure", "milestone")
# # #     milestone_every: int = 100                  # notify every N successful ads


# # # @dataclass(frozen=True)
# # # class OutputConfig:
# # #     """Multiple output size support."""
# # #     primary_size:   Tuple[int, int] = (1080, 1080)
# # #     extra_sizes:    Tuple[Tuple[int, int], ...] = (
# # #         (1200, 628),    # Facebook
# # #         (1080, 1920),   # Instagram Story
# # #         (800, 800),     # Thumbnail
# # #     )
# # #     watermark_text:  str   = ""
# # #     watermark_opacity: int = 40
# # #     jpeg_quality:    int   = 95


# # # @dataclass(frozen=True)
# # # class PipelineConfig:
# # #     max_workers:       int   = 4
# # #     inter_ad_delay:    float = 0.5
# # #     csv_save_interval: int   = 5
# # #     download_timeout:  int   = 10
# # #     worker_timeout:    int   = 300
# # #     async_batch_size:  int   = 10   # download N images concurrently


# # # @dataclass
# # # class AppConfig:
# # #     paths:        PathConfig              = field(default_factory=PathConfig)
# # #     quality:      ImageQualityConfig      = field(default_factory=ImageQualityConfig)
# # #     bg:           BackgroundRemovalConfig = field(default_factory=BackgroundRemovalConfig)
# # #     search:       SearchConfig            = field(default_factory=SearchConfig)
# # #     proxy:        ProxyConfig             = field(default_factory=ProxyConfig)
# # #     notify:       NotificationConfig      = field(default_factory=NotificationConfig)
# # #     output:       OutputConfig            = field(default_factory=OutputConfig)
# # #     pipeline:     PipelineConfig          = field(default_factory=PipelineConfig)

# # #     resume:       bool         = RESUME_FROM_PROGRESS
# # #     dry_run:      bool         = DRY_RUN
# # #     verbose:      bool         = VERBOSE_LOGGING
# # #     remove_temp:  bool         = REMOVE_TEMP_ON_FINISH
# # #     start_index:  int | None   = START_INDEX
# # #     end_index:    int | None   = END_INDEX
# # #     enable_cache: bool         = ENABLE_IMAGE_CACHE
# # #     enable_async: bool         = ENABLE_ASYNC_DOWNLOAD
# # #     enable_health: bool        = ENABLE_HEALTH_MONITOR
# # #     enable_dlq:   bool         = ENABLE_DEAD_LETTER
# # #     dlq_retries:  int          = DEAD_LETTER_MAX_RETRIES
# # #     chunk_size:   int          = CHUNK_SIZE
# # #     multi_size:   bool         = ENABLE_MULTI_SIZE
# # #     watermark:    bool         = ENABLE_WATERMARK

# # #     def validate(self) -> None:
# # #         if not self.paths.csv_input.exists():
# # #             raise FileNotFoundError(f"Input CSV missing: {self.paths.csv_input}")
# # #         if self.pipeline.max_workers < 1:
# # #             raise ValueError("max_workers must be >= 1")
# # #         for eng in self.search.priority:
# # #             if eng not in ("google", "duckduckgo", "bing"):
# # #                 raise ValueError(f"Unknown engine: {eng}")


# # # cfg = AppConfig()


# # # COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
# # #     "Red":    (220,  20,  60), "Blue":   (  0, 102, 204),
# # #     "Green":  ( 34, 139,  34), "Yellow": (255, 193,   7),
# # #     "Orange": (255, 102,   0), "Pink":   (255, 105, 180),
# # #     "Purple": (128,   0, 128), "Black":  ( 45,  45,  45),
# # #     "White":  (255, 255, 255), "Brown":  (139,  69,  19),
# # #     "Grey":   (128, 128, 128),
# # # }

# # # DEFAULT_HEADERS: Dict[str, str] = {
# # #     "User-Agent": (
# # #         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
# # #         "AppleWebKit/537.36 (KHTML, like Gecko) "
# # #         "Chrome/120.0.0.0 Safari/537.36"
# # #     ),
# # #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
# # #     "Accept-Language": "en-US,en;q=0.9",
# # #     "DNT": "1",
# # #     "Connection": "keep-alive",
# # #     "Upgrade-Insecure-Requests": "1",
# # # }
# # """
# # All configuration — flags, knobs, feature toggles.
# # """

# # from __future__ import annotations

# # import os
# # from dataclasses import dataclass, field
# # from pathlib import Path
# # from typing import Dict, List, Optional, Tuple

# # ROOT_DIR = Path(__file__).resolve().parent.parent
# # DATA_DIR = ROOT_DIR / "data"

# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # #  FLAGS
# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # RESUME_FROM_PROGRESS    = False
# # DRY_RUN                 = False
# # VERBOSE_LOGGING         = False    # ← Set False to reduce noise
# # REMOVE_TEMP_ON_FINISH   = True
# # START_INDEX: int | None = None
# # END_INDEX:   int | None = None

# # # Feature flags
# # ENABLE_IMAGE_CACHE      = True
# # ENABLE_PROXY_ROTATION   = False
# # ENABLE_NOTIFICATIONS    = False
# # ENABLE_MULTI_SIZE       = False
# # ENABLE_WATERMARK        = False
# # ENABLE_ASYNC_DOWNLOAD   = True
# # ENABLE_HEALTH_MONITOR   = True
# # ENABLE_DEAD_LETTER      = True
# # DEAD_LETTER_MAX_RETRIES = 2
# # CHUNK_SIZE              = 50


# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # #  QUERY CONFIGURATION — CUSTOMIZE YOUR CSV COLUMNS HERE
# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # @dataclass(frozen=True)
# # class QueryConfig:
# #     """
# #     Configure which CSV columns to use for search queries.
# #     The pipeline tries columns in order until it finds a valid value.
# #     """
# #     # Columns to try, in priority order
# #     # Change these to match YOUR CSV column names!
# #     priority_columns: Tuple[str, ...] = (
# #         "img_desc",           # ← Your primary column
# #         "keywords",
# #         "object_detected",
# #         "product_name",
# #         "description",
# #         "text",
# #     )
    
# #     # Column for ad text (title, description)
# #     img_desc_column: str = "img_desc"
# #     text_column: str = "text"
    
# #     # Column for discount/price
# #     monetary_column: str = "monetary_mention"
    
# #     # Column for CTA button
# #     cta_column: str = "call_to_action"
    
# #     # Column for background color
# #     color_column: str = "dominant_colour"
    
# #     # Max words to take from query
# #     max_query_words: int = 0
    
# #     # Values to ignore (treated as empty)
# #     ignore_values: Tuple[str, ...] = (
# #         "nan", "none", "", "general", "food", 
# #         "automotive", "object", "unknown", "null",
# #     )

# #     strip_suffixes: Tuple[str, ...] = (
# #         "filetype png",
# #         "filetype jpg",
# #         "filetype jpeg",
# #         "filetype webp",
# #         "site:",
# #         "inurl:",
# #     )

# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # #  PATH CONFIG
# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # @dataclass(frozen=True)
# # class PathConfig:
# #     root:         Path = DATA_DIR
# #     csv_input:    Path = DATA_DIR / "input" / "main.csv"
# #     csv_output:   Path = DATA_DIR / "output" / "Train.csv"
# #     images_dir:   Path = DATA_DIR / "output" / "images"
# #     temp_dir:     Path = DATA_DIR / "temp" / "workers"
# #     progress_db:  Path = DATA_DIR / "temp" / "progress.db"
# #     cache_db:     Path = DATA_DIR / "cache" / "images.db"
# #     log_file:     Path = DATA_DIR / "logs" / "ad_generator.log"
# #     fonts_dir:    Path = DATA_DIR / "fonts"
# #     proxy_file:   Path = DATA_DIR / "config" / "proxies.txt"

# #     def ensure(self) -> None:
# #         for d in (
# #             self.images_dir, self.temp_dir,
# #             self.csv_output.parent, self.progress_db.parent,
# #             self.cache_db.parent, self.log_file.parent,
# #             self.fonts_dir,
# #         ):
# #             d.mkdir(parents=True, exist_ok=True)


# # @dataclass(frozen=True)
# # class ImageQualityConfig:
# #     min_width:          int   = 60
# #     min_height:         int   = 60
# #     min_file_bytes:     int   = 30_000
# #     max_search_results: int   = 100
# #     min_aspect:         float = 0.3
# #     max_aspect:         float = 3.0
# #     min_unique_colours: int   = 100
# #     min_std_dev:        float = 10.0
# #     sharpness_weight:   float = 0.3
# #     contrast_weight:    float = 0.2
# #     resolution_weight:  float = 0.3
# #     source_weight:      float = 0.2


# # @dataclass(frozen=True)
# # class BackgroundRemovalConfig:
# #     min_retention:    float = 0.05
# #     max_retention:    float = 0.95
# #     min_object_ratio: float = 0.10
# #     min_fill_ratio:   float = 0.15
# #     scene_keywords:   Tuple[str, ...] = (
# #         "highway", "road", "street", "city", "landscape", "beach",
# #         "mountain", "forest", "park", "building", "house", "room",
# #         "interior", "outdoor", "sky", "sunset", "sunrise", "driving",
# #         "parking", "traffic", "accident", "breakdown", "crowd", "group",
# #         "family", "restaurant", "dining", "concert", "festival",
# #         "wedding", "ceremony", "meeting", "party", "office", "store",
# #         "shop", "mall", "gym", "stadium", "arena",
# #     )


# # @dataclass(frozen=True)
# # class SearchConfig:
# #     priority:             List[str] = field(default_factory=lambda: [
# #         "google", "duckduckgo", "bing",
# #     ])
# #     adv_search_term:      str   = "product image"
# #     min_results_fallback: int   = 10
# #     inter_engine_delay:   float = 0.5
# #     per_request_delay:    float = 0.3
# #     rate_limit_per_sec:   float = 2.0
# #     breaker_threshold:    int   = 5
# #     breaker_cooldown:     float = 120.0


# # @dataclass(frozen=True)
# # class ProxyConfig:
# #     enabled:          bool  = ENABLE_PROXY_ROTATION
# #     rotation_mode:    str   = "round_robin"
# #     max_failures:     int   = 3
# #     test_url:         str   = "https://httpbin.org/ip"
# #     test_timeout:     int   = 5


# # @dataclass(frozen=True)
# # class NotificationConfig:
# #     enabled:         bool = ENABLE_NOTIFICATIONS
# #     webhook_url:     str  = ""
# #     email_to:        str  = ""
# #     smtp_host:       str  = ""
# #     smtp_port:       int  = 587
# #     smtp_user:       str  = ""
# #     smtp_pass:       str  = ""
# #     notify_on:       Tuple[str, ...] = ("completion", "failure", "milestone")
# #     milestone_every: int  = 100


# # @dataclass(frozen=True)
# # class OutputConfig:
# #     primary_size:      Tuple[int, int] = (1080, 1080)
# #     extra_sizes:       Tuple[Tuple[int, int], ...] = (
# #         (1200, 628),
# #         (1080, 1920),
# #         (800, 800),
# #     )
# #     watermark_text:    str = ""
# #     watermark_opacity: int = 40
# #     jpeg_quality:      int = 95


# # @dataclass(frozen=True)
# # class PipelineConfig:
# #     max_workers:       int   = 4
# #     inter_ad_delay:    float = 0.5
# #     csv_save_interval: int   = 5
# #     download_timeout:  int   = 10
# #     worker_timeout:    int   = 300
# #     async_batch_size:  int   = 10


# # @dataclass
# # class AppConfig:
# #     paths:        PathConfig              = field(default_factory=PathConfig)
# #     quality:      ImageQualityConfig      = field(default_factory=ImageQualityConfig)
# #     bg:           BackgroundRemovalConfig = field(default_factory=BackgroundRemovalConfig)
# #     search:       SearchConfig            = field(default_factory=SearchConfig)
# #     query:        QueryConfig             = field(default_factory=QueryConfig)  # ← NEW
# #     proxy:        ProxyConfig             = field(default_factory=ProxyConfig)
# #     notify:       NotificationConfig      = field(default_factory=NotificationConfig)
# #     output:       OutputConfig            = field(default_factory=OutputConfig)
# #     pipeline:     PipelineConfig          = field(default_factory=PipelineConfig)

# #     resume:        bool         = RESUME_FROM_PROGRESS
# #     dry_run:       bool         = DRY_RUN
# #     verbose:       bool         = VERBOSE_LOGGING
# #     remove_temp:   bool         = REMOVE_TEMP_ON_FINISH
# #     start_index:   int | None   = START_INDEX
# #     end_index:     int | None   = END_INDEX
# #     enable_cache:  bool         = ENABLE_IMAGE_CACHE
# #     enable_async:  bool         = ENABLE_ASYNC_DOWNLOAD
# #     enable_health: bool         = ENABLE_HEALTH_MONITOR
# #     enable_dlq:    bool         = ENABLE_DEAD_LETTER
# #     dlq_retries:   int          = DEAD_LETTER_MAX_RETRIES
# #     chunk_size:    int          = CHUNK_SIZE
# #     multi_size:    bool         = ENABLE_MULTI_SIZE
# #     watermark:     bool         = ENABLE_WATERMARK

# #     def validate(self) -> None:
# #         if not self.paths.csv_input.exists():
# #             raise FileNotFoundError(f"Input CSV missing: {self.paths.csv_input}")
# #         if self.pipeline.max_workers < 1:
# #             raise ValueError("max_workers must be >= 1")
# #         for eng in self.search.priority:
# #             if eng not in ("google", "duckduckgo", "bing"):
# #                 raise ValueError(f"Unknown engine: {eng}")


# # cfg = AppConfig()


# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # #  CONSTANTS
# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
# #     "Red":    (220,  20,  60), "Blue":   (  0, 102, 204),
# #     "Green":  ( 34, 139,  34), "Yellow": (255, 193,   7),
# #     "Orange": (255, 102,   0), "Pink":   (255, 105, 180),
# #     "Purple": (128,   0, 128), "Black":  ( 45,  45,  45),
# #     "White":  (255, 255, 255), "Brown":  (139,  69,  19),
# #     "Grey":   (128, 128, 128),
# # }

# # DEFAULT_HEADERS: Dict[str, str] = {
# #     "User-Agent": (
# #         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
# #         "AppleWebKit/537.36 (KHTML, like Gecko) "
# #         "Chrome/120.0.0.0 Safari/537.36"
# #     ),
# #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
# #     "Accept-Language": "en-US,en;q=0.9",
# #     "DNT": "1",
# #     "Connection": "keep-alive",
# #     "Upgrade-Insecure-Requests": "1",
# # }



# """
# All configuration — flags, knobs, feature toggles.
# """

# from __future__ import annotations

# import os
# from dataclasses import dataclass, field
# from pathlib import Path
# from typing import Dict, List, Optional, Tuple

# ROOT_DIR = Path(__file__).resolve().parent.parent
# DATA_DIR = ROOT_DIR / "data"

# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# #  FLAGS
# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# RESUME_FROM_PROGRESS    = False
# DRY_RUN                 = False
# VERBOSE_LOGGING         = False
# REMOVE_TEMP_ON_FINISH   = True
# START_INDEX: int | None = None
# END_INDEX:   int | None = None

# # Feature flags
# ENABLE_IMAGE_CACHE      = False
# ENABLE_PROXY_ROTATION   = False
# ENABLE_NOTIFICATIONS    = False
# ENABLE_MULTI_SIZE       = False
# ENABLE_WATERMARK        = False
# ENABLE_ASYNC_DOWNLOAD   = True
# ENABLE_HEALTH_MONITOR   = True
# ENABLE_DEAD_LETTER      = True
# DEAD_LETTER_MAX_RETRIES = 2
# CHUNK_SIZE              = 50

# # ═══════════════════════════════════════════════════════════
# #  CLIP + BLIP VERIFICATION
# # ═══════════════════════════════════════════════════════════
# ENABLE_CLIP_VERIFICATION = True     # Use CLIP for image-text matching
# ENABLE_BLIP_VERIFICATION = True     # Use BLIP for caption cross-check


# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# #  VERIFICATION CONFIG
# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# @dataclass(frozen=True)
# class VerificationConfig:
#     """
#     CLIP + BLIP cross-verification settings.
    
#     Scores:
#         CLIP score   : 0.0–1.0 (cosine similarity between image & text)
#         BLIP score   : 0.0–1.0 (word overlap between caption & query)
#         Combined     : weighted average of both
    
#     Thresholds:
#         - Images ABOVE accept_threshold   → accepted immediately
#         - Images BELOW reject_threshold   → rejected immediately
#         - Images BETWEEN                  → accepted if best available
#     """
    
#     # Enable/disable each model
#     use_clip:                bool  = ENABLE_CLIP_VERIFICATION
#     use_blip:                bool  = ENABLE_BLIP_VERIFICATION
    
#     # Model names (HuggingFace)
#     clip_model:              str   = "openai/clip-vit-base-patch32"
#     blip_model:              str   = "Salesforce/blip-image-captioning-base"
    
#     # Thresholds
#     clip_accept_threshold:   float = 0.25    # CLIP score to auto-accept
#     clip_reject_threshold:   float = 0.15    # CLIP score to auto-reject
#     blip_accept_threshold:   float = 0.30    # BLIP word overlap to auto-accept
#     blip_reject_threshold:   float = 0.10    # BLIP word overlap to auto-reject
    
#     combined_accept:         float = 0.25    # Combined score to accept
#     combined_reject:         float = 0.12    # Combined score to reject
    
#     # Weights for combined score
#     clip_weight:             float = 0.6     # CLIP is usually more reliable
#     blip_weight:             float = 0.4
    
#     # Performance
#     max_verify_candidates:   int   = 10      # Max images to verify before giving up
#     device:                  str   = "auto"  # "auto", "cuda", "cpu"
#     batch_size:              int   = 1       # Process N images at once
    
#     # Fallback behaviour
#     accept_on_model_failure: bool  = True    # If models crash, accept image anyway
#     min_candidates_before_best: int = 3      # Try at least N before picking best score


# @dataclass(frozen=True)
# class QueryConfig:
#     priority_columns: Tuple[str, ...] = (
#         "img_desc",
#         "keywords",
#         "object_detected",
#         "product_name",
#         "description",
#         "text",
#     )
#     text_column:     str = "text"
#     monetary_column: str = "monetary_mention"
#     cta_column:      str = "call_to_action"
#     color_column:    str = "dominant_colour"
#     max_query_words: int = 0
#     ignore_values:   Tuple[str, ...] = (
#         "nan", "none", "", "general", "food",
#         "automotive", "object", "unknown", "null",
#     )
#     strip_suffixes:  Tuple[str, ...] = (
#         "filetype png", "filetype jpg", "filetype jpeg",
#         "filetype webp", "site:", "inurl:",
#     )


# @dataclass(frozen=True)
# class PathConfig:
#     root:         Path = DATA_DIR
#     csv_input:    Path = DATA_DIR / "input" / "main.csv"
#     csv_output:   Path = DATA_DIR / "output" / "ads_with_images.csv"
#     images_dir:   Path = DATA_DIR / "output" / "images"
#     temp_dir:     Path = DATA_DIR / "temp" / "workers"
#     progress_db:  Path = DATA_DIR / "temp" / "progress.db"
#     cache_db:     Path = DATA_DIR / "cache" / "images.db"
#     log_file:     Path = DATA_DIR / "logs" / "ad_generator.log"
#     fonts_dir:    Path = DATA_DIR / "fonts"
#     proxy_file:   Path = DATA_DIR / "config" / "proxies.txt"
#     models_dir:   Path = DATA_DIR / "models"  # ← NEW: cache models locally
#     # models_dir:   Path = DATA_DIR / "models" 

#     def ensure(self) -> None:
#         for d in (
#             self.images_dir, self.temp_dir,
#             self.csv_output.parent, self.progress_db.parent,
#             self.cache_db.parent, self.log_file.parent,
#             self.fonts_dir, self.models_dir,
#         ):
#             d.mkdir(parents=True, exist_ok=True)


# @dataclass(frozen=True)
# class ImageQualityConfig:
#     min_width:          int   = 60
#     min_height:         int   = 60
#     min_file_bytes:     int   = 30_000
#     max_search_results: int   = 100
#     min_aspect:         float = 0.3
#     max_aspect:         float = 3.0
#     min_unique_colours: int   = 100
#     min_std_dev:        float = 10.0
#     sharpness_weight:   float = 0.3
#     contrast_weight:    float = 0.2
#     resolution_weight:  float = 0.3
#     source_weight:      float = 0.2


# @dataclass(frozen=True)
# class BackgroundRemovalConfig:
#     min_retention:    float = 0.05
#     max_retention:    float = 0.95
#     min_object_ratio: float = 0.10
#     min_fill_ratio:   float = 0.15
#     scene_keywords:   Tuple[str, ...] = (
#         "highway", "road", "street", "city", "landscape", "beach",
#         "mountain", "forest", "park", "building", "house", "room",
#         "interior", "outdoor", "sky", "sunset", "sunrise", "driving",
#         "parking", "traffic", "accident", "breakdown", "crowd", "group",
#         "family", "restaurant", "dining", "concert", "festival",
#         "wedding", "ceremony", "meeting", "party", "office", "store",
#         "shop", "mall", "gym", "stadium", "arena",
#     )


# @dataclass(frozen=True)
# class SearchConfig:
#     priority:             List[str] = field(default_factory=lambda: [
#         "google", "duckduckgo", "bing",
#     ])
#     adv_search_term:      str   = "product image"
#     min_results_fallback: int   = 10
#     inter_engine_delay:   float = 0.5
#     per_request_delay:    float = 0.3
#     rate_limit_per_sec:   float = 2.0
#     breaker_threshold:    int   = 5
#     breaker_cooldown:     float = 120.0


# @dataclass(frozen=True)
# class ProxyConfig:
#     enabled:       bool = ENABLE_PROXY_ROTATION
#     rotation_mode: str  = "round_robin"
#     max_failures:  int  = 3
#     test_url:      str  = "https://httpbin.org/ip"
#     test_timeout:  int  = 5


# @dataclass(frozen=True)
# class NotificationConfig:
#     enabled:         bool = ENABLE_NOTIFICATIONS
#     webhook_url:     str  = ""
#     email_to:        str  = ""
#     smtp_host:       str  = ""
#     smtp_port:       int  = 587
#     smtp_user:       str  = ""
#     smtp_pass:       str  = ""
#     notify_on:       Tuple[str, ...] = ("completion", "failure", "milestone")
#     milestone_every: int  = 100


# @dataclass(frozen=True)
# class OutputConfig:
#     primary_size:      Tuple[int, int] = (1080, 1080)
#     jpeg_quality:      int = 95


# @dataclass(frozen=True)
# class PipelineConfig:
#     max_workers:       int   = 4
#     inter_ad_delay:    float = 0.5
#     csv_save_interval: int   = 5
#     download_timeout:  int   = 10
#     worker_timeout:    int   = 300


# @dataclass
# class AppConfig:
#     paths:        PathConfig              = field(default_factory=PathConfig)
#     quality:      ImageQualityConfig      = field(default_factory=ImageQualityConfig)
#     bg:           BackgroundRemovalConfig = field(default_factory=BackgroundRemovalConfig)
#     search:       SearchConfig            = field(default_factory=SearchConfig)
#     query:        QueryConfig             = field(default_factory=QueryConfig)
#     verify:       VerificationConfig      = field(default_factory=VerificationConfig)  # ← NEW
#     proxy:        ProxyConfig             = field(default_factory=ProxyConfig)
#     notify:       NotificationConfig      = field(default_factory=NotificationConfig)
#     output:       OutputConfig            = field(default_factory=OutputConfig)
#     pipeline:     PipelineConfig          = field(default_factory=PipelineConfig)

#     resume:        bool         = RESUME_FROM_PROGRESS
#     dry_run:       bool         = DRY_RUN
#     verbose:       bool         = VERBOSE_LOGGING
#     remove_temp:   bool         = REMOVE_TEMP_ON_FINISH
#     start_index:   int | None   = START_INDEX
#     end_index:     int | None   = END_INDEX
#     enable_cache:  bool         = ENABLE_IMAGE_CACHE
#     enable_async:  bool         = ENABLE_ASYNC_DOWNLOAD
#     enable_health: bool         = ENABLE_HEALTH_MONITOR
#     enable_dlq:    bool         = ENABLE_DEAD_LETTER
#     dlq_retries:   int          = DEAD_LETTER_MAX_RETRIES
#     chunk_size:    int          = CHUNK_SIZE
#     multi_size:    bool         = ENABLE_MULTI_SIZE
#     watermark:     bool         = ENABLE_WATERMARK

#     def validate(self) -> None:
#         if not self.paths.csv_input.exists():
#             raise FileNotFoundError(f"Input CSV missing: {self.paths.csv_input}")
#         if self.pipeline.max_workers < 1:
#             raise ValueError("max_workers must be >= 1")
#         for eng in self.search.priority:
#             if eng not in ("google", "duckduckgo", "bing"):
#                 raise ValueError(f"Unknown engine: {eng}")


# cfg = AppConfig()


# COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
#     "Red":    (220,  20,  60), "Blue":   (  0, 102, 204),
#     "Green":  ( 34, 139,  34), "Yellow": (255, 193,   7),
#     "Orange": (255, 102,   0), "Pink":   (255, 105, 180),
#     "Purple": (128,   0, 128), "Black":  ( 45,  45,  45),
#     "White":  (255, 255, 255), "Brown":  (139,  69,  19),
#     "Grey":   (128, 128, 128),
# }

# DEFAULT_HEADERS: Dict[str, str] = {
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#         "AppleWebKit/537.36 (KHTML, like Gecko) "
#         "Chrome/120.0.0.0 Safari/537.36"
#     ),
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
#     "Accept-Language": "en-US,en;q=0.9",
#     "DNT": "1",
#     "Connection": "keep-alive",
#     "Upgrade-Insecure-Requests": "1",
# }
"""
All configuration — flags, knobs, feature toggles.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FLAGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESUME_FROM_PROGRESS    = False
DRY_RUN                 = False
VERBOSE_LOGGING         = False
REMOVE_TEMP_ON_FINISH   = True
START_INDEX: int | None = None
END_INDEX:   int | None = None

ENABLE_IMAGE_CACHE      = True
ENABLE_PROXY_ROTATION   = False
ENABLE_NOTIFICATIONS    = False
ENABLE_MULTI_SIZE       = False
ENABLE_WATERMARK        = False
ENABLE_ASYNC_DOWNLOAD   = True
ENABLE_HEALTH_MONITOR   = True
ENABLE_DEAD_LETTER      = True
DEAD_LETTER_MAX_RETRIES = 2
CHUNK_SIZE              = 50

# ═══════════════════════════════════════════════════════════
#  VERIFICATION FLAGS
# ═══════════════════════════════════════════════════════════
ENABLE_CLIP_VERIFICATION     = True     # CLIP for download check
ENABLE_BLIP_VERIFICATION     = True     # BLIP for download check
ENABLE_POST_COMPOSE_VERIFY   = True     # Verify AFTER ad is composed


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  VERIFICATION CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class VerificationConfig:
    """
    CLIP + BLIP verification at TWO stages:
    
    Stage 1 (Download): Strict thresholds
        "Does the downloaded image match the query?"
        
    Stage 2 (Post-Compose): Relaxed thresholds
        "Does the final ad still show the product?"
        Lower thresholds because text overlays, gradients,
        and background changes alter the image.
    """

    # ── Model selection ──
    use_clip:                bool  = ENABLE_CLIP_VERIFICATION
    use_blip:                bool  = ENABLE_BLIP_VERIFICATION
    use_post_compose:        bool  = ENABLE_POST_COMPOSE_VERIFY

    # ── Model names ──
    clip_model:              str   = "openai/clip-vit-base-patch32"
    blip_model:              str   = "Salesforce/blip-image-captioning-base"

    # ── STAGE 1: Download verification (STRICT) ──
    clip_accept_threshold:   float = 0.25
    clip_reject_threshold:   float = 0.15
    blip_accept_threshold:   float = 0.30
    blip_reject_threshold:   float = 0.10
    combined_accept:         float = 0.25
    combined_reject:         float = 0.12

    # ── STAGE 2: Post-compose verification (RELAXED) ──
    post_clip_accept:        float = 0.18    # Lower — text overlays reduce score
    post_clip_reject:        float = 0.08    # Much lower — composed ads look different
    post_blip_accept:        float = 0.20
    post_blip_reject:        float = 0.05
    post_combined_accept:    float = 0.15    # More forgiving
    post_combined_reject:    float = 0.06

    # ── Weights ──
    clip_weight:             float = 0.6
    blip_weight:             float = 0.4

    # ── Performance ──
    max_verify_candidates:   int   = 10
    device:                  str   = "auto"
    batch_size:              int   = 1

    # ── Fallback ──
    accept_on_model_failure: bool  = True
    min_candidates_before_best: int = 3

    # ── Post-compose behaviour ──
    max_recompose_attempts:  int   = 2       # How many times to retry compose
    recompose_without_bg:    bool  = True     # Try without bg removal on fail
    recompose_simpler_text:  bool  = True     # Try with less text on fail


@dataclass(frozen=True)
class QueryConfig:
    priority_columns: Tuple[str, ...] = (
        "img_desc", "keywords", "object_detected",
        "product_name", "description", "text",
    )
    text_column:     str = "text"
    monetary_column: str = "monetary_mention"
    cta_column:      str = "call_to_action"
    color_column:    str = "dominant_colour"
    max_query_words: int = 0
    ignore_values:   Tuple[str, ...] = (
        "nan", "none", "", "general", "food",
        "automotive", "object", "unknown", "null",
    )
    strip_suffixes:  Tuple[str, ...] = (
        "filetype png", "filetype jpg", "filetype jpeg",
        "filetype webp", "site:", "inurl:",
    )


@dataclass(frozen=True)
class PathConfig:
    root:         Path = DATA_DIR
    csv_input:    Path = DATA_DIR / "input" / "main.csv"
    csv_output:   Path = DATA_DIR / "output" / "ads_with_images.csv"
    images_dir:   Path = DATA_DIR / "output" / "images"
    temp_dir:     Path = DATA_DIR / "temp" / "workers"
    progress_db:  Path = DATA_DIR / "temp" / "progress.db"
    cache_db:     Path = DATA_DIR / "cache" / "images.db"
    log_file:     Path = DATA_DIR / "logs" / "ad_generator.log"
    fonts_dir:    Path = DATA_DIR / "fonts"
    proxy_file:   Path = DATA_DIR / "config" / "proxies.txt"
    models_dir:   Path = DATA_DIR / "models"

    def ensure(self) -> None:
        for d in (
            self.images_dir, self.temp_dir,
            self.csv_output.parent, self.progress_db.parent,
            self.cache_db.parent, self.log_file.parent,
            self.fonts_dir, self.models_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class ImageQualityConfig:
    min_width:          int   = 60
    min_height:         int   = 60
    min_file_bytes:     int   = 30_000
    max_search_results: int   = 100
    min_aspect:         float = 0.3
    max_aspect:         float = 3.0
    min_unique_colours: int   = 100
    min_std_dev:        float = 10.0
    sharpness_weight:   float = 0.3
    contrast_weight:    float = 0.2
    resolution_weight:  float = 0.3
    source_weight:      float = 0.2


@dataclass(frozen=True)
class BackgroundRemovalConfig:
    min_retention:    float = 0.05
    max_retention:    float = 0.95
    min_object_ratio: float = 0.10
    min_fill_ratio:   float = 0.15
    scene_keywords:   Tuple[str, ...] = (
        "highway", "road", "street", "city", "landscape", "beach",
        "mountain", "forest", "park", "building", "house", "room",
        "interior", "outdoor", "sky", "sunset", "sunrise", "driving",
        "parking", "traffic", "accident", "breakdown", "crowd", "group",
        "family", "restaurant", "dining", "concert", "festival",
        "wedding", "ceremony", "meeting", "party", "office", "store",
        "shop", "mall", "gym", "stadium", "arena",
    )


@dataclass(frozen=True)
class SearchConfig:
    priority:             List[str] = field(default_factory=lambda: [
        "google", "duckduckgo", "bing",
    ])
    adv_search_term:      str   = "product image"
    min_results_fallback: int   = 10
    inter_engine_delay:   float = 0.5
    per_request_delay:    float = 0.3
    rate_limit_per_sec:   float = 2.0
    breaker_threshold:    int   = 5
    breaker_cooldown:     float = 120.0


@dataclass(frozen=True)
class ProxyConfig:
    enabled:       bool = ENABLE_PROXY_ROTATION
    rotation_mode: str  = "round_robin"
    max_failures:  int  = 3
    test_url:      str  = "https://httpbin.org/ip"
    test_timeout:  int  = 5


@dataclass(frozen=True)
class NotificationConfig:
    enabled:         bool = ENABLE_NOTIFICATIONS
    webhook_url:     str  = ""
    email_to:        str  = ""
    smtp_host:       str  = ""
    smtp_port:       int  = 587
    smtp_user:       str  = ""
    smtp_pass:       str  = ""
    notify_on:       Tuple[str, ...] = ("completion", "failure", "milestone")
    milestone_every: int  = 100


@dataclass(frozen=True)
class OutputConfig:
    primary_size:      Tuple[int, int] = (1080, 1080)
    jpeg_quality:      int = 95


@dataclass(frozen=True)
class PipelineConfig:
    max_workers:       int   = 4
    inter_ad_delay:    float = 0.5
    csv_save_interval: int   = 5
    download_timeout:  int   = 10
    worker_timeout:    int   = 300


@dataclass
class AppConfig:
    paths:        PathConfig              = field(default_factory=PathConfig)
    quality:      ImageQualityConfig      = field(default_factory=ImageQualityConfig)
    bg:           BackgroundRemovalConfig = field(default_factory=BackgroundRemovalConfig)
    search:       SearchConfig            = field(default_factory=SearchConfig)
    query:        QueryConfig             = field(default_factory=QueryConfig)
    verify:       VerificationConfig      = field(default_factory=VerificationConfig)
    proxy:        ProxyConfig             = field(default_factory=ProxyConfig)
    notify:       NotificationConfig      = field(default_factory=NotificationConfig)
    output:       OutputConfig            = field(default_factory=OutputConfig)
    pipeline:     PipelineConfig          = field(default_factory=PipelineConfig)

    resume:        bool         = RESUME_FROM_PROGRESS
    dry_run:       bool         = DRY_RUN
    verbose:       bool         = VERBOSE_LOGGING
    remove_temp:   bool         = REMOVE_TEMP_ON_FINISH
    start_index:   int | None   = START_INDEX
    end_index:     int | None   = END_INDEX
    enable_cache:  bool         = ENABLE_IMAGE_CACHE
    enable_async:  bool         = ENABLE_ASYNC_DOWNLOAD
    enable_health: bool         = ENABLE_HEALTH_MONITOR
    enable_dlq:    bool         = ENABLE_DEAD_LETTER
    dlq_retries:   int          = DEAD_LETTER_MAX_RETRIES
    chunk_size:    int          = CHUNK_SIZE
    multi_size:    bool         = ENABLE_MULTI_SIZE
    watermark:     bool         = ENABLE_WATERMARK

    def validate(self) -> None:
        if not self.paths.csv_input.exists():
            raise FileNotFoundError(f"Input CSV missing: {self.paths.csv_input}")
        if self.pipeline.max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        for eng in self.search.priority:
            if eng not in ("google", "duckduckgo", "bing"):
                raise ValueError(f"Unknown engine: {eng}")


cfg = AppConfig()


COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
    "Red":    (220,  20,  60), "Blue":   (  0, 102, 204),
    "Green":  ( 34, 139,  34), "Yellow": (255, 193,   7),
    "Orange": (255, 102,   0), "Pink":   (255, 105, 180),
    "Purple": (128,   0, 128), "Black":  ( 45,  45,  45),
    "White":  (255, 255, 255), "Brown":  (139,  69,  19),
    "Grey":   (128, 128, 128),
}

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}