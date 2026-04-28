from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

LOGGER_NAME = "all_in_one_automation"


def setup_logger(verbose: bool = True, log_file: str | None = None) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    if not verbose:
        logger.disabled = True
    return logger


def print_block(logger: logging.Logger, lines: Iterable[str]) -> None:
    for line in lines:
        logger.info(line)


__all__ = ["setup_logger", "print_block"]
