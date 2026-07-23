# app/utils/logger.py
import logging
import sys
from app.core.config import settings


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger.
    In DEBUG mode: verbose output with line numbers.
    In production: clean INFO-level logs.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger   # Already configured

    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    fmt = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
        if settings.DEBUG
        else "%(asctime)s | %(levelname)-8s | %(message)s"
    )

    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger