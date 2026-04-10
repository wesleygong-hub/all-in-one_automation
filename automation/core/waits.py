from __future__ import annotations

from playwright.sync_api import Page

from automation.core.selectors import locator


def wait_visible(page: Page, selector: str, timeout: int) -> None:
    locator(page, selector).first.wait_for(timeout=timeout)


def wait_url_contains(page: Page, text: str, timeout: int) -> None:
    page.wait_for_url(f"**{text}**", timeout=timeout)


def wait_after_login(page: Page, timeout: int) -> None:
    try:
        page.wait_for_url("**/hr/employee/archive**", timeout=timeout)
        return
    except Exception:
        pass
    try:
        page.get_by_text("上传档案附件", exact=False).first.wait_for(timeout=timeout)
        return
    except Exception:
        pass
    try:
        page.get_by_text("档案管理", exact=False).first.wait_for(timeout=timeout)
        return
    except Exception:
        pass
    raise RuntimeError("登录后未进入业务首页，页面仍停留在登录态")
