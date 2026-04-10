from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import FileChooser, Locator, Page

from automation.core.selectors import locator, locator_with_scope, modal_scope
from automation.core.state import is_upload_page


def fill_locator(page: Page, selector: str, value: str, timeout: int) -> None:
    target = locator(page, selector)
    target.first.wait_for(timeout=timeout)
    target.first.fill(value, timeout=timeout)


def click_locator(page: Page, selector: str, timeout: int, within_modal: bool = False) -> None:
    target = locator(page, selector)
    if within_modal:
        target = locator_with_scope(modal_scope(page), selector)
    target.first.wait_for(timeout=timeout)
    target.first.click(timeout=timeout)


def dismiss_overlays(page: Page) -> None:
    esc_presses = 0
    while esc_presses < 3:
        try:
            page.keyboard.press("Escape")
        except Exception:
            break
        page.wait_for_timeout(100)
        esc_presses += 1

    closers = [
        page.locator(".ant-modal-close"),
        page.locator(".ant-drawer-close"),
        page.locator(".ant-select-dropdown .ant-select-item-option-active"),
    ]
    for current in closers:
        try:
            if current.count() > 0 and current.first.is_visible():
                current.first.click(timeout=500)
        except Exception:
            continue


def wait_confirm_submit_modal(page: Page, selectors: dict[str, str], timeout: int) -> None:
    modal = modal_scope(page)
    candidates = [
        selectors.get("confirm_modal_content", "text=是否确定上传文件？"),
        selectors.get("confirm_modal_title", "text=提示"),
        selectors.get("confirm_ok_button", "button.ant-btn-primary"),
        "button.ant-btn-primary",
    ]
    deadline_ms = min(timeout, 4000)
    interval_ms = 200
    elapsed_ms = 0

    while elapsed_ms <= deadline_ms:
        for selector in candidates:
            try:
                current = locator_with_scope(modal, selector).first
                if current.count() > 0 and current.is_visible():
                    return
            except Exception:
                continue
        page.wait_for_timeout(interval_ms)
        elapsed_ms += interval_ms
    raise RuntimeError("确认上传弹窗未出现")


def click_confirm_submit(page: Page, selectors: dict[str, str], timeout: int) -> None:
    modal = modal_scope(page)
    candidates = [
        selectors.get("confirm_ok_button", "button.ant-btn-primary"),
        "button.ant-btn-primary",
        'button:has-text("确定")',
        "text=确定",
    ]
    last_error: Exception | None = None
    for selector in candidates:
        try:
            locator_with_scope(modal, selector).first.click(timeout=min(timeout, 1500))
            return
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("未找到确认上传的确定按钮")


def upload_file(page: Page, upload_selector: str, file_path: str, timeout: int) -> None:
    file_name = Path(file_path).name
    errors: list[str] = []

    try:
        current = locator(page, upload_selector)
        current.first.set_input_files(file_path, timeout=timeout)
        page.wait_for_timeout(800)
        wait_uploaded_file_visible(page, file_name, timeout)
        return
    except Exception as exc:
        errors.append(f"hidden-input upload failed: {exc}")

    try:
        with page.expect_file_chooser(timeout=timeout) as chooser_info:
            click_visible_upload_file_button(page, timeout)
        chooser: FileChooser = chooser_info.value
        chooser.set_files(file_path, timeout=timeout)
        page.wait_for_timeout(800)
        wait_uploaded_file_visible(page, file_name, timeout)
        return
    except Exception as exc:
        errors.append(f"visible-button upload failed: {exc}")

    raise RuntimeError("文件上传未成功: " + " | ".join(errors))


def click_visible_upload_file_button(page: Page, timeout: int) -> None:
    candidates = [
        page.locator("button.ant-btn.cdc-app.ant-btn-default.ant-btn-color-default.ant-btn-variant-outlined").filter(
            has_text=re.compile("^上传文件$")
        ),
        page.locator("button.ant-btn.cdc-app").filter(has_text=re.compile("^上传文件$")),
        page.get_by_role("button", name="上传文件"),
        page.locator("button").filter(has_text=re.compile("上传文件")),
        page.get_by_text("上传文件", exact=False),
    ]
    for current in candidates:
        try:
            if current.count() > 0:
                current.first.click(timeout=timeout)
                return
        except Exception:
            continue
    raise RuntimeError("未找到可见的“上传文件”按钮")


def wait_uploaded_file_visible(page: Page, file_name: str, timeout: int) -> None:
    candidates = [
        page.get_by_text(file_name, exact=False),
        page.locator(f"text={file_name}"),
    ]
    for current in candidates:
        try:
            current.first.wait_for(timeout=timeout)
            return
        except Exception:
            continue
    raise RuntimeError(f"页面未显示已上传文件名: {file_name}")


def click_submit(page: Page, submit_selector: str, timeout: int) -> None:
    attempts = [
        lambda: click_locator(page, submit_selector, timeout),
        lambda: page.get_by_role("button", name="提交").first.click(timeout=2500),
        lambda: page.get_by_text("提交", exact=False).first.click(timeout=2500),
    ]
    last_error: Exception | None = None
    for action in attempts:
        try:
            action()
            return
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("未找到提交按钮")


def click_visible_upload_entry(page: Page, timeout: int) -> None:
    candidates = [
        page.get_by_role("button", name="上传档案附件"),
        page.locator("button").filter(has_text=re.compile("上传档案附件")),
        page.get_by_text("上传档案附件", exact=False),
    ]
    for current in candidates:
        try:
            if current.count() > 0:
                current.first.click(timeout=timeout)
                return
        except Exception:
            continue
    raise RuntimeError("当前页面未找到可点击的“上传档案附件”按钮")


def click_person_search(page: Page, timeout: int) -> None:
    modal = modal_scope(page)
    candidates = [
        modal.locator(".ant-input-search-button"),
        modal.locator("button.ant-input-search-button"),
        modal.locator("span[role='img'][aria-label='search']"),
        modal.locator("xpath=//input[@placeholder='搜索人员']/following-sibling::*[1]"),
    ]
    for current in candidates:
        try:
            if current.count() > 0:
                current.first.click(timeout=timeout)
                return
        except Exception:
            continue
    raise RuntimeError("未找到人员搜索按钮（放大镜）")


def wait_person_search_results(page: Page, timeout: int) -> None:
    modal = modal_scope(page)
    spinner_candidates = [
        modal.locator(".ant-spin-spinning"),
        modal.locator(".ant-spin-dot"),
    ]

    page.wait_for_timeout(800)
    for spinner in spinner_candidates:
        try:
            if spinner.count() > 0:
                spinner.first.wait_for(state="hidden", timeout=timeout)
        except Exception:
            continue

    page.wait_for_timeout(800)


def select_person_radio(modal: Locator, timeout: int) -> None:
    candidates = [
        modal.locator(".ant-radio-wrapper"),
        modal.locator("label.ant-radio-wrapper"),
        modal.locator("input.ant-radio-input"),
    ]
    for current in candidates:
        try:
            if current.count() > 0:
                current.first.click(timeout=timeout)
                return
        except Exception:
            continue
    raise RuntimeError("未找到员工记录单选按钮")


def wait_person_modal(page: Page, selectors: dict[str, str], timeout: int) -> None:
    candidates = [
        selectors.get("person_modal_title", "text=选择员工"),
        selectors.get("person_query_input", "input[placeholder='搜索人员']"),
        "input[placeholder='搜索人员']",
    ]
    for selector in candidates:
        try:
            locator(page, selector).first.wait_for(timeout=timeout)
            return
        except Exception:
            continue
    raise RuntimeError("人员选择弹窗未出现")


def open_person_selector(page: Page, selectors: dict[str, str], timeout: int) -> None:
    if not is_upload_page(page):
        raise RuntimeError("当前页面不在上传表单，无法打开人员弹窗")

    try:
        click_locator(page, selectors["person_select_button"], min(timeout, 3000))
        wait_person_modal(page, selectors, min(timeout, 4000))
        return
    except Exception:
        pass

    try:
        click_locator(page, ".cdc-employee-picker_box-entry", min(timeout, 3000))
        wait_person_modal(page, selectors, min(timeout, 4000))
        return
    except Exception:
        pass

    input_locator = person_input_locator(page)
    input_locator.wait_for(timeout=timeout)
    box = input_locator.bounding_box(timeout=timeout)
    if not box:
        raise RuntimeError("无法获取选择人员输入框位置")

    field_x = box["x"] + min(box["width"] * 0.35, 120)
    icon_x = box["x"] + box["width"] - 18
    y = box["y"] + box["height"] / 2

    page.mouse.click(field_x, y)
    page.wait_for_timeout(120)
    _trigger_person_picker(page, icon_x, y)
    wait_person_modal(page, selectors, min(timeout, 4000))


def person_input_locator(page: Page) -> Locator:
    candidates = [
        page.locator("xpath=//*[contains(normalize-space(.), '选择人员')]/following::input[1]"),
        page.locator("input").first,
    ]
    for current in candidates:
        try:
            if current.count() > 0:
                return current.first
        except Exception:
            continue
    raise RuntimeError("未找到选择人员输入框")


def select_option(page: Page, field_selector: str, value: str, timeout: int) -> None:
    field = locator(page, field_selector)
    field.first.click(timeout=timeout)
    page.wait_for_timeout(300)

    option_candidates = (
        page.locator(f".ant-select-item.ant-select-item-option[title='{value}']"),
        page.locator(f".ant-select-item-option[title='{value}'] .ant-select-item-option-content"),
        page.locator(".ant-select-dropdown").get_by_text(value, exact=True),
        page.locator(".ant-select-item-option-content").get_by_text(value, exact=True),
        page.get_by_role("option", name=value),
        page.get_by_text(value, exact=True),
        page.locator(f"text={value}"),
    )
    for candidate in option_candidates:
        try:
            if candidate.count() > 0:
                candidate.first.click(timeout=timeout)
                page.wait_for_timeout(300)
                return
        except Exception:
            continue
    raise RuntimeError(f"页面中找不到选项值: {value}")


def _trigger_person_picker(page: Page, icon_x: float, y: float) -> None:
    offsets = [0, -4, 4]
    for offset in offsets:
        page.mouse.click(icon_x + offset, y)
        page.wait_for_timeout(120)
        page.mouse.dblclick(icon_x + offset, y)
        page.wait_for_timeout(180)
