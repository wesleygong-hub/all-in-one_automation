from __future__ import annotations

from time import perf_counter
from typing import Any, Callable


def attempt_finance_share_activation(
    page: Any,
    action: Callable[[], None],
    finance_ready_selectors: list[str],
    timeout: int,
    is_finance_share_page: Callable[[Any, list[str]], bool],
) -> Any | None:
    del timeout
    before_pages = list(page.context.pages)
    action()

    for _ in range(4):
        page.wait_for_timeout(140)
        for candidate in reversed(page.context.pages):
            if candidate.is_closed():
                continue
            try:
                candidate.wait_for_load_state("domcontentloaded", timeout=300)
            except Exception:
                pass
            if is_finance_share_page(candidate, finance_ready_selectors):
                return candidate

    if len(page.context.pages) > len(before_pages):
        for candidate in reversed(page.context.pages):
            if candidate not in before_pages and not candidate.is_closed():
                return candidate

    return None


def safe_click_target(target: Any, timeout: int, force: bool = False) -> None:
    target.click(timeout=timeout, force=force)


def visible_tree_node(page: Any, text: str) -> Any:
    return page.locator("div.tree-node:visible").filter(has=page.locator("span.tree-title", has_text=text)).first


def ensure_tree_node_expanded(page: Any, text: str, timeout: int) -> None:
    node = visible_tree_node(page, text)
    node.wait_for(state="visible", timeout=timeout)
    hit = node.locator("span.tree-hit").first
    if hit.count() == 0:
        return

    try:
        hit.click(timeout=timeout)
        page.wait_for_timeout(100)
    except Exception:
        pass

    try:
        clazz = hit.get_attribute("class") or ""
        if "tree-collapsed" in clazz:
            hit.click(timeout=timeout)
            page.wait_for_timeout(100)
    except Exception:
        pass


def click_tree_title_fast(
    page: Any,
    text: str,
    timeout: int,
    wait_visible: Callable[[Any, int], bool],
) -> None:
    last_error: Exception | None = None
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        title_locator = visible_tree_node(page, text).locator("span.tree-title").first
        try:
            if wait_visible(title_locator, 300):
                title_locator.click(timeout=300)
                return
        except Exception as exc:
            last_error = exc
        page.wait_for_timeout(60)
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"未找到可点击的树菜单节点：{text}")


def click_go_reimbursement_fast(
    page: Any,
    selector: str,
    timeout: int,
    click_locator_fast: Callable[[Any, Any, str, int, str], None],
) -> None:
    click_locator_fast(page, page, selector, timeout, "未找到可点击的‘我要报账’按钮")


def wait_iam_login_state(
    username_locator: Any,
    finance_locator: Any,
    timeout_ms: int,
    wait_visible: Callable[[Any, int], bool],
) -> str:
    interval_ms = 250
    elapsed_ms = 0
    while elapsed_ms <= timeout_ms:
        if wait_visible(finance_locator, 250):
            return "finance"
        if wait_visible(username_locator, 250):
            return "username"
        elapsed_ms += interval_ms
    return "timeout"


def click_optional(locator: Any) -> None:
    try:
        locator.click(force=True)
    except Exception:
        pass


def activate_by_keyboard(page: Any, locator: Any) -> None:
    locator.focus()
    page.keyboard.press("Enter")


def is_finance_share_page(
    page: Any,
    selectors: list[str],
    wait_visible: Callable[[Any, int], bool],
) -> bool:
    try:
        if "fssc.fsg.inner" in page.url.lower():
            return True
    except Exception:
        pass
    for selector in selectors:
        if not selector:
            continue
        try:
            if wait_visible(page.locator(selector).first, 200):
                return True
        except Exception:
            continue
    return False


__all__ = [
    "activate_by_keyboard",
    "attempt_finance_share_activation",
    "click_go_reimbursement_fast",
    "click_optional",
    "click_tree_title_fast",
    "ensure_tree_node_expanded",
    "is_finance_share_page",
    "safe_click_target",
    "visible_tree_node",
    "wait_iam_login_state",
]
