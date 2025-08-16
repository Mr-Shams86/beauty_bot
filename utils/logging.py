# utils/logging.py
from __future__ import annotations
from loguru import logger
import sys

def setup_logging(debug: bool = False):
    logger.remove()
    logger.add(
        sys.stdout,
        level="DEBUG" if debug else "INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
        backtrace=False,
        diagnose=False,
    )
    return logger
