# # # # # """
# # # # # Main pipeline — multi-threaded orchestrator.

# # # # #     CSV row → search → download → bg-remove → composite → save
# # # # # """

# # # # # from __future__ import annotations

# # # # # import gc
# # # # # import re
# # # # # import shutil
# # # # # import signal
# # # # # import threading
# # # # # import time
# # # # # from concurrent.futures import ThreadPoolExecutor, as_completed
# # # # # from pathlib import Path
# # # # # from typing import Any, Dict, List

# # # # # import pandas as pd

# # # # # from config.settings import AppConfig
# # # # # from core.compositor import AdCompositor
# # # # # from core.progress import ProgressManager
# # # # # from imaging.background import BackgroundRemover
# # # # # from imaging.downloader import ImageDownloader
# # # # # from search.manager import SearchManager
# # # # # from utils.concurrency import AtomicCounter
# # # # # from utils.log_config import get_logger

# # # # # log = get_logger(__name__)


# # # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # # # #  STATISTICS
# # # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # # # class Stats:
# # # # #     def __init__(self) -> None:
# # # # #         self.total       = AtomicCounter()
# # # # #         self.success     = AtomicCounter()
# # # # #         self.failed      = AtomicCounter()
# # # # #         self.placeholder = AtomicCounter()
# # # # #         self.bg_removed  = AtomicCounter()
# # # # #         self.bg_skipped  = AtomicCounter()
# # # # #         self.skipped     = AtomicCounter()
# # # # #         self._t0         = time.monotonic()

# # # # #     def report(self) -> str:
# # # # #         elapsed = time.monotonic() - self._t0
# # # # #         tps = self.total.value / max(elapsed, 0.1)
# # # # #         return (
# # # # #             "\n" + "=" * 60
# # # # #             + "\n📊  PIPELINE REPORT"
# # # # #             + f"\n{'─' * 60}"
# # # # #             + f"\n  Processed    : {self.total.value}"
# # # # #             + f"\n  Success      : {self.success.value}"
# # # # #             + f"\n  Failed       : {self.failed.value}"
# # # # #             + f"\n  Placeholders : {self.placeholder.value}"
# # # # #             + f"\n  BG removed   : {self.bg_removed.value}"
# # # # #             + f"\n  BG skipped   : {self.bg_skipped.value}"
# # # # #             + f"\n  Already done : {self.skipped.value}"
# # # # #             + f"\n  Elapsed      : {elapsed:.1f}s"
# # # # #             + f"\n  Throughput   : {tps:.2f} ads/s"
# # # # #             + f"\n{'=' * 60}\n"
# # # # #         )


# # # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # # # #  QUERY BUILDER
# # # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # # # _IGNORED = frozenset({"nan", "none", "", "general", "food", "automotive", "object"})


# # # # # def build_query(row: pd.Series) -> str:
# # # # #     for col in ("keywords", "object_detected"):
# # # # #         val = str(row.get(col, "")).strip()
# # # # #         if val and val.lower() not in _IGNORED:
# # # # #             return " ".join(val.split()[:3])
# # # # #     text = re.sub(r"[^\w\s]", "", str(row.get("text", "")))
# # # # #     return " ".join(text.split()[:3])


# # # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # # # #  PIPELINE
# # # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # # # class AdPipeline:

# # # # #     def __init__(self, cfg: AppConfig) -> None:
# # # # #         self.cfg = cfg
# # # # #         cfg.paths.ensure()
# # # # #         cfg.validate()

# # # # #         self.df = pd.read_csv(cfg.paths.csv_input)
# # # # #         if "image_path" not in self.df.columns:
# # # # #             self.df["image_path"] = ""

# # # # #         self.search    = SearchManager(cfg.search)
# # # # #         self.download  = ImageDownloader(
# # # # #             cfg.quality,
# # # # #             self.search.downloaded_hashes,
# # # # #             timeout=cfg.pipeline.download_timeout,
# # # # #         )
# # # # #         self.bg        = BackgroundRemover(cfg.bg)
# # # # #         self.comp      = AdCompositor()
# # # # #         self.progress  = ProgressManager(cfg.paths.progress)
# # # # #         self.stats     = Stats()

# # # # #         self._df_lock   = threading.Lock()
# # # # #         self._csv_cnt   = AtomicCounter()
# # # # #         self._shutdown  = threading.Event()

# # # # #         signal.signal(signal.SIGINT,  self._on_signal)
# # # # #         signal.signal(signal.SIGTERM, self._on_signal)

# # # # #     def _on_signal(self, signum: int, _: Any) -> None:
# # # # #         log.warning("Signal %d received — graceful shutdown", signum)
# # # # #         self._shutdown.set()

# # # # #     # ── per-worker temp dir ─────────────────────────────────
# # # # #     @staticmethod
# # # # #     def _worker_dir(base: Path, wid: int) -> Path:
# # # # #         d = base / f"w{wid}"
# # # # #         d.mkdir(parents=True, exist_ok=True)
# # # # #         return d

# # # # #     # ── atomic CSV save ─────────────────────────────────────
# # # # #     def _save_csv(self) -> None:
# # # # #         with self._df_lock:
# # # # #             tmp = self.cfg.paths.csv_output.with_suffix(".tmp")
# # # # #             self.df.to_csv(tmp, index=False)
# # # # #             tmp.replace(self.cfg.paths.csv_output)

# # # # #     # ── single row processor ────────────────────────────────
# # # # #     def _process(self, idx: int) -> Dict[str, Any]:
# # # # #         meta: Dict[str, Any] = {"id": idx, "success": False, "filename": ""}

# # # # #         if self._shutdown.is_set():
# # # # #             meta["skipped"] = True
# # # # #             return meta

# # # # #         row = self.df.iloc[idx]
# # # # #         query = build_query(row)
# # # # #         meta["query"] = query

# # # # #         out_name = f"ad_{idx + 1:04d}.jpg"
# # # # #         out_path = self.cfg.paths.images_dir / out_name
# # # # #         meta["filename"] = out_name

# # # # #         tid = threading.current_thread().ident or 0
# # # # #         tmp = self._worker_dir(self.cfg.paths.temp_dir, tid % 100)
# # # # #         tmp_img  = tmp / f"dl_{idx}.jpg"
# # # # #         tmp_nobg = tmp / f"nobg_{idx}.png"

# # # # #         log.info("[%d/%d] q='%s'", idx + 1, len(self.df), query)

# # # # #         try:
# # # # #             # 1. search + download
# # # # #             results = self.search.search(query)
# # # # #             dl = self.download.download_best(results, tmp_img)

# # # # #             if not dl.success:
# # # # #                 fb = str(row.get("object_detected", ""))
# # # # #                 if fb and fb.lower() not in _IGNORED and fb.lower() != query.lower():
# # # # #                     log.info("Fallback query: '%s'", fb)
# # # # #                     dl = self.download.download_best(
# # # # #                         self.search.search(fb), tmp_img,
# # # # #                     )

# # # # #             if not dl.success or dl.path is None:
# # # # #                 self.stats.placeholder.increment()
# # # # #                 dl_path = self.comp.placeholder(query, tmp_img)
# # # # #             else:
# # # # #                 dl_path = dl.path

# # # # #             # 2. background removal
# # # # #             use_orig = True
# # # # #             if self.bg.should_remove(query):
# # # # #                 bg_res = self.bg.remove(dl_path, tmp_nobg)
# # # # #                 use_orig = bg_res.use_original
# # # # #                 if not use_orig:
# # # # #                     self.stats.bg_removed.increment()
# # # # #             else:
# # # # #                 self.stats.bg_skipped.increment()

# # # # #             # 3. composite
# # # # #             nobg_for = tmp_nobg if (not use_orig and tmp_nobg.exists()) else None
# # # # #             if not self.cfg.dry_run:
# # # # #                 self.comp.compose(
# # # # #                     product_path=dl_path,
# # # # #                     nobg_path=nobg_for,
# # # # #                     use_original=use_orig,
# # # # #                     row=row,
# # # # #                     output=out_path,
# # # # #                 )

# # # # #             # 4. update dataframe
# # # # #             rel = f"data/output/images/{out_name}"
# # # # #             with self._df_lock:
# # # # #                 self.df.at[idx, "image_path"] = rel

# # # # #             meta["success"] = True
# # # # #             meta["source"]  = dl.info.get("source_engine", "placeholder")
# # # # #             self.stats.success.increment()

# # # # #         except Exception as exc:
# # # # #             log.exception("Row %d failed", idx)
# # # # #             meta["error"] = str(exc)
# # # # #             self.stats.failed.increment()

# # # # #         finally:
# # # # #             for f in (tmp_img, tmp_nobg):
# # # # #                 try:
# # # # #                     f.unlink(missing_ok=True)
# # # # #                 except OSError:
# # # # #                     pass

# # # # #             self.stats.total.increment()
# # # # #             if self._csv_cnt.increment() % self.cfg.pipeline.csv_save_interval == 0:
# # # # #                 self._save_csv()

# # # # #         return meta

# # # # #     # ── main entry ──────────────────────────────────────────
# # # # #     def run(self) -> None:
# # # # #         total = len(self.df)
# # # # #         lo = self.cfg.start_index or 0
# # # # #         hi = self.cfg.end_index or total

# # # # #         indices = [
# # # # #             i for i in range(lo, min(hi, total))
# # # # #             if not (self.cfg.resume and self.progress.is_done(i))
# # # # #         ]
# # # # #         self.stats.skipped.increment((hi - lo) - len(indices))

# # # # #         log.info(
# # # # #             "Pipeline: %d to process, %d skipped, workers=%d",
# # # # #             len(indices),
# # # # #             self.stats.skipped.value,
# # # # #             self.cfg.pipeline.max_workers,
# # # # #         )

# # # # #         workers = self.cfg.pipeline.max_workers

# # # # #         if workers <= 1:
# # # # #             for idx in indices:
# # # # #                 if self._shutdown.is_set():
# # # # #                     break
# # # # #                 meta = self._process(idx)
# # # # #                 self.progress.mark_done(idx, meta)
# # # # #                 time.sleep(self.cfg.pipeline.inter_ad_delay)
# # # # #         else:
# # # # #             with ThreadPoolExecutor(
# # # # #                 max_workers=workers,
# # # # #                 thread_name_prefix="adgen",
# # # # #             ) as pool:
# # # # #                 futs = {pool.submit(self._process, i): i for i in indices}
# # # # #                 for fut in as_completed(futs):
# # # # #                     if self._shutdown.is_set():
# # # # #                         pool.shutdown(wait=False, cancel_futures=True)
# # # # #                         break
# # # # #                     idx = futs[fut]
# # # # #                     try:
# # # # #                         meta = fut.result(timeout=self.cfg.pipeline.worker_timeout)
# # # # #                         self.progress.mark_done(idx, meta)
# # # # #                     except Exception as exc:
# # # # #                         log.error("Worker crash idx=%d: %s", idx, exc)
# # # # #                         self.stats.failed.increment()

# # # # #         # final save + cleanup
# # # # #         self._save_csv()
# # # # #         log.info(self.stats.report())
# # # # #         log.info("CSV → %s", self.cfg.paths.csv_output)

# # # # #         if self.cfg.remove_temp:
# # # # #             self._cleanup()

# # # # #     def _cleanup(self) -> None:
# # # # #         try:
# # # # #             if self.cfg.paths.temp_dir.exists():
# # # # #                 shutil.rmtree(self.cfg.paths.temp_dir, ignore_errors=True)
# # # # #                 log.info("Cleaned temp directory")
# # # # #         except Exception as exc:
# # # # #             log.warning("Cleanup failed: %s", exc)


# # # # """
# # # # Main pipeline with:
# # # #   - Chunked processing (memory-efficient)
# # # #   - Dead-letter queue (retry failed rows)
# # # #   - Health monitoring
# # # #   - Notifications
# # # #   - Image cache
# # # #   - Multi-size output
# # # # """

# # # # from __future__ import annotations

# # # # import gc
# # # # import re
# # # # import shutil
# # # # import signal
# # # # import threading
# # # # import time
# # # # from concurrent.futures import ThreadPoolExecutor, as_completed
# # # # from pathlib import Path
# # # # from typing import Any, Dict, List

# # # # import pandas as pd

# # # # from config.settings import AppConfig
# # # # from config.templates import ALL_TEMPLATES, DEFAULT_TEMPLATE
# # # # from core.compositor import AdCompositor
# # # # from core.health import HealthMonitor
# # # # from core.progress import ProgressManager
# # # # from imaging.background import BackgroundRemover
# # # # from imaging.cache import ImageCache
# # # # from imaging.downloader import ImageDownloader
# # # # from imaging.scorer import ImageQualityScorer
# # # # from notifications.notifier import Notifier
# # # # from search.manager import SearchManager
# # # # from utils.concurrency import AtomicCounter
# # # # from utils.log_config import get_logger

# # # # log = get_logger(__name__)


# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # # #  STATS
# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # # class Stats:
# # # #     def __init__(self) -> None:
# # # #         self.total        = AtomicCounter()
# # # #         self.success      = AtomicCounter()
# # # #         self.failed       = AtomicCounter()
# # # #         self.placeholder  = AtomicCounter()
# # # #         self.bg_removed   = AtomicCounter()
# # # #         self.bg_skipped   = AtomicCounter()
# # # #         self.skipped      = AtomicCounter()
# # # #         self.cache_hits   = AtomicCounter()
# # # #         self.dlq_retries  = AtomicCounter()
# # # #         self._t0          = time.monotonic()

# # # #     @property
# # # #     def elapsed(self) -> float:
# # # #         return time.monotonic() - self._t0

# # # #     def report(self) -> str:
# # # #         e = self.elapsed
# # # #         return (
# # # #             "\n" + "=" * 60
# # # #             + "\n📊  PIPELINE REPORT"
# # # #             + f"\n{'─' * 60}"
# # # #             + f"\n  Processed     : {self.total.value}"
# # # #             + f"\n  Success       : {self.success.value}"
# # # #             + f"\n  Failed        : {self.failed.value}"
# # # #             + f"\n  Placeholders  : {self.placeholder.value}"
# # # #             + f"\n  BG removed    : {self.bg_removed.value}"
# # # #             + f"\n  BG skipped    : {self.bg_skipped.value}"
# # # #             + f"\n  Cache hits    : {self.cache_hits.value}"
# # # #             + f"\n  DLQ retries   : {self.dlq_retries.value}"
# # # #             + f"\n  Already done  : {self.skipped.value}"
# # # #             + f"\n  Elapsed       : {e:.1f}s"
# # # #             + f"\n  Throughput    : {self.total.value / max(e, 0.1):.2f} ads/s"
# # # #             + f"\n{'=' * 60}\n"
# # # #         )


# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # # #  QUERY BUILDER
# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # # _IGNORED = frozenset({
# # # #     "nan", "none", "", "general", "food", "automotive", "object",
# # # # })


# # # # def build_query(row: pd.Series) -> str:
# # # #     # for col in ("keywords", "object_detected"):
# # # #     #     val = str(row.get(col, "")).strip()
# # # #     #     if val and val.lower() not in _IGNORED:
# # # #     #         return " ".join(val.split()[:3])
# # # #     text = re.sub(r"[^\w\s]", "", str(row.get("img_desc", "")))
# # # #     return " ".join(text)


# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # # #  PIPELINE
# # # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # # class AdPipeline:

# # # #     def __init__(self, cfg: AppConfig) -> None:
# # # #         self.cfg = cfg
# # # #         cfg.paths.ensure()
# # # #         cfg.validate()

# # # #         self.df = pd.read_csv(cfg.paths.csv_input)
# # # #         if "image_path" not in self.df.columns:
# # # #             self.df["image_path"] = ""

# # # #         # ── components ──
# # # #         self.search   = SearchManager(cfg.search)
# # # #         self.scorer   = ImageQualityScorer(cfg.quality)
# # # #         self.download = ImageDownloader(
# # # #             cfg.quality,
# # # #             self.search.downloaded_hashes,
# # # #             timeout=cfg.pipeline.download_timeout,
# # # #             scorer=self.scorer,
# # # #         )
# # # #         self.bg       = BackgroundRemover(cfg.bg)
# # # #         self.comp     = AdCompositor(cfg.paths.fonts_dir)
# # # #         self.progress = ProgressManager(
# # # #             cfg.paths.progress_db,
# # # #             max_retries=cfg.dlq_retries,
# # # #         )
# # # #         self.stats    = Stats()
# # # #         self.notifier = Notifier(cfg.notify)
# # # #         self.health   = HealthMonitor() if cfg.enable_health else None

# # # #         # ── cache ──
# # # #         self.cache: ImageCache | None = None
# # # #         if cfg.enable_cache:
# # # #             self.cache = ImageCache(cfg.paths.cache_db)

# # # #         # ── threading ──
# # # #         self._df_lock  = threading.Lock()
# # # #         self._csv_cnt  = AtomicCounter()
# # # #         self._shutdown = threading.Event()

# # # #         signal.signal(signal.SIGINT,  self._on_signal)
# # # #         signal.signal(signal.SIGTERM, self._on_signal)

# # # #     def _on_signal(self, signum: int, _: Any) -> None:
# # # #         log.warning("Signal %d — shutting down gracefully", signum)
# # # #         self._shutdown.set()

# # # #     @staticmethod
# # # #     def _worker_dir(base: Path, wid: int) -> Path:
# # # #         d = base / f"w{wid}"
# # # #         d.mkdir(parents=True, exist_ok=True)
# # # #         return d

# # # #     def _save_csv(self) -> None:
# # # #         with self._df_lock:
# # # #             tmp = self.cfg.paths.csv_output.with_suffix(".tmp")
# # # #             self.df.to_csv(tmp, index=False)
# # # #             tmp.replace(self.cfg.paths.csv_output)

# # # #     # ── single row ──────────────────────────────────────────
# # # #     def _process(self, idx: int) -> Dict[str, Any]:
# # # #         meta: Dict[str, Any] = {"id": idx, "success": False}

# # # #         if self._shutdown.is_set():
# # # #             meta["skipped"] = True
# # # #             return meta

# # # #         row = self.df.iloc[idx]
# # # #         query = build_query(row)
# # # #         meta["query"] = query

# # # #         out_name = f"ad_{idx + 1:04d}.jpg"
# # # #         out_path = self.cfg.paths.images_dir / out_name
# # # #         meta["filename"] = out_name

# # # #         tid = threading.current_thread().ident or 0
# # # #         tmp = self._worker_dir(self.cfg.paths.temp_dir, tid % 100)
# # # #         tmp_img  = tmp / f"dl_{idx}.jpg"
# # # #         tmp_nobg = tmp / f"nobg_{idx}.png"

# # # #         log.info("[%d/%d] q='%s'", idx + 1, len(self.df), query)

# # # #         try:
# # # #             dl_path = None

# # # #             # ── 0. CHECK CACHE ──
# # # #             if self.cache:
# # # #                 cached = self.cache.get(query)
# # # #                 if cached and Path(cached["file_path"]).exists():
# # # #                     log.info("Cache hit — skipping download")
# # # #                     import shutil
# # # #                     shutil.copy2(cached["file_path"], tmp_img)
# # # #                     dl_path = tmp_img
# # # #                     self.stats.cache_hits.increment()
# # # #                     meta["source"] = "cache"

# # # #             # ── 1. SEARCH + DOWNLOAD ──
# # # #             if dl_path is None:
# # # #                 t0 = time.monotonic()
# # # #                 results = self.search.search(query)

# # # #                 if self.health:
# # # #                     for eng_name in self.cfg.search.priority:
# # # #                         eng_results = [r for r in results if r.source == eng_name]
# # # #                         if eng_results:
# # # #                             self.health.record_call(
# # # #                                 eng_name, True,
# # # #                                 len(eng_results),
# # # #                                 time.monotonic() - t0,
# # # #                             )

# # # #                 dl = self.download.download_best(results, tmp_img)

# # # #                 if not dl.success:
# # # #                     fb = str(row.get("object_detected", ""))
# # # #                     if fb and fb.lower() not in _IGNORED and fb.lower() != query.lower():
# # # #                         log.info("Fallback: '%s'", fb)
# # # #                         dl = self.download.download_best(
# # # #                             self.search.search(fb), tmp_img,
# # # #                         )

# # # #                 if not dl.success or dl.path is None:
# # # #                     self.stats.placeholder.increment()
# # # #                     dl_path = self.comp.placeholder(query, tmp_img)
# # # #                     meta["source"] = "placeholder"
# # # #                 else:
# # # #                     dl_path = dl.path
# # # #                     meta["source"] = dl.info.get("source_engine", "unknown")

# # # #                     # store in cache
# # # #                     if self.cache and dl.source_url:
# # # #                         self.cache.put(
# # # #                             query=query,
# # # #                             source_url=dl.source_url,
# # # #                             file_path=str(dl_path),
# # # #                             file_hash=dl.info.get("hash", ""),
# # # #                             width=dl.info.get("width", 0),
# # # #                             height=dl.info.get("height", 0),
# # # #                             file_size=dl.info.get("file_size", 0),
# # # #                             source_engine=dl.info.get("source_engine", ""),
# # # #                         )

# # # #             # ── 2. BACKGROUND REMOVAL ──
# # # #             use_orig = True
# # # #             if self.bg.should_remove(query):
# # # #                 bg_res = self.bg.remove(dl_path, tmp_nobg)
# # # #                 use_orig = bg_res.use_original
# # # #                 if not use_orig:
# # # #                     self.stats.bg_removed.increment()
# # # #             else:
# # # #                 self.stats.bg_skipped.increment()

# # # #             # ── 3. COMPOSE ──
# # # #             nobg = tmp_nobg if (not use_orig and tmp_nobg.exists()) else None
# # # #             if not self.cfg.dry_run:
# # # #                 self.comp.compose(
# # # #                     product_path=dl_path,
# # # #                     nobg_path=nobg,
# # # #                     use_original=use_orig,
# # # #                     row=row,
# # # #                     output=out_path,
# # # #                 )

# # # #                 # ── 3b. MULTI-SIZE ──
# # # #                 if self.cfg.multi_size:
# # # #                     for tpl_name, tpl in ALL_TEMPLATES.items():
# # # #                         if tpl_name == DEFAULT_TEMPLATE:
# # # #                             continue
# # # #                         extra_out = out_path.with_name(
# # # #                             f"ad_{idx + 1:04d}_{tpl_name}.jpg"
# # # #                         )
# # # #                         self.comp.compose(
# # # #                             product_path=dl_path,
# # # #                             nobg_path=nobg,
# # # #                             use_original=use_orig,
# # # #                             row=row,
# # # #                             output=extra_out,
# # # #                             template_name=tpl_name,
# # # #                         )

# # # #             # ── 4. UPDATE DF ──
# # # #             rel = f"data/output/images/{out_name}"
# # # #             with self._df_lock:
# # # #                 self.df.at[idx, "image_path"] = rel

# # # #             meta["success"] = True
# # # #             self.stats.success.increment()

# # # #             # milestone notification
# # # #             self.notifier.on_milestone(self.stats.success.value)

# # # #         except Exception as exc:
# # # #             log.exception("Row %d failed", idx)
# # # #             meta["error"] = str(exc)
# # # #             self.stats.failed.increment()
# # # #             self.notifier.on_failure(idx, str(exc))

# # # #         finally:
# # # #             for f in (tmp_img, tmp_nobg):
# # # #                 try:
# # # #                     f.unlink(missing_ok=True)
# # # #                 except OSError:
# # # #                     pass
# # # #             self.stats.total.increment()
# # # #             if self._csv_cnt.increment() % self.cfg.pipeline.csv_save_interval == 0:
# # # #                 self._save_csv()
# # # #             gc.collect()

# # # #         return meta

# # # #     # ── chunked execution ───────────────────────────────────
# # # #     def _run_indices(self, indices: List[int]) -> None:
# # # #         """Process a list of indices with the thread pool."""
# # # #         workers = self.cfg.pipeline.max_workers

# # # #         if workers <= 1:
# # # #             for idx in indices:
# # # #                 if self._shutdown.is_set():
# # # #                     break
# # # #                 meta = self._process(idx)
# # # #                 if meta.get("success"):
# # # #                     self.progress.mark_done(idx, meta)
# # # #                 elif not meta.get("skipped"):
# # # #                     self.progress.mark_failed(idx, meta)
# # # #                 time.sleep(self.cfg.pipeline.inter_ad_delay)
# # # #         else:
# # # #             with ThreadPoolExecutor(
# # # #                 max_workers=workers,
# # # #                 thread_name_prefix="adgen",
# # # #             ) as pool:
# # # #                 futs = {pool.submit(self._process, i): i for i in indices}
# # # #                 for fut in as_completed(futs):
# # # #                     if self._shutdown.is_set():
# # # #                         pool.shutdown(wait=False, cancel_futures=True)
# # # #                         break
# # # #                     idx = futs[fut]
# # # #                     try:
# # # #                         meta = fut.result(timeout=self.cfg.pipeline.worker_timeout)
# # # #                         if meta.get("success"):
# # # #                             self.progress.mark_done(idx, meta)
# # # #                         elif not meta.get("skipped"):
# # # #                             self.progress.mark_failed(idx, meta)
# # # #                     except Exception as exc:
# # # #                         log.error("Worker crash idx=%d: %s", idx, exc)
# # # #                         self.progress.mark_failed(idx, {"error": str(exc)})
# # # #                         self.stats.failed.increment()

# # # #     # ── main ────────────────────────────────────────────────
# # # #     def run(self) -> None:
# # # #         total = len(self.df)
# # # #         lo = self.cfg.start_index or 0
# # # #         hi = self.cfg.end_index or total

# # # #         all_indices = list(range(lo, min(hi, total)))
# # # #         if self.cfg.resume:
# # # #             indices = [i for i in all_indices if not self.progress.is_done(i)]
# # # #         else:
# # # #             indices = all_indices

# # # #         self.stats.skipped.increment(len(all_indices) - len(indices))

# # # #         log.info(
# # # #             "Pipeline: %d to process, %d skipped, workers=%d, chunks=%d",
# # # #             len(indices), self.stats.skipped.value,
# # # #             self.cfg.pipeline.max_workers, self.cfg.chunk_size,
# # # #         )

# # # #         # ── process in chunks (memory control) ──
# # # #         chunk = self.cfg.chunk_size
# # # #         for i in range(0, len(indices), chunk):
# # # #             if self._shutdown.is_set():
# # # #                 break
# # # #             batch = indices[i : i + chunk]
# # # #             log.info("── Chunk %d–%d ──", batch[0], batch[-1])
# # # #             self._run_indices(batch)
# # # #             gc.collect()

# # # #         # ── dead-letter queue ──
# # # #         if self.cfg.enable_dlq and not self._shutdown.is_set():
# # # #             dlq = self.progress.get_dead_letters()
# # # #             if dlq:
# # # #                 log.info("── Dead-letter retry: %d rows ──", len(dlq))
# # # #                 self.stats.dlq_retries.increment(len(dlq))
# # # #                 self._run_indices(dlq)

# # # #         # ── final writes ──
# # # #         self._save_csv()

# # # #         # ── health report ──
# # # #         if self.health:
# # # #             self.health.log_report()

# # # #         # ── cache stats ──
# # # #         if self.cache:
# # # #             log.info("Cache stats: %s", self.cache.stats())

# # # #         # ── progress stats ──
# # # #         log.info("Progress DB: %s", self.progress.stats())

# # # #         # ── final report ──
# # # #         log.info(self.stats.report())
# # # #         log.info("CSV → %s", self.cfg.paths.csv_output)

# # # #         # ── notify ──
# # # #         self.notifier.on_completion(
# # # #             self.stats.total.value,
# # # #             self.stats.success.value,
# # # #             self.stats.elapsed,
# # # #         )

# # # #         # ── cleanup ──
# # # #         if self.cfg.remove_temp:
# # # #             self._cleanup()

# # # #     def _cleanup(self) -> None:
# # # #         try:
# # # #             if self.cfg.paths.temp_dir.exists():
# # # #                 shutil.rmtree(self.cfg.paths.temp_dir, ignore_errors=True)
# # # #                 log.info("Temp directory cleaned")
# # # #         except Exception as exc:
# # # #             log.warning("Cleanup failed: %s", exc)


# # # """
# # # Main pipeline with all improvements.
# # # """

# # # from __future__ import annotations

# # # import gc
# # # import re
# # # import shutil
# # # import signal
# # # import threading
# # # import time
# # # from concurrent.futures import ThreadPoolExecutor, as_completed
# # # from pathlib import Path
# # # from typing import Any, Dict, List

# # # import pandas as pd

# # # from config.settings import AppConfig
# # # from core.compositor import AdCompositor
# # # from core.health import HealthMonitor
# # # from core.progress import ProgressManager
# # # from imaging.background import BackgroundRemover
# # # from imaging.cache import ImageCache
# # # from imaging.downloader import ImageDownloader
# # # from imaging.scorer import ImageQualityScorer
# # # from notifications.notifier import Notifier
# # # from search.manager import SearchManager
# # # from utils.concurrency import AtomicCounter
# # # from utils.log_config import get_logger

# # # log = get_logger(__name__)


# # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # #  STATS
# # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # class Stats:
# # #     def __init__(self) -> None:
# # #         self.total        = AtomicCounter()
# # #         self.success      = AtomicCounter()
# # #         self.failed       = AtomicCounter()
# # #         self.placeholder  = AtomicCounter()
# # #         self.bg_removed   = AtomicCounter()
# # #         self.bg_skipped   = AtomicCounter()
# # #         self.skipped      = AtomicCounter()
# # #         self.cache_hits   = AtomicCounter()
# # #         self.dlq_retries  = AtomicCounter()
# # #         self._t0          = time.monotonic()

# # #     @property
# # #     def elapsed(self) -> float:
# # #         return time.monotonic() - self._t0

# # #     def report(self) -> str:
# # #         e = self.elapsed
# # #         return (
# # #             "\n" + "=" * 60
# # #             + "\n📊  PIPELINE REPORT"
# # #             + f"\n{'─' * 60}"
# # #             + f"\n  Processed     : {self.total.value}"
# # #             + f"\n  Success       : {self.success.value}"
# # #             + f"\n  Failed        : {self.failed.value}"
# # #             + f"\n  Placeholders  : {self.placeholder.value}"
# # #             + f"\n  BG removed    : {self.bg_removed.value}"
# # #             + f"\n  BG skipped    : {self.bg_skipped.value}"
# # #             + f"\n  Cache hits    : {self.cache_hits.value}"
# # #             + f"\n  DLQ retries   : {self.dlq_retries.value}"
# # #             + f"\n  Already done  : {self.skipped.value}"
# # #             + f"\n  Elapsed       : {e:.1f}s"
# # #             + f"\n  Throughput    : {self.total.value / max(e, 0.1):.2f} ads/s"
# # #             + f"\n{'=' * 60}\n"
# # #         )


# # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # #  QUERY BUILDER (FIXED)
# # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # _IGNORED = frozenset({
# # #     "nan", "none", "", "general", "food", "automotive", "object",
# # # })


# # # def clean_query(text: str) -> str:
# # #     """
# # #     Clean and normalize query text.
    
# # #     Fixes:
# # #     - Characters separated by spaces: "p i z z a" → "pizza"
# # #     - Multiple spaces → single space
# # #     - Special characters removed
# # #     - Strip whitespace
# # #     """
# # #     if not text:
# # #         return ""
    
# # #     # Convert to string and strip
# # #     text = str(text).strip()
    
# # #     # Check if text has character-by-character spacing
# # #     # Pattern: single chars separated by spaces like "p i z z a"
# # #     words = text.split()
    
# # #     # If all "words" are single characters, join them without spaces
# # #     # Example: ["p", "i", "z", "z", "a"] → "pizza"
# # #     if words and all(len(w) == 1 for w in words):
# # #         # This is character-by-character text, reconstruct words
# # #         # Join all chars, then split on multiple spaces (which were originally word boundaries)
# # #         reconstructed = ""
# # #         i = 0
# # #         original_with_spaces = text
        
# # #         # Find runs of single chars separated by single spaces vs multiple spaces
# # #         # "p i z z a   s l i c e" → "pizza slice"
# # #         char_groups = re.split(r'\s{2,}', text)  # Split on 2+ spaces
        
# # #         reconstructed_words = []
# # #         for group in char_groups:
# # #             # Each group is like "p i z z a" - join the chars
# # #             chars = group.split()
# # #             if chars:
# # #                 reconstructed_words.append("".join(chars))
        
# # #         text = " ".join(reconstructed_words)
    
# # #     # Remove special characters except spaces
# # #     text = re.sub(r'[^\w\s]', '', text)
    
# # #     # Normalize whitespace (multiple spaces → single)
# # #     text = re.sub(r'\s+', ' ', text).strip()
    
# # #     return text


# # # def build_query(row: pd.Series) -> str:
# # #     """
# # #     Build search query from CSV row.
    
# # #     Priority:
# # #         1. keywords       (first 3 words)
# # #         2. object_detected (first 3 words)  
# # #         3. text           (first 3 words)
    
# # #     All values are cleaned to fix spacing issues.
# # #     """
# # #     # Priority 1: Try "keywords" column
# # #     # Priority 2: Try "object_detected" column
# # #     # for col in ("keywords", "object_detected"):
# # #     #     val = str(row.get(col, "")).strip()
# # #     #     if val and val.lower() not in _IGNORED:
# # #     #         cleaned = clean_query(val)
# # #     #         if cleaned:
# # #     #             words = cleaned.split()[:3]
# # #     #             query = " ".join(words)
# # #     #             log.debug("Query from '%s': raw='%s' → cleaned='%s'", col, val[:30], query)
# # #     #             return query
    
# # #     # Priority 3: Fall back to "text" column
# # #     text = str(row.get("img_desc", ""))
# # #     cleaned = clean_query(text)
# # #     words = cleaned
# # #     query = " ".join(words)
# # #     log.debug("Query from 'img_desc': raw='%s' → cleaned='%s'", query)
# # #     return query


# # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # # #  PIPELINE
# # # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # class AdPipeline:

# # #     def __init__(self, cfg: AppConfig) -> None:
# # #         self.cfg = cfg
# # #         cfg.paths.ensure()
# # #         cfg.validate()

# # #         self.df = pd.read_csv(cfg.paths.csv_input)
# # #         if "image_path" not in self.df.columns:
# # #             self.df["image_path"] = ""

# # #         # ── components ──
# # #         self.search   = SearchManager(cfg.search)
# # #         self.scorer   = ImageQualityScorer(cfg.quality)
# # #         self.download = ImageDownloader(
# # #             cfg.quality,
# # #             self.search.downloaded_hashes,
# # #             timeout=cfg.pipeline.download_timeout,
# # #             scorer=self.scorer,
# # #         )
# # #         self.bg       = BackgroundRemover(cfg.bg)
# # #         self.comp     = AdCompositor(cfg.paths.fonts_dir)
# # #         self.progress = ProgressManager(
# # #             cfg.paths.progress_db,
# # #             max_retries=cfg.dlq_retries,
# # #         )
# # #         self.stats    = Stats()
# # #         self.notifier = Notifier(cfg.notify)
# # #         self.health   = HealthMonitor() if cfg.enable_health else None

# # #         # ── cache ──
# # #         self.cache: ImageCache | None = None
# # #         if cfg.enable_cache:
# # #             self.cache = ImageCache(cfg.paths.cache_db)

# # #         # ── threading ──
# # #         self._df_lock  = threading.Lock()
# # #         self._csv_cnt  = AtomicCounter()
# # #         self._shutdown = threading.Event()

# # #         signal.signal(signal.SIGINT,  self._on_signal)
# # #         signal.signal(signal.SIGTERM, self._on_signal)

# # #     def _on_signal(self, signum: int, _: Any) -> None:
# # #         log.warning("Signal %d — shutting down gracefully", signum)
# # #         self._shutdown.set()

# # #     @staticmethod
# # #     def _worker_dir(base: Path, wid: int) -> Path:
# # #         d = base / f"w{wid}"
# # #         d.mkdir(parents=True, exist_ok=True)
# # #         return d

# # #     def _save_csv(self) -> None:
# # #         with self._df_lock:
# # #             tmp = self.cfg.paths.csv_output.with_suffix(".tmp")
# # #             self.df.to_csv(tmp, index=False)
# # #             tmp.replace(self.cfg.paths.csv_output)

# # #     # ── single row ──────────────────────────────────────────
# # #     def _process(self, idx: int) -> Dict[str, Any]:
# # #         meta: Dict[str, Any] = {"id": idx, "success": False}

# # #         if self._shutdown.is_set():
# # #             meta["skipped"] = True
# # #             return meta

# # #         row = self.df.iloc[idx]
# # #         query = build_query(row)
# # #         meta["query"] = query

# # #         out_name = f"ad_{idx + 1:04d}.jpg"
# # #         out_path = self.cfg.paths.images_dir / out_name
# # #         meta["filename"] = out_name

# # #         tid = threading.current_thread().ident or 0
# # #         tmp = self._worker_dir(self.cfg.paths.temp_dir, tid % 100)
# # #         tmp_img  = tmp / f"dl_{idx}.jpg"
# # #         tmp_nobg = tmp / f"nobg_{idx}.png"

# # #         log.info("[%d/%d] query='%s'", idx + 1, len(self.df), query)

# # #         try:
# # #             dl_path = None

# # #             # ── 0. CHECK CACHE ──
# # #             if self.cache:
# # #                 cached = self.cache.get(query)
# # #                 if cached and Path(cached["file_path"]).exists():
# # #                     log.info("Cache hit — skipping download")
# # #                     import shutil as shutil_mod
# # #                     shutil_mod.copy2(cached["file_path"], tmp_img)
# # #                     dl_path = tmp_img
# # #                     self.stats.cache_hits.increment()
# # #                     meta["source"] = "cache"

# # #             # ── 1. SEARCH + DOWNLOAD ──
# # #             if dl_path is None:
# # #                 t0 = time.monotonic()
# # #                 results = self.search.search(query)

# # #                 if self.health:
# # #                     for eng_name in self.cfg.search.priority:
# # #                         eng_results = [r for r in results if r.source == eng_name]
# # #                         if eng_results:
# # #                             self.health.record_call(
# # #                                 eng_name, True,
# # #                                 len(eng_results),
# # #                                 time.monotonic() - t0,
# # #                             )

# # #                 dl = self.download.download_best(results, tmp_img)

# # #                 if not dl.success:
# # #                     fb = str(row.get("object_detected", ""))
# # #                     fb_cleaned = clean_query(fb)
# # #                     if fb_cleaned and fb_cleaned.lower() not in _IGNORED and fb_cleaned.lower() != query.lower():
# # #                         log.info("Fallback: '%s'", fb_cleaned)
# # #                         dl = self.download.download_best(
# # #                             self.search.search(fb_cleaned), tmp_img,
# # #                         )

# # #                 if not dl.success or dl.path is None:
# # #                     self.stats.placeholder.increment()
# # #                     dl_path = self.comp.placeholder(query, tmp_img)
# # #                     meta["source"] = "placeholder"
# # #                 else:
# # #                     dl_path = dl.path
# # #                     meta["source"] = dl.info.get("source_engine", "unknown")

# # #                     # store in cache
# # #                     if self.cache and dl.source_url:
# # #                         self.cache.put(
# # #                             query=query,
# # #                             source_url=dl.source_url,
# # #                             file_path=str(dl_path),
# # #                             file_hash=dl.info.get("hash", ""),
# # #                             width=dl.info.get("width", 0),
# # #                             height=dl.info.get("height", 0),
# # #                             file_size=dl.info.get("file_size", 0),
# # #                             source_engine=dl.info.get("source_engine", ""),
# # #                         )

# # #             # ── 2. BACKGROUND REMOVAL ──
# # #             use_orig = True
# # #             if self.bg.should_remove(query):
# # #                 bg_res = self.bg.remove(dl_path, tmp_nobg)
# # #                 use_orig = bg_res.use_original
# # #                 if not use_orig:
# # #                     self.stats.bg_removed.increment()
# # #             else:
# # #                 self.stats.bg_skipped.increment()

# # #             # ── 3. COMPOSE ──
# # #             nobg = tmp_nobg if (not use_orig and tmp_nobg.exists()) else None
# # #             if not self.cfg.dry_run:
# # #                 self.comp.compose(
# # #                     product_path=dl_path,
# # #                     nobg_path=nobg,
# # #                     use_original=use_orig,
# # #                     row=row,
# # #                     output=out_path,
# # #                 )

# # #             # ── 4. UPDATE DF ──
# # #             rel = f"data/output/images/{out_name}"
# # #             with self._df_lock:
# # #                 self.df.at[idx, "image_path"] = rel

# # #             meta["success"] = True
# # #             self.stats.success.increment()

# # #             # milestone notification
# # #             self.notifier.on_milestone(self.stats.success.value)

# # #         except Exception as exc:
# # #             log.exception("Row %d failed", idx)
# # #             meta["error"] = str(exc)
# # #             self.stats.failed.increment()
# # #             self.notifier.on_failure(idx, str(exc))

# # #         finally:
# # #             for f in (tmp_img, tmp_nobg):
# # #                 try:
# # #                     f.unlink(missing_ok=True)
# # #                 except OSError:
# # #                     pass
# # #             self.stats.total.increment()
# # #             if self._csv_cnt.increment() % self.cfg.pipeline.csv_save_interval == 0:
# # #                 self._save_csv()
# # #             gc.collect()

# # #         return meta

# # #     # ── chunked execution ───────────────────────────────────
# # #     def _run_indices(self, indices: List[int]) -> None:
# # #         """Process a list of indices with the thread pool."""
# # #         workers = self.cfg.pipeline.max_workers

# # #         if workers <= 1:
# # #             for idx in indices:
# # #                 if self._shutdown.is_set():
# # #                     break
# # #                 meta = self._process(idx)
# # #                 if meta.get("success"):
# # #                     self.progress.mark_done(idx, meta)
# # #                 elif not meta.get("skipped"):
# # #                     self.progress.mark_failed(idx, meta)
# # #                 time.sleep(self.cfg.pipeline.inter_ad_delay)
# # #         else:
# # #             with ThreadPoolExecutor(
# # #                 max_workers=workers,
# # #                 thread_name_prefix="adgen",
# # #             ) as pool:
# # #                 futs = {pool.submit(self._process, i): i for i in indices}
# # #                 for fut in as_completed(futs):
# # #                     if self._shutdown.is_set():
# # #                         pool.shutdown(wait=False, cancel_futures=True)
# # #                         break
# # #                     idx = futs[fut]
# # #                     try:
# # #                         meta = fut.result(timeout=self.cfg.pipeline.worker_timeout)
# # #                         if meta.get("success"):
# # #                             self.progress.mark_done(idx, meta)
# # #                         elif not meta.get("skipped"):
# # #                             self.progress.mark_failed(idx, meta)
# # #                     except Exception as exc:
# # #                         log.error("Worker crash idx=%d: %s", idx, exc)
# # #                         self.progress.mark_failed(idx, {"error": str(exc)})
# # #                         self.stats.failed.increment()

# # #     # ── main ────────────────────────────────────────────────
# # #     def run(self) -> None:
# # #         total = len(self.df)
# # #         lo = self.cfg.start_index or 0
# # #         hi = self.cfg.end_index or total

# # #         all_indices = list(range(lo, min(hi, total)))
# # #         if self.cfg.resume:
# # #             indices = [i for i in all_indices if not self.progress.is_done(i)]
# # #         else:
# # #             indices = all_indices

# # #         self.stats.skipped.increment(len(all_indices) - len(indices))

# # #         log.info(
# # #             "Pipeline: %d to process, %d skipped, workers=%d, chunks=%d",
# # #             len(indices), self.stats.skipped.value,
# # #             self.cfg.pipeline.max_workers, self.cfg.chunk_size,
# # #         )

# # #         # ── process in chunks (memory control) ──
# # #         chunk = self.cfg.chunk_size
# # #         for i in range(0, len(indices), chunk):
# # #             if self._shutdown.is_set():
# # #                 break
# # #             batch = indices[i : i + chunk]
# # #             log.info("── Chunk %d–%d ──", batch[0], batch[-1])
# # #             self._run_indices(batch)
# # #             gc.collect()

# # #         # ── dead-letter queue ──
# # #         if self.cfg.enable_dlq and not self._shutdown.is_set():
# # #             dlq = self.progress.get_dead_letters()
# # #             if dlq:
# # #                 log.info("── Dead-letter retry: %d rows ──", len(dlq))
# # #                 self.stats.dlq_retries.increment(len(dlq))
# # #                 self._run_indices(dlq)

# # #         # ── final writes ──
# # #         self._save_csv()

# # #         # ── health report ──
# # #         if self.health:
# # #             self.health.log_report()

# # #         # ── cache stats ──
# # #         if self.cache:
# # #             log.info("Cache stats: %s", self.cache.stats())

# # #         # ── progress stats ──
# # #         log.info("Progress DB: %s", self.progress.stats())

# # #         # ── final report ──
# # #         log.info(self.stats.report())
# # #         log.info("CSV → %s", self.cfg.paths.csv_output)

# # #         # ── notify ──
# # #         self.notifier.on_completion(
# # #             self.stats.total.value,
# # #             self.stats.success.value,
# # #             self.stats.elapsed,
# # #         )

# # #         # ── cleanup ──
# # #         if self.cfg.remove_temp:
# # #             self._cleanup()

# # #     def _cleanup(self) -> None:
# # #         try:
# # #             if self.cfg.paths.temp_dir.exists():
# # #                 shutil.rmtree(self.cfg.paths.temp_dir, ignore_errors=True)
# # #                 log.info("Temp directory cleaned")
# # #         except Exception as exc:
# # #             log.warning("Cleanup failed: %s", exc)

# # """
# # Main pipeline with all improvements.
# # """

# # from __future__ import annotations

# # import gc
# # import re
# # import shutil
# # import signal
# # import threading
# # import time
# # from concurrent.futures import ThreadPoolExecutor, as_completed
# # from pathlib import Path
# # from typing import Any, Dict, List, Optional

# # import pandas as pd

# # from config.settings import AppConfig, QueryConfig
# # from core.compositor import AdCompositor
# # from core.health import HealthMonitor
# # from core.progress import ProgressManager
# # from imaging.background import BackgroundRemover
# # from imaging.cache import ImageCache
# # from imaging.downloader import ImageDownloader
# # from imaging.scorer import ImageQualityScorer
# # from notifications.notifier import Notifier
# # from search.manager import SearchManager
# # from utils.concurrency import AtomicCounter
# # from utils.log_config import get_logger
# # from utils.text_cleaner import clean_query, is_valid_query

# # log = get_logger(__name__)


# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # #  STATS
# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # class Stats:
# #     def __init__(self) -> None:
# #         self.total        = AtomicCounter()
# #         self.success      = AtomicCounter()
# #         self.failed       = AtomicCounter()
# #         self.placeholder  = AtomicCounter()
# #         self.bg_removed   = AtomicCounter()
# #         self.bg_skipped   = AtomicCounter()
# #         self.skipped      = AtomicCounter()
# #         self.cache_hits   = AtomicCounter()
# #         self.dlq_retries  = AtomicCounter()
# #         self._t0          = time.monotonic()

# #     @property
# #     def elapsed(self) -> float:
# #         return time.monotonic() - self._t0

# #     def report(self) -> str:
# #         e = self.elapsed
# #         return (
# #             "\n" + "=" * 60
# #             + "\n📊  PIPELINE REPORT"
# #             + f"\n{'─' * 60}"
# #             + f"\n  Processed     : {self.total.value}"
# #             + f"\n  Success       : {self.success.value}"
# #             + f"\n  Failed        : {self.failed.value}"
# #             + f"\n  Placeholders  : {self.placeholder.value}"
# #             + f"\n  BG removed    : {self.bg_removed.value}"
# #             + f"\n  BG skipped    : {self.bg_skipped.value}"
# #             + f"\n  Cache hits    : {self.cache_hits.value}"
# #             + f"\n  DLQ retries   : {self.dlq_retries.value}"
# #             + f"\n  Already done  : {self.skipped.value}"
# #             + f"\n  Elapsed       : {e:.1f}s"
# #             + f"\n  Throughput    : {self.total.value / max(e, 0.1):.2f} ads/s"
# #             + f"\n{'=' * 60}\n"
# #         )


# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # #  QUERY BUILDER
# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # # def build_query(row: pd.Series, cfg: QueryConfig) -> str:
# # #     """
# # #     Build search query from CSV row using configured column priority.
    
# # #     Applies text cleaning to fix character spacing issues.
    
# # #     Args:
# # #         row: DataFrame row
# # #         cfg: QueryConfig with column priority and settings
        
# # #     Returns:
# # #         Cleaned search query string
# # #     """
# # #     # Try each column in priority order
# # #     for col in cfg.priority_columns:
# # #         if col not in row.index:
# # #             continue
        
# # #         raw_value = row.get(col)
        
# # #         # Skip NaN/None
# # #         if pd.isna(raw_value):
# # #             continue
        
# # #         raw_str = str(raw_value).strip()
        
# # #         # Skip ignored values
# # #         if not is_valid_query(raw_str, cfg.ignore_values):
# # #             continue
        
# # #         # Clean the query (fixes spacing issues!)
# # #         cleaned = clean_query(raw_str, max_words=cfg.max_query_words)
        
# # #         if cleaned:
# # #             log.info("Query from '%s': '%s' → '%s'", col, raw_str[:-1], cleaned)
# # #             return cleaned
    
# # #     # Final fallback: use text column
# # #     text = str(row.get(cfg.img_desc_column, ""))
# # #     cleaned = clean_query(text, max_words=cfg.max_query_words)
# # #     log.info("Query from fallback '%s': '%s'", cfg.img_desc_column, cleaned)
# # #     return cleaned

# # def build_query(row: pd.Series, cfg: QueryConfig) -> str:
# #     """
# #     Build search query from CSV row using configured column priority.
# #     Uses full text (no word limit unless configured).
# #     """
# #     for col in cfg.priority_columns:
# #         if col not in row.index:
# #             continue
        
# #         raw_value = row.get(col)
        
# #         if pd.isna(raw_value):
# #             continue
        
# #         raw_str = str(raw_value).strip()
        
# #         if not is_valid_query(raw_str, cfg.ignore_values):
# #             continue
        
# #         # Clean the query — pass max_words and strip_suffixes from config
# #         cleaned = clean_query(
# #             raw_str,
# #             max_words=cfg.max_query_words,           # 0 = no limit
# #             # strip_suffixes=cfg.strip_suffixes,        # remove "filetype png" etc.
# #         )
        
# #         if cleaned:
# #             log.info("Query from '%s': '%s' → '%s'", col, raw_str[:50], cleaned)
# #             return cleaned
    
# #     # Fallback to text column
# #     text = str(row.get(cfg.img_desc_column, ""))
# #     cleaned = clean_query(
# #         text,
# #         max_words=cfg.max_query_words,
# #         strip_suffixes=cfg.strip_suffixes,
# #     )
# #     log.info("Query from fallback '%s': '%s'", cfg.img_desc_column, cleaned)
# #     return cleaned

# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# # #  PIPELINE
# # # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# # class AdPipeline:

# #     def __init__(self, cfg: AppConfig) -> None:
# #         self.cfg = cfg
# #         cfg.paths.ensure()
# #         cfg.validate()

# #         self.df = pd.read_csv(cfg.paths.csv_input)
        
# #         # Log available columns
# #         log.info("CSV columns: %s", list(self.df.columns))
        
# #         if "image_path" not in self.df.columns:
# #             self.df["image_path"] = ""

# #         # Components
# #         self.search   = SearchManager(cfg.search)
# #         self.scorer   = ImageQualityScorer(cfg.quality)
# #         self.download = ImageDownloader(
# #             cfg.quality,
# #             self.search.downloaded_hashes,
# #             timeout=cfg.pipeline.download_timeout,
# #             scorer=self.scorer,
# #         )
# #         self.bg       = BackgroundRemover(cfg.bg)
# #         self.comp     = AdCompositor(cfg.paths.fonts_dir)
# #         self.progress = ProgressManager(
# #             cfg.paths.progress_db,
# #             max_retries=cfg.dlq_retries,
# #         )
# #         self.stats    = Stats()
# #         self.notifier = Notifier(cfg.notify)
# #         self.health   = HealthMonitor() if cfg.enable_health else None

# #         # Cache
# #         self.cache: Optional[ImageCache] = None
# #         if cfg.enable_cache:
# #             self.cache = ImageCache(cfg.paths.cache_db)

# #         # Threading
# #         self._df_lock  = threading.Lock()
# #         self._csv_cnt  = AtomicCounter()
# #         self._shutdown = threading.Event()

# #         signal.signal(signal.SIGINT,  self._on_signal)
# #         signal.signal(signal.SIGTERM, self._on_signal)

# #     def _on_signal(self, signum: int, _: Any) -> None:
# #         log.warning("Signal %d — shutting down gracefully", signum)
# #         self._shutdown.set()

# #     @staticmethod
# #     def _worker_dir(base: Path, wid: int) -> Path:
# #         d = base / f"w{wid}"
# #         d.mkdir(parents=True, exist_ok=True)
# #         return d

# #     def _save_csv(self) -> None:
# #         with self._df_lock:
# #             tmp = self.cfg.paths.csv_output.with_suffix(".tmp")
# #             self.df.to_csv(tmp, index=False)
# #             tmp.replace(self.cfg.paths.csv_output)

# #     def _process(self, idx: int) -> Dict[str, Any]:
# #         """Process a single row."""
# #         meta: Dict[str, Any] = {"id": idx, "success": False}

# #         if self._shutdown.is_set():
# #             meta["skipped"] = True
# #             return meta

# #         row = self.df.iloc[idx]
        
# #         # Build and clean query
# #         query = build_query(row, self.cfg.query)
# #         meta["query"] = query

# #         out_name = f"ad_{idx + 1:04d}.jpg"
# #         out_path = self.cfg.paths.images_dir / out_name
# #         meta["filename"] = out_name

# #         tid = threading.current_thread().ident or 0
# #         tmp = self._worker_dir(self.cfg.paths.temp_dir, tid % 100)
# #         tmp_img  = tmp / f"dl_{idx}.jpg"
# #         tmp_nobg = tmp / f"nobg_{idx}.png"

# #         log.info("[%d/%d] query='%s'", idx + 1, len(self.df), query)

# #         try:
# #             dl_path = None

# #             # 0. Check cache
# #             if self.cache:
# #                 cached = self.cache.get(query)
# #                 if cached and Path(cached["file_path"]).exists():
# #                     log.info("Cache hit — skipping download")
# #                     import shutil as shutil_mod
# #                     shutil_mod.copy2(cached["file_path"], tmp_img)
# #                     dl_path = tmp_img
# #                     self.stats.cache_hits.increment()
# #                     meta["source"] = "cache"

# #             # 1. Search + download
# #             if dl_path is None:
# #                 t0 = time.monotonic()
# #                 results = self.search.search(query)

# #                 if self.health:
# #                     for eng_name in self.cfg.search.priority:
# #                         eng_results = [r for r in results if r.source == eng_name]
# #                         if eng_results:
# #                             self.health.record_call(
# #                                 eng_name, True,
# #                                 len(eng_results),
# #                                 time.monotonic() - t0,
# #                             )

# #                 dl = self.download.download_best(results, tmp_img)

# #                 # Fallback query if first fails
# #                 if not dl.success:
# #                     # Try object_detected or other columns
# #                     for fallback_col in ("object_detected", "product", "category"):
# #                         if fallback_col in row.index and pd.notna(row.get(fallback_col)):
# #                             fb_raw = str(row.get(fallback_col))
# #                             fb_cleaned = clean_query(fb_raw, max_words=3)
# #                             if fb_cleaned and fb_cleaned.lower() != query.lower():
# #                                 log.info("Fallback query: '%s'", fb_cleaned)
# #                                 dl = self.download.download_best(
# #                                     self.search.search(fb_cleaned), tmp_img,
# #                                 )
# #                                 if dl.success:
# #                                     break

# #                 if not dl.success or dl.path is None:
# #                     self.stats.placeholder.increment()
# #                     dl_path = self.comp.placeholder(query, tmp_img)
# #                     meta["source"] = "placeholder"
# #                 else:
# #                     dl_path = dl.path
# #                     meta["source"] = dl.info.get("source_engine", "unknown")

# #                     # Store in cache
# #                     if self.cache and dl.source_url:
# #                         self.cache.put(
# #                             query=query,
# #                             source_url=dl.source_url,
# #                             file_path=str(dl_path),
# #                             file_hash=dl.info.get("hash", ""),
# #                             width=dl.info.get("width", 0),
# #                             height=dl.info.get("height", 0),
# #                             file_size=dl.info.get("file_size", 0),
# #                             source_engine=dl.info.get("source_engine", ""),
# #                         )

# #             # 2. Background removal
# #             use_orig = True
# #             if self.bg.should_remove(query):
# #                 bg_res = self.bg.remove(dl_path, tmp_nobg)
# #                 use_orig = bg_res.use_original
# #                 if not use_orig:
# #                     self.stats.bg_removed.increment()
# #             else:
# #                 self.stats.bg_skipped.increment()

# #             # 3. Compose
# #             nobg = tmp_nobg if (not use_orig and tmp_nobg.exists()) else None
# #             if not self.cfg.dry_run:
# #                 self.comp.compose(
# #                     product_path=dl_path,
# #                     nobg_path=nobg,
# #                     use_original=use_orig,
# #                     row=row,
# #                     output=out_path,
# #                 )

# #             # 4. Update DataFrame
# #             rel = f"data/output/images/{out_name}"
# #             with self._df_lock:
# #                 self.df.at[idx, "image_path"] = rel

# #             meta["success"] = True
# #             self.stats.success.increment()
# #             self.notifier.on_milestone(self.stats.success.value)

# #         except Exception as exc:
# #             log.exception("Row %d failed", idx)
# #             meta["error"] = str(exc)
# #             self.stats.failed.increment()
# #             self.notifier.on_failure(idx, str(exc))

# #         finally:
# #             for f in (tmp_img, tmp_nobg):
# #                 try:
# #                     f.unlink(missing_ok=True)
# #                 except OSError:
# #                     pass
# #             self.stats.total.increment()
# #             if self._csv_cnt.increment() % self.cfg.pipeline.csv_save_interval == 0:
# #                 self._save_csv()
# #             gc.collect()

# #         return meta

# #     def _run_indices(self, indices: List[int]) -> None:
# #         """Process a list of indices."""
# #         workers = self.cfg.pipeline.max_workers

# #         if workers <= 1:
# #             for idx in indices:
# #                 if self._shutdown.is_set():
# #                     break
# #                 meta = self._process(idx)
# #                 if meta.get("success"):
# #                     self.progress.mark_done(idx, meta)
# #                 elif not meta.get("skipped"):
# #                     self.progress.mark_failed(idx, meta)
# #                 time.sleep(self.cfg.pipeline.inter_ad_delay)
# #         else:
# #             with ThreadPoolExecutor(
# #                 max_workers=workers,
# #                 thread_name_prefix="adgen",
# #             ) as pool:
# #                 futs = {pool.submit(self._process, i): i for i in indices}
# #                 for fut in as_completed(futs):
# #                     if self._shutdown.is_set():
# #                         pool.shutdown(wait=False, cancel_futures=True)
# #                         break
# #                     idx = futs[fut]
# #                     try:
# #                         meta = fut.result(timeout=self.cfg.pipeline.worker_timeout)
# #                         if meta.get("success"):
# #                             self.progress.mark_done(idx, meta)
# #                         elif not meta.get("skipped"):
# #                             self.progress.mark_failed(idx, meta)
# #                     except Exception as exc:
# #                         log.error("Worker crash idx=%d: %s", idx, exc)
# #                         self.progress.mark_failed(idx, {"error": str(exc)})
# #                         self.stats.failed.increment()

# #     def run(self) -> None:
# #         """Main entry point."""
# #         total = len(self.df)
# #         lo = self.cfg.start_index or 0
# #         hi = self.cfg.end_index or total

# #         all_indices = list(range(lo, min(hi, total)))
# #         if self.cfg.resume:
# #             indices = [i for i in all_indices if not self.progress.is_done(i)]
# #         else:
# #             indices = all_indices

# #         self.stats.skipped.increment(len(all_indices) - len(indices))

# #         log.info(
# #             "Pipeline: %d to process, %d skipped, workers=%d",
# #             len(indices), self.stats.skipped.value,
# #             self.cfg.pipeline.max_workers,
# #         )

# #         # Process in chunks
# #         chunk = self.cfg.chunk_size
# #         for i in range(0, len(indices), chunk):
# #             if self._shutdown.is_set():
# #                 break
# #             batch = indices[i : i + chunk]
# #             log.info("── Chunk %d–%d ──", batch[0] + 1, batch[-1] + 1)
# #             self._run_indices(batch)
# #             gc.collect()

# #         # Dead-letter queue
# #         if self.cfg.enable_dlq and not self._shutdown.is_set():
# #             dlq = self.progress.get_dead_letters()
# #             if dlq:
# #                 log.info("── Dead-letter retry: %d rows ──", len(dlq))
# #                 self.stats.dlq_retries.increment(len(dlq))
# #                 self._run_indices(dlq)

# #         # Final writes
# #         self._save_csv()

# #         if self.health:
# #             self.health.log_report()

# #         if self.cache:
# #             log.info("Cache stats: %s", self.cache.stats())

# #         log.info("Progress DB: %s", self.progress.stats())
# #         log.info(self.stats.report())
# #         log.info("CSV → %s", self.cfg.paths.csv_output)

# #         self.notifier.on_completion(
# #             self.stats.total.value,
# #             self.stats.success.value,
# #             self.stats.elapsed,
# #         )

# #         if self.cfg.remove_temp:
# #             self._cleanup()

# #     def _cleanup(self) -> None:
# #         try:
# #             if self.cfg.paths.temp_dir.exists():
# #                 shutil.rmtree(self.cfg.paths.temp_dir, ignore_errors=True)
# #                 log.info("Temp directory cleaned")
# #         except Exception as exc:
# #             log.warning("Cleanup failed: %s", exc)


# """
# Main pipeline — multi-threaded orchestrator.
# """

# from __future__ import annotations

# import gc
# import re
# import shutil
# import signal
# import threading
# import time
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from pathlib import Path
# from typing import Any, Dict, List, Optional

# import pandas as pd

# from config.settings import AppConfig, QueryConfig
# from core.compositor import AdCompositor
# from core.health import HealthMonitor
# from core.progress import ProgressManager
# from imaging.background import BackgroundRemover
# from imaging.cache import ImageCache
# from imaging.downloader import ImageDownloader
# from imaging.scorer import ImageQualityScorer
# from imaging.verifier import ImageVerifier
# from notifications.notifier import Notifier
# from search.manager import SearchManager
# from utils.concurrency import AtomicCounter
# from utils.log_config import get_logger
# from utils.text_cleaner import clean_query, is_valid_query

# log = get_logger(__name__)


# class Stats:
#     def __init__(self) -> None:
#         self.total        = AtomicCounter()
#         self.success      = AtomicCounter()
#         self.failed       = AtomicCounter()
#         self.placeholder  = AtomicCounter()
#         self.bg_removed   = AtomicCounter()
#         self.bg_skipped   = AtomicCounter()
#         self.skipped      = AtomicCounter()
#         self.cache_hits   = AtomicCounter()
#         self.dlq_retries  = AtomicCounter()
#         self.verified     = AtomicCounter()     # ← NEW
#         self.verify_fails = AtomicCounter()     # ← NEW
#         self._t0          = time.monotonic()

#     @property
#     def elapsed(self) -> float:
#         return time.monotonic() - self._t0

#     def report(self) -> str:
#         e = self.elapsed
#         return (
#             "\n" + "=" * 60
#             + "\n📊  PIPELINE REPORT"
#             + f"\n{'─' * 60}"
#             + f"\n  Processed       : {self.total.value}"
#             + f"\n  Success         : {self.success.value}"
#             + f"\n  Failed          : {self.failed.value}"
#             + f"\n  Placeholders    : {self.placeholder.value}"
#             + f"\n  BG removed      : {self.bg_removed.value}"
#             + f"\n  BG skipped      : {self.bg_skipped.value}"
#             + f"\n  Cache hits      : {self.cache_hits.value}"
#             + f"\n  DLQ retries     : {self.dlq_retries.value}"
#             + f"\n  Verified (CLIP) : {self.verified.value}"
#             + f"\n  Verify rejects  : {self.verify_fails.value}"
#             + f"\n  Already done    : {self.skipped.value}"
#             + f"\n  Elapsed         : {e:.1f}s"
#             + f"\n  Throughput      : {self.total.value / max(e, 0.1):.2f} ads/s"
#             + f"\n{'=' * 60}\n"
#         )


# _IGNORED = frozenset({
#     "nan", "none", "", "general", "food", "automotive", "object", "unknown", "null",
# })


# def build_query(row: pd.Series, cfg: QueryConfig) -> str:
#     for col in cfg.priority_columns:
#         if col not in row.index:
#             continue
#         raw_value = row.get(col)
#         if pd.isna(raw_value):
#             continue
#         raw_str = str(raw_value).strip()
#         if not is_valid_query(raw_str, cfg.ignore_values):
#             continue
#         cleaned = clean_query(
#             raw_str,
#             max_words=cfg.max_query_words,
#             strip_suffixes=cfg.strip_suffixes,
#         )
#         if cleaned:
#             log.info("Query from '%s': '%s' → '%s'", col, raw_str[:50], cleaned)
#             return cleaned
    
#     text = str(row.get(cfg.text_column, ""))
#     cleaned = clean_query(text, max_words=cfg.max_query_words, strip_suffixes=cfg.strip_suffixes)
#     return cleaned


# class AdPipeline:

#     def __init__(self, cfg: AppConfig) -> None:
#         self.cfg = cfg
#         cfg.paths.ensure()
#         cfg.validate()

#         self.df = pd.read_csv(cfg.paths.csv_input)
#         log.info("CSV columns: %s", list(self.df.columns))
        
#         if "image_path" not in self.df.columns:
#             self.df["image_path"] = ""

#         # ── Search ──
#         self.search = SearchManager(cfg.search)
#         self.scorer = ImageQualityScorer(cfg.quality)
        
#         # ── Verifier (CLIP + BLIP) ──
#         # self.verifier: Optional[ImageVerifier] = None
#         # if cfg.verify.use_clip or cfg.verify.use_blip:
#         #     log.info("Initializing CLIP+BLIP verification...")
#         #     try:
#         #         self.verifier = ImageVerifier(cfg.verify)
#         #         log.info("Verifier ready: %s", self.verifier.stats())
#         #     except Exception as exc:
#         #         log.error("Verifier init failed: %s — continuing without verification", exc)
#         #         self.verifier = None
        
#                 # ── Verifier (CLIP + BLIP) ──
#         self.verifier: Optional[ImageVerifier] = None
#         if cfg.verify.use_clip or cfg.verify.use_blip:
#             log.info("Initializing CLIP+BLIP verification...")
#             try:
#                 # Pass models_dir so models download to ./data/models/
#                 self.verifier = ImageVerifier(
#                     cfg.verify,
#                     models_dir=cfg.paths.models_dir,  
#                 )
#                 log.info("Verifier status: %s", self.verifier.stats())
#             except Exception as exc:
#                 log.error("Verifier init failed: %s", exc, exc_info=True)
#                 self.verifier = None


#         # ── Downloader (with verifier) ──
#         self.download = ImageDownloader(
#             cfg.quality,
#             self.search.downloaded_hashes,
#             timeout=cfg.pipeline.download_timeout,
#             scorer=self.scorer,
#             verifier=self.verifier,
#             verify_cfg=cfg.verify,
#         )
        
#         self.bg       = BackgroundRemover(cfg.bg)
#         self.comp     = AdCompositor(cfg.paths.fonts_dir)
#         self.progress = ProgressManager(cfg.paths.progress_db, max_retries=cfg.dlq_retries)
#         self.stats    = Stats()
#         self.notifier = Notifier(cfg.notify)
#         self.health   = HealthMonitor() if cfg.enable_health else None

#         self.cache: Optional[ImageCache] = None
#         if cfg.enable_cache:
#             self.cache = ImageCache(cfg.paths.cache_db)

#         self._df_lock  = threading.Lock()
#         self._csv_cnt  = AtomicCounter()
#         self._shutdown = threading.Event()

#         signal.signal(signal.SIGINT,  self._on_signal)
#         signal.signal(signal.SIGTERM, self._on_signal)

#     def _on_signal(self, signum: int, _: Any) -> None:
#         log.warning("Signal %d — shutting down gracefully", signum)
#         self._shutdown.set()

#     @staticmethod
#     def _worker_dir(base: Path, wid: int) -> Path:
#         d = base / f"w{wid}"
#         d.mkdir(parents=True, exist_ok=True)
#         return d

#     def _save_csv(self) -> None:
#         with self._df_lock:
#             tmp = self.cfg.paths.csv_output.with_suffix(".tmp")
#             self.df.to_csv(tmp, index=False)
#             tmp.replace(self.cfg.paths.csv_output)

#     def _process(self, idx: int) -> Dict[str, Any]:
#         """Process a single row with verification."""
#         meta: Dict[str, Any] = {"id": idx, "success": False}

#         if self._shutdown.is_set():
#             meta["skipped"] = True
#             return meta

#         row = self.df.iloc[idx]
#         query = build_query(row, self.cfg.query)
#         meta["query"] = query

#         out_name = f"ad_{idx + 1:04d}.jpg"
#         out_path = self.cfg.paths.images_dir / out_name
#         meta["filename"] = out_name

#         tid = threading.current_thread().ident or 0
#         tmp = self._worker_dir(self.cfg.paths.temp_dir, tid % 100)
#         tmp_img  = tmp / f"dl_{idx}.jpg"
#         tmp_nobg = tmp / f"nobg_{idx}.png"

#         log.info("[%d/%d] query='%s'", idx + 1, len(self.df), query)

#         try:
#             dl_path = None

#             # 0. Cache check
#             if self.cache:
#                 cached = self.cache.get(query)
#                 if cached and Path(cached["file_path"]).exists():
#                     log.info("Cache hit — skipping download")
#                     import shutil as shutil_mod
#                     shutil_mod.copy2(cached["file_path"], tmp_img)
#                     dl_path = tmp_img
#                     self.stats.cache_hits.increment()
#                     meta["source"] = "cache"

#             # 1. Search + Download + VERIFY
#             if dl_path is None:
#                 t0 = time.monotonic()
#                 results = self.search.search(query)

#                 if self.health:
#                     for eng_name in self.cfg.search.priority:
#                         eng_results = [r for r in results if r.source == eng_name]
#                         if eng_results:
#                             self.health.record_call(
#                                 eng_name, True,
#                                 len(eng_results),
#                                 time.monotonic() - t0,
#                             )

#                 # Pass query to downloader for CLIP+BLIP verification
#                 dl = self.download.download_best(results, tmp_img, query=query)

#                 # Track verification stats
#                 if dl.verification:
#                     self.stats.verified.increment()
#                     if not dl.verification.get("accepted", True):
#                         self.stats.verify_fails.increment()

#                 # Fallback if first attempt fails
#                 if not dl.success:
#                     for fallback_col in ("object_detected", "keywords"):
#                         if fallback_col in row.index and pd.notna(row.get(fallback_col)):
#                             fb_raw = str(row.get(fallback_col))
#                             fb_cleaned = clean_query(fb_raw, max_words=0, strip_suffixes=self.cfg.query.strip_suffixes)
#                             if fb_cleaned and fb_cleaned.lower() != query.lower():
#                                 log.info("Fallback query: '%s'", fb_cleaned)
#                                 fb_results = self.search.search(fb_cleaned)
#                                 dl = self.download.download_best(fb_results, tmp_img, query=fb_cleaned)
#                                 if dl.success:
#                                     break

#                 if not dl.success or dl.path is None:
#                     self.stats.placeholder.increment()
#                     dl_path = self.comp.placeholder(query, tmp_img)
#                     meta["source"] = "placeholder"
#                 else:
#                     dl_path = dl.path
#                     meta["source"] = dl.info.get("source_engine", "unknown")
                    
#                     # Add verification info to metadata
#                     if dl.verification:
#                         meta["clip_score"] = dl.verification.get("clip_score", 0)
#                         meta["blip_score"] = dl.verification.get("blip_score", 0)
#                         meta["blip_caption"] = dl.verification.get("blip_caption", "")

#                     if self.cache and dl.source_url:
#                         self.cache.put(
#                             query=query,
#                             source_url=dl.source_url,
#                             file_path=str(dl_path),
#                             file_hash=dl.info.get("hash", ""),
#                             width=dl.info.get("width", 0),
#                             height=dl.info.get("height", 0),
#                             file_size=dl.info.get("file_size", 0),
#                             source_engine=dl.info.get("source_engine", ""),
#                         )

#             # 2. Background removal
#             use_orig = True
#             if self.bg.should_remove(query):
#                 bg_res = self.bg.remove(dl_path, tmp_nobg)
#                 use_orig = bg_res.use_original
#                 if not use_orig:
#                     self.stats.bg_removed.increment()
#             else:
#                 self.stats.bg_skipped.increment()

#             # 3. Compose
#             nobg = tmp_nobg if (not use_orig and tmp_nobg.exists()) else None
#             if not self.cfg.dry_run:
#                 self.comp.compose(
#                     product_path=dl_path,
#                     nobg_path=nobg,
#                     use_original=use_orig,
#                     row=row,
#                     output=out_path,
#                 )

#             # 4. Update DataFrame
#             rel = f"data/output/images/{out_name}"
#             with self._df_lock:
#                 self.df.at[idx, "image_path"] = rel

#             meta["success"] = True
#             self.stats.success.increment()
#             self.notifier.on_milestone(self.stats.success.value)

#         except Exception as exc:
#             log.exception("Row %d failed", idx)
#             meta["error"] = str(exc)
#             self.stats.failed.increment()
#             self.notifier.on_failure(idx, str(exc))

#         finally:
#             for f in (tmp_img, tmp_nobg):
#                 try:
#                     f.unlink(missing_ok=True)
#                 except OSError:
#                     pass
#             self.stats.total.increment()
#             if self._csv_cnt.increment() % self.cfg.pipeline.csv_save_interval == 0:
#                 self._save_csv()
#             gc.collect()

#         return meta

#     def _run_indices(self, indices: List[int]) -> None:
#         workers = self.cfg.pipeline.max_workers

#         if workers <= 1:
#             for idx in indices:
#                 if self._shutdown.is_set():
#                     break
#                 meta = self._process(idx)
#                 if meta.get("success"):
#                     self.progress.mark_done(idx, meta)
#                 elif not meta.get("skipped"):
#                     self.progress.mark_failed(idx, meta)
#                 time.sleep(self.cfg.pipeline.inter_ad_delay)
#         else:
#             with ThreadPoolExecutor(
#                 max_workers=workers,
#                 thread_name_prefix="adgen",
#             ) as pool:
#                 futs = {pool.submit(self._process, i): i for i in indices}
#                 for fut in as_completed(futs):
#                     if self._shutdown.is_set():
#                         pool.shutdown(wait=False, cancel_futures=True)
#                         break
#                     idx = futs[fut]
#                     try:
#                         meta = fut.result(timeout=self.cfg.pipeline.worker_timeout)
#                         if meta.get("success"):
#                             self.progress.mark_done(idx, meta)
#                         elif not meta.get("skipped"):
#                             self.progress.mark_failed(idx, meta)
#                     except Exception as exc:
#                         log.error("Worker crash idx=%d: %s", idx, exc)
#                         self.progress.mark_failed(idx, {"error": str(exc)})
#                         self.stats.failed.increment()

#     def run(self) -> None:
#         total = len(self.df)
#         lo = self.cfg.start_index or 0
#         hi = self.cfg.end_index or total

#         all_indices = list(range(lo, min(hi, total)))
#         if self.cfg.resume:
#             indices = [i for i in all_indices if not self.progress.is_done(i)]
#         else:
#             indices = all_indices

#         self.stats.skipped.increment(len(all_indices) - len(indices))

#         log.info(
#             "Pipeline: %d to process, %d skipped, workers=%d",
#             len(indices), self.stats.skipped.value,
#             self.cfg.pipeline.max_workers,
#         )
        
#         if self.verifier:
#             log.info("Verification: %s", self.verifier.stats())

#         chunk = self.cfg.chunk_size
#         for i in range(0, len(indices), chunk):
#             if self._shutdown.is_set():
#                 break
#             batch = indices[i : i + chunk]
#             log.info("── Chunk %d–%d ──", batch[0] + 1, batch[-1] + 1)
#             self._run_indices(batch)
#             gc.collect()

#         if self.cfg.enable_dlq and not self._shutdown.is_set():
#             dlq = self.progress.get_dead_letters()
#             if dlq:
#                 log.info("── Dead-letter retry: %d rows ──", len(dlq))
#                 self.stats.dlq_retries.increment(len(dlq))
#                 self._run_indices(dlq)

#         self._save_csv()

#         if self.health:
#             self.health.log_report()
#         if self.cache:
#             log.info("Cache stats: %s", self.cache.stats())

#         log.info("Progress DB: %s", self.progress.stats())
#         log.info(self.stats.report())
#         log.info("CSV → %s", self.cfg.paths.csv_output)

#         self.notifier.on_completion(
#             self.stats.total.value,
#             self.stats.success.value,
#             self.stats.elapsed,
#         )

#         if self.cfg.remove_temp:
#             self._cleanup()

#     def _cleanup(self) -> None:
#         try:
#             if self.cfg.paths.temp_dir.exists():
#                 shutil.rmtree(self.cfg.paths.temp_dir, ignore_errors=True)
#                 log.info("Temp directory cleaned")
#         except Exception as exc:
#             log.warning("Cleanup failed: %s", exc)

"""
Main pipeline — multi-threaded orchestrator.
Fixed: Ctrl+C works reliably on Windows + Linux.
"""

from __future__ import annotations

import gc
import os
import re
import shutil
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from config.settings import AppConfig, QueryConfig
from core.compositor import AdCompositor
from core.health import HealthMonitor
from core.progress import ProgressManager
from imaging.background import BackgroundRemover
from imaging.cache import ImageCache
from imaging.downloader import ImageDownloader
from imaging.scorer import ImageQualityScorer
from imaging.verifier import ImageVerifier
from notifications.notifier import Notifier
from search.manager import SearchManager
from utils.concurrency import AtomicCounter
from utils.log_config import get_logger
from utils.text_cleaner import clean_query, is_valid_query
    # Add to imports at top of core/pipeline.py
from cli.display import create_progress, format_row_status
from cli.console import console
from config.templates import ALL_TEMPLATES , TEMPLATE_CYCLE



log = get_logger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# class Stats:
#     def __init__(self) -> None:
#         self.total        = AtomicCounter()
#         self.success      = AtomicCounter()
#         self.failed       = AtomicCounter()
#         self.placeholder  = AtomicCounter()
#         self.bg_removed   = AtomicCounter()
#         self.bg_skipped   = AtomicCounter()
#         self.skipped      = AtomicCounter()
#         self.cache_hits   = AtomicCounter()
#         self.dlq_retries  = AtomicCounter()
#         self.verified     = AtomicCounter()
#         self.verify_fails = AtomicCounter()
#         self._t0          = time.monotonic()

#     @property
#     def elapsed(self) -> float:
#         return time.monotonic() - self._t0

#     def report(self) -> str:
#         e = self.elapsed
#         return (
#             "\n" + "=" * 60
#             + "\n📊  PIPELINE REPORT"
#             + f"\n{'─' * 60}"
#             + f"\n  Processed       : {self.total.value}"
#             + f"\n  Success         : {self.success.value}"
#             + f"\n  Failed          : {self.failed.value}"
#             + f"\n  Placeholders    : {self.placeholder.value}"
#             + f"\n  BG removed      : {self.bg_removed.value}"
#             + f"\n  BG skipped      : {self.bg_skipped.value}"
#             + f"\n  Cache hits      : {self.cache_hits.value}"
#             + f"\n  DLQ retries     : {self.dlq_retries.value}"
#             + f"\n  Verified (CLIP) : {self.verified.value}"
#             + f"\n  Verify rejects  : {self.verify_fails.value}"
#             + f"\n  Already done    : {self.skipped.value}"
#             + f"\n  Elapsed         : {e:.1f}s"
#             + f"\n  Throughput      : {self.total.value / max(e, 0.1):.2f} ads/s"
#             + f"\n{'=' * 60}\n"
#         )

class Stats:
    def __init__(self) -> None:
        self.total        = AtomicCounter()
        self.success      = AtomicCounter()
        self.failed       = AtomicCounter()
        self.placeholder  = AtomicCounter()
        self.bg_removed   = AtomicCounter()
        self.bg_skipped   = AtomicCounter()
        self.skipped      = AtomicCounter()
        self.cache_hits   = AtomicCounter()
        self.dlq_retries  = AtomicCounter()
        self.verified     = AtomicCounter()
        self.verify_fails = AtomicCounter()

        # NEW: for post‑compose verification
        self.post_verified      = AtomicCounter()
        self.post_verify_fails  = AtomicCounter()

        self._t0          = time.monotonic()

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._t0

    def report(self) -> str:
        e = self.elapsed
        return (
            "\n" + "=" * 60
            + "\n📊  PIPELINE REPORT"
            + f"\n{'─' * 60}"
            + f"\n  Processed       : {self.total.value}"
            + f"\n  Success         : {self.success.value}"
            + f"\n  Failed          : {self.failed.value}"
            + f"\n  Placeholders    : {self.placeholder.value}"
            + f"\n  BG removed      : {self.bg_removed.value}"
            + f"\n  BG skipped      : {self.bg_skipped.value}"
            + f"\n  Cache hits      : {self.cache_hits.value}"
            + f"\n  DLQ retries     : {self.dlq_retries.value}"
            + f"\n  Verified (CLIP) : {self.verified.value}"
            + f"\n  Verify rejects  : {self.verify_fails.value}"
            + f"\n  Post‑verified   : {self.post_verified.value}"
            + f"\n  Post‑verify rej.: {self.post_verify_fails.value}"
            + f"\n  Already done    : {self.skipped.value}"
            + f"\n  Elapsed         : {e:.1f}s"
            + f"\n  Throughput      : {self.total.value / max(e, 0.1):.2f} ads/s"
            + f"\n{'=' * 60}\n"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  QUERY BUILDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_IGNORED = frozenset({
    "nan", "none", "", "general", "food", "automotive", "object", "unknown", "null",
})


def build_query(row: pd.Series, cfg: QueryConfig) -> str:
    for col in cfg.priority_columns:
        if col not in row.index:
            continue
        raw_value = row.get(col)
        if pd.isna(raw_value):
            continue
        raw_str = str(raw_value).strip()
        if not is_valid_query(raw_str, cfg.ignore_values):
            continue
        cleaned = clean_query(
            raw_str,
            max_words=cfg.max_query_words,
            strip_suffixes=cfg.strip_suffixes,
        )
        if cleaned:
            log.info("Query from '%s': '%s' → '%s'", col, raw_str[:50], cleaned)
            return cleaned

    text = str(row.get(cfg.text_column, ""))
    cleaned = clean_query(text, max_words=cfg.max_query_words, strip_suffixes=cfg.strip_suffixes)
    return cleaned


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SHUTDOWN HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ShutdownHandler:
    """
    Reliable shutdown for Windows + Linux.
    
    Problems with signal.signal() in threads:
      - Python only handles signals in the main thread
      - ThreadPoolExecutor.as_completed() blocks and swallows KeyboardInterrupt
      - On Windows, SIGTERM doesn't work properly
    
    Solution:
      - Use threading.Event for cross-thread communication
      - Catch KeyboardInterrupt in the main loop
      - Use short timeouts on future.result() so main thread stays responsive
    """
    
    def __init__(self) -> None:
        self._event = threading.Event()
        self._ctrl_c_count = 0
        self._lock = threading.Lock()
        
        # Install signal handler ONLY in main thread
        if threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGINT, self._handle)
                signal.signal(signal.SIGTERM, self._handle)
            except (OSError, ValueError):
                # May fail in some environments
                pass
    
    def _handle(self, signum: int, frame: Any) -> None:
        """Called on SIGINT/SIGTERM."""
        with self._lock:
            self._ctrl_c_count += 1
            count = self._ctrl_c_count
        
        if count == 1:
            log.warning("")
            log.warning("=" * 50)
            log.warning("⚠️  Ctrl+C detected — finishing current tasks...")
            log.warning("   Press Ctrl+C again to force quit")
            log.warning("=" * 50)
            self._event.set()
        elif count >= 2:
            log.warning("")
            log.warning("🛑 Force quit!")
            # Save what we can
            os._exit(1)
    
    @property
    def should_stop(self) -> bool:
        return self._event.is_set()
    
    def request_stop(self) -> None:
        """Programmatic stop request."""
        self._event.set()
    
    def check(self) -> None:
        """Call periodically to check for shutdown."""
        if self._event.is_set():
            raise KeyboardInterrupt("Shutdown requested")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PIPELINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AdPipeline:

    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        cfg.paths.ensure()
        cfg.validate()

        
        self.df = pd.read_csv(cfg.paths.csv_input)
        log.info("CSV columns: %s", list(self.df.columns))

        if "image_path" not in self.df.columns:
            self.df["image_path"] = ""

        # Components
        self.search   = SearchManager(cfg.search)
        self.scorer   = ImageQualityScorer(cfg.quality)

        # Verifier
        self.verifier: Optional[ImageVerifier] = None
        if cfg.verify.use_clip or cfg.verify.use_blip:
            log.info("Initializing CLIP+BLIP verification...")
            try:
                self.verifier = ImageVerifier(cfg.verify, models_dir=cfg.paths.models_dir)
                log.info("Verifier status: %s", self.verifier.stats())
            except Exception as exc:
                log.error("Verifier init failed: %s", exc, exc_info=True)

        # Downloader
        self.download = ImageDownloader(
            cfg.quality,
            self.search.downloaded_hashes,
            timeout=cfg.pipeline.download_timeout,
            scorer=self.scorer,
            verifier=self.verifier,
            verify_cfg=cfg.verify,
        )

        self.bg       = BackgroundRemover(cfg.bg)
        self.comp     = AdCompositor(cfg.paths.fonts_dir)
        self.progress = ProgressManager(cfg.paths.progress_db, max_retries=cfg.dlq_retries)
        self.stats    = Stats()
        self.notifier = Notifier(cfg.notify)
        self.health   = HealthMonitor() if cfg.enable_health else None

        self.cache: Optional[ImageCache] = None
        if cfg.enable_cache:
            self.cache = ImageCache(cfg.paths.cache_db)

        # Thread-safe state
        self._df_lock  = threading.Lock()
        self._csv_cnt  = AtomicCounter()
        
        # Shutdown handler (replaces signal.signal)
        self._shutdown = ShutdownHandler()

    @staticmethod
    def _worker_dir(base: Path, wid: int) -> Path:
        d = base / f"w{wid}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _save_csv(self) -> None:
        with self._df_lock:
            try:
                tmp = self.cfg.paths.csv_output.with_suffix(".tmp")
                self.df.to_csv(tmp, index=False)
                tmp.replace(self.cfg.paths.csv_output)
                log.debug("CSV saved")
            except Exception as exc:
                log.warning("CSV save failed: %s", exc)

    # ── single row ──────────────────────────────────────────
    # def _process(self, idx: int) -> Dict[str, Any]:
    #     meta: Dict[str, Any] = {"id": idx, "success": False}

    #     # Check shutdown at start
    #     if self._shutdown.should_stop:
    #         meta["skipped"] = True
    #         return meta

    #     row = self.df.iloc[idx]
    #     query = build_query(row, self.cfg.query)
    #     meta["query"] = query

    #     out_name = f"ad_{idx + 1:04d}.jpg"
    #     out_path = self.cfg.paths.images_dir / out_name
    #     meta["filename"] = out_name

    #     tid = threading.current_thread().ident or 0
    #     tmp = self._worker_dir(self.cfg.paths.temp_dir, tid % 100)
    #     tmp_img  = tmp / f"dl_{idx}.jpg"
    #     tmp_nobg = tmp / f"nobg_{idx}.png"

    #     log.info("[%d/%d] query='%s'", idx + 1, len(self.df), query)

    #     try:
    #         dl_path = None
    #         from_cache = False

    #         # 0. Cache
    #         if self.cache:
    #             cached = self.cache.get(query)
    #             if cached and cached.get("file_path") and Path(cached["file_path"]).exists():
    #                 log.info("Cache hit")
    #                 import shutil as _sh
    #                 _sh.copy2(cached["file_path"], tmp_img)
    #                 dl_path = tmp_img
    #                 from_cache = True
    #                 self.stats.cache_hits.increment()
    #                 meta["source"] = "cache"

    #         # 1. Search + Download + Verify
    #         if dl_path is None:
    #             # Check shutdown before expensive operation
    #             if self._shutdown.should_stop:
    #                 meta["skipped"] = True
    #                 return meta

    #             t0 = time.monotonic()
    #             results = self.search.search(query)

    #             if self.health:
    #                 for eng_name in self.cfg.search.priority:
    #                     eng_results = [r for r in results if r.source == eng_name]
    #                     if eng_results:
    #                         self.health.record_call(
    #                             eng_name, True,
    #                             len(eng_results),
    #                             time.monotonic() - t0,
    #                         )

    #             dl = self.download.download_best(results, tmp_img, query=query)

    #             if dl.verification:
    #                 self.stats.verified.increment()
    #                 if not dl.verification.get("accepted", True):
    #                     self.stats.verify_fails.increment()

    #             # Fallback
    #             if not dl.success and not self._shutdown.should_stop:
    #                 for fb_col in ("object_detected", "keywords"):
    #                     if fb_col in row.index and pd.notna(row.get(fb_col)):
    #                         fb_raw = str(row.get(fb_col))
    #                         fb_cleaned = clean_query(
    #                             fb_raw, max_words=0,
    #                             strip_suffixes=self.cfg.query.strip_suffixes,
    #                         )
    #                         if fb_cleaned and fb_cleaned.lower() != query.lower():
    #                             log.info("Fallback: '%s'", fb_cleaned)
    #                             fb_results = self.search.search(fb_cleaned)
    #                             dl = self.download.download_best(
    #                                 fb_results, tmp_img, query=fb_cleaned,
    #                             )
    #                             if dl.success:
    #                                 break

    #             if not dl.success or dl.path is None:
    #                 self.stats.placeholder.increment()
    #                 dl_path = self.comp.placeholder(query, tmp_img)
    #                 meta["source"] = "placeholder"
    #             else:
    #                 dl_path = dl.path
    #                 meta["source"] = dl.info.get("source_engine", "unknown")

    #                 if dl.verification:
    #                     meta["clip_score"] = dl.verification.get("clip_score", 0)
    #                     meta["blip_score"] = dl.verification.get("blip_score", 0)
    #                     meta["blip_caption"] = dl.verification.get("blip_caption", "")

    #                 if self.cache and dl.source_url:
    #                     self.cache.put(
    #                         query=query,
    #                         source_url=dl.source_url,
    #                         file_path=str(dl_path),
    #                         file_hash=dl.info.get("hash", ""),
    #                         width=dl.info.get("width", 0),
    #                         height=dl.info.get("height", 0),
    #                         file_size=dl.info.get("file_size", 0),
    #                         source_engine=dl.info.get("source_engine", ""),
    #                     )

    #         # Check shutdown before compose
    #         if self._shutdown.should_stop:
    #             meta["skipped"] = True
    #             return meta

    #         # 2. BG removal
    #         use_orig = True
    #         if self.bg.should_remove(query):
    #             bg_res = self.bg.remove(dl_path, tmp_nobg)
    #             use_orig = bg_res.use_original
    #             if not use_orig:
    #                 self.stats.bg_removed.increment()
    #         else:
    #             self.stats.bg_skipped.increment()

    #         # 3. Compose
    #         nobg = tmp_nobg if (not use_orig and tmp_nobg.exists()) else None
    #         if not self.cfg.dry_run:
    #             self.comp.compose(
    #                 product_path=dl_path,
    #                 nobg_path=nobg,
    #                 use_original=use_orig,
    #                 row=row,
    #                 output=out_path,
    #             )

    #         # 4. Update DF
    #         rel = f"data/output/images/{out_name}"
    #         with self._df_lock:
    #             self.df.at[idx, "image_path"] = rel

    #         meta["success"] = True
    #         self.stats.success.increment()
    #         self.notifier.on_milestone(self.stats.success.value)

    #     except Exception as exc:
    #         log.exception("Row %d failed", idx)
    #         meta["error"] = str(exc)
    #         self.stats.failed.increment()

    #     finally:
    #         for f in (tmp_img, tmp_nobg):
    #             try:
    #                 f.unlink(missing_ok=True)
    #             except OSError:
    #                 pass
    #         self.stats.total.increment()
    #         if self._csv_cnt.increment() % self.cfg.pipeline.csv_save_interval == 0:
    #             self._save_csv()
    #         gc.collect()

    #     return meta


    def _process(self, idx: int) -> Dict[str, Any]:
        """
        Process a single row with DOUBLE verification:
            Stage 1: After download (strict)
            Stage 2: After compose (relaxed)
        """
        meta: Dict[str, Any] = {"id": idx, "success": False}

        if self._shutdown.should_stop:
            meta["skipped"] = True
            return meta

        row = self.df.iloc[idx]
        query = build_query(row, self.cfg.query)
        meta["query"] = query

        out_name = f"ad_{idx + 1:04d}.jpg"
        out_path = self.cfg.paths.images_dir / out_name
        meta["filename"] = out_name

        tid = threading.current_thread().ident or 0
        tmp = self._worker_dir(self.cfg.paths.temp_dir, tid % 100)
        tmp_img  = tmp / f"dl_{idx}.jpg"
        tmp_nobg = tmp / f"nobg_{idx}.png"

        log.info("[%d/%d] query='%s'", idx + 1, len(self.df), query)

        try:
            dl_path = None
            from_cache = False

            # ═══════════════════════════════════════════════
            #  0. CACHE CHECK
            # ═══════════════════════════════════════════════
            if self.cache:
                cached = self.cache.get(query)
                if cached and cached.get("file_path") and Path(cached["file_path"]).exists():
                    log.info("Cache hit")
                    import shutil as _sh
                    _sh.copy2(cached["file_path"], tmp_img)
                    dl_path = tmp_img
                    from_cache = True
                    self.stats.cache_hits.increment()
                    meta["source"] = "cache"

            # ═══════════════════════════════════════════════
            #  1. SEARCH + DOWNLOAD + STAGE 1 VERIFY
            # ═══════════════════════════════════════════════
            if dl_path is None:
                if self._shutdown.should_stop:
                    meta["skipped"] = True
                    return meta

                results = self.search.search(query)

                # Stage 1 verification happens inside download_best()
                dl = self.download.download_best(results, tmp_img, query=query)

                if dl.verification:
                    self.stats.verified.increment()
                    meta["stage1_clip"] = dl.verification.get("clip_score", 0)
                    meta["stage1_blip"] = dl.verification.get("blip_score", 0)
                    meta["stage1_caption"] = dl.verification.get("blip_caption", "")
                    meta["stage1_accepted"] = dl.verification.get("accepted", False)

                # Fallback
                if not dl.success and not self._shutdown.should_stop:
                    for fb_col in ("object_detected", "keywords"):
                        if fb_col in row.index and pd.notna(row.get(fb_col)):
                            fb_raw = str(row.get(fb_col))
                            fb_cleaned = clean_query(
                                fb_raw, max_words=0,
                                strip_suffixes=self.cfg.query.strip_suffixes,
                            )
                            if fb_cleaned and fb_cleaned.lower() != query.lower():
                                log.info("Fallback: '%s'", fb_cleaned)
                                dl = self.download.download_best(
                                    self.search.search(fb_cleaned),
                                    tmp_img, query=fb_cleaned,
                                )
                                if dl.success:
                                    break

                if not dl.success or dl.path is None:
                    self.stats.placeholder.increment()
                    dl_path = self.comp.placeholder(query, tmp_img)
                    meta["source"] = "placeholder"
                else:
                    dl_path = dl.path
                    meta["source"] = dl.info.get("source_engine", "unknown")

                    if self.cache and dl.source_url:
                        self.cache.put(
                            query=query, source_url=dl.source_url,
                            file_path=str(dl_path),
                            file_hash=dl.info.get("hash", ""),
                            width=dl.info.get("width", 0),
                            height=dl.info.get("height", 0),
                            file_size=dl.info.get("file_size", 0),
                            source_engine=dl.info.get("source_engine", ""),
                        )

            if self._shutdown.should_stop:
                meta["skipped"] = True
                return meta

            # ═══════════════════════════════════════════════
            #  2. BACKGROUND REMOVAL
            # ═══════════════════════════════════════════════
            use_orig = True
            bg_attempted = False
            if self.bg.should_remove(query):
                bg_res = self.bg.remove(dl_path, tmp_nobg)
                use_orig = bg_res.use_original
                bg_attempted = True
                if not use_orig:
                    self.stats.bg_removed.increment()
            else:
                self.stats.bg_skipped.increment()

            # ═══════════════════════════════════════════════
            #  3. COMPOSE AD
            # ═══════════════════════════════════════════════
            if not self.cfg.dry_run:
                nobg = tmp_nobg if (not use_orig and tmp_nobg.exists()) else None
                # template 
                template_name = TEMPLATE_CYCLE[idx % len(TEMPLATE_CYCLE)]
                log.info("[%d] Using template: %s", idx + 1, template_name)


                self.comp.compose(
                    product_path=dl_path,
                    nobg_path=nobg,
                    use_original=use_orig,
                    row=row,
                    output=out_path,
                    template_name=template_name,
                    
                )

                # ═══════════════════════════════════════════
                #  4. STAGE 2: POST-COMPOSE VERIFICATION
                # ═══════════════════════════════════════════
                if (
                    self.verifier
                    and self.cfg.verify.use_post_compose
                    and out_path.exists()
                    and meta.get("source") != "placeholder"
                ):
                    log.info("[%d] Stage 2: Verifying composed ad...", idx + 1)

                    from PIL import Image as PILImage
                    composed_img = PILImage.open(out_path)
                    post_result = self.verifier.verify_composed(composed_img, query)
                    composed_img.close()

                    self.stats.post_verified.increment()

                    meta["stage2_clip"] = post_result.clip_score
                    meta["stage2_blip"] = post_result.blip_score
                    meta["stage2_caption"] = post_result.blip_caption
                    meta["stage2_accepted"] = post_result.accepted

                    log.info(
                        "[%d] Stage 2: %s",
                        idx + 1, post_result.summary(),
                    )

                    if not post_result.accepted:
                        self.stats.post_verify_fails.increment()
                        log.warning(
                            "[%d] Post-compose FAILED — attempting recovery",
                            idx + 1,
                        )

                        recomposed = self._recompose(
                            idx, dl_path, tmp_nobg,
                            bg_attempted, use_orig,
                            row, query, out_path,
                        )

                        if recomposed:
                            meta["recomposed"] = True
                            meta["recompose_reason"] = "post_verify_fail"
                        else:
                            meta["recomposed"] = False
                            log.warning(
                                "[%d] Recompose failed — keeping original",
                                idx + 1,
                            )

            # ═══════════════════════════════════════════════
            #  5. UPDATE DATAFRAME
            # ═══════════════════════════════════════════════
            rel = f"images/{out_name}"
            with self._df_lock:
                self.df.at[idx, "image_path"] = rel

            meta["success"] = True
            self.stats.success.increment()
            self.notifier.on_milestone(self.stats.success.value)

        except Exception as exc:
            log.exception("Row %d failed", idx)
            meta["error"] = str(exc)
            self.stats.failed.increment()

        finally:
            for f in (tmp_img, tmp_nobg):
                try:
                    f.unlink(missing_ok=True)
                except OSError:
                    pass
            self.stats.total.increment()
            if self._csv_cnt.increment() % self.cfg.pipeline.csv_save_interval == 0:
                self._save_csv()
            gc.collect()

        return meta

    # ── RECOMPOSE ON POST-VERIFY FAILURE ────────────────────

    def _recompose(
        self,
        idx: int,
        dl_path: Path,
        tmp_nobg: Path,
        bg_was_attempted: bool,
        original_use_orig: bool,
        row: pd.Series,
        query: str,
        out_path: Path,
    ) -> bool:
        """
        Try to recompose the ad when post-verification fails.
        
        Strategy:
            Attempt 1: Compose WITHOUT background removal
            Attempt 2: Compose with original image + simpler text
        """
        cfg = self.cfg.verify
        from PIL import Image as PILImage

        for attempt in range(cfg.max_recompose_attempts):
            log.info("[%d] Recompose attempt %d/%d", idx + 1, attempt + 1, cfg.max_recompose_attempts)

            try:
                if attempt == 0 and cfg.recompose_without_bg and bg_was_attempted:
                    # Attempt 1: Use original image (no BG removal)
                    log.info("[%d] Recomposing WITHOUT background removal", idx + 1)
                    self.comp.compose(
                        product_path=dl_path,
                        nobg_path=None,           # Force original
                        use_original=True,         # Force original
                        row=row,
                        output=out_path,
                    )

                elif attempt == 1 and cfg.recompose_simpler_text:
                    # Attempt 2: Simpler text layout
                    log.info("[%d] Recomposing with simpler text", idx + 1)
                    simplified_row = row.copy()
                    simplified_row["monetary_mention"] = ""
                    simplified_row["call_to_action"] = ""

                    self.comp.compose(
                        product_path=dl_path,
                        nobg_path=None,
                        use_original=True,
                        row=simplified_row,
                        output=out_path,
                    )

                else:
                    continue

                # Verify the recomposed version
                if out_path.exists() and self.verifier:
                    composed_img = PILImage.open(out_path)
                    result = self.verifier.verify_composed(composed_img, query)
                    composed_img.close()

                    log.info("[%d] Recompose attempt %d: %s", idx + 1, attempt + 1, result.summary())

                    if result.accepted:
                        log.info("[%d] ✅ Recompose succeeded on attempt %d", idx + 1, attempt + 1)
                        return True

            except Exception as exc:
                log.warning("[%d] Recompose attempt %d error: %s", idx + 1, attempt + 1, exc)

        return False
    # ── run indices (single-threaded) ───────────────────────
    # def _run_single(self, indices: List[int]) -> None:
    #     """Single-threaded — simple, Ctrl+C works natively."""
    #     for idx in indices:
    #         if self._shutdown.should_stop:
    #             break
    #         meta = self._process(idx)
    #         if meta.get("success"):
    #             self.progress.mark_done(idx, meta)
    #         elif not meta.get("skipped"):
    #             self.progress.mark_failed(idx, meta)
    #         time.sleep(self.cfg.pipeline.inter_ad_delay)

    # # ── run indices (multi-threaded with working Ctrl+C) ────
    # def _run_threaded(self, indices: List[int]) -> None:
    #     """
    #     Multi-threaded with reliable Ctrl+C.
        
    #     Key: use SHORT timeouts on future.result() so the main
    #     thread stays responsive to KeyboardInterrupt.
    #     """
    #     workers = self.cfg.pipeline.max_workers
    #     pending: Dict[Future, int] = {}

    #     pool = ThreadPoolExecutor(
    #         max_workers=workers,
    #         thread_name_prefix="adgen",
    #     )

    #     try:
    #         # Submit all tasks
    #         for i in indices:
    #             if self._shutdown.should_stop:
    #                 break
    #             fut = pool.submit(self._process, i)
    #             pending[fut] = i

    #         # Collect results with SHORT timeout
    #         # This is the key — short timeout lets main thread
    #         # check for KeyboardInterrupt frequently
    #         while pending:
    #             if self._shutdown.should_stop:
    #                 log.warning("Shutdown: cancelling %d pending tasks", len(pending))
    #                 for fut in pending:
    #                     fut.cancel()
    #                 break

    #             # Check completed futures with 1-second timeout
    #             done_futures = []
    #             for fut in list(pending.keys()):
    #                 if fut.done():
    #                     done_futures.append(fut)

    #             if not done_futures:
    #                 # No futures done yet — sleep briefly to stay responsive
    #                 try:
    #                     time.sleep(0.5)
    #                 except KeyboardInterrupt:
    #                     self._shutdown.request_stop()
    #                     break
    #                 continue

    #             for fut in done_futures:
    #                 idx = pending.pop(fut)
    #                 try:
    #                     meta = fut.result(timeout=1.0)
    #                     if meta.get("success"):
    #                         self.progress.mark_done(idx, meta)
    #                     elif not meta.get("skipped"):
    #                         self.progress.mark_failed(idx, meta)
    #                 except KeyboardInterrupt:
    #                     self._shutdown.request_stop()
    #                     break
    #                 except Exception as exc:
    #                     log.error("Worker crash idx=%d: %s", idx, exc)
    #                     self.progress.mark_failed(idx, {"error": str(exc)})
    #                     self.stats.failed.increment()

    #     except KeyboardInterrupt:
    #         self._shutdown.request_stop()
    #         log.warning("KeyboardInterrupt in thread pool")

    #     finally:
    #         # Always shut down the pool
    #         log.info("Shutting down thread pool...")
    #         pool.shutdown(wait=False, cancel_futures=True)
    #         log.info("Thread pool stopped")

    # Add to imports at top of core/pipeline.py
    from cli.display import create_progress, format_row_status
    from cli.console import console

    # Replace _run_threaded with this version:

    def _run_threaded(self, indices: List[int]) -> None:
        """Multi-threaded with Rich progress bar."""
        workers = self.cfg.pipeline.max_workers
        pending: Dict[Future, int] = {}

        progress = create_progress()
        task = progress.add_task(
            "Generating ads...",
            total=len(indices),
        )

        pool = ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="adgen",
        )

        try:
            with progress:
                for i in indices:
                    if self._shutdown.should_stop:
                        break
                    fut = pool.submit(self._process, i)
                    pending[fut] = i

                while pending:
                    if self._shutdown.should_stop:
                        for fut in pending:
                            fut.cancel()
                        break

                    done_futures = [f for f in list(pending.keys()) if f.done()]

                    if not done_futures:
                        try:
                            time.sleep(0.3)
                        except KeyboardInterrupt:
                            self._shutdown.request_stop()
                            break
                        continue

                    for fut in done_futures:
                        idx = pending.pop(fut)
                        try:
                            meta = fut.result(timeout=1.0)
                            if meta.get("success"):
                                self.progress.mark_done(idx, meta)
                                progress.update(
                                    task,
                                    advance=1,
                                    description=format_row_status(
                                        idx + 1, len(self.df),
                                        meta.get("query", ""),
                                        "success",
                                    ),
                                )
                            elif not meta.get("skipped"):
                                self.progress.mark_failed(idx, meta)
                                progress.update(task, advance=1)
                        except KeyboardInterrupt:
                            self._shutdown.request_stop()
                            break
                        except Exception as exc:
                            self.progress.mark_failed(idx, {"error": str(exc)})
                            self.stats.failed.increment()
                            progress.update(task, advance=1)

        except KeyboardInterrupt:
            self._shutdown.request_stop()
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def _run_single(self, indices: List[int]) -> None:
        """Single-threaded with Rich progress bar."""
        progress = create_progress()
        task = progress.add_task("Generating ads...", total=len(indices))

        with progress:
            for idx in indices:
                if self._shutdown.should_stop:
                    break

                meta = self._process(idx)

                if meta.get("success"):
                    self.progress.mark_done(idx, meta)
                    progress.update(
                        task,
                        advance=1,
                        description=format_row_status(
                            idx + 1, len(self.df),
                            meta.get("query", ""),
                            "success",
                        ),
                    )
                elif not meta.get("skipped"):
                    self.progress.mark_failed(idx, meta)
                    progress.update(task, advance=1)

                time.sleep(self.cfg.pipeline.inter_ad_delay)


    # ── run indices (dispatcher) ────────────────────────────
    def _run_indices(self, indices: List[int]) -> None:
        if self.cfg.pipeline.max_workers <= 1:
            self._run_single(indices)
        else:
            self._run_threaded(indices)

    # ── main ────────────────────────────────────────────────
    def run(self) -> None:
        total = len(self.df)
        lo = self.cfg.start_index or 0
        hi = self.cfg.end_index or total

        all_indices = list(range(lo, min(hi, total)))
        if self.cfg.resume:
            indices = [i for i in all_indices if not self.progress.is_done(i)]
        else:
            indices = all_indices

        self.stats.skipped.increment(len(all_indices) - len(indices))

        log.info(
            "Pipeline: %d to process, %d skipped, workers=%d",
            len(indices), self.stats.skipped.value,
            self.cfg.pipeline.max_workers,
        )

        if self.verifier:
            log.info("Verification: %s", self.verifier.stats())

        try:
            # Process in chunks
            chunk = self.cfg.chunk_size
            for i in range(0, len(indices), chunk):
                if self._shutdown.should_stop:
                    log.warning("Shutdown: skipping remaining chunks")
                    break
                batch = indices[i : i + chunk]
                log.info("── Chunk %d–%d ──", batch[0] + 1, batch[-1] + 1)
                self._run_indices(batch)
                gc.collect()

            # Dead-letter queue
            if self.cfg.enable_dlq and not self._shutdown.should_stop:
                dlq = self.progress.get_dead_letters()
                if dlq:
                    log.info("── Dead-letter retry: %d rows ──", len(dlq))
                    self.stats.dlq_retries.increment(len(dlq))
                    self._run_indices(dlq)

        except KeyboardInterrupt:
            log.warning("KeyboardInterrupt in main loop")
            self._shutdown.request_stop()

        finally:
            # ALWAYS save progress and report, even on Ctrl+C
            log.info("")
            log.info("Saving final state...")
            self._save_csv()

            if self.health:
                self.health.log_report()
            if self.cache:
                log.info("Cache stats: %s", self.cache.stats())

            log.info("Progress DB: %s", self.progress.stats())
            log.info(self.stats.report())
            log.info("CSV → %s", self.cfg.paths.csv_output)

            if self._shutdown.should_stop:
                log.info("✅ Graceful shutdown complete — progress saved, safe to resume")
            
            self.notifier.on_completion(
                self.stats.total.value,
                self.stats.success.value,
                self.stats.elapsed,
            )

            if self.cfg.remove_temp and not self._shutdown.should_stop:
                self._cleanup()

    def _cleanup(self) -> None:
        try:
            if self.cfg.paths.temp_dir.exists():
                shutil.rmtree(self.cfg.paths.temp_dir, ignore_errors=True)
                log.info("Temp directory cleaned")
        except Exception as exc:
            log.warning("Cleanup failed: %s", exc)