from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import Locator, Page

from automation.core.actions import (
    click_confirm_submit,
    click_locator,
    click_person_search,
    click_submit,
    click_visible_upload_entry,
    dismiss_overlays,
    fill_locator,
    open_person_selector,
    select_option,
    select_person_radio,
    upload_file,
    wait_confirm_submit_modal,
    wait_person_search_results,
)
from automation.core.selectors import locator, modal_scope
from automation.core.state import (
    is_archive_list_page,
    is_upload_page,
    wait_archive_list_ready,
    wait_upload_page,
)
from automation.core.waits import wait_after_login, wait_url_contains
from flows.archive_upload.task_loader import load_tasks, validate_tasks
from flows.archive_upload.task_model import TaskRecord, TaskResult


StepLogger = Callable[[str, str, str], None]


@dataclass(slots=True)
class ArchiveUploadFlow:
    name: str = "archive-upload"

    def load_tasks(self, task_path: str):
        return load_tasks(task_path)

    def validate_tasks(self, tasks):
        return validate_tasks(tasks)

    def initialize_batch_session(self, page, config: dict, logger) -> None:
        initialize_batch_session(page, config, logger)

    def run_task(self, page, config: dict, task, logger, step_log):
        return run_task(page, config, task, logger, step_log)

    def capture_screenshot(self, page, screenshot_dir: str, task):
        return capture_screenshot(page, screenshot_dir, task)

    def reset_task_context(self, page, config: dict, logger, task_id: str) -> None:
        reset_task_context(page, config, logger, task_id)


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
        open_person_selector(page, selectors, timeout)
        _step(logger, step_log, task, "open_person_selector", "SUCCESS", "人员弹窗已打开")

        _step(logger, step_log, task, "search_person", "START", "搜索并选择人员")
        _select_person(page, selectors, task, timeout)
        _step(logger, step_log, task, "search_person", "SUCCESS", f"已选人员 {task.employee_id}/{task.employee_name}")

        _step(logger, step_log, task, "confirm_person", "START", "确认人员")
        click_locator(page, selectors["person_confirm_button"], timeout, within_modal=True)
        _step(logger, step_log, task, "confirm_person", "SUCCESS", "人员已确认")

        _step(logger, step_log, task, "select_business_line", "START", f"选择所属业务 {task.business_line}")
        select_option(page, selectors["business_line_select"], _map_value(mapping, "business_line", task.business_line), timeout)
        _step(logger, step_log, task, "select_business_line", "SUCCESS", "所属业务已选择")

        _step(logger, step_log, task, "select_business_type", "START", f"选择业务类型 {task.business_type}")
        select_option(page, selectors["business_type_select"], _map_value(mapping, "business_type", task.business_type), timeout)
        _step(logger, step_log, task, "select_business_type", "SUCCESS", "业务类型已选择")

        _step(logger, step_log, task, "upload_file", "START", f"上传文件 {task.file_name}")
        upload_file(page, selectors["upload_file_button"], task.file_path, timeout)
        _step(logger, step_log, task, "upload_file", "SUCCESS", "文件已上传")

        _step(logger, step_log, task, "submit_form", "START", "提交表单")
        click_submit(page, selectors["submit_button"], timeout)
        _step(logger, step_log, task, "submit_form", "SUCCESS", "已点击提交")

        _step(logger, step_log, task, "confirm_submit", "START", "确认提交")
        wait_confirm_submit_modal(page, selectors, timeout)
        click_confirm_submit(page, selectors, timeout)
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
        dismiss_overlays(page)
    except Exception:
        pass

    try:
        if is_archive_list_page(page):
            wait_archive_list_ready(page, timeout)
            logger.info(f"[TASK {task_id}] context_reset=current_list_page")
            return
    except Exception:
        pass

    try:
        page.goto(list_url, wait_until="domcontentloaded")
        wait_archive_list_ready(page, timeout)
        logger.info(f"[TASK {task_id}] context_reset={list_url}")
        return
    except Exception:
        pass

    try:
        page.reload(wait_until="domcontentloaded")
        wait_archive_list_ready(page, timeout)
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
    fill_locator(page, selectors["username_input"], auth["username"], timeout)
    fill_locator(page, selectors["password_input"], auth["password"], timeout)
    _ensure_privacy_agreement(page)
    _submit_login(page, selectors["login_button"], selectors["password_input"], timeout)


def _submit_login(page: Page, login_selector: str, password_selector: str, timeout: int) -> None:
    last_error: Exception | None = None
    attempts = [
        lambda: locator(page, password_selector).first.press("Enter", timeout=1500),
        lambda: click_locator(page, login_selector, timeout),
        lambda: page.locator("button[type='submit']").first.click(timeout=2500),
        lambda: page.locator("button").filter(has_text=re.compile("登录")).first.click(timeout=2500),
        lambda: page.get_by_text("登录", exact=False).first.click(timeout=2500),
    ]

    for action in attempts:
        try:
            action()
            wait_after_login(page, timeout)
            return
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("登录提交失败")


def _select_person(page: Page, selectors: dict[str, str], task: TaskRecord, timeout: int) -> None:
    query_value = task.employee_id or task.employee_name
    fill_locator(page, selectors["person_query_input"], query_value, timeout)
    click_person_search(page, timeout)
    wait_person_search_results(page, timeout)

    modal = modal_scope(page)
    if task.employee_id and modal.get_by_text(task.employee_id, exact=False).count() == 0:
        raise RuntimeError(f"搜索后未找到目标人员或结果尚未加载完成: {query_value}")
    if task.employee_name and modal.get_by_text(task.employee_name, exact=False).count() == 0:
        raise RuntimeError(f"搜索后未找到目标人员或结果尚未加载完成: {query_value}")

    select_person_radio(modal, timeout)


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
                wait_url_contains(page, "/hr/employee/archive", min(verify_timeout, 5000))
            except Exception:
                pass
            wait_archive_list_ready(page, min(verify_timeout, 12000))
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

    for current in candidates:
        try:
            count = current.count()
        except Exception:
            continue
        for index in range(count):
            row = current.nth(index)
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


def _map_value(mapping: dict[str, Any], key: str, value: str) -> str:
    mapped = mapping.get(key, {})
    return mapped.get(value, value)


def _open_upload_page(page: Page, selectors: dict[str, str], base_url: str, timeout: int) -> None:
    if is_upload_page(page):
        return

    last_error: Exception | None = None
    attempts = [
        lambda: click_visible_upload_entry(page, timeout),
        lambda: page.goto(_upload_page_url(base_url), wait_until="domcontentloaded"),
        lambda: click_locator(page, selectors["upload_entry"], timeout),
        lambda: page.get_by_role("button", name="上传档案附件").first.click(timeout=2500),
        lambda: click_visible_upload_entry(page, timeout),
    ]

    for action in attempts:
        try:
            action()
            wait_upload_page(page, timeout)
            return
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError("未能进入上传页")


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
