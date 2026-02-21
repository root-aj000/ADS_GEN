# # #!/usr/bin/env python3
# # """
# # Ad Generator v4.0 — Production-grade, multi-threaded.

# # Configuration lives in  config/settings.py
# # No CLI arguments — everything is controlled via flags.
# # """

# # from config.settings import cfg
# # from utils.log_config import setup_root, get_logger
# # from core.pipeline import AdPipeline


# # def main() -> None:
# #     # 1. bootstrap logging
# #     setup_root(cfg.paths.log_file, verbose=cfg.verbose)
# #     log = get_logger("main")

# #     # 2. banner
# #     log.info("=" * 60)
# #     log.info("🚀  AD GENERATOR v4.0  —  Production / Multi-Threaded")
# #     log.info("=" * 60)
# #     log.info("Search priority : %s", " → ".join(cfg.search.priority))
# #     log.info("Workers         : %d", cfg.pipeline.max_workers)
# #     log.info("Resume          : %s", cfg.resume)
# #     log.info("Dry run         : %s", cfg.dry_run)
# #     log.info("Verbose         : %s", cfg.verbose)
# #     log.info("Input CSV       : %s", cfg.paths.csv_input)
# #     log.info("Output dir      : %s", cfg.paths.images_dir)

# #     # 3. initialise & validate
# #     cfg.paths.ensure()
# #     cfg.validate()

# #     # 4. build pipeline
# #     pipeline = AdPipeline(cfg)

# #     if not cfg.resume:
# #         pipeline.progress.reset()
# #         log.info("Progress reset — fresh start")

# #     # 5. run
# #     pipeline.run()


# # if __name__ == "__main__":
# #     main()

# #!/usr/bin/env python3
# """
# Ad Generator v4.0 — Production-grade, multi-threaded.
# """

# from config.settings import cfg
# from utils.log_config import setup_root, get_logger
# from core.pipeline import AdPipeline


# def main() -> None:
#     setup_root(cfg.paths.log_file, verbose=cfg.verbose)
#     log = get_logger("main")

#     log.info("=" * 60)
#     log.info("🚀  AD GENERATOR v4.0  —  Production / Multi-Threaded")
#     log.info("=" * 60)
#     log.info("Search priority : %s", " → ".join(cfg.search.priority))
#     log.info("Workers         : %d", cfg.pipeline.max_workers)
#     log.info("Resume          : %s", cfg.resume)
#     log.info("Dry run         : %s", cfg.dry_run)
#     log.info("Verbose         : %s", cfg.verbose)
#     log.info("Input CSV       : %s", cfg.paths.csv_input)
#     log.info("Output dir      : %s", cfg.paths.images_dir)
#     log.info("CLIP verify     : %s", cfg.verify.use_clip)
#     log.info("BLIP verify     : %s", cfg.verify.use_blip)

#     cfg.paths.ensure()
#     cfg.validate()

#     pipeline = AdPipeline(cfg)

#     if not cfg.resume:
#         pipeline.progress.reset()
#         log.info("Progress reset — fresh start")

#     # Verification status
#     if pipeline.verifier:
#         status = pipeline.verifier.stats()
#         if status.get("clip_loaded") or status.get("blip_loaded"):
#             log.info("=" * 40)
#             log.info("🔍 VERIFICATION ACTIVE")
#             log.info("   CLIP : %s", "✅" if status["clip_loaded"] else "❌")
#             log.info("   BLIP : %s", "✅" if status["blip_loaded"] else "❌")
#             log.info("   Device: %s", status["device"])
#             log.info("   Models: %s", status.get("models_dir", "default"))
#             log.info("=" * 40)
#         else:
#             log.warning("⚠️  Verification enabled but no models loaded")
#     else:
#         log.info("Verification: DISABLED")

#     # Run with proper Ctrl+C handling
#     try:
#         pipeline.run()
#     except KeyboardInterrupt:
#         log.warning("")
#         log.warning("Interrupted — saving progress...")
#         pipeline._save_csv()
#         log.info("✅ Progress saved. Run again to resume.")
#     except Exception as exc:
#         log.exception("Fatal error: %s", exc)
#         pipeline._save_csv()
#         raise


# if __name__ == "__main__":
#     main()


#!/usr/bin/env python3
"""
Ad Generator v4.0 — Rich CLI Entry Point.

Usage:
    python main.py                    # Show help
    python main.py run                # Start pipeline
    python main.py run --fresh -w 8   # Fresh start, 8 workers
    python main.py status             # Show progress
    python main.py preview            # Preview queries
    python main.py config             # Show configuration
    python main.py verify img.jpg "red shoes"
    python main.py cache --clear
    python main.py clean --all
"""

from cli.app import app

if __name__ == "__main__":
    app()