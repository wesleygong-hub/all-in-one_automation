from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import FileChooser, Locator, Page, TimeoutError as PlaywrightTimeoutError

from dsn_uploader.db import insert_operation_log
from dsn_uploader.models import TaskRecord, TaskResult


StepLogger = Callable[[str, str, str], None]


STEP_NAMES = (
    "open_login",
    "login",
    "open_upload_entry",
    "open_person_selector",
    "search_person",
    "confirm_person",
    "select_business_line",
    "select_business_type",
    "upload_file",
    "submit_form",
    "confirm_submit",
    "verify_result",
)


def run_task(
    page: Page,
    config: dict[str, Any],
    task: TaskRecord,
    logger: logging.Logger,
    step_log: StepLogger,
) -> TaskResult:
    selectors = config["selectors"]
    timeout = config["system"]["timeout_ms"]
    mapping = config.get("mapping", {})

    try:
        _step(logger, step_log, task, "open_upload_entry", "START", "进入上传页")
        _open_upload_page(page, selectors, config["system"]["base_url"], timeout)
        _step(logger, step_log, task, "open_upload_entry", "SUCCESS", "已进入上传页")

        _step(logger, step_log, task, "open_person_selector", "START", "打开人员选择弹窗")
        _open_person_selector(page, selectors, timeout)
        _step(logger, step_log, task, "open_person_selector", "SUCCESS", "人员弹窗已打开")

        _step(logger, step_log, task, "search_person", "START", "搜索并选择人员")
        _select_person(page, selectors, task, timeout)
        _step(logger, step_log, task, "search_person", "SUCCESS", f"已选人员 {task.employee_id}/{task.employee_name}")

        _step(logger, step_log, task, "confirm_person", "START", "确认人员")
        _click_locator(page, selectors["person_confirm_button"], timeout, within_modal=True)
        _step(logger, step_log, task, "confirm_person", "SUCCESS", "人员已确认")

        _step(logger, step_log, task, "select_business_line", "START", f"选择所属业务 {task.business_line}")
        _select_option(page, selectors["business_line_select"], _map_value(mapping, "business_line", task.business_line), timeout)
        _step(logger, step_log, task, "select_business_line", "SUCCESS", "所属业务已选择")

        _step(logger, step_log, task, "select_business_type", "START", f"选择业务类型 {task.business_type}")
        _select_option(page, selectors["business_type_select"], _map_value(mapping, "business_type", task.business_type), timeout)
        _step(logger, step_log, task, "select_business_type", "SUCCESS", "业务类型已选择")

        _step(logger, step_log, task, "upload_file", "START", f"上传文件 {task.file_name}")
        _upload_file(page, selectors["upload_file_button"], task.file_path, timeout)
        _step(logger, step_log, task, "upload_file", "SUCCESS", "文件已上传")

        _step(logger, step_log, task, "submit_form", "START", "提交表单")
        _click_submit(page, selectors["submit_button"], timeout)
        _step(logger, step_log, task, "submit_form", "SUCCESS", "已点击提交")

        _step(logger, step_log, task, "confirm_submit", "START", "确认提交")
        _wait_confirm_submit_modal(page, selectors, timeout)
        _click_confirm_submit(page, selectors, timeout)
        _step(logger, step_log, task, "confirm_submit", "SUCCESS", "已确认提交")

        _step(logger, step_log, task, "verify_result", "START", "校验列表页第一条记录")
        _verify_first_row(page, selectors, task, timeout)
        _step(logger, step_log, task, "verify_result", "SUCCESS", "首条记录校验通过")

        return TaskResult(status="success", message="上传成功并通过列表校验")
    except Exception as exc:
        return TaskResult(status="failed", message=str(exc))


def initialize_batch_session(
    page: Page,
    config: dict[str, Any],
    logger: logging.Logger,
) -> None:
    selectors = config["selectors"]
    timeout = config["system"]["timeout_ms"]

    logger.info("[BATCH] [open_login] START 打开登录页")
    page.goto(config["system"]["base_url"], wait_until="domcontentloaded")
    logger.info("[BATCH] [open_login] SUCCESS 登录页已打开")

    logger.info("[BATCH] [login] START 执行登录")
    _fill_login(page, selectors, config["auth"], timeout)
    logger.info("[BATCH] [login] SUCCESS 登录完成")


def reset_task_context(
    page: Page,
    config: dict[str, Any],
    logger: logging.Logger,
    task_id: str,
) -> None:
    timeout = min(config["system"]["timeout_ms"], 6000)
    list_url = _archive_list_url(config["system"]["base_url"])

    try:
        _dismiss_overlays(page)
    except Exception:
        pass

    try:
        if _is_archive_list_page(page):
            _wait_archive_list_ready(page, timeout)
            logger.info(f"[TASK {task_id}] context_reset=current_list_page")
            return
    except Exception:
        pass

    try:
        page.goto(list_url, wait_until="domcontentloaded")
        _wait_archive_list_ready(page, timeout)
        logger.info(f"[TASK {task_id}] context_reset={list_url}")
        return
    except Exception:
        pass

    try:
        page.reload(wait_until="domcontentloaded")
        _wait_archive_list_ready(page, timeout)
        logger.info(f"[TASK {task_id}] context_reset=reload")
    except Exception as exc:
        logger.warning(f"[TASK {task_id}] context_reset_warning={exc}")


def capture_screenshot(page: Page, screenshot_dir: str, task: TaskRecord) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(screenshot_dir) / f"{task.task_id}_{timestamp}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def _step(
    logger: logging.Logger,
    step_log: StepLogger,
    task: TaskRecord,
    step_name: str,
    status: str,
    message: str,
) -> None:
    logger.info(f"[TASK {task.task_id}] [{step_name}] {status} {message}")
    step_log(task.task_id, step_name, f"{status} {message}")


def _fill_login(page: Page, selectors: dict[str, str], auth: dict[str, str], timeout: int) -> None:
    _fill_locator(page, selectors["username_input"], auth["username"], timeout)
    _fill_locator(page, selectors["password_input"], auth["password"], timeout)
    _ensure_privacy_agreement(page)
    _submit_login(page, selectors["login_button"], selectors["password_input"], timeout)


def _submit_login(page: Page, login_selector: str, password_selector: str, timeout: int) -> None:
    last_error: Exception | None = None
    attempts = [
        lambda: _locator(page, password_selector).first.press("Enter", timeout=1500),
        lambda: _click_locator(page, login_selector, timeout),
        lambda: page.locator("button[type='submit']").first.click(timeout=2500),
        lambda: page.locator("button").filter(has_text=re.compile("登录")).first.click(timeout=2500),
        lambda: page.get_by_text("登录", exact=False).first.click(timeout=2500),
    ]

    for action in attempts:
        try:
            action()
            _wait_after_login(page, timeout)
            return
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("登录提交失败")


def _select_person(page: Page, selectors: dict[str, str], task: TaskRecord, timeout: int) -> None:
    query_value = task.employee_id or task.employee_name
    _fill_locator(page, selectors["person_query_input"], query_value, timeout)
    _click_person_search(page, timeout)
    _wait_person_search_results(page, timeout)

    modal = _modal_scope(page)
    if task.employee_id and modal.get_by_text(task.employee_id, exact=False).count() == 0:
        raise RuntimeError(f"搜索后未找到目标人员或结果尚未加载完成: {query_value}")
    if task.employee_name and modal.get_by_text(task.employee_name, exact=False).count() == 0:
        raise RuntimeError(f"搜索后未找到目标人员或结果尚未加载完成: {query_value}")

    _select_person_radio(modal, timeout)


def _click_person_search(page: Page, timeout: int) -> None:
    modal = _modal_scope(page)
    candidates = [
        modal.locator(".ant-input-search-button"),
        modal.locator("button.ant-input-search-button"),
        modal.locator("span[role='img'][aria-label='search']"),
        modal.locator("xpath=//input[@placeholder='搜索人员']/following-sibling::*[1]"),
    ]
    for locator in candidates:
        try:
            if locator.count() > 0:
                locator.first.click(timeout=timeout)
                return
        except Exception:
            continue
    raise RuntimeError("未找到人员搜索按钮（放大镜）")


def _click_submit(page: Page, submit_selector: str, timeout: int) -> None:
    attempts = [
        lambda: _click_locator(page, submit_selector, timeout),
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


def _wait_confirm_submit_modal(page: Page, selectors: dict[str, str], timeout: int) -> None:
    modal = _modal_scope(page)
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
                locator = _locator_with_scope(modal, selector).first
                if locator.count() > 0 and locator.is_visible():
                    return
            except Exception:
                continue
        page.wait_for_timeout(interval_ms)
        elapsed_ms += interval_ms
    raise RuntimeError("确认上传弹窗未出现")


def _click_confirm_submit(page: Page, selectors: dict[str, str], timeout: int) -> None:
    modal = _modal_scope(page)
    candidates = [
        selectors.get("confirm_ok_button", "button.ant-btn-primary"),
        "button.ant-btn-primary",
        'button:has-text("确定")',
        'text=确定',
    ]
    last_error: Exception | None = None
    for selector in candidates:
        try:
            _locator_with_scope(modal, selector).first.click(timeout=min(timeout, 1500))
            return
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("未找到确认上传的确定按钮")


def _select_person_radio(modal: Locator, timeout: int) -> None:
    candidates = [
        modal.locator(".ant-radio-wrapper"),
        modal.locator("label.ant-radio-wrapper"),
        modal.locator("input.ant-radio-input"),
    ]
    for locator in candidates:
        try:
            if locator.count() > 0:
                locator.first.click(timeout=timeout)
                return
        except Exception:
            continue
    raise RuntimeError("未找到员工记录单选按钮")


def _wait_person_search_results(page: Page, timeout: int) -> None:
    modal = _modal_scope(page)
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


def _open_person_selector(page: Page, selectors: dict[str, str], timeout: int) -> None:
    if not _is_upload_page(page):
        raise RuntimeError("当前页面不在上传表单，无法打开人员弹窗")

    try:
        _click_locator(page, selectors["person_select_button"], min(timeout, 3000))
        _wait_person_modal(page, selectors, min(timeout, 4000))
        return
    except Exception:
        pass

    try:
        _click_locator(page, ".cdc-employee-picker_box-entry", min(timeout, 3000))
        _wait_person_modal(page, selectors, min(timeout, 4000))
        return
    except Exception:
        pass

    input_locator = _person_input_locator(page)
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
    _wait_person_modal(page, selectors, min(timeout, 4000))


def _trigger_person_picker(page: Page, icon_x: float, y: float) -> None:
    offsets = [0, -4, 4]
    for offset in offsets:
        page.mouse.click(icon_x + offset, y)
        page.wait_for_timeout(120)
        page.mouse.dblclick(icon_x + offset, y)
        page.wait_for_timeout(180)


def _select_option(page: Page, field_selector: str, value: str, timeout: int) -> None:
    field = _locator(page, field_selector)
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


def _upload_file(page: Page, upload_selector: str, file_path: str, timeout: int) -> None:
    file_name = Path(file_path).name
    errors: list[str] = []

    try:
        locator = _locator(page, upload_selector)
        locator.first.set_input_files(file_path, timeout=timeout)
        page.wait_for_timeout(800)
        _wait_uploaded_file_visible(page, file_name, timeout)
        return
    except Exception as exc:
        errors.append(f"hidden-input upload failed: {exc}")

    try:
        with page.expect_file_chooser(timeout=timeout) as chooser_info:
            _click_visible_upload_file_button(page, timeout)
        chooser: FileChooser = chooser_info.value
        chooser.set_files(file_path, timeout=timeout)
        page.wait_for_timeout(800)
        _wait_uploaded_file_visible(page, file_name, timeout)
        return
    except Exception as exc:
        errors.append(f"visible-button upload failed: {exc}")

    raise RuntimeError("文件上传未成功: " + " | ".join(errors))


def _click_visible_upload_file_button(page: Page, timeout: int) -> None:
    candidates = [
        page.locator("button.ant-btn.cdc-app.ant-btn-default.ant-btn-color-default.ant-btn-variant-outlined").filter(
            has_text=re.compile("^上传文件$")
        ),
        page.locator("button.ant-btn.cdc-app").filter(has_text=re.compile("^上传文件$")),
        page.get_by_role("button", name="上传文件"),
        page.locator("button").filter(has_text=re.compile("上传文件")),
        page.get_by_text("上传文件", exact=False),
    ]
    for locator in candidates:
        try:
            if locator.count() > 0:
                locator.first.click(timeout=timeout)
                return
        except Exception:
            continue
    raise RuntimeError("未找到可见的“上传文件”按钮")


def _wait_uploaded_file_visible(page: Page, file_name: str, timeout: int) -> None:
    candidates = [
        page.get_by_text(file_name, exact=False),
        page.locator(f"text={file_name}"),
    ]
    for locator in candidates:
        try:
            locator.first.wait_for(timeout=timeout)
            return
        except Exception:
            continue
    raise RuntimeError(f"页面未显示已上传文件名: {file_name}")


def _verify_first_row(page: Page, selectors: dict[str, str], task: TaskRecord, timeout: int) -> None:
    verify_timeout = min(timeout, 15000)
    attempts = [
        lambda: None,
        lambda: page.reload(wait_until="domcontentloaded"),
    ]
    last_error: Exception | None = None

    for action in attempts:
        try:
            action()
            try:
                _wait_url_contains(page, "/hr/employee/archive", min(verify_timeout, 5000))
            except Exception:
                pass
            _wait_archive_list_ready(page, min(verify_timeout, 12000))
            row = _wait_first_visible_archive_row(page, selectors, verify_timeout)
            row_text = row.inner_text(timeout=1200)
            if task.employee_id not in row_text:
                raise RuntimeError(f"首条记录未匹配 employee_id: {task.employee_id}")
            if task.business_type not in row_text:
                raise RuntimeError(f"首条记录未匹配 business_type: {task.business_type}")
            return
        except Exception as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error
    raise RuntimeError("列表首条记录校验失败")


def _wait_archive_list_ready(page: Page, timeout: int) -> None:
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


def _is_archive_list_page(page: Page) -> bool:
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


def _wait_first_visible_archive_row(page: Page, selectors: dict[str, str], timeout: int) -> Locator:
    interval_ms = 200
    elapsed_ms = 0
    last_error: Exception | None = None

    while elapsed_ms <= timeout:
        try:
            return _first_visible_archive_row(page, selectors, min(timeout, 1200))
        except Exception as exc:
            last_error = exc
            page.wait_for_timeout(interval_ms)
            elapsed_ms += interval_ms

    if last_error is not None:
        raise last_error
    raise RuntimeError("列表页未找到可见的业务数据首行")


def _first_visible_archive_row(page: Page, selectors: dict[str, str], timeout: int) -> Locator:
    candidates = [
        page.locator("tbody tr").filter(has_not=page.locator(".ant-table-measure-row")),
        page.locator("tbody tr[aria-hidden='false']"),
        page.locator("tbody tr:not(.ant-table-measure-row)"),
        page.locator(selectors.get("list_first_row", "tbody tr:first-child")),
    ]

    for locator in candidates:
        try:
            count = locator.count()
        except Exception:
            continue
        for index in range(count):
            row = locator.nth(index)
            try:
                row.wait_for(state="visible", timeout=min(timeout, 800))
                aria_hidden = row.get_attribute("aria-hidden")
                class_name = row.get_attribute("class") or ""
                if aria_hidden == "true":
                    continue
                if "ant-table-measure-row" in class_name:
                    continue
                text = row.inner_text(timeout=800).strip()
                if not text:
                    continue
                return row
            except Exception:
                continue
    raise RuntimeError("列表页未找到可见的业务数据首行")


def _fill_locator(page: Page, selector: str, value: str, timeout: int) -> None:
    locator = _locator(page, selector)
    locator.first.wait_for(timeout=timeout)
    locator.first.fill(value, timeout=timeout)


def _click_locator(page: Page, selector: str, timeout: int, within_modal: bool = False) -> None:
    locator = _modal_scope(page) if within_modal else _locator(page, selector)
    if within_modal:
        locator = _locator_with_scope(_modal_scope(page), selector)
    locator.first.wait_for(timeout=timeout)
    locator.first.click(timeout=timeout)


def _wait_visible(page: Page, selector: str, timeout: int) -> None:
    _locator(page, selector).first.wait_for(timeout=timeout)


def _wait_url_contains(page: Page, text: str, timeout: int) -> None:
    page.wait_for_url(f"**{text}**", timeout=timeout)


def _locator(page: Page, selector: str) -> Locator:
    return _locator_with_scope(page, selector)


def _locator_with_scope(scope: Page | Locator, selector: str) -> Locator:
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


def _modal_scope(page: Page) -> Locator:
    modal = page.locator(".ant-modal,.ant-modal-root").last
    if modal.count() == 0:
        return page.locator("body")
    return modal


def _dismiss_overlays(page: Page) -> None:
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
    for locator in closers:
        try:
            if locator.count() > 0 and locator.first.is_visible():
                locator.first.click(timeout=500)
        except Exception:
            continue


def _map_value(mapping: dict[str, Any], key: str, value: str) -> str:
    mapped = mapping.get(key, {})
    return mapped.get(value, value)


def _open_upload_page(page: Page, selectors: dict[str, str], base_url: str, timeout: int) -> None:
    if _is_upload_page(page):
        return

    last_error: Exception | None = None
    attempts = [
        lambda: _click_visible_upload_button(page, timeout),
        lambda: page.goto(_upload_page_url(base_url), wait_until="domcontentloaded"),
        lambda: _click_locator(page, selectors["upload_entry"], timeout),
        lambda: page.get_by_role("button", name="上传档案附件").first.click(timeout=2500),
        lambda: _click_visible_upload_button(page, timeout),
    ]

    for action in attempts:
        try:
            action()
            _wait_upload_page(page, timeout)
            return
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError("未能进入上传页")


def _click_visible_upload_button(page: Page, timeout: int) -> None:
    candidates = [
        page.get_by_role("button", name="上传档案附件"),
        page.locator("button").filter(has_text=re.compile("上传档案附件")),
        page.get_by_text("上传档案附件", exact=False),
    ]
    for locator in candidates:
        try:
            if locator.count() > 0:
                locator.first.click(timeout=timeout)
                return
        except Exception:
            continue
    raise RuntimeError("当前页面未找到可点击的“上传档案附件”按钮")


def _wait_after_login(page: Page, timeout: int) -> None:
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


def _wait_upload_page(page: Page, timeout: int) -> None:
    try:
        page.wait_for_url("**/hr/employee/archive/uploadArchive**", timeout=timeout)
    except Exception:
        pass

    try:
        _wait_visible(page, "text=上传方式", timeout)
        _wait_visible(page, "text=选择人员", timeout)
        return
    except Exception:
        pass

    raise RuntimeError("未成功进入上传页，当前页面仍不是上传表单")


def _is_upload_page(page: Page) -> bool:
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


def _person_input_locator(page: Page) -> Locator:
    candidates = [
        page.locator("xpath=//*[contains(normalize-space(.), '选择人员')]/following::input[1]"),
        page.locator("input").first,
    ]
    for locator in candidates:
        try:
            if locator.count() > 0:
                return locator.first
        except Exception:
            continue
    raise RuntimeError("未找到选择人员输入框")


def _wait_person_modal(page: Page, selectors: dict[str, str], timeout: int) -> None:
    candidates = [
        selectors.get("person_modal_title", "text=选择员工"),
        selectors.get("person_query_input", "input[placeholder='搜索人员']"),
        "input[placeholder='搜索人员']",
    ]
    for selector in candidates:
        try:
            _wait_visible(page, selector, timeout)
            return
        except Exception:
            continue
    raise RuntimeError("人员选择弹窗未出现")


def _ensure_privacy_agreement(page: Page) -> None:
    try:
        checkboxes = page.get_by_role("checkbox")
        count = checkboxes.count()
        if count >= 2:
            privacy_checkbox = checkboxes.nth(1)
            if not privacy_checkbox.is_checked():
                privacy_checkbox.check(timeout=1500)
            return
    except Exception:
        pass

    try:
        agreement_text = page.get_by_text("同意并接受", exact=False)
        if agreement_text.count() > 0:
            agreement_text.first.click(timeout=1500)
    except Exception:
        pass


def _upload_page_url(base_url: str) -> str:
    return base_url.replace("/login?redirect_uri=%2Fhr%2Femployee%2Farchive", "/hr/employee/archive/uploadArchive")


def _archive_list_url(base_url: str) -> str:
    return base_url.replace("/login?redirect_uri=%2Fhr%2Femployee%2Farchive", "/hr/employee/archive")
