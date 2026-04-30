from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

from automation.core.ui_patterns import wait_for_condition


LocatorContext = Any


def ensure_my_reimbursement_page(
    page: Any,
    selectors: dict[str, str],
    timeout: int,
    is_my_reimbursement_page: Callable[[Any, dict[str, str], int], bool],
) -> None:
    if not is_my_reimbursement_page(page, selectors, timeout):
        raise RuntimeError("未成功进入‘我要报账’页面，未检测到页面到达标志")


def ensure_target_reimbursement_bill_page(
    page: Any,
    selectors: dict[str, str],
    bill_subtype: str,
    timeout: int,
    is_target_reimbursement_bill_page: Callable[[Any, dict[str, str], str, int], bool],
) -> None:
    if not is_target_reimbursement_bill_page(page, selectors, bill_subtype, timeout):
        raise RuntimeError(f"未成功进入‘{bill_subtype}’单据页，未检测到页面到达标志")


def is_my_reimbursement_page(
    page: Any,
    selectors: dict[str, str],
    timeout: int,
    resolve_reimbursement_context: Callable[[Any, dict[str, str]], LocatorContext],
    wait_markers_in_context: Callable[[LocatorContext, Any, list[str], int], bool],
) -> bool:
    context = resolve_reimbursement_context(page, selectors)
    marker_selectors = [
        selectors.get("new_bill_button", ""),
        'h2:has-text("新建单据")',
        'text=费用报销类',
        'text=业务招待费报销',
        'text=市内交通费报销',
        'text=草稿箱',
    ]
    return wait_markers_in_context(context, page, marker_selectors, timeout)


def is_target_reimbursement_bill_page(
    page: Any,
    selectors: dict[str, str],
    bill_subtype: str,
    timeout: int,
    has_selected_bill_tab_title: Callable[[Any, str, int], bool],
    resolve_bill_form_context: Callable[[Any, dict[str, str]], LocatorContext],
    resolve_reimbursement_context: Callable[[Any, dict[str, str]], LocatorContext],
    bill_page_markers: Callable[[dict[str, str], str], list[str]],
    wait_markers_in_context: Callable[[LocatorContext, Any, list[str], int], bool],
) -> bool:
    if has_selected_bill_tab_title(page, bill_subtype, min(timeout, 120)):
        return True
    bill_context = resolve_bill_form_context(page, selectors)
    reimbursement_context = resolve_reimbursement_context(page, selectors)
    try:
        if bill_context is reimbursement_context:
            return False
    except Exception:
        pass
    return wait_markers_in_context(bill_context, page, bill_page_markers(selectors, bill_subtype), timeout)


def is_target_reimbursement_bill_page_precheck(
    page: Any,
    selectors: dict[str, str],
    bill_subtype: str,
    has_selected_bill_tab_title: Callable[[Any, str, int], bool],
    get_cached_bill_form_context: Callable[[Any], LocatorContext | None],
    bill_page_markers: Callable[[dict[str, str], str], list[str]],
    wait_markers_in_context: Callable[[LocatorContext, Any, list[str], int], bool],
) -> bool:
    if has_selected_bill_tab_title(page, bill_subtype, 120):
        return True
    bill_context = get_cached_bill_form_context(page)
    if bill_context is None:
        return False
    return wait_markers_in_context(bill_context, page, bill_page_markers(selectors, bill_subtype), 120)


def has_selected_bill_tab_title(page: Any, bill_subtype: str, timeout: int, wait_visible: Callable[[Any, int], bool]) -> bool:
    title_selector = f'li.tabs-selected .tabs-title:has-text("{bill_subtype}")'
    try:
        return wait_visible(page.locator(title_selector).first, timeout)
    except Exception:
        return False


def has_selected_bill_tab_title_fast(page: Any, bill_subtype: str) -> bool:
    title_selector = f'li.tabs-selected .tabs-title:has-text("{bill_subtype}")'
    try:
        return page.locator(title_selector).count() > 0
    except Exception:
        return False


def is_fast_clean_reimbursement_state(
    page: Any,
    selectors: dict[str, str],
    resolve_image_system_context: Callable[[Any], LocatorContext | None],
    has_selected_bill_tab_title_fast: Callable[[Any, str], bool],
    get_cached_reimbursement_context: Callable[[Any], LocatorContext | None],
    resolve_reimbursement_context: Callable[[Any, dict[str, str]], LocatorContext],
) -> bool:
    try:
        if page.is_closed():
            return False
    except Exception:
        return False
    try:
        if resolve_image_system_context(page) is not None:
            return False
    except Exception:
        return False
    if has_selected_bill_tab_title_fast(page, "业务招待费报销") or has_selected_bill_tab_title_fast(page, "市内交通费报销"):
        return False
    quick_markers = [
        selectors.get("new_bill_button", ""),
        'h2:has-text("新建单据")',
        'text=费用报销类',
        'text=草稿箱',
    ]
    context = get_cached_reimbursement_context(page)
    if context is None:
        context = resolve_reimbursement_context(page, selectors)
    if context is None:
        return False
    for selector in quick_markers:
        if not selector:
            continue
        try:
            if context.locator(selector).count() > 0:
                return True
        except Exception:
            continue
    return False


def wait_for_selected_bill_tab_title(
    page: Any,
    bill_subtype: str,
    timeout: int,
    has_selected_bill_tab_title: Callable[[Any, str, int], bool],
) -> bool:
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        if has_selected_bill_tab_title(page, bill_subtype, 80):
            return True
        page.wait_for_timeout(30)
    return False


def ensure_electronic_image_page(
    page: Any,
    selectors: dict[str, str],
    timeout: int,
    is_electronic_image_page_precheck: Callable[[Any, dict[str, str], int], bool],
) -> None:
    if is_electronic_image_page_precheck(page, selectors, timeout):
        return
    raise RuntimeError("未成功进入电子影像页面")


def ensure_reimbursement_saved(
    page: Any,
    selectors: dict[str, str],
    timeout: int,
    is_reimbursement_saved: Callable[[Any, dict[str, str], int], bool],
) -> None:
    if is_reimbursement_saved(page, selectors, timeout):
        return
    raise RuntimeError("未检测到报销单保存完成标志")


def is_electronic_image_page(
    page: Any,
    selectors: dict[str, str],
    timeout: int,
    resolve_image_system_context: Callable[[Any], LocatorContext | None],
    candidate_bill_contexts: Callable[[Any, dict[str, str]], list[LocatorContext]],
    wait_visible: Callable[[Any, int], bool],
) -> bool:
    if resolve_image_system_context(page) is not None:
        return True
    markers = [
        selectors.get("local_upload_button", ""),
        selectors.get("recognize_button", ""),
        'text=本地上传',
        'text=识别',
        'text=电子影像',
    ]
    per_try_timeout = min(timeout, 120)
    rounds = max(1, int(max(timeout, 180) / per_try_timeout))
    contexts = candidate_bill_contexts(page, selectors)
    for _ in range(rounds):
        for context in contexts:
            for selector in markers:
                if not selector:
                    continue
                try:
                    if wait_visible(context.locator(selector).first, per_try_timeout):
                        return True
                except Exception:
                    continue
        page.wait_for_timeout(25)
    return False


def is_electronic_image_page_precheck(
    page: Any,
    selectors: dict[str, str],
    timeout: int,
    get_cached_electronic_image_context: Callable[[Any], LocatorContext | None],
    get_cached_bill_form_context: Callable[[Any], LocatorContext | None],
    get_cached_reimbursement_context: Callable[[Any], LocatorContext | None],
    wait_visible: Callable[[Any, int], bool],
) -> bool:
    marker_selectors = [
        selectors.get("local_upload_button", ""),
        selectors.get("recognize_button", ""),
        'text=本地上传',
        'text=识别',
        'text=电子影像',
    ]
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx: LocatorContext | None) -> None:
        if ctx is None:
            return
        marker = id(ctx)
        if marker in seen:
            return
        seen.add(marker)
        contexts.append(ctx)

    add(get_cached_electronic_image_context(page))
    add(get_cached_bill_form_context(page))
    add(get_cached_reimbursement_context(page))
    add(page)

    per_try_timeout = min(timeout, 80)
    rounds = max(1, int(max(timeout, 80) / max(per_try_timeout, 1)))
    for _ in range(rounds):
        for context in contexts:
            for selector in marker_selectors:
                if not selector:
                    continue
                try:
                    if wait_visible(context.locator(selector).first, per_try_timeout):
                        return True
                except Exception:
                    continue
        page.wait_for_timeout(20)
    return False


def is_reimbursement_saved(
    page: Any,
    selectors: dict[str, str],
    timeout: int,
    candidate_bill_contexts: Callable[[Any, dict[str, str]], list[LocatorContext]],
    wait_markers_in_context: Callable[[LocatorContext, Any, list[str], int], bool],
    wait_any_marker: Callable[[Any, list[str], int], bool],
) -> bool:
    marker_selectors = [
        selectors.get("save_success_toast", ""),
        'text=保存成功',
    ]
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        for context in candidate_bill_contexts(page, selectors):
            if wait_markers_in_context(context, page, marker_selectors, 180):
                return True
        if wait_any_marker(page, marker_selectors, 180):
            return True
        page.wait_for_timeout(50)
    return False


def ensure_upload_dialog_open(
    page: Any,
    selectors: dict[str, str],
    timeout: int,
    is_upload_dialog_open: Callable[[Any, dict[str, str], int], bool],
    diagnose_upload_dialog: Callable[[Any, dict[str, str]], str],
) -> None:
    if is_upload_dialog_open(page, selectors, timeout):
        return
    raise RuntimeError(diagnose_upload_dialog(page, selectors))


def is_upload_dialog_open(
    page: Any,
    selectors: dict[str, str],
    timeout: int,
    resolve_electronic_image_context: Callable[[Any, dict[str, str]], LocatorContext],
    resolve_upload_dialog_context: Callable[[Any, dict[str, str]], LocatorContext | None],
    count_visible_elements: Callable[[LocatorContext, str], int],
) -> bool:
    del timeout
    dialog_host_context = resolve_electronic_image_context(page, selectors)
    dialog_selector = selectors.get("upload_dialog", "")
    if dialog_selector:
        try:
            if count_visible_elements(dialog_host_context, dialog_selector) > 0:
                return True
        except Exception:
            pass
    iframe_selector = selectors.get("upload_dialog_iframe", 'iframe[id^="layui-layer-iframe"]')
    try:
        if count_visible_elements(dialog_host_context, iframe_selector) > 0:
            return True
    except Exception:
        pass
    return resolve_upload_dialog_context(page, selectors) is not None


def ensure_reimbursement_bill_tab_closed(
    page: Any,
    selectors: dict[str, str],
    timeout: int,
    is_my_reimbursement_page: Callable[[Any, dict[str, str], int], bool],
) -> None:
    closed = wait_for_condition(
        page,
        lambda: (
            not page.locator("li.tabs-selected").filter(has_text="业务招待费报销").count()
            and not page.locator("li.tabs-selected").filter(has_text="市内交通费报销").count()
            and is_my_reimbursement_page(page, selectors, 120)
        ),
        timeout,
        40,
    )
    if not closed:
        raise RuntimeError("关闭报销单页签后未返回我要报账列表")


__all__ = [
    "ensure_electronic_image_page",
    "ensure_my_reimbursement_page",
    "ensure_reimbursement_bill_tab_closed",
    "ensure_reimbursement_saved",
    "ensure_target_reimbursement_bill_page",
    "ensure_upload_dialog_open",
    "has_selected_bill_tab_title",
    "has_selected_bill_tab_title_fast",
    "is_electronic_image_page",
    "is_electronic_image_page_precheck",
    "is_fast_clean_reimbursement_state",
    "is_my_reimbursement_page",
    "is_reimbursement_saved",
    "is_target_reimbursement_bill_page",
    "is_target_reimbursement_bill_page_precheck",
    "is_upload_dialog_open",
    "wait_for_selected_bill_tab_title",
]
