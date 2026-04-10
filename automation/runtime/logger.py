from __future__ import annotations

import logging
from typing import Iterable


def setup_logger(verbose: bool = True) -> logging.Logger:
    logger = logging.getLogger("dsn_uploader")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    if not verbose:
        logger.disabled = True
    return logger


def print_block(logger: logging.Logger, lines: Iterable[str]) -> None:
    for line in lines:
        logger.info(line)


__all__ = ["setup_logger", "print_block"]
