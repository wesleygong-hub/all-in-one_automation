from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

from automation.core.contexts import context_debug_name


def has_visible_dialog(
    context: Any,
    wait_visible: Callable[[Any, int], bool],
    dialog_selector: str = ".messager-button",
    timeout_ms: int = 80,
) -> bool:
    try:
        return wait_visible(context.locator(dialog_selector).last, timeout_ms)
    except Exception:
        return False


def click_dialog_button_if_needed(
    page: Any,
    contexts: list[Any],
    wait_visible: Callable[[Any, int], bool],
    button_text: str = "确定",
    confirm_selectors: list[str] | None = None,
    dialog_selector: str = ".messager-button",
    button_selector: str = ".messager-button a",
    timeout_ms: int = 1200,
    post_click_wait_ms: int = 80,
) -> tuple[bool, bool, list[str]]:
    attempts: list[str] = []
    dialog_seen = False
    end_at = perf_counter() + (timeout_ms / 1000)
    selectors = confirm_selectors or []

    while perf_counter() < end_at:
        dialog_visible_any = False
        for context_index, context in enumerate(contexts):
            context_name = context_debug_name(context, context_index)
            try:
                dialog_visible = has_visible_dialog(context, wait_visible, dialog_selector, min(timeout_ms, 80))
                attempts.append(f"{context_name}:dialog_visible={dialog_visible}")
                dialog_visible_any = dialog_visible_any or dialog_visible
                dialog_seen = dialog_seen or dialog_visible
            except Exception as exc:
                attempts.append(f"{context_name}:dialog_visible=error:{type(exc).__name__}")
                dialog_visible = False

            if not dialog_visible:
                continue

            try:
                buttons = context.locator(button_selector)
                button_count = buttons.count()
                attempts.append(f"{context_name}:button_count={button_count}")
                for index in range(button_count):
                    button = buttons.nth(index)
                    visible = wait_visible(button, 80)
                    attempts.append(f"{context_name}:button[{index}].visible={visible}")
                    if not visible:
                        continue
                    text = ""
                    try:
                        text = (button.inner_text(timeout=40) or "").strip()
                    except Exception:
                        text = ""
                    if not text:
                        try:
                            text = (button.text_content(timeout=40) or "").strip()
                        except Exception:
                            text = ""
                    attempts.append(f"{context_name}:button[{index}].text={text or '<empty>'}")
                    if button_text not in text:
                        continue
                    clicked = _click_dialog_locator(button, attempts, f"{context_name}:button[{index}]")
                    if not clicked:
                        continue
                    page.wait_for_timeout(post_click_wait_ms)
                    if not has_visible_dialog(context, wait_visible, dialog_selector, 80):
                        attempts.append(f"{context_name}:button[{index}].dialog_closed=true")
                        return True, dialog_seen, attempts
                    attempts.append(f"{context_name}:button[{index}].dialog_closed=false")
            except Exception as exc:
                attempts.append(f"{context_name}:messager_buttons=error:{type(exc).__name__}")

            for selector in selectors:
                if not selector:
                    continue
                try:
                    locator = context.locator(selector).last
                    visible = wait_visible(locator, 80)
                    attempts.append(f"{context_name}:selector:{selector}:visible={visible}")
                    if not visible:
                        continue
                    clicked = _click_dialog_locator(locator, attempts, f"{context_name}:selector:{selector}")
                    if not clicked:
                        continue
                    page.wait_for_timeout(post_click_wait_ms)
                    if not has_visible_dialog(context, wait_visible, dialog_selector, 80):
                        attempts.append(f"{context_name}:selector:{selector}:dialog_closed=true")
                        return True, dialog_seen, attempts
                    attempts.append(f"{context_name}:selector:{selector}:dialog_closed=false")
                except Exception as exc:
                    attempts.append(f"{context_name}:selector:{selector}:error:{type(exc).__name__}")

        if not dialog_visible_any:
            return False, dialog_seen, attempts
        page.wait_for_timeout(40)

    return False, dialog_seen, attempts


def wait_for_condition(
    page: Any,
    condition: Callable[[], bool],
    timeout_ms: int,
    interval_ms: int = 40,
) -> bool:
    end_at = perf_counter() + (timeout_ms / 1000)
    while perf_counter() < end_at:
        try:
            if condition():
                return True
        except Exception:
            pass
        page.wait_for_timeout(interval_ms)
    return False


def is_selected_tab_present(page: Any, tab_text: str) -> bool:
    try:
        return page.locator("li.tabs-selected").filter(has_text=tab_text).count() > 0
    except Exception:
        return False


def wait_for_selected_tab_closed(
    page: Any,
    tab_text: str,
    timeout_ms: int,
    interval_ms: int = 40,
) -> bool:
    return wait_for_condition(
        page,
        lambda: not is_selected_tab_present(page, tab_text),
        timeout_ms,
        interval_ms,
    )


def wait_for_tab_closed_and_state(
    page: Any,
    tab_text: str,
    state_check: Callable[[], bool],
    timeout_ms: int,
    interval_ms: int = 40,
) -> bool:
    return wait_for_condition(
        page,
        lambda: (not is_selected_tab_present(page, tab_text)) and state_check(),
        timeout_ms,
        interval_ms,
    )


def _click_dialog_locator(locator: Any, attempts: list[str], prefix: str) -> bool:
    try:
        locator.click(timeout=100)
        attempts.append(f"{prefix}.click=ok")
        return True
    except Exception as exc:
        attempts.append(f"{prefix}.click=error:{type(exc).__name__}")
        try:
            locator.click(timeout=100, force=True)
            attempts.append(f"{prefix}.force_click=ok")
            return True
        except Exception as force_exc:
            attempts.append(f"{prefix}.force_click=error:{type(force_exc).__name__}")
            try:
                locator.evaluate("(el) => el.click()")
                attempts.append(f"{prefix}.js_click=ok")
                return True
            except Exception as js_exc:
                attempts.append(f"{prefix}.js_click=error:{type(js_exc).__name__}")
                return False


__all__ = [
    "click_dialog_button_if_needed",
    "has_visible_dialog",
    "is_selected_tab_present",
    "wait_for_condition",
    "wait_for_selected_tab_closed",
    "wait_for_tab_closed_and_state",
]
