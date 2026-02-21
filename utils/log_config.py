# # """
# # Centralised logging setup.
# # Every module does:  ``from utils.log_config import get_logger``
# # """

# # from __future__ import annotations

# # import logging
# # import sys
# # from pathlib import Path
# # from typing import Optional

# # _CONFIGURED = False


# # def setup_root(
# #     log_file: Path,
# #     verbose: bool = False,
# # ) -> None:
# #     """Call once at startup to wire console + file handlers."""
# #     global _CONFIGURED
# #     if _CONFIGURED:
# #         return

# #     level = logging.DEBUG if verbose else logging.INFO
# #     fmt = "%(asctime)s │ %(levelname)-7s │ %(threadName)-14s │ %(name)-22s │ %(message)s"
# #     datefmt = "%H:%M:%S"

# #     log_file.parent.mkdir(parents=True, exist_ok=True)

# #     logging.basicConfig(
# #         level=level,
# #         format=fmt,
# #         datefmt=datefmt,
# #         handlers=[
# #             logging.StreamHandler(sys.stdout),
# #             logging.FileHandler(str(log_file), encoding="utf-8"),
# #         ],
# #     )

# #     # silence chatty third-party loggers
# #     for name in ("urllib3", "PIL", "rembg", "onnxruntime", "httpx"):
# #         logging.getLogger(name).setLevel(logging.WARNING)

# #     _CONFIGURED = True


# # def get_logger(name: Optional[str] = None) -> logging.Logger:
# #     """Return a child logger.  Typical usage: ``log = get_logger(__name__)``."""
# #     return logging.getLogger(name or "adgen")

# """
# Centralised logging setup.
# Every module does:  ``from utils.log_config import get_logger``
# """

# from __future__ import annotations

# import logging
# import sys
# from pathlib import Path
# from typing import Optional

# _CONFIGURED = False

# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# #  NOISY LOGGERS TO SILENCE
# # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# NOISY_LOGGERS = [
#     # Network / HTTP
#     "urllib3",
#     "urllib3.connectionpool",
#     "requests",
#     "httpx",
#     "httpcore",
#     "httpcore.http11",
#     "httpcore.connection",
#     "h11",
#     "h2",
#     "h2.client",
#     "h2.proto",
#     "h2.codec",
#     "h2.frame",
#     "h2.hpack",
#     "hyper",
#     "hyper_util",
#     "hyper_util.client",
#     "hyper_util.client.legacy",
#     "hyper_util.client.legacy.pool",
    
#     # TLS / Security
#     "rustls",
#     "rustls.client",
#     "rustls.client.hs",
#     "rustls.client.tls13",
    
#     # Image processing
#     "PIL",
#     "PIL.Image",
#     "PIL.PngImagePlugin",
#     "PIL.JpegImagePlugin",
    
#     # Background removal
#     "rembg",
#     "rembg.bg",
#     "onnxruntime",
#     "onnx",
    
#     # DuckDuckGo
#     "duckduckgo_search",
#     "duckduckgo_search.DDGS",
#     "primp",
    
#     # Other
#     "asyncio",
#     "concurrent",
#     "concurrent.futures",
#     "chardet",
#     "charset_normalizer",
#     "filelock",
# ]


# def setup_root(
#     log_file: Path,
#     verbose: bool = False,
# ) -> None:
#     """Call once at startup to wire console + file handlers."""
#     global _CONFIGURED
#     if _CONFIGURED:
#         return

#     level = logging.DEBUG if verbose else logging.INFO
#     fmt = "%(asctime)s │ %(levelname)-7s │ %(threadName)-14s │ %(name)-22s │ %(message)s"
#     datefmt = "%H:%M:%S"

#     log_file.parent.mkdir(parents=True, exist_ok=True)

#     logging.basicConfig(
#         level=level,
#         format=fmt,
#         datefmt=datefmt,
#         handlers=[
#             logging.StreamHandler(sys.stdout),
#             logging.FileHandler(str(log_file), encoding="utf-8"),
#         ],
#     )

#     # Silence all noisy third-party loggers
#     for name in NOISY_LOGGERS:
#         logger = logging.getLogger(name)
#         logger.setLevel(logging.WARNING)
#         logger.propagate = False

#     # Also silence any logger starting with these prefixes
#     for prefix in ["h2.", "rustls.", "hyper", "httpcore.", "httpx."]:
#         for handler_name in logging.Logger.manager.loggerDict:
#             if handler_name.startswith(prefix):
#                 logging.getLogger(handler_name).setLevel(logging.WARNING)

#     _CONFIGURED = True


# def get_logger(name: Optional[str] = None) -> logging.Logger:
#     """Return a child logger.  Typical usage: ``log = get_logger(__name__)``."""
#     return logging.getLogger(name or "adgen")


# def silence_logger(name: str) -> None:
#     """Dynamically silence a logger after setup."""
#     logger = logging.getLogger(name)
#     logger.setLevel(logging.WARNING)
#     logger.propagate = False

"""
Centralised logging setup.
"""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path
from typing import Optional

_CONFIGURED = False

# All noisy loggers to silence
NOISY_LOGGERS = [
    # Network
    "urllib3", "urllib3.connectionpool", "requests", "httpx", "httpcore",
    "h11", "h2", "hyper", "hyper_util", "hpack",
    # TLS
    "rustls", "ssl",
    # HTTP/2
    "h2.client", "h2.proto", "h2.codec", "h2.frame", "h2.hpack",
    "hyper_util.client", "hyper_util.client.legacy", "hyper_util.client.legacy.pool",
    # Image
    "PIL", "PIL.Image", "PIL.PngImagePlugin", "PIL.JpegImagePlugin",
    # ML/Background removal
    "rembg", "rembg.bg", "onnxruntime", "onnx",
    # Search
    "duckduckgo_search", "duckduckgo_search.DDGS", "primp", "reqwest",
    # Other
    "asyncio", "concurrent", "chardet", "charset_normalizer", "filelock",
]


def setup_root(log_file: Path, verbose: bool = False) -> None:
    """Configure logging once at startup."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s │ %(levelname)-7s │ %(threadName)-14s │ %(message)s"
    datefmt = "%H:%M:%S"

    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_file), encoding="utf-8"),
        ],
    )

    # Silence noisy loggers
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.ERROR)
        logging.getLogger(name).propagate = False

    # Silence all loggers starting with these prefixes
    for prefix in ["h2.", "rustls.", "hyper", "httpcore.", "httpx.", "reqwest."]:
        for handler_name in list(logging.Logger.manager.loggerDict.keys()):
            if handler_name.startswith(prefix):
                logging.getLogger(handler_name).setLevel(logging.ERROR)
                logging.getLogger(handler_name).propagate = False

    # Suppress Python warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", message=".*duckduckgo_search.*")
    warnings.filterwarnings("ignore", message=".*Palette images.*")

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name or "adgen")