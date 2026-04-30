from __future__ import annotations

from typing import Any

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from automation.core.selectors import locator


def wait_visible(page: Page, selector: str, timeout: int) -> None:
    locator(page, selector).first.wait_for(timeout=timeout)


def wait_visible_bool(target: Any, timeout_ms: int) -> bool:
    try:
        target.wait_for(state="visible", timeout=timeout_ms)
        return True
    except PlaywrightTimeoutError:
        return False


def ensure_visible(target: Any, timeout_ms: int, error_message: str) -> None:
    if not wait_visible_bool(target, timeout_ms):
        raise RuntimeError(error_message)


def count_visible_elements(context: Any, selector: str) -> int:
    try:
        return int(
            context.evaluate(
                """
                (selector) => {
                  const isVisible = (el) => {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none'
                      && style.visibility !== 'hidden'
                      && Number(style.opacity || '1') !== 0
                      && rect.width > 0
                      && rect.height > 0;
                  };
                  return Array.from(document.querySelectorAll(selector)).filter(isVisible).length;
                }
                """,
                selector,
            )
        )
    except Exception:
        return 0


def locator_has_non_empty_value(target: Any) -> bool:
    try:
        return bool(
            target.evaluate(
                """
                (el) => {
                  if (!el) return false;
                  const value = String(el.value ?? el.getAttribute('value') ?? el.textContent ?? '').trim();
                  return value.length > 0;
                }
                """
            )
        )
    except Exception:
        return False


def wait_markers_in_context(
    context: Any,
    page: Page,
    marker_selectors: list[str],
    timeout: int,
    per_try_timeout: int = 400,
    interval_ms: int = 60,
) -> bool:
    current_timeout = max(1, min(timeout, per_try_timeout))
    rounds = max(1, int(timeout / current_timeout))
    for _ in range(rounds):
        for selector in marker_selectors:
            if not selector:
                continue
            try:
                if wait_visible_bool(context.locator(selector).first, current_timeout):
                    return True
            except Exception:
                continue
        page.wait_for_timeout(interval_ms)
    return False


def wait_any_marker(
    page: Page,
    contexts: list[Any],
    marker_selectors: list[str],
    timeout: int,
    per_try_timeout: int = 400,
    interval_ms: int = 60,
) -> bool:
    current_timeout = max(1, min(timeout, per_try_timeout))
    rounds = max(1, int(timeout / current_timeout))
    for _ in range(rounds):
        for context in contexts:
            for selector in marker_selectors:
                if not selector:
                    continue
                try:
                    if wait_visible_bool(context.locator(selector).first, current_timeout):
                        return True
                except Exception:
                    continue
        page.wait_for_timeout(interval_ms)
    return False


def wait_url_contains(page: Page, text: str, timeout: int) -> None:
    page.wait_for_url(f"**{text}**", timeout=timeout)


__all__ = [
    "count_visible_elements",
    "ensure_visible",
    "locator_has_non_empty_value",
    "wait_any_marker",
    "wait_markers_in_context",
    "wait_url_contains",
    "wait_visible",
    "wait_visible_bool",
]
