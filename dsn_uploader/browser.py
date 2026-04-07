from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import Browser, Error, Page, Playwright, sync_playwright


@contextmanager
def open_browser(headed: bool, browser_channel: str | None = None, executable_path: str | None = None) -> Iterator[tuple[Playwright, Browser, Page]]:
    with sync_playwright() as playwright:
        browser = _launch_browser(
            playwright,
            headed=headed,
            browser_channel=browser_channel,
            executable_path=executable_path,
        )
        context_options = {"no_viewport": True} if headed else {}
        context = browser.new_context(**context_options)
        page = context.new_page()
        try:
            yield playwright, browser, page
        finally:
            context.close()
            browser.close()


def _launch_browser(
    playwright: Playwright,
    headed: bool,
    browser_channel: str | None = None,
    executable_path: str | None = None,
) -> Browser:
    launch_options = {"headless": not headed}
    if headed:
        launch_options["args"] = ["--start-maximized"]
    if executable_path:
        try:
            return playwright.chromium.launch(executable_path=executable_path, **launch_options)
        except Error:
            pass
    if browser_channel:
        try:
            return playwright.chromium.launch(channel=browser_channel, **launch_options)
        except Error:
            pass
    for channel in ("msedge", "chrome"):
        try:
            return playwright.chromium.launch(channel=channel, **launch_options)
        except Error:
            continue
    return playwright.chromium.launch(**launch_options)
