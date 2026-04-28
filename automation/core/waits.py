from __future__ import annotations

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from automation.core.selectors import locator


def wait_visible(page: Page, selector: str, timeout: int) -> None:
    locator(page, selector).first.wait_for(timeout=timeout)


def wait_visible_bool(target, timeout_ms: int) -> bool:
    try:
        target.wait_for(state="visible", timeout=timeout_ms)
        return True
    except PlaywrightTimeoutError:
        return False


def ensure_visible(target, timeout_ms: int, error_message: str) -> None:
    if not wait_visible_bool(target, timeout_ms):
        raise RuntimeError(error_message)


def count_visible_elements(context, selector: str) -> int:
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


def locator_has_non_empty_value(target) -> bool:
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
