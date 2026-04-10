from __future__ import annotations

from playwright.sync_api import Page

from automation.core.waits import wait_visible


def wait_upload_page(page: Page, timeout: int) -> None:
    try:
        page.wait_for_url("**/hr/employee/archive/uploadArchive**", timeout=timeout)
    except Exception:
        pass

    try:
        wait_visible(page, "text=上传方式", timeout)
        wait_visible(page, "text=选择人员", timeout)
        return
    except Exception:
        pass

    raise RuntimeError("未成功进入上传页，当前页面仍不是上传表单")


def is_upload_page(page: Page) -> bool:
    try:
        if "/hr/employee/archive/uploadArchive" in page.url:
            return True
    except Exception:
        pass
    try:
        return (
            page.get_by_text("上传方式", exact=False).count() > 0
            and page.get_by_text("选择人员", exact=False).count() > 0
        )
    except Exception:
        return False


def wait_archive_list_ready(page: Page, timeout: int) -> None:
    interval_ms = 300
    elapsed_ms = 0
    success_toast = page.get_by_text("操作成功", exact=False)
    loading_indicators = [
        page.locator(".ant-spin-spinning"),
        page.locator(".ant-spin-dot"),
        page.get_by_text("加载中", exact=False),
    ]

    while elapsed_ms <= timeout:
        try:
            if success_toast.count() > 0 and success_toast.first.is_visible():
                page.wait_for_timeout(300)
        except Exception:
            pass

        loading = False
        for indicator in loading_indicators:
            try:
                if indicator.count() > 0 and indicator.first.is_visible():
                    loading = True
                    break
            except Exception:
                continue

        if not loading:
            return

        page.wait_for_timeout(interval_ms)
        elapsed_ms += interval_ms


def is_archive_list_page(page: Page) -> bool:
    try:
        if "/hr/employee/archive" not in page.url:
            return False
        if "/hr/employee/archive/uploadArchive" in page.url:
            return False
    except Exception:
        return False

    try:
        return (
            page.get_by_text("档案管理", exact=False).count() > 0
            or page.get_by_text("上传档案附件", exact=False).count() > 0
        )
    except Exception:
        return False
