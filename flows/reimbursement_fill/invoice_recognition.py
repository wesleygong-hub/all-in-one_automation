from __future__ import annotations

from time import perf_counter
from typing import Callable

from playwright.sync_api import Page


def observe_recognition_outcome(
    page: Page,
    selectors: dict[str, str],
    timeout_ms: int,
    detect_duplicate_invoice_message_fast: Callable[[Page, dict[str, str], int], str | None],
    is_invoice_recognized: Callable[[Page, dict[str, str], int], bool],
) -> tuple[bool, str | None]:
    end_at = perf_counter() + (timeout_ms / 1000)
    recognized_at: float | None = None
    post_recognize_guard_ms = min(1200, max(500, timeout_ms))
    while perf_counter() < end_at:
        duplicate_message = detect_duplicate_invoice_message_fast(page, selectors, 40)
        if duplicate_message:
            return False, duplicate_message
        if is_invoice_recognized(page, selectors, 120):
            if recognized_at is None:
                recognized_at = perf_counter()
            elif (perf_counter() - recognized_at) * 1000 >= post_recognize_guard_ms:
                return True, None
        page.wait_for_timeout(40)
    return (recognized_at is not None), None


__all__ = ["observe_recognition_outcome"]
