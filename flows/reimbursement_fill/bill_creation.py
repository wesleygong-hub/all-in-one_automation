from __future__ import annotations

from time import perf_counter
from typing import Any, Callable


LocatorContext = Any


def open_new_bill_menu(
    page: Any,
    context: LocatorContext,
    selectors: dict[str, str],
    timeout: int,
    is_new_bill_menu_open: Callable[[LocatorContext, Any, dict[str, str], int], bool],
    click_latest_visible_element: Callable[[LocatorContext, str], bool],
    first_visible_locator: Callable[[LocatorContext, str, int], Any | None],
) -> None:
    if is_new_bill_menu_open(context, page, selectors, 160):
        return

    trigger_selectors: list[tuple[str, str]] = [
        ("new_bill_header_container", "div.pros.subpage"),
        ("new_bill_header_h2", "div.pros.subpage > h2"),
    ]

    for _label, selector in reversed(trigger_selectors):
        if not selector:
            continue
        try:
            if click_latest_visible_element(context, selector):
                page.wait_for_timeout(40)
                if is_new_bill_menu_open(context, page, selectors, 80):
                    return
        except Exception:
            continue
        try:
            js_result = context.evaluate(
                """
                (sel) => {
                  const isVisible = (el) => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                  const nodes = [...document.querySelectorAll(sel)].filter(isVisible);
                  const el = nodes[nodes.length - 1];
                  if (!el) return false;
                  ['mouseover', 'mouseenter', 'mousedown', 'mouseup', 'click'].forEach((type) => {
                    el.dispatchEvent(new MouseEvent(type, { bubbles: true }));
                  });
                  return true;
                }
                """,
                selector,
            )
            if js_result:
                page.wait_for_timeout(40)
                if is_new_bill_menu_open(context, page, selectors, 80):
                    return
        except Exception:
            continue

    attempts: list[str] = []
    per_wait = 30
    end_at = perf_counter() + (min(timeout, 900) / 1000)
    while perf_counter() < end_at:
        for label, selector in trigger_selectors:
            if not selector:
                continue
            locator = first_visible_locator(context, selector, 50)
            try:
                if locator is None:
                    attempts.append(f"{label}:visible=false")
                    continue

                attempts.append(f"{label}:visible=true")
                try:
                    locator.scroll_into_view_if_needed(timeout=120)
                    attempts.append(f"{label}:scroll=ok")
                except Exception as exc:
                    attempts.append(f"{label}:scroll=fail:{type(exc).__name__}")

                try:
                    locator.click(timeout=120)
                    attempts.append(f"{label}:click=ok")
                except Exception as exc:
                    attempts.append(f"{label}:click=fail:{type(exc).__name__}")
                page.wait_for_timeout(per_wait)
                if is_new_bill_menu_open(context, page, selectors, 100):
                    attempts.append(f"{label}:menu_open_after_click=true")
                    return

                try:
                    locator.click(timeout=120, force=True)
                    attempts.append(f"{label}:force_click=ok")
                except Exception as exc:
                    attempts.append(f"{label}:force_click=fail:{type(exc).__name__}")
                page.wait_for_timeout(per_wait)
                if is_new_bill_menu_open(context, page, selectors, 100):
                    attempts.append(f"{label}:menu_open_after_force_click=true")
                    return
                try:
                    js_result = context.evaluate(
                        """
                        (sel) => {
                          if (sel.startsWith('xpath=')) return 'skip-xpath-js';
                          const isVisible = (el) => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                          const nodes = [...document.querySelectorAll(sel)].filter(isVisible);
                          if (!nodes.length) return 'no-visible-node';
                          const el = nodes[0];
                          ['mouseover', 'mouseenter', 'mousedown', 'mouseup', 'click'].forEach(type => {
                            el.dispatchEvent(new MouseEvent(type, { bubbles: true }));
                          });
                          return `js-dispatched:${nodes.length}`;
                        }
                        """,
                        selector,
                    )
                    attempts.append(f"{label}:js={js_result}")
                except Exception as exc:
                    attempts.append(f"{label}:js=fail:{type(exc).__name__}")
                page.wait_for_timeout(per_wait)
                if is_new_bill_menu_open(context, page, selectors, 100):
                    attempts.append(f"{label}:menu_open_after_js=true")
                    return
            except Exception as exc:
                attempts.append(f"{label}:outer_fail:{type(exc).__name__}")
        page.wait_for_timeout(per_wait)

    raise RuntimeError(f"未成功展开‘新建单据’菜单 attempts={attempts}")


def is_new_bill_menu_open(
    context: LocatorContext,
    page: Any,
    selectors: dict[str, str],
    timeout: int,
    wait_markers_in_context: Callable[[LocatorContext, Any, list[str], int], bool],
) -> bool:
    marker_selectors = [
        "li.prosahover",
        "div.prosmore:not(.hide)",
        selectors.get("bill_type_expense", ""),
        selectors.get("bill_subtype_business_entertainment", ""),
        selectors.get("bill_subtype_city_transport", ""),
    ]
    return wait_markers_in_context(context, page, marker_selectors, timeout)


def first_visible_locator(
    context: LocatorContext,
    selector: str,
    timeout_ms: int,
    wait_visible: Callable[[Any, int], bool],
) -> Any | None:
    if not selector:
        return None
    try:
        locator = context.locator(selector)
        count = locator.count()
        for idx in range(count):
            candidate = locator.nth(idx)
            if wait_visible(candidate, timeout_ms):
                return candidate
    except Exception:
        return None
    return None


def diagnose_new_bill_menu(page: Any, context: LocatorContext, selectors: dict[str, str]) -> None:
    del page
    info = {}
    for key, selector in {
        "menu_visible": "li.prosahover",
        "submenu_visible": "div.prosmore:not(.hide)",
        "expense_link": selectors.get("bill_type_expense", ""),
        "business_entertainment_link": selectors.get("bill_subtype_business_entertainment", ""),
        "city_transport_link": selectors.get("bill_subtype_city_transport", ""),
        "xselector_combo": "#XSelectorLX + span.combo",
    }.items():
        if not selector:
            continue
        try:
            info[key] = context.locator(selector).count()
        except Exception:
            info[key] = "error"
    if not (info.get("expense_link") or info.get("business_entertainment_link") or info.get("city_transport_link")):
        raise RuntimeError(f"新建单据菜单诊断结果: {info}")


def click_bill_subtype_link(
    page: Any,
    context: LocatorContext,
    selectors: dict[str, str],
    bill_subtype: str,
    timeout: int,
    bill_subtype_candidates: Callable[[dict[str, str], str], list[str]],
    first_visible_locator: Callable[[LocatorContext, str, int], Any | None],
) -> None:
    candidates = bill_subtype_candidates(selectors, bill_subtype)
    last_error: Exception | None = None
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        for selector in candidates:
            if not selector:
                continue
            locator = first_visible_locator(context, selector, 250)
            if locator is None:
                continue
            try:
                locator.scroll_into_view_if_needed(timeout=300)
            except Exception:
                pass
            try:
                locator.click(timeout=300)
                return
            except Exception as exc:
                last_error = exc
            try:
                locator.click(timeout=300, force=True)
                return
            except Exception as exc:
                last_error = exc
            page.wait_for_timeout(60)
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"未找到可点击的‘{bill_subtype}’入口")


def follow_new_page_after_bill_click(page: Any, timeout: int) -> Any:
    end_at = perf_counter() + (min(timeout, 600) / 1000)
    known_pages = list(page.context.pages)
    while perf_counter() < end_at:
        current_pages = list(page.context.pages)
        for candidate in reversed(current_pages):
            if candidate.is_closed():
                continue
            if candidate not in known_pages:
                try:
                    candidate.wait_for_load_state("domcontentloaded", timeout=300)
                except Exception:
                    pass
                return candidate
        page.wait_for_timeout(50)
    return page


__all__ = [
    "click_bill_subtype_link",
    "diagnose_new_bill_menu",
    "first_visible_locator",
    "follow_new_page_after_bill_click",
    "is_new_bill_menu_open",
    "open_new_bill_menu",
]
