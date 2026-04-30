from __future__ import annotations

from typing import Any, Callable

from playwright.sync_api import Page


def select_cleanup_working_page(page: Page, working_page: Page, actions: list[str]) -> Page:
    try:
        if not working_page.is_closed():
            return working_page
        actions.append("working_page_closed")
    except Exception:
        actions.append("working_page_closed")
    try:
        if not page.is_closed():
            actions.append("cleanup_fallback=page")
            return page
    except Exception:
        pass
    try:
        for candidate in page.context.pages:
            try:
                if not candidate.is_closed():
                    actions.append("cleanup_fallback=context_page")
                    return candidate
            except Exception:
                continue
    except Exception:
        pass
    return working_page


def diagnose_cleanup_state(
    page: Page,
    working_page: Page,
    selectors: dict[str, str],
    is_electronic_image_page: Callable[[Page, dict[str, str], int], bool],
    has_selected_bill_tab_title: Callable[[Page, str, int], bool],
    is_my_reimbursement_page: Callable[[Page, dict[str, str], int], bool],
) -> str:
    parts: list[str] = []
    try:
        parts.append(f"working_closed={working_page.is_closed()}")
    except Exception as exc:
        parts.append(f"working_closed=error:{type(exc).__name__}")
    try:
        parts.append(f"working_url={getattr(working_page, 'url', '')}")
    except Exception as exc:
        parts.append(f"working_url=error:{type(exc).__name__}")
    try:
        parts.append(f"is_electronic_image={is_electronic_image_page(working_page, selectors, 80)}")
    except Exception as exc:
        parts.append(f"is_electronic_image=error:{type(exc).__name__}")
    try:
        parts.append(f"selected_business_tab={has_selected_bill_tab_title(working_page, '业务招待费报销', 60)}")
    except Exception as exc:
        parts.append(f"selected_business_tab=error:{type(exc).__name__}")
    try:
        parts.append(f"selected_transport_tab={has_selected_bill_tab_title(working_page, '市内交通费报销', 60)}")
    except Exception as exc:
        parts.append(f"selected_transport_tab=error:{type(exc).__name__}")
    try:
        parts.append(f"is_my_reimbursement={is_my_reimbursement_page(working_page, selectors, 120)}")
    except Exception as exc:
        parts.append(f"is_my_reimbursement=error:{type(exc).__name__}")
    return " ".join(parts)


__all__ = ["diagnose_cleanup_state", "select_cleanup_working_page"]
