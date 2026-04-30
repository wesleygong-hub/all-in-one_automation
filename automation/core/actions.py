from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from playwright.sync_api import FileChooser, Page

from automation.core.selectors import locator, locator_with_scope, modal_scope


def fill_locator(page: Page, selector: str, value: str, timeout: int) -> None:
    target = locator(page, selector)
    target.first.wait_for(timeout=timeout)
    target.first.fill(value, timeout=timeout)


def click_locator(page: Page, selector: str, timeout: int, within_modal: bool = False) -> None:
    target = locator(page, selector)
    if within_modal:
        target = locator_with_scope(modal_scope(page), selector)
    target.first.wait_for(timeout=timeout)
    target.first.click(timeout=timeout)


def click_locator_fast(context: Any, page: Page, selector: str, timeout: int, error_message: str) -> None:
    last_error: Exception | None = None
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        current = context.locator(selector).first
        try:
            current.wait_for(state="visible", timeout=300)
            current.click(timeout=300)
            return
        except Exception as exc:
            last_error = exc
        page.wait_for_timeout(60)
    if last_error is not None:
        raise last_error
    raise RuntimeError(error_message)


def hover_locator_fast(context: Any, page: Page, selector: str, timeout: int, error_message: str) -> None:
    last_error: Exception | None = None
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        current = context.locator(selector).first
        try:
            current.wait_for(state="visible", timeout=300)
            current.hover(timeout=300)
            return
        except Exception as exc:
            last_error = exc
        page.wait_for_timeout(60)
    if last_error is not None:
        raise last_error
    raise RuntimeError(error_message)


def click_latest_visible_element(context: Any, selector: str) -> bool:
    try:
        return bool(
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
                  const nodes = Array.from(document.querySelectorAll(selector)).filter(isVisible);
                  const target = nodes[nodes.length - 1];
                  if (!target) return false;
                  target.click();
                  return true;
                }
                """,
                selector,
            )
        )
    except Exception:
        return False


def fill_locator_value(
    context: Any,
    selector: str,
    value: str,
    timeout: int,
    error_message: str,
    wait_visible: Callable[[Any, int], bool],
) -> None:
    target = context.locator(selector).first
    if not wait_visible(target, min(timeout, 1800)):
        raise RuntimeError(error_message)
    try:
        target.click(timeout=300)
    except Exception:
        pass
    target.fill(value, timeout=timeout)
    try:
        target.dispatch_event("change")
    except Exception:
        pass


def fill_first_matching_locator(
    contexts: list[Any],
    selector_candidates: list[str],
    value: str,
    timeout: int,
    error_message: str,
    wait_visible: Callable[[Any, int], bool],
    context_namer: Callable[[Any, int], str] | None = None,
) -> None:
    attempts: list[str] = []
    namer = context_namer or (lambda _context, idx: f"context[{idx}]")
    for idx, context in enumerate(contexts):
        context_name = namer(context, idx)
        for selector in selector_candidates:
            if not selector:
                continue
            try:
                target = context.locator(selector)
                count = target.count()
                attempts.append(f"{context_name}:{selector}:count={count}")
                if count == 0:
                    continue
                if not wait_visible(target.first, min(timeout, 500)):
                    attempts.append(f"{context_name}:{selector}:visible=false")
                    continue
                fill_locator_value(context, selector, value, timeout, error_message, wait_visible)
                return
            except Exception as exc:
                attempts.append(f"{context_name}:{selector}:error={type(exc).__name__}")
    raise RuntimeError(f"{error_message} attempts={attempts}")


def click_first_matching_locator(
    contexts: list[Any],
    page: Page,
    selector_candidates: list[str],
    timeout: int,
    error_message: str,
    context_namer: Callable[[Any, int], str] | None = None,
) -> None:
    attempts: list[str] = []
    namer = context_namer or (lambda _context, idx: f"context[{idx}]")
    for idx, context in enumerate(contexts):
        context_name = namer(context, idx)
        for selector in selector_candidates:
            if not selector:
                continue
            try:
                target = context.locator(selector)
                count = target.count()
                attempts.append(f"{context_name}:{selector}:count={count}")
                if count == 0:
                    continue
                click_locator_fast(context, page, selector, min(timeout, 1200), error_message)
                return
            except Exception as exc:
                attempts.append(f"{context_name}:{selector}:error={type(exc).__name__}")
    raise RuntimeError(f"{error_message} attempts={attempts}")


def set_input_files(context: Any, selector: str, file_paths: str | list[str], timeout: int, error_message: str) -> None:
    target = context.locator(selector).first
    try:
        target.wait_for(state="visible", timeout=min(timeout, 800))
    except Exception as exc:
        raise RuntimeError(error_message) from exc
    target.set_input_files(file_paths, timeout=timeout)


def dismiss_overlays(page: Page) -> None:
    esc_presses = 0
    while esc_presses < 3:
        try:
            page.keyboard.press("Escape")
        except Exception:
            break
        page.wait_for_timeout(100)
        esc_presses += 1

    closers = [
        page.locator(".ant-modal-close"),
        page.locator(".ant-drawer-close"),
        page.locator(".ant-select-dropdown .ant-select-item-option-active"),
    ]
    for current in closers:
        try:
            if current.count() > 0 and current.first.is_visible():
                current.first.click(timeout=500)
        except Exception:
            continue


def upload_file(page: Page, upload_selector: str, file_path: str, timeout: int) -> None:
    file_name = Path(file_path).name
    errors: list[str] = []

    try:
        current = locator(page, upload_selector)
        current.first.set_input_files(file_path, timeout=timeout)
        page.wait_for_timeout(800)
        wait_uploaded_file_visible(page, file_name, timeout)
        return
    except Exception as exc:
        errors.append(f"hidden-input upload failed: {exc}")

    try:
        with page.expect_file_chooser(timeout=timeout) as chooser_info:
            click_visible_upload_file_button(page, timeout)
        chooser: FileChooser = chooser_info.value
        chooser.set_files(file_path, timeout=timeout)
        page.wait_for_timeout(800)
        wait_uploaded_file_visible(page, file_name, timeout)
        return
    except Exception as exc:
        errors.append(f"visible-button upload failed: {exc}")

    raise RuntimeError("文件上传未成功: " + " | ".join(errors))


def click_visible_upload_file_button(page: Page, timeout: int) -> None:
    candidates = [
        page.locator("button.ant-btn.cdc-app.ant-btn-default.ant-btn-color-default.ant-btn-variant-outlined").filter(
            has_text=re.compile("^上传文件$")
        ),
        page.locator("button.ant-btn.cdc-app").filter(has_text=re.compile("^上传文件$")),
        page.get_by_role("button", name="上传文件"),
        page.locator("button").filter(has_text=re.compile("上传文件")),
        page.get_by_text("上传文件", exact=False),
    ]
    for current in candidates:
        try:
            if current.count() > 0:
                current.first.click(timeout=timeout)
                return
        except Exception:
            continue
    raise RuntimeError("未找到可见的“上传文件”按钮")


def wait_uploaded_file_visible(page: Page, file_name: str, timeout: int) -> None:
    candidates = [
        page.get_by_text(file_name, exact=False),
        page.locator(f"text={file_name}"),
    ]
    for current in candidates:
        try:
            current.first.wait_for(timeout=timeout)
            return
        except Exception:
            continue
    raise RuntimeError(f"页面未显示已上传文件名: {file_name}")


__all__ = [
    "click_first_matching_locator",
    "click_latest_visible_element",
    "click_locator",
    "click_locator_fast",
    "click_visible_upload_file_button",
    "dismiss_overlays",
    "fill_first_matching_locator",
    "fill_locator",
    "fill_locator_value",
    "hover_locator_fast",
    "set_input_files",
    "upload_file",
    "wait_uploaded_file_visible",
]
