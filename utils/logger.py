"""
Logging utility with fallback to standard library logging if loguru is not installed.
"""

import sys

try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger("DesktopPilot")

__all__ = ["logger"]

