from __future__ import annotations

from playwright.sync_api import Locator, Page


def locator(page: Page, selector: str) -> Locator:
    return locator_with_scope(page, selector)


def locator_with_scope(scope: Page | Locator, selector: str) -> Locator:
    if selector.startswith("label="):
        return scope.get_by_label(selector.split("=", 1)[1], exact=False)
    if selector.startswith("text="):
        return scope.get_by_text(selector.split("=", 1)[1], exact=False)
    if selector.startswith('button:has-text("') and selector.endswith('")'):
        button_text = selector[len('button:has-text("') : -2]
        button = scope.get_by_role("button", name=button_text)
        if button.count() > 0:
            return button
        return scope.get_by_text(button_text, exact=False)
    return scope.locator(selector)


def modal_scope(page: Page) -> Locator:
    modal = page.locator(".ant-modal,.ant-modal-root").last
    if modal.count() == 0:
        return page.locator("body")
    return modal
