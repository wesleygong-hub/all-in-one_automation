from __future__ import annotations

from typing import Any, Callable

from automation.core.contexts import (
    cache_active_working_page as cache_active_working_page_value,
    cache_page_context,
    get_cached_active_working_page as get_cached_active_working_page_value,
    get_cached_page_context_matching,
    page_candidates as core_page_candidates,
)
from automation.core.contexts import context_debug_name as core_context_debug_name


LocatorContext = Any


def cache_bill_outer_context(page: Any, context: LocatorContext | None) -> None:
    cache_page_context(page, "_bill_outer_context", context)


def get_cached_bill_outer_context(page: Any, wait_visible: Callable[[Any, int], bool]) -> LocatorContext | None:
    return get_cached_page_context_matching(
        page,
        "_bill_outer_context",
        [
            "text=电子影像",
            "text=保存",
            "text=报销明细信息",
            "text=费用分摊",
            "text=关闭",
        ],
        wait_visible,
        40,
    )


def cache_reimbursement_context(page: Any, context: LocatorContext | None) -> None:
    cache_page_context(page, "_reimbursement_context", context)


def get_cached_reimbursement_context(page: Any, wait_visible: Callable[[Any, int], bool]) -> LocatorContext | None:
    return get_cached_page_context_matching(
        page,
        "_reimbursement_context",
        [
            'h2:has-text("新建单据")',
            "text=草稿箱",
            "text=业务招待费报销",
            "text=市内交通费报销",
        ],
        wait_visible,
        50,
    )


def cache_bill_form_context(page: Any, context: LocatorContext | None) -> None:
    cache_page_context(page, "_bill_form_context", context)


def get_cached_bill_form_context(page: Any, wait_visible: Callable[[Any, int], bool]) -> LocatorContext | None:
    context = get_cached_page_context_matching(
        page,
        "_bill_form_context",
        [
            "text=电子影像",
            "text=报销明细信息",
            "text=费用分摊",
            "text=保存",
            "text=业务招待费报销",
            "text=市内交通费报销",
        ],
        wait_visible,
        50,
    )
    if context is not None and hasattr(context, "main_frame"):
        return None
    return context


def cache_electronic_image_context(page: Any, context: LocatorContext | None) -> None:
    cache_page_context(page, "_reimbursement_electronic_image_context", context)


def get_cached_electronic_image_context(page: Any, wait_visible: Callable[[Any, int], bool]) -> LocatorContext | None:
    return get_cached_page_context_matching(
        page,
        "_reimbursement_electronic_image_context",
        [
            "text=本地上传",
            "#btnInOCR",
            ".sortwrap .thumb",
        ],
        wait_visible,
        60,
    )


def cache_active_working_page(page: Any, working_page: Any | None) -> None:
    cache_active_working_page_value(page, working_page, "_active_reimbursement_working_page")


def get_cached_active_working_page(page: Any) -> Any | None:
    return get_cached_active_working_page_value(page, "_active_reimbursement_working_page")


def page_candidates(page: Any) -> list[Any]:
    return core_page_candidates(page)


def context_debug_name(context: LocatorContext, index: int) -> str:
    return core_context_debug_name(context, index)


__all__ = [
    "cache_active_working_page",
    "cache_bill_form_context",
    "cache_bill_outer_context",
    "cache_electronic_image_context",
    "cache_reimbursement_context",
    "context_debug_name",
    "get_cached_active_working_page",
    "get_cached_bill_form_context",
    "get_cached_bill_outer_context",
    "get_cached_electronic_image_context",
    "get_cached_reimbursement_context",
    "page_candidates",
]
