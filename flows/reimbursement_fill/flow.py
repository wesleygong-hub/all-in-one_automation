from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter, sleep
from typing import Any, Callable

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from flows.reimbursement_fill.task_loader import load_tasks, validate_tasks
from flows.reimbursement_fill.task_model import ReimbursementTaskRecord, ReimbursementTaskResult


StepLogger = Callable[[str, str, str], None]
LocatorContext = Any


class DuplicateInvoiceDetectedError(RuntimeError):
    pass


@dataclass(slots=True)
class ReimbursementFillFlow:
    name: str = "reimbursement-fill"

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


def initialize_batch_session(page, config: dict[str, Any], logger: logging.Logger) -> None:
    logger.info("[BATCH] [open_iam_panel] START 打开 IAM 面板")
    started_at = perf_counter()
    page.goto(config["system"]["base_url"], wait_until="domcontentloaded")
    logger.info(f"[BATCH] [open_iam_panel] SUCCESS IAM 面板已打开 elapsed_ms={_elapsed_ms(started_at)}")
    _login_iam(page, config, logger)


def run_task(page, config: dict[str, Any], task: ReimbursementTaskRecord, logger: logging.Logger, step_log: StepLogger) -> ReimbursementTaskResult:
    timeout = int(config["system"].get("timeout_ms", 15000))
    selectors = config.get("selectors", {})
    working_page = page

    _step(logger, step_log, task, "open_finance_share", "START", "进入财务共享")
    started_at = perf_counter()
    working_page = _open_finance_share(working_page, config, selectors, timeout)
    _step(logger, step_log, task, "open_finance_share", "SUCCESS", f"已进入财务共享 elapsed_ms={_elapsed_ms(started_at)}")

    _step(logger, step_log, task, "open_my_reimbursement", "START", "进入我要报账")
    started_at = perf_counter()
    _open_my_reimbursement(working_page, selectors, timeout, logger, task.task_id, step_log)
    _step(logger, step_log, task, "open_my_reimbursement", "SUCCESS", f"已进入我要报账 elapsed_ms={_elapsed_ms(started_at)}")

    _step(logger, step_log, task, "create_business_entertainment_bill", "START", "创建业务招待费报销单据")
    started_at = perf_counter()
    working_page = _create_business_entertainment_bill(working_page, config, selectors, timeout, logger, task.task_id, step_log)
    _step(
        logger,
        step_log,
        task,
        "create_business_entertainment_bill",
        "SUCCESS",
        f"已进入业务招待费报销单据页 elapsed_ms={_elapsed_ms(started_at)}",
    )

    _step(logger, step_log, task, "open_electronic_image_tab", "START", "打开电子影像")
    started_at = perf_counter()
    _open_electronic_image_tab(working_page, selectors, timeout, logger, task.task_id, step_log)
    _step(logger, step_log, task, "open_electronic_image_tab", "SUCCESS", f"已打开电子影像 elapsed_ms={_elapsed_ms(started_at)}")

    _step(logger, step_log, task, "open_local_upload_dialog", "START", "打开本地上传弹窗")
    started_at = perf_counter()
    _open_local_upload_dialog(working_page, selectors, timeout, logger, task.task_id, step_log)
    _step(logger, step_log, task, "open_local_upload_dialog", "SUCCESS", f"本地上传弹窗已打开 elapsed_ms={_elapsed_ms(started_at)}")

    _step(logger, step_log, task, "upload_invoice_file", "START", "上传发票文件")
    started_at = perf_counter()
    _upload_invoice_files(working_page, task, selectors, timeout, logger, task.task_id, step_log)
    _step(logger, step_log, task, "upload_invoice_file", "SUCCESS", f"发票文件已上传 elapsed_ms={_elapsed_ms(started_at)}")

    _step(logger, step_log, task, "close_upload_dialog", "START", "关闭上传弹窗")
    started_at = perf_counter()
    _close_upload_dialog(working_page, selectors, timeout)
    _step(logger, step_log, task, "close_upload_dialog", "SUCCESS", f"上传弹窗已关闭 elapsed_ms={_elapsed_ms(started_at)}")

    _step(logger, step_log, task, "detect_uploaded_invoice", "START", "检测已上传发票")
    started_at = perf_counter()
    try:
        _detect_uploaded_invoice(working_page, task, selectors, timeout)
    except DuplicateInvoiceDetectedError as exc:
        _step(logger, step_log, task, "detect_uploaded_invoice", "FAILED", str(exc))
        return _abort_duplicate_invoice_task(working_page, selectors, timeout, logger, task, step_log, exc)
    _step(logger, step_log, task, "detect_uploaded_invoice", "SUCCESS", f"已检测到上传发票 elapsed_ms={_elapsed_ms(started_at)}")

    _step(logger, step_log, task, "recognize_uploaded_invoice", "START", "识别已上传发票")
    started_at = perf_counter()
    try:
        _recognize_uploaded_invoice(working_page, selectors, timeout, logger, task.task_id, step_log)
    except DuplicateInvoiceDetectedError as exc:
        _step(logger, step_log, task, "recognize_uploaded_invoice", "FAILED", str(exc))
        return _abort_duplicate_invoice_task(working_page, selectors, timeout, logger, task, step_log, exc)
    _step(logger, step_log, task, "recognize_uploaded_invoice", "SUCCESS", f"已完成发票识别 elapsed_ms={_elapsed_ms(started_at)}")

    _step(logger, step_log, task, "close_electronic_image_tab", "START", "关闭电子影像页签")
    started_at = perf_counter()
    _close_electronic_image_tab(working_page, selectors, timeout, logger, task.task_id, step_log)
    _step(logger, step_log, task, "close_electronic_image_tab", "SUCCESS", f"已关闭电子影像页签 elapsed_ms={_elapsed_ms(started_at)}")

    _step(logger, step_log, task, "fill_reimbursement_form", "START", "填写报销单字段")
    started_at = perf_counter()
    _fill_reimbursement_form(working_page, task, selectors, config.get("mapping", {}), timeout, logger, task.task_id, step_log)
    _step(logger, step_log, task, "fill_reimbursement_form", "SUCCESS", f"已填写报销单字段 elapsed_ms={_elapsed_ms(started_at)}")

    _step(logger, step_log, task, "save_reimbursement_form", "START", "保存报销单")
    started_at = perf_counter()
    _save_reimbursement_form(working_page, selectors, timeout, logger, task.task_id, step_log)
    _step(logger, step_log, task, "save_reimbursement_form", "SUCCESS", f"已保存报销单 elapsed_ms={_elapsed_ms(started_at)}")

    _step(logger, step_log, task, "close_reimbursement_bill_tab", "START", "关闭当前报销单页签")
    started_at = perf_counter()
    _close_reimbursement_bill_tab(working_page, selectors, timeout, logger, task.task_id, step_log)
    _step(logger, step_log, task, "close_reimbursement_bill_tab", "SUCCESS", f"已关闭当前报销单页签并返回我要报账 elapsed_ms={_elapsed_ms(started_at)}")

    return ReimbursementTaskResult(status="success", message="reimbursement form saved")


def reset_task_context(page, config: dict[str, Any], logger: logging.Logger, task_id: str) -> None:
    logger.info(f"[TASK {task_id}] context_reset=noop")


def capture_screenshot(page, screenshot_dir: str, task: ReimbursementTaskRecord) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(screenshot_dir) / f"{task.task_id}_{timestamp}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def _login_iam(page, config: dict[str, Any], logger: logging.Logger) -> None:
    selectors = config.get("selectors", {})
    username_selector = selectors.get("iam_username_input", "#passworLogin_account")
    password_selector = selectors.get("iam_password_input", "#passworLogin_password")
    agreement_selector = selectors.get("iam_agreement_checkbox", '.authing-agreements-checkbox')
    login_button_selector = selectors.get("iam_login_button", 'button[type="submit"]')
    finance_share_selector = selectors.get("finance_share_entry", "text=财务共享")
    timeout_ms = int(config.get("system", {}).get("timeout_ms", 15000))
    login_wait_ms = max(timeout_ms, 45000)

    username = str(config.get("auth", {}).get("username", "")).strip()
    password = str(config.get("auth", {}).get("password", "")).strip()
    if not username or not password or "${" in username or "${" in password:
        raise RuntimeError(
            "reimbursement-fill 目前要求先完成 IAM 登录。"
            "请使用本地配置文件或设置 IAM_USERNAME/IAM_PASSWORD。"
        )

    username_locator = page.locator(username_selector).first
    password_locator = page.locator(password_selector).first
    agreement_locator = page.locator(agreement_selector).first
    login_button_locator = page.locator(login_button_selector).first
    finance_locator = page.locator(finance_share_selector).first

    if _wait_visible(finance_locator, 1200):
        logger.info("[BATCH] [login_iam] SKIP 已检测到 IAM 面板入口 elapsed_ms=0")
        return

    logger.info("[BATCH] [login_iam] START 执行 IAM 登录")

    state_started_at = perf_counter()
    login_state = _wait_iam_login_state(username_locator, finance_locator, login_wait_ms)
    logger.info(f"[BATCH] [detect_iam_login_state] SUCCESS state={login_state} elapsed_ms={_elapsed_ms(state_started_at)}")

    if login_state == "finance":
        logger.info("[BATCH] [login_iam] SKIP 等待过程中已进入 IAM 面板")
        return
    if login_state != "username":
        raise RuntimeError("IAM 登录页加载超时，未检测到用户名输入框，且未进入 IAM 面板")

    _timed_batch_step(logger, "wait_iam_password", "等待密码框", lambda: _ensure_visible(password_locator, 3000, "IAM 登录页未检测到密码输入框"))
    _timed_batch_step(logger, "fill_iam_username", "填写用户名", lambda: username_locator.fill(username))
    _timed_batch_step(logger, "fill_iam_password", "填写密码", lambda: password_locator.fill(password))

    if agreement_locator.count():
        _timed_batch_step(logger, "check_iam_agreement", "勾选公司规定确认", lambda: _click_optional(agreement_locator))

    _timed_batch_step(logger, "wait_iam_login_button", "等待登录按钮", lambda: _ensure_visible(login_button_locator, 3000, "IAM 登录页未检测到登录按钮"))
    _timed_batch_step(logger, "click_iam_login_button", "点击登录按钮", lambda: login_button_locator.click())
    _timed_batch_step(logger, "wait_iam_panel", "等待 IAM 面板入口", lambda: _ensure_visible(finance_locator, min(login_wait_ms, 3000), "IAM 登录后未进入面板页，未检测到 `财务共享` 入口"))

    logger.info("[BATCH] [login_iam] SUCCESS IAM 登录完成")


def _open_finance_share(page: Page, config: dict[str, Any], selectors: dict[str, str], timeout: int) -> Page:
    finance_share_selector = selectors.get("finance_share_entry", "text=财务共享")
    finance_ready_selectors = [
        selectors.get("menu_finance_share", ""),
        selectors.get("go_reimbursement_button", ""),
    ]

    if _is_finance_share_page(page, finance_ready_selectors):
        return page

    target = page.locator(finance_share_selector).first
    if not _wait_visible(target, min(timeout, 3000)):
        raise RuntimeError("IAM 面板未检测到可点击的‘财务共享’卡片")

    last_error: Exception | None = None
    actions = [
        lambda: _safe_click_target(target, timeout),
        lambda: _safe_click_target(target, timeout, force=True),
        lambda: _activate_by_keyboard(page, target),
        lambda: target.dispatch_event("click"),
        lambda: page.evaluate("(el) => el.click()", target.element_handle(timeout=timeout)),
    ]

    for action in actions:
        try:
            target.scroll_into_view_if_needed(timeout=timeout)
        except Exception:
            pass
        page.wait_for_timeout(120)
        try:
            candidate_page = _attempt_finance_share_activation(page, action, finance_ready_selectors, timeout)
            if candidate_page:
                return candidate_page
        except Exception as exc:
            last_error = exc

    fallback_url = str(config.get("system", {}).get("finance_share_url", "")).strip()
    if fallback_url:
        try:
            page.goto(fallback_url, wait_until="domcontentloaded")
            page.wait_for_timeout(600)
            if _is_finance_share_page(page, finance_ready_selectors):
                return page
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise RuntimeError(f"未成功进入财务共享应用：{last_error}")
    raise RuntimeError("未成功进入财务共享应用，卡片激活与 URL 兜底均失败")


def _open_my_reimbursement(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> None:
    detect_timeout = min(timeout, 900)
    menu_timeout = min(timeout, 3000)
    if _is_my_reimbursement_page(page, selectors, 300):
        return

    _timed_substep(logger, step_log, task_id, "expand_finance_tree", "展开财务共享菜单", lambda: _ensure_tree_node_expanded(page, "财务共享", menu_timeout))
    _timed_substep(logger, step_log, task_id, "click_online_reimbursement", "点击网上报账平台", lambda: _click_tree_title_fast(page, "网上报账平台", menu_timeout))
    page.wait_for_timeout(120)
    _timed_substep(logger, step_log, task_id, "click_go_reimbursement", "点击我要报账", lambda: _click_go_reimbursement_fast(page, selectors["go_reimbursement_button"], menu_timeout))
    _timed_substep(logger, step_log, task_id, "detect_my_reimbursement_page", "检测我要报账页面到达", lambda: _ensure_my_reimbursement_page(page, selectors, detect_timeout))
    _cache_reimbursement_context(page, _resolve_reimbursement_context(page, selectors))


def _create_business_entertainment_bill(
    page: Page,
    config: dict[str, Any],
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> Page:
    detect_timeout = min(timeout, 1200)
    click_timeout = min(timeout, 2800)
    context_holder: dict[str, LocatorContext] = {}
    bill_page_state: dict[str, bool] = {}
    _timed_substep(
        logger,
        step_log,
        task_id,
        "resolve_reimbursement_context_for_new_bill",
        "定位我要报账上下文",
        lambda: context_holder.__setitem__("context", _resolve_reimbursement_context(page, selectors)),
    )
    context = context_holder["context"]
    _timed_substep(
        logger,
        step_log,
        task_id,
        "precheck_business_entertainment_bill_page",
        "预检业务招待费报销单据页状态",
        lambda: bill_page_state.__setitem__("matched", _is_business_entertainment_bill_page_precheck(page, selectors)),
    )
    if bill_page_state.get("matched", False):
        return page

    _timed_substep(
        logger,
        step_log,
        task_id,
        "open_new_bill_menu",
        "展开新建单据菜单",
        lambda: _open_new_bill_menu(page, context, selectors, click_timeout),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "diagnose_new_bill_menu",
        "诊断新建单据菜单展开状态",
        lambda: _diagnose_new_bill_menu(page, context, selectors),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "hover_bill_type_expense",
        "悬停费用报销类",
        lambda: _hover_locator_fast(
            context,
            page,
            selectors["bill_type_expense"],
            click_timeout,
            "未找到可悬停的‘费用报销类’入口",
        ),
    )
    page.wait_for_timeout(120)
    _timed_substep(
        logger,
        step_log,
        task_id,
        "click_bill_subtype_business_entertainment",
        "点击业务招待费报销",
        lambda: _click_business_entertainment_link(page, context, selectors, click_timeout),
    )
    page = _follow_new_page_after_bill_click(page, timeout)
    _timed_substep(
        logger,
        step_log,
        task_id,
        "detect_business_entertainment_bill_page",
        "检测业务招待费报销单据页到达",
        lambda: _ensure_business_entertainment_bill_page(page, selectors, detect_timeout),
    )
    return page


def _open_electronic_image_tab(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> None:
    click_timeout = min(timeout, 3000)
    detect_timeout = min(timeout, 260)
    _timed_substep(
        logger,
        step_log,
        task_id,
        "click_electronic_image_tab",
        "点击电子影像入口",
        lambda: _click_electronic_image_tab(page, selectors, click_timeout),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "detect_electronic_image_page",
        "检测电子影像页面到达",
        lambda: _ensure_electronic_image_page(page, selectors, detect_timeout),
    )


def _open_local_upload_dialog(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> None:
    click_timeout = min(timeout, 1200)
    detect_timeout = min(timeout, 1200)
    image_context_holder: dict[str, LocatorContext] = {}

    def resolve_image_context() -> None:
        image_context_holder["context"] = _resolve_electronic_image_context(page, selectors)

    _timed_substep(
        logger,
        step_log,
        task_id,
        "resolve_electronic_image_context",
        "定位电子影像上下文",
        resolve_image_context,
    )
    image_context = image_context_holder["context"]
    _cache_electronic_image_context(page, image_context)
    _timed_substep(
        logger,
        step_log,
        task_id,
        "click_local_upload_button",
        "点击本地上传",
        lambda: _click_locator_fast(image_context, page, selectors["local_upload_button"], click_timeout, "未找到可点击的‘本地上传’按钮"),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "detect_upload_dialog",
        "检测上传弹窗打开",
        lambda: _ensure_upload_dialog_open(page, selectors, detect_timeout),
    )


def _upload_invoice_files(
    page: Page,
    task: ReimbursementTaskRecord,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> None:
    upload_context_holder: dict[str, LocatorContext] = {}

    def resolve_upload_context() -> None:
        end_at = perf_counter() + (min(timeout, 1200) / 1000)
        while perf_counter() < end_at:
            upload_context = _resolve_upload_dialog_context(page, selectors)
            if upload_context is not None:
                upload_context_holder["context"] = upload_context
                return
            page.wait_for_timeout(40)
        raise RuntimeError(_diagnose_upload_dialog(page, selectors))

    _timed_substep(
        logger,
        step_log,
        task_id,
        "resolve_upload_dialog_context",
        "定位上传弹窗上下文",
        resolve_upload_context,
    )
    upload_context = upload_context_holder["context"]

    file_paths = [str(Path(invoice.file_path).resolve()) for invoice in task.invoices]
    if not file_paths:
        raise RuntimeError("当前任务未配置发票文件")

    _timed_substep(
        logger,
        step_log,
        task_id,
        "detect_choose_file_ready",
        "检测选择文件控件就绪",
        lambda: _ensure_upload_file_ready(upload_context, selectors, min(timeout, 1200)),
    )

    _timed_substep(
        logger,
        step_log,
        task_id,
        "set_upload_files",
        "选择本地文件",
        lambda: _set_upload_files(upload_context, selectors["file_input"], file_paths, timeout),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "click_start_upload_button",
        "点击开始上传",
        lambda: _click_locator_fast(upload_context, page, selectors["start_upload_button"], min(timeout, 3000), "未找到可点击的‘开始上传’按钮"),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "detect_upload_finished",
        "检测上传完成",
        lambda: _ensure_upload_files_selected(upload_context, file_paths, timeout),
    )


def _close_upload_dialog(page: Page, selectors: dict[str, str], timeout: int) -> None:
    dialog_host_context = _resolve_electronic_image_context(page, selectors)
    if not _click_latest_visible_element(dialog_host_context, selectors["close_upload_dialog_button"]):
        _click_locator_fast(dialog_host_context, page, selectors["close_upload_dialog_button"], min(timeout, 1200), "未找到上传弹窗关闭按钮")
    dialog_selector = selectors.get("upload_dialog", '.layui-layer.layui-layer-iframe')
    dialog_iframe_selector = selectors.get("upload_dialog_iframe", 'iframe[id^="layui-layer-iframe"]')
    end_at = perf_counter() + (min(timeout, 900) / 1000)
    while perf_counter() < end_at:
        if _count_visible_elements(dialog_host_context, dialog_selector) == 0 and _count_visible_elements(dialog_host_context, dialog_iframe_selector) == 0:
            return
        page.wait_for_timeout(40)
    raise RuntimeError("上传弹窗关闭后仍然可见")


def _detect_uploaded_invoice(page: Page, task: ReimbursementTaskRecord, selectors: dict[str, str], timeout: int) -> None:
    context = _resolve_electronic_image_context(page, selectors)
    marker_names = [invoice.file_name for invoice in task.invoices if invoice.file_name]
    expected_count = max(1, len(task.invoices))
    item_selectors = [
        selectors.get("invoice_list_item", ""),
        ".sortwrap .thumb",
        ".thumbwrap .thumb",
        ".uploadInvoiceList .thumb",
        ".invoice-list .thumb",
        ".thumb",
        ".uploadInvoiceList li",
    ]
    container_selectors = [
        ".sortwrap",
        ".thumbwrap",
        ".uploadInvoiceList",
        ".invoice-list",
    ]
    if _quick_detect_uploaded_invoice_in_context(
        context,
        marker_names,
        item_selectors,
        container_selectors,
        expected_count,
        min(timeout, 180),
        25,
    ):
        return
    page.wait_for_timeout(500)
    context = _resolve_electronic_image_context(page, selectors)
    if _quick_detect_uploaded_invoice_in_context(
        context,
        marker_names,
        item_selectors,
        container_selectors,
        expected_count,
        min(timeout, 220),
        30,
    ):
        return
    attempts: list[str] = []
    for index, candidate_context in enumerate(_candidate_recognition_contexts(page, selectors)):
        context_name = _context_debug_name(candidate_context, index)
        _uploaded_invoice_ready_in_context(
            candidate_context,
            marker_names,
            item_selectors,
            container_selectors,
            expected_count,
            attempts,
            context_name,
        )
    duplicate_message = _detect_duplicate_invoice_message(page, selectors)
    if duplicate_message is not None:
        raise DuplicateInvoiceDetectedError(duplicate_message)
    raise RuntimeError(f"未检测到已上传发票记录 attempts={attempts}")


def _quick_detect_uploaded_invoice_in_context(
    context: LocatorContext,
    marker_names: list[str],
    item_selectors: list[str],
    container_selectors: list[str],
    expected_count: int,
    timeout_ms: int,
    interval_ms: int,
) -> bool:
    end_at = perf_counter() + (timeout_ms / 1000)
    while perf_counter() < end_at:
        if _uploaded_invoice_ready_in_context(
            context,
            marker_names,
            item_selectors,
            container_selectors,
            expected_count,
        ):
            return True
        context.wait_for_timeout(interval_ms) if hasattr(context, "wait_for_timeout") else None
    return False


def _abort_duplicate_invoice_task(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task: ReimbursementTaskRecord,
    step_log: StepLogger,
    exc: DuplicateInvoiceDetectedError,
) -> ReimbursementTaskResult:
    _step(logger, step_log, task, "close_electronic_image_tab", "START", "关闭电子影像页签")
    close_started_at = perf_counter()
    try:
        _close_electronic_image_tab(page, selectors, timeout, logger, task.task_id, step_log)
        _step(logger, step_log, task, "close_electronic_image_tab", "SUCCESS", f"已关闭电子影像页签 elapsed_ms={_elapsed_ms(close_started_at)}")
    except Exception as close_exc:
        _step(logger, step_log, task, "close_electronic_image_tab", "FAILED", str(close_exc))
    _step(logger, step_log, task, "close_reimbursement_bill_tab", "START", "关闭当前报销单页签")
    close_bill_started_at = perf_counter()
    try:
        _close_reimbursement_bill_tab(page, selectors, timeout, logger, task.task_id, step_log)
        _step(logger, step_log, task, "close_reimbursement_bill_tab", "SUCCESS", f"已关闭当前报销单页签并返回我要报账 elapsed_ms={_elapsed_ms(close_bill_started_at)}")
    except Exception as close_bill_exc:
        _step(logger, step_log, task, "close_reimbursement_bill_tab", "FAILED", str(close_bill_exc))
    return ReimbursementTaskResult(status="failed", message=str(exc))


def _uploaded_invoice_ready_in_context(
    context: LocatorContext,
    marker_names: list[str],
    item_selectors: list[str],
    container_selectors: list[str],
    expected_count: int,
    attempts: list[str] | None = None,
    context_name: str | None = None,
) -> bool:
    for idx, selector in enumerate(item_selectors):
        if not selector:
            continue
        count = 0
        try:
            count = _count_visible_elements(context, selector)
        except Exception as exc:
            if attempts is not None and context_name is not None:
                attempts.append(f"{context_name}:items[{idx}]=error:{type(exc).__name__}")
            continue
        if attempts is not None and context_name is not None:
            attempts.append(f"{context_name}:items[{idx}]={count}")
        if count >= expected_count:
            return True
    for idx, selector in enumerate(container_selectors):
        try:
            visible = _count_visible_elements(context, selector) > 0
        except Exception as exc:
            if attempts is not None and context_name is not None:
                attempts.append(f"{context_name}:container[{idx}]=error:{type(exc).__name__}")
            continue
        if attempts is not None and context_name is not None:
            attempts.append(f"{context_name}:container[{idx}]={visible}")
        if not visible:
            continue
        for item_idx, item_selector in enumerate(item_selectors):
            if not item_selector:
                continue
            try:
                count = _count_visible_elements(context, item_selector)
            except Exception as exc:
                if attempts is not None and context_name is not None:
                    attempts.append(f"{context_name}:container_items[{idx}][{item_idx}]=error:{type(exc).__name__}")
                continue
            if attempts is not None and context_name is not None:
                attempts.append(f"{context_name}:container_items[{idx}][{item_idx}]={count}")
            if count >= expected_count:
                return True
    for idx, name in enumerate(marker_names):
        try:
            visible = context.get_by_text(name, exact=False).count() > 0
        except Exception as exc:
            if attempts is not None and context_name is not None:
                attempts.append(f"{context_name}:filename[{idx}]=error:{type(exc).__name__}")
            continue
        if attempts is not None and context_name is not None:
            attempts.append(f"{context_name}:filename[{idx}]={visible}")
        if visible:
            return True
    return False


def _recognize_uploaded_invoice(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> None:
    click_timeout = min(timeout, 2500)
    detect_timeout = 10000
    image_context = _resolve_electronic_image_context(page, selectors)
    _timed_substep(
        logger,
        step_log,
        task_id,
        "click_recognize_button",
        "点击识别",
        lambda: _click_locator_fast(image_context, page, selectors["recognize_button"], click_timeout, "未找到可点击的‘识别’按钮"),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "detect_recognize_finished",
        "检测识别完成",
        lambda: _ensure_invoice_recognized(page, selectors, detect_timeout),
    )


def _fill_reimbursement_form(
    page: Page,
    task: ReimbursementTaskRecord,
    selectors: dict[str, str],
    mapping: dict[str, Any],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> None:
    field_timeout = min(timeout, 2500)
    selectors["_detail_reception_type_value"] = str((mapping.get("detail_reception_type") or {}).get("internal", "内部接待"))
    attachment_selectors = [
        selectors["attachment_count_input"],
        'xpath=//label[contains(normalize-space(.),"附件个数")]/following::input[contains(@class,"textbox-text")][1]',
        'xpath=//*[contains(normalize-space(.),"附件个数")]/following::input[contains(@class,"textbox-text")][1]',
    ]
    business_unit_input_selectors = [
        selectors["business_unit_input"],
        'xpath=//label[contains(normalize-space(.),"业务单位")]/following::input[contains(@class,"textbox-text")][1]',
        'xpath=//*[contains(normalize-space(.),"业务单位")]/following::input[contains(@class,"textbox-text")][1]',
        'xpath=//label[contains(normalize-space(.),"业务单位")]/ancestor::td[1]/following-sibling::td[1]//input[1]',
    ]
    business_unit_arrow_selectors = [
        selectors.get("business_unit_arrow", ""),
        'xpath=//label[contains(normalize-space(.),"业务单位")]/following::*[contains(@class,"combo-arrow")][1]',
        'xpath=//*[contains(normalize-space(.),"业务单位")]/following::*[contains(@class,"combo-arrow")][1]',
        'xpath=//label[contains(normalize-space(.),"业务单位")]/ancestor::td[1]/following-sibling::td[1]//*[contains(@class,"adp-combobox")]//*[contains(@class,"combo-arrow")][last()]',
    ]

    _timed_substep(
        logger,
        step_log,
        task_id,
        "fill_attachment_count",
        "填写附件个数",
        lambda: _fill_any_locator_value_in_bill_contexts(page, selectors, attachment_selectors, str(task.attachment_count), field_timeout, "未找到可填写的‘附件个数’输入框"),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "fill_business_unit",
        "填写业务单位",
        lambda: _select_business_unit_in_bill_contexts(
            page,
            selectors,
            selectors.get("business_unit_select", ""),
            business_unit_input_selectors,
            business_unit_arrow_selectors,
            task.business_department,
            field_timeout,
            "未找到可填写的‘业务单位’输入框",
        ),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "fill_payment_purpose",
        "填写付款用途",
        lambda: _fill_any_locator_value_in_bill_contexts(
            page,
            selectors,
            [
                selectors["payment_purpose_input"],
                selectors.get("payment_purpose_input_fallback", ""),
                'xpath=//label[contains(normalize-space(.),"付款用途")]/following::textarea[1]',
                'xpath=//*[contains(normalize-space(.),"付款用途")]/following::textarea[1]',
                'textarea[data-bind*="ROBXDJ_ZY"]',
            ],
            task.payment_purpose,
            field_timeout,
            "未找到可填写的‘付款用途’输入框",
        ),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "open_detail_tab",
        "打开报销明细信息",
        lambda: _click_locator_in_bill_contexts(page, selectors, selectors["detail_tab_select"], field_timeout, "未找到可点击的‘报销明细信息’页签"),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "fill_detail_rows",
        "填写报销明细",
        lambda: _fill_detail_rows(_resolve_bill_form_context(page, selectors), page, task, selectors, field_timeout),
    )


def _close_electronic_image_tab(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> None:
    click_timeout = min(timeout, 2500)
    detect_timeout = min(timeout, 2500)
    _timed_substep(
        logger,
        step_log,
        task_id,
        "click_electronic_image_tab_close",
        "点击关闭电子影像页签",
        lambda: _click_locator_fast(page, page, selectors["electronic_image_tab_close"], click_timeout, "未找到可点击的‘电子影像关闭’按钮"),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "detect_electronic_image_tab_closed",
        "检测电子影像页签已关闭",
        lambda: _ensure_electronic_image_tab_closed(page, selectors, detect_timeout),
    )
    _cache_electronic_image_context(page, None)


def _close_reimbursement_bill_tab(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> None:
    click_timeout = min(timeout, 1200)
    detect_timeout = min(timeout, 1800)
    close_selector = selectors.get("reimbursement_bill_tab_close", 'li.tabs-selected .tabs-close')
    _timed_substep(
        logger,
        step_log,
        task_id,
        "click_reimbursement_bill_tab_close",
        "点击关闭当前报销单页签",
        lambda: _click_locator_fast(page, page, close_selector, click_timeout, "未找到可点击的‘报销单关闭’按钮"),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "confirm_reimbursement_bill_tab_close",
        "确认关闭当前报销单页签",
        lambda: _confirm_reimbursement_bill_tab_close_if_needed(page, selectors, click_timeout),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "detect_reimbursement_bill_tab_closed",
        "检测已返回我要报账列表",
        lambda: _ensure_reimbursement_bill_tab_closed(page, selectors, detect_timeout),
    )


def _confirm_reimbursement_bill_tab_close_if_needed(page: Page, selectors: dict[str, str], timeout: int) -> None:
    confirm_selectors = [
        selectors.get("reimbursement_bill_close_confirm_button", ""),
        'xpath=//div[contains(@class,"messager-button")]//a[.//span[normalize-space(.)="确定"]]',
        'xpath=//div[contains(@class,"messager-button")]//span[normalize-space(.)="确定"]/ancestor::a[1]',
    ]
    attempts: list[str] = []
    dialog_seen = False
    end_at = perf_counter() + (min(timeout, 1200) / 1000)
    while perf_counter() < end_at:
        dialog_visible_any = False
        for context_index, context in enumerate(_candidate_close_confirm_contexts(page, selectors)):
            context_name = _context_debug_name(context, context_index)
            try:
                dialog_visible = _has_visible_close_confirm_dialog(context)
                attempts.append(f"{context_name}:dialog_visible={dialog_visible}")
                dialog_visible_any = dialog_visible_any or dialog_visible
                dialog_seen = dialog_seen or dialog_visible
            except Exception as exc:
                attempts.append(f"{context_name}:dialog_visible=error:{type(exc).__name__}")
                dialog_visible = False
            try:
                buttons = context.locator('.messager-button a')
                button_count = buttons.count()
                attempts.append(f"{context_name}:button_count={button_count}")
                for index in range(button_count):
                    button = buttons.nth(index)
                    visible = _wait_visible(button, 80)
                    attempts.append(f"{context_name}:button[{index}].visible={visible}")
                    if not visible:
                        continue
                    text = ""
                    try:
                        text = (button.inner_text(timeout=120) or "").strip()
                    except Exception:
                        text = ""
                    if not text:
                        try:
                            text = (button.text_content(timeout=120) or "").strip()
                        except Exception:
                            text = ""
                    attempts.append(f"{context_name}:button[{index}].text={text or '<empty>'}")
                    if "确定" not in text:
                        continue
                    try:
                        button.click(timeout=200)
                        attempts.append(f"{context_name}:button[{index}].click=ok")
                    except Exception as exc:
                        attempts.append(f"{context_name}:button[{index}].click=error:{type(exc).__name__}")
                        try:
                            button.click(timeout=200, force=True)
                            attempts.append(f"{context_name}:button[{index}].force_click=ok")
                        except Exception as force_exc:
                            attempts.append(f"{context_name}:button[{index}].force_click=error:{type(force_exc).__name__}")
                            continue
                    page.wait_for_timeout(80)
                    if not _has_visible_close_confirm_dialog(context):
                        attempts.append(f"{context_name}:button[{index}].dialog_closed=true")
                        return
                    attempts.append(f"{context_name}:button[{index}].dialog_closed=false")
            except Exception as exc:
                attempts.append(f"{context_name}:messager_buttons=error:{type(exc).__name__}")
            for selector in confirm_selectors:
                if not selector:
                    continue
                try:
                    locator = context.locator(selector).last
                    visible = _wait_visible(locator, 80)
                    attempts.append(f"{context_name}:selector:{selector}:visible={visible}")
                    if visible:
                        try:
                            locator.click(timeout=200)
                            attempts.append(f"{context_name}:selector:{selector}:click=ok")
                        except Exception as exc:
                            attempts.append(f"{context_name}:selector:{selector}:click=error:{type(exc).__name__}")
                            try:
                                locator.click(timeout=200, force=True)
                                attempts.append(f"{context_name}:selector:{selector}:force_click=ok")
                            except Exception as force_exc:
                                attempts.append(f"{context_name}:selector:{selector}:force_click=error:{type(force_exc).__name__}")
                                continue
                        page.wait_for_timeout(80)
                        if not _has_visible_close_confirm_dialog(context):
                            attempts.append(f"{context_name}:selector:{selector}:dialog_closed=true")
                            return
                        attempts.append(f"{context_name}:selector:{selector}:dialog_closed=false")
                except Exception as exc:
                    attempts.append(f"{context_name}:selector:{selector}:error:{type(exc).__name__}")
                    continue
        if not dialog_visible_any:
            return
        page.wait_for_timeout(40)
    if dialog_seen:
        raise RuntimeError(f"未成功点击关闭报销单确认框的‘确定’按钮 attempts={attempts}")


def _candidate_close_confirm_contexts(page: Page, selectors: dict[str, str]) -> list[LocatorContext]:
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx: LocatorContext | None) -> None:
        if ctx is None:
            return
        marker = id(ctx)
        if marker in seen:
            return
        seen.add(marker)
        contexts.append(ctx)

    add(_get_cached_bill_form_context(page))
    add(_resolve_bill_form_context(page, selectors))
    for context in _candidate_bill_contexts(page, selectors):
        add(context)
    add(page)
    return contexts


def _has_visible_close_confirm_dialog(context: LocatorContext) -> bool:
    try:
        return _wait_visible(context.locator('.messager-button').last, 80)
    except Exception:
        return False


def _save_reimbursement_form(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> None:
    click_timeout = min(timeout, 2500)
    detect_timeout = min(timeout, 4000)
    _timed_substep(
        logger,
        step_log,
        task_id,
        "click_save_button",
        "点击保存",
        lambda: _click_locator_in_bill_contexts(
            page,
            selectors,
            selectors["save_button"],
            click_timeout,
            "未找到可点击的‘保存’按钮",
        ),
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "detect_save_finished",
        "检测保存完成",
        lambda: _ensure_reimbursement_saved(page, selectors, detect_timeout),
    )


def _resolve_reimbursement_context(page: Page, selectors: dict[str, str]) -> LocatorContext:
    cached_context = _get_cached_reimbursement_context(page)
    if cached_context is not None:
        return cached_context
    iframe_selector = selectors.get("my_reimbursement_iframe", 'iframe[id^="rtf_frm_"]')
    try:
        frame_node = page.locator(iframe_selector).first
        if _wait_visible(frame_node, 220):
            handle = frame_node.element_handle()
            if handle is not None:
                frame = handle.content_frame()
                if frame is not None:
                    return frame
    except Exception:
        pass

    return page


def _cache_reimbursement_context(page: Page, context: LocatorContext | None) -> None:
    try:
        setattr(page, "_reimbursement_context", context)
    except Exception:
        pass


def _get_cached_reimbursement_context(page: Page) -> LocatorContext | None:
    try:
        context = getattr(page, "_reimbursement_context", None)
    except Exception:
        return None
    if context is None:
        return None
    marker_selectors = [
        'h2:has-text("新建单据")',
        'text=草稿箱',
        'text=业务招待费报销',
    ]
    for selector in marker_selectors:
        try:
            if _wait_visible(context.locator(selector).first, 50):
                return context
        except Exception:
            continue
    return None


def _resolve_bill_form_context(page: Page, selectors: dict[str, str]) -> LocatorContext:
    cached_context = _get_cached_bill_form_context(page)
    if cached_context is not None:
        return cached_context
    outer_iframe_selectors = [
        selectors.get("bill_page_iframe", ""),
        'iframe[id^="rtf_frm_"][src*="firstlatitude=7453727a-449f-4b2d-8a26-b3d99ba359fc"]',
        'iframe[src*="funcid=7453727a-449f-4b2d-8a26-b3d99ba359fc"]',
    ]
    for selector in outer_iframe_selectors:
        if not selector:
            continue
        try:
            iframe_node = page.locator(selector).first
            if _wait_visible(iframe_node, 600):
                handle = iframe_node.element_handle()
                if handle is not None:
                    frame = handle.content_frame()
                    if frame is not None:
                        nested = _resolve_inner_bill_iframe(frame, selectors)
                        if nested is not None:
                            _cache_bill_form_context(page, nested)
                            return nested
                        _cache_bill_form_context(page, frame)
                        return frame
        except Exception:
            continue

    parent = _resolve_reimbursement_context(page, selectors)
    nested = _resolve_inner_bill_iframe(parent, selectors)
    if nested is not None:
        _cache_bill_form_context(page, nested)
        return nested
    _cache_bill_form_context(page, parent)
    return parent


def _cache_bill_form_context(page: Page, context: LocatorContext | None) -> None:
    try:
        setattr(page, "_bill_form_context", context)
    except Exception:
        pass


def _get_cached_bill_form_context(page: Page) -> LocatorContext | None:
    try:
        context = getattr(page, "_bill_form_context", None)
    except Exception:
        return None
    if context is None:
        return None
    marker_selectors = [
        'text=电子影像',
        'text=报销明细信息',
        'text=保存',
    ]
    for selector in marker_selectors:
        try:
            if _wait_visible(context.locator(selector).first, 50):
                return context
        except Exception:
            continue
    return None


def _resolve_inner_bill_iframe(parent: LocatorContext, selectors: dict[str, str]) -> LocatorContext | None:
    iframe_selectors = [
        selectors.get("bill_form_iframe", ""),
        'iframe#billIframe',
        'iframe[id="billIframe"]',
        'iframe.approvalIframe',
        'iframe[src*="/ro/ywcl/"][src*="firstlatitude=7453727a-449f-4b2d-8a26-b3d99ba359fc"]',
    ]
    for selector in iframe_selectors:
        if not selector:
            continue
        try:
            iframe_node = parent.locator(selector).first
            if _wait_visible(iframe_node, 500):
                handle = iframe_node.element_handle()
                if handle is not None:
                    frame = handle.content_frame()
                    if frame is not None:
                        return frame
        except Exception:
            continue
    return None


def _candidate_bill_contexts(page: Page, selectors: dict[str, str]) -> list[LocatorContext]:
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx):
        if ctx is None:
            return
        marker = id(ctx)
        if marker in seen:
            return
        seen.add(marker)
        contexts.append(ctx)

    add(_resolve_bill_form_context(page, selectors))
    add(_resolve_reimbursement_context(page, selectors))
    try:
        for frame in page.frames:
            try:
                url = getattr(frame, "url", "") or ""
                if (
                    "funcid=7453727a-449f-4b2d-8a26-b3d99ba359fc" in url
                    or "firstlatitude=7453727a-449f-4b2d-8a26-b3d99ba359fc" in url
                    or "7453727a-449f-4b2d-8a26-b3d99ba359fc" in url
                ):
                    add(frame)
            except Exception:
                continue
    except Exception:
        pass
    add(page)
    return contexts


def _candidate_recognition_contexts(page: Page, selectors: dict[str, str]) -> list[LocatorContext]:
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx):
        if ctx is None:
            return
        marker = id(ctx)
        if marker in seen:
            return
        seen.add(marker)
        contexts.append(ctx)

    add(_resolve_electronic_image_context(page, selectors))
    for ctx in _candidate_bill_contexts(page, selectors):
        add(ctx)
    try:
        for frame in page.frames:
            try:
                url = getattr(frame, "url", "") or ""
                if "ImageSSO.aspx" in url or "yxedit" in url or "ImageSystem" in url:
                    add(frame)
            except Exception:
                continue
    except Exception:
        pass
    return contexts


def _click_electronic_image_tab(page: Page, selectors: dict[str, str], timeout: int) -> None:
    selector_candidates = [
        ("config.electronic_image_tab_entry", selectors.get("electronic_image_tab_entry", "")),
        ("name.btnViewImage", 'a[name="btnViewImage"]'),
        ("action.ViewImage", 'a[data-action="ViewImage"]'),
        ("text.button_electronic_image", 'xpath=//a[.//span[contains(@class,"l-btn-text") and normalize-space(.)="电子影像"]]'),
    ]
    contexts: list[tuple[str, LocatorContext]] = []
    seen: set[int] = set()

    def add_context(label: str, ctx: LocatorContext):
        marker = id(ctx)
        if marker in seen:
            return
        seen.add(marker)
        contexts.append((label, ctx))

    add_context("bill_form_context", _resolve_bill_form_context(page, selectors))
    add_context("reimbursement_context", _resolve_reimbursement_context(page, selectors))
    try:
        for idx, frame in enumerate(page.frames):
            url = getattr(frame, "url", "") or ""
            label = f"frame[{idx}]"
            if url:
                label = f"{label}:{url}"
            add_context(label, frame)
    except Exception:
        pass
    add_context("page", page)
    attempts: list[str] = []
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        for context_label, context in contexts:
            for selector_label, selector in selector_candidates:
                if not selector:
                    continue
                locator = _first_visible_locator(context, selector, 180)
                if locator is None:
                    attempts.append(f"{context_label}:{selector_label}:visible=false")
                    continue
                attempts.append(f"{context_label}:{selector_label}:visible=true")
                try:
                    locator.scroll_into_view_if_needed(timeout=160)
                    attempts.append(f"{context_label}:{selector_label}:scroll=ok")
                except Exception:
                    attempts.append(f"{context_label}:{selector_label}:scroll=fail")
                try:
                    locator.click(timeout=220)
                    return
                except Exception as exc:
                    attempts.append(f"{context_label}:{selector_label}:click=fail:{type(exc).__name__}")
                try:
                    locator.click(timeout=220, force=True)
                    return
                except Exception as exc:
                    attempts.append(f"{context_label}:{selector_label}:force_click=fail:{type(exc).__name__}")
        page.wait_for_timeout(50)
    raise RuntimeError(f"未找到可点击的‘电子影像’入口 attempts={attempts}")


def _open_new_bill_menu(page: Page, context: LocatorContext, selectors: dict[str, str], timeout: int) -> None:
    if _is_new_bill_menu_open(context, page, selectors, 160):
        return

    trigger_selectors: list[tuple[str, str]] = [
        ("new_bill_header_container", 'div.pros.subpage'),
        ("new_bill_header_h2", 'div.pros.subpage > h2'),
    ]

    attempts: list[str] = []
    per_wait = 30
    end_at = perf_counter() + (min(timeout, 1800) / 1000)
    while perf_counter() < end_at:
        for label, selector in trigger_selectors:
            if not selector:
                continue
            locator = _first_visible_locator(context, selector, 80)
            try:
                if locator is None:
                    attempts.append(f"{label}:visible=false")
                    continue

                attempts.append(f"{label}:visible=true")
                try:
                    locator.scroll_into_view_if_needed(timeout=120)
                    attempts.append(f"{label}:scroll=ok")
                except Exception as exc:
                    attempts.append(f"{label}:scroll=fail:{type(exc).__name__}")

                try:
                    locator.click(timeout=120)
                    attempts.append(f"{label}:click=ok")
                except Exception as exc:
                    attempts.append(f"{label}:click=fail:{type(exc).__name__}")
                page.wait_for_timeout(per_wait)
                if _is_new_bill_menu_open(context, page, selectors, 100):
                    attempts.append(f"{label}:menu_open_after_click=true")
                    return

                try:
                    locator.click(timeout=120, force=True)
                    attempts.append(f"{label}:force_click=ok")
                except Exception as exc:
                    attempts.append(f"{label}:force_click=fail:{type(exc).__name__}")
                page.wait_for_timeout(per_wait)
                if _is_new_bill_menu_open(context, page, selectors, 100):
                    attempts.append(f"{label}:menu_open_after_force_click=true")
                    return
                try:
                    js_result = context.evaluate(
                        """
                        (sel) => {
                          if (sel.startsWith('xpath=')) return 'skip-xpath-js';
                          const isVisible = (el) => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                          const nodes = [...document.querySelectorAll(sel)].filter(isVisible);
                          if (!nodes.length) return 'no-visible-node';
                          const el = nodes[0];
                          ['mouseover', 'mouseenter', 'mousedown', 'mouseup', 'click'].forEach(type => {
                            el.dispatchEvent(new MouseEvent(type, { bubbles: true }));
                          });
                          return `js-dispatched:${nodes.length}`;
                        }
                        """,
                        selector,
                    )
                    attempts.append(f"{label}:js={js_result}")
                except Exception as exc:
                    attempts.append(f"{label}:js=fail:{type(exc).__name__}")
                page.wait_for_timeout(per_wait)
                if _is_new_bill_menu_open(context, page, selectors, 100):
                    attempts.append(f"{label}:menu_open_after_js=true")
                    return
            except Exception as exc:
                attempts.append(f"{label}:outer_fail:{type(exc).__name__}")
        page.wait_for_timeout(per_wait)

    raise RuntimeError(f"未成功展开‘新建单据’菜单 attempts={attempts}")


def _is_new_bill_menu_open(context: LocatorContext, page: Page, selectors: dict[str, str], timeout: int) -> bool:
    marker_selectors = [
        'li.prosahover',
        'div.prosmore:not(.hide)',
        selectors.get("bill_type_expense", ""),
        selectors.get("bill_subtype_business_entertainment", ""),
    ]
    return _wait_markers_in_context(context, page, marker_selectors, timeout)


def _first_visible_locator(context: LocatorContext, selector: str, timeout_ms: int):
    if not selector:
        return None
    try:
        locator = context.locator(selector)
        count = locator.count()
        for idx in range(count):
            candidate = locator.nth(idx)
            if _wait_visible(candidate, timeout_ms):
                return candidate
    except Exception:
        return None
    return None


def _diagnose_new_bill_menu(page: Page, context: LocatorContext, selectors: dict[str, str]) -> None:
    info = {}
    for key, selector in {
        "menu_visible": 'li.prosahover',
        "submenu_visible": 'div.prosmore:not(.hide)',
        "expense_link": selectors.get("bill_type_expense", ""),
        "business_entertainment_link": selectors.get("bill_subtype_business_entertainment", ""),
        "xselector_combo": '#XSelectorLX + span.combo',
    }.items():
        if not selector:
            continue
        try:
            info[key] = context.locator(selector).count()
        except Exception:
            info[key] = "error"
    if not (info.get("expense_link") or info.get("business_entertainment_link")):
        raise RuntimeError(f"新建单据菜单诊断结果: {info}")


def _click_business_entertainment_link(page: Page, context: LocatorContext, selectors: dict[str, str], timeout: int) -> None:
    candidates = [
        selectors.get("bill_subtype_business_entertainment", ""),
        '[id="7453727a-449f-4b2d-8a26-b3d99ba359fc"]',
        'a.td:has-text("业务招待费报销")',
        'xpath=//a[contains(@class,"td") and normalize-space(.)="业务招待费报销"]',
    ]
    last_error: Exception | None = None
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        for selector in candidates:
            if not selector:
                continue
            locator = _first_visible_locator(context, selector, 250)
            if locator is None:
                continue
            try:
                locator.scroll_into_view_if_needed(timeout=300)
            except Exception:
                pass
            try:
                locator.click(timeout=300)
                return
            except Exception as exc:
                last_error = exc
            try:
                locator.click(timeout=300, force=True)
                return
            except Exception as exc:
                last_error = exc
            page.wait_for_timeout(60)
    if last_error is not None:
        raise last_error
    raise RuntimeError("未找到可点击的‘业务招待费报销’入口")


def _follow_new_page_after_bill_click(page: Page, timeout: int) -> Page:
    end_at = perf_counter() + (min(timeout, 2500) / 1000)
    known_pages = list(page.context.pages)
    while perf_counter() < end_at:
        current_pages = list(page.context.pages)
        for candidate in reversed(current_pages):
            if candidate.is_closed():
                continue
            if candidate not in known_pages:
                try:
                    candidate.wait_for_load_state("domcontentloaded", timeout=300)
                except Exception:
                    pass
                return candidate
        page.wait_for_timeout(50)
    return page


def _resolve_electronic_image_context(page: Page, selectors: dict[str, str]) -> LocatorContext:
    cached_context = _get_cached_electronic_image_context(page)
    if cached_context is not None:
        return cached_context
    frame_context = _resolve_image_system_context(page)
    if frame_context is not None:
        return frame_context
    selectors_to_check = [
        selectors.get("local_upload_button", ""),
        selectors.get("invoice_list_item", ""),
        selectors.get("recognize_button", ""),
    ]
    return _resolve_context_by_markers(page, selectors_to_check, selectors) or _resolve_reimbursement_context(page, selectors)


def _resolve_upload_dialog_context(page: Page, selectors: dict[str, str]) -> LocatorContext | None:
    dialog_host_context = _resolve_electronic_image_context(page, selectors)
    iframe_candidates = [
        selectors.get("upload_dialog_iframe", ""),
        'iframe[id^="layui-layer-iframe"]',
        '.layui-layer.layui-layer-iframe iframe',
    ]
    for selector in iframe_candidates:
        if not selector:
            continue
        try:
            locator = dialog_host_context.locator(selector)
            count = locator.count()
            for index in range(count - 1, -1, -1):
                iframe_node = locator.nth(index)
                if _wait_visible(iframe_node, 120):
                    handle = iframe_node.element_handle()
                    if handle is not None:
                        frame = handle.content_frame()
                        if frame is not None:
                            return frame
        except Exception:
            continue
    return None


def _cache_electronic_image_context(page: Page, context: LocatorContext | None) -> None:
    try:
        setattr(page, "_reimbursement_electronic_image_context", context)
    except Exception:
        pass


def _get_cached_electronic_image_context(page: Page) -> LocatorContext | None:
    try:
        context = getattr(page, "_reimbursement_electronic_image_context", None)
    except Exception:
        return None
    if context is None:
        return None
    marker_selectors = [
        'text=本地上传',
        '#btnInOCR',
        '.sortwrap .thumb',
    ]
    for selector in marker_selectors:
        try:
            if _wait_visible(context.locator(selector).first, 60):
                return context
        except Exception:
            continue
    return None


def _resolve_context_by_markers(page: Page, marker_selectors: list[str], selectors: dict[str, str]) -> LocatorContext | None:
    for candidate in _page_candidates(page):
        for selector in marker_selectors:
            if not selector:
                continue
            try:
                if _wait_visible(candidate.locator(selector).first, 80):
                    return candidate
            except Exception:
                continue
    return None


def _resolve_image_system_context(page: Page) -> LocatorContext | None:
    try:
        frames = list(page.frames)
    except Exception:
        return None
    for frame in reversed(frames):
        try:
            if frame == page.main_frame:
                continue
            url = getattr(frame, "url", "") or ""
            if "ImageSSO.aspx" in url or "yxedit" in url or "ImageSystem" in url:
                return frame
        except Exception:
            continue
    return None


def _open_business_entertainment_bill_direct(context: LocatorContext, config: dict[str, Any], timeout: int) -> None:
    form_url = str(config.get("system", {}).get("business_entertainment_form_url", "")).strip()
    if not form_url:
        raise RuntimeError("未配置业务招待费报销直达 URL")
    if not hasattr(context, "goto"):
        raise RuntimeError("当前上下文不支持直达业务单据页")
    context.goto(form_url, wait_until="domcontentloaded", timeout=timeout)


def _set_upload_files(context: LocatorContext, selector: str, file_paths: list[str], timeout: int) -> None:
    locator = context.locator(selector).first
    if not _wait_visible(locator, min(timeout, 800)):
        raise RuntimeError("上传弹窗中未检测到文件选择控件")
    locator.set_input_files(file_paths, timeout=timeout)


def _fill_locator_value(context: LocatorContext, selector: str, value: str, timeout: int, error_message: str) -> None:
    locator = context.locator(selector).first
    if not _wait_visible(locator, min(timeout, 1800)):
        raise RuntimeError(error_message)
    try:
        locator.click(timeout=300)
    except Exception:
        pass
    locator.fill(value, timeout=timeout)
    try:
        locator.dispatch_event("change")
    except Exception:
        pass


def _fill_locator_value_in_bill_contexts(
    page: Page,
    selectors: dict[str, str],
    selector: str,
    value: str,
    timeout: int,
    error_message: str,
) -> None:
    attempts: list[str] = []
    for idx, context in enumerate(_candidate_bill_contexts(page, selectors)):
        context_name = _context_debug_name(context, idx)
        try:
            locator = context.locator(selector)
            count = locator.count()
            attempts.append(f"{context_name}:count={count}")
            if count == 0:
                continue
            if not _wait_visible(locator.first, min(timeout, 500)):
                attempts.append(f"{context_name}:visible=false")
                continue
            _fill_locator_value(context, selector, value, timeout, error_message)
            return
        except Exception as exc:
            attempts.append(f"{context_name}:error={type(exc).__name__}")
    raise RuntimeError(f"{error_message} attempts={attempts}")


def _fill_any_locator_value_in_bill_contexts(
    page: Page,
    selectors: dict[str, str],
    selector_candidates: list[str],
    value: str,
    timeout: int,
    error_message: str,
) -> None:
    attempts: list[str] = []
    for idx, context in enumerate(_candidate_bill_contexts(page, selectors)):
        context_name = _context_debug_name(context, idx)
        for selector in selector_candidates:
            if not selector:
                continue
            try:
                locator = context.locator(selector)
                count = locator.count()
                attempts.append(f"{context_name}:{selector}:count={count}")
                if count == 0:
                    continue
                if not _wait_visible(locator.first, min(timeout, 500)):
                    attempts.append(f"{context_name}:{selector}:visible=false")
                    continue
                _fill_locator_value(context, selector, value, timeout, error_message)
                return
            except Exception as exc:
                attempts.append(f"{context_name}:{selector}:error={type(exc).__name__}")
    raise RuntimeError(f"{error_message} attempts={attempts}")


def _fill_any_locator_value_in_bill_contexts(
    page: Page,
    selectors: dict[str, str],
    selector_candidates: list[str],
    value: str,
    timeout: int,
    error_message: str,
) -> None:
    attempts: list[str] = []
    for idx, context in enumerate(_candidate_bill_contexts(page, selectors)):
        context_name = _context_debug_name(context, idx)
        for selector in selector_candidates:
            if not selector:
                continue
            try:
                locator = context.locator(selector)
                count = locator.count()
                attempts.append(f"{context_name}:{selector}:count={count}")
                if count == 0:
                    continue
                if not _wait_visible(locator.first, min(timeout, 500)):
                    attempts.append(f"{context_name}:{selector}:visible=false")
                    continue
                _fill_locator_value(context, selector, value, timeout, error_message)
                return
            except Exception as exc:
                attempts.append(f"{context_name}:{selector}:error={type(exc).__name__}")
    raise RuntimeError(f"{error_message} attempts={attempts}")


def _select_combo_value_in_bill_contexts(
    page: Page,
    selectors: dict[str, str],
    input_selector: str,
    arrow_selector: str,
    value: str,
    timeout: int,
    error_message: str,
) -> None:
    attempts: list[str] = []
    option_selectors = [
        f'div.combo-panel:visible .combobox-item:has-text("{value}")',
        f'div.panel.combo-p:visible .combobox-item:has-text("{value}")',
        f'xpath=//div[contains(@class,"combo-panel") and not(contains(@style,"display: none"))]//*[contains(@class,"combobox-item") and normalize-space(.)="{value}"]',
    ]
    for idx, context in enumerate(_candidate_bill_contexts(page, selectors)):
        context_name = _context_debug_name(context, idx)
        try:
            input_locator = context.locator(input_selector)
            input_count = input_locator.count()
            attempts.append(f"{context_name}:input_count={input_count}")
            if input_count == 0:
                continue
            if arrow_selector:
                arrow_locator = context.locator(arrow_selector)
                arrow_count = arrow_locator.count()
                attempts.append(f"{context_name}:arrow_count={arrow_count}")
                if arrow_count > 0 and _wait_visible(arrow_locator.first, 400):
                    try:
                        arrow_locator.first.click(timeout=400)
                    except Exception:
                        try:
                            arrow_locator.first.click(timeout=400, force=True)
                        except Exception:
                            pass
            if _wait_visible(input_locator.first, 400):
                input_locator.first.fill(value, timeout=timeout)
                try:
                    input_locator.first.press("Enter", timeout=300)
                except Exception:
                    pass
            for option_selector in option_selectors:
                option = _first_visible_locator(page, option_selector, 250)
                if option is not None:
                    try:
                        option.click(timeout=300)
                        return
                    except Exception as exc:
                        attempts.append(f"{context_name}:option_click_error={type(exc).__name__}")
            try:
                input_locator.first.press("Tab", timeout=300)
            except Exception:
                pass
            return
        except Exception as exc:
            attempts.append(f"{context_name}:error={type(exc).__name__}")
    raise RuntimeError(f"{error_message} attempts={attempts}")


def _select_any_combo_value_in_bill_contexts(
    page: Page,
    selectors: dict[str, str],
    input_selectors: list[str],
    arrow_selectors: list[str],
    value: str,
    timeout: int,
    error_message: str,
) -> None:
    attempts: list[str] = []
    option_selectors = [
        f'div.combo-panel:visible .combobox-item:has-text("{value}")',
        f'div.panel.combo-p:visible .combobox-item:has-text("{value}")',
        f'xpath=//div[contains(@class,"combo-panel") and not(contains(@style,"display: none"))]//*[contains(@class,"combobox-item") and normalize-space(.)="{value}"]',
    ]
    for idx, context in enumerate(_candidate_bill_contexts(page, selectors)):
        context_name = _context_debug_name(context, idx)
        for input_selector in input_selectors:
            if not input_selector:
                continue
            try:
                input_locator = context.locator(input_selector)
                input_count = input_locator.count()
                attempts.append(f"{context_name}:{input_selector}:input_count={input_count}")
                if input_count == 0:
                    continue
                for arrow_selector in arrow_selectors:
                    if not arrow_selector:
                        continue
                    try:
                        arrow_locator = context.locator(arrow_selector)
                        arrow_count = arrow_locator.count()
                        attempts.append(f"{context_name}:{arrow_selector}:arrow_count={arrow_count}")
                        if arrow_count > 0 and _wait_visible(arrow_locator.first, 300):
                            try:
                                arrow_locator.first.click(timeout=300)
                                break
                            except Exception:
                                try:
                                    arrow_locator.first.click(timeout=300, force=True)
                                    break
                                except Exception:
                                    continue
                    except Exception as exc:
                        attempts.append(f"{context_name}:{arrow_selector}:error={type(exc).__name__}")
                if _wait_visible(input_locator.first, 400):
                    input_locator.first.fill(value, timeout=timeout)
                    try:
                        input_locator.first.press("Enter", timeout=300)
                    except Exception:
                        pass
                for option_selector in option_selectors:
                    option = _first_visible_locator(page, option_selector, 250)
                    if option is not None:
                        try:
                            option.click(timeout=300)
                            if _combo_value_selected(input_locator.first, value):
                                return
                        except Exception as exc:
                            attempts.append(f"{context_name}:option_click_error={type(exc).__name__}")
                try:
                    input_locator.first.press("Tab", timeout=300)
                except Exception:
                    pass
                if _combo_value_selected(input_locator.first, value):
                    return
                attempts.append(f"{context_name}:selected_value_mismatch")
            except Exception as exc:
                attempts.append(f"{context_name}:{input_selector}:error={type(exc).__name__}")
    raise RuntimeError(f"{error_message} attempts={attempts}")


def _select_business_unit_in_bill_contexts(
    page: Page,
    selectors: dict[str, str],
    select_selector: str,
    input_selectors: list[str],
    arrow_selectors: list[str],
    value: str,
    timeout: int,
    error_message: str,
) -> None:
    attempts: list[str] = []
    if select_selector:
        for idx, context in enumerate(_candidate_bill_contexts(page, selectors)):
            context_name = _context_debug_name(context, idx)
            try:
                select_locator = context.locator(select_selector)
                select_count = select_locator.count()
                attempts.append(f"{context_name}:select_count={select_count}")
                if select_count == 0:
                    continue
                result = context.evaluate(
                    """
                    ({ selector, text }) => {
                      const candidates = Array.from(document.querySelectorAll(selector));
                      const target = candidates.find((el) => {
                        const options = Array.from(el.options || []);
                        return options.some((opt) => (opt.text || '').trim() === text.trim());
                      });
                      if (!target) return { ok: false, reason: 'select-not-found' };
                      const option = Array.from(target.options || []).find((opt) => (opt.text || '').trim() === text.trim());
                      if (!option) return { ok: false, reason: 'option-not-found' };
                      target.value = option.value;
                      target.dispatchEvent(new Event('change', { bubbles: true }));
                      const combo = target.nextElementSibling;
                      const textInput = combo ? combo.querySelector('input.combo-text, input.textbox-text') : null;
                      if (textInput) {
                        textInput.value = option.text;
                        textInput.dispatchEvent(new Event('input', { bubbles: true }));
                        textInput.dispatchEvent(new Event('change', { bubbles: true }));
                        textInput.dispatchEvent(new Event('blur', { bubbles: true }));
                      }
                      return { ok: true, optionValue: option.value, optionText: option.text };
                    }
                    """,
                    {"selector": select_selector, "text": value},
                )
                attempts.append(f"{context_name}:select_result={result}")
                if isinstance(result, dict) and result.get("ok"):
                    return
            except Exception as exc:
                attempts.append(f"{context_name}:select_error={type(exc).__name__}")
    try:
        _select_any_combo_value_in_bill_contexts(page, selectors, input_selectors, arrow_selectors, value, timeout, error_message)
        return
    except Exception as exc:
        attempts.append(f"fallback_combo={exc}")
    raise RuntimeError(f"{error_message} attempts={attempts}")


def _click_locator_in_bill_contexts(
    page: Page,
    selectors: dict[str, str],
    selector: str,
    timeout: int,
    error_message: str,
) -> None:
    attempts: list[str] = []
    for idx, context in enumerate(_candidate_bill_contexts(page, selectors)):
        context_name = _context_debug_name(context, idx)
        try:
            locator = context.locator(selector)
            count = locator.count()
            attempts.append(f"{context_name}:count={count}")
            if count == 0:
                continue
            _click_locator_fast(context, page, selector, min(timeout, 1200), error_message)
            return
        except Exception as exc:
            attempts.append(f"{context_name}:error={type(exc).__name__}")
    raise RuntimeError(f"{error_message} attempts={attempts}")


def _combo_value_selected(locator, expected_value: str) -> bool:
    try:
        current_value = (locator.input_value(timeout=200) or "").strip()
        return expected_value.strip() in current_value if current_value else False
    except Exception:
        try:
            current_value = (locator.get_attribute("value") or "").strip()
            return expected_value.strip() in current_value if current_value else False
        except Exception:
            return False


def _fill_detail_cell_value(
    row,
    page: Page,
    input_selector: str,
    cell_selector: str,
    value: str,
    timeout: int,
    attempts: list[str],
    row_label: str,
    field_label: str,
) -> bool:
    input_locator = row.locator(input_selector).first
    if _wait_visible(input_locator, 300):
        try:
            input_locator.fill(value, timeout=timeout)
            attempts.append(f"{row_label}:{field_label}=filled_direct")
            return True
        except Exception as exc:
            attempts.append(f"{row_label}:{field_label}=direct_error:{type(exc).__name__}")
    else:
        attempts.append(f"{row_label}:{field_label}=direct_hidden")

    try:
        cell = row.locator(cell_selector).first
        if _wait_visible(cell, 300):
            try:
                cell.click(timeout=300)
            except Exception:
                cell.click(timeout=300, force=True)
            page.wait_for_timeout(80)
            fallback_inputs = [
                row.locator(f"{cell_selector} input.textbox-text").first,
                row.locator(f"{cell_selector} input[type='text']").first,
                row.locator(f"{cell_selector} textarea").first,
                page.locator(f"{cell_selector} input.textbox-text").first,
                page.locator(f"{cell_selector} input[type='text']").first,
                page.locator(f"{cell_selector} textarea").first,
                page.locator("input.textbox-text:visible").last,
                page.locator("input.datagrid-editable-input:visible").last,
                page.locator("textarea:visible").last,
            ]
            for locator in fallback_inputs:
                if _wait_visible(locator, 250):
                    locator.fill(value, timeout=timeout)
                    attempts.append(f"{row_label}:{field_label}=filled_after_click")
                    return True
            attempts.append(f"{row_label}:{field_label}=input_missing_after_click")
        else:
            attempts.append(f"{row_label}:{field_label}=cell_hidden")
    except Exception as exc:
        attempts.append(f"{row_label}:{field_label}=cell_error:{type(exc).__name__}")
    return False


def _detail_rows_locator(context: LocatorContext, selectors: dict[str, str]):
    row_selector = selectors.get("detail_row", "tr.datagrid-row")
    primary = context.locator('div.datagrid-view2 div.datagrid-body tr.datagrid-row:visible')
    try:
        if primary.count() > 0:
            return primary
    except Exception:
        pass
    secondary = context.locator(f'div.datagrid-body {row_selector}:visible')
    try:
        if secondary.count() > 0:
            return secondary
    except Exception:
        pass
    return context.locator(f'{row_selector}:visible')


def _detail_row_count(context: LocatorContext, selectors: dict[str, str]) -> int:
    try:
        return _detail_rows_locator(context, selectors).count()
    except Exception:
        return 0


def _is_effective_detail_row(row) -> bool:
    try:
        if row.locator('td[field="ROBXMX_GXM2"]').count() > 0:
            return True
        if row.locator('td[field="ROBXMX_ZS2"]').count() > 0:
            return True
        if row.locator('td[field="ROBXMX_XXSM"]').count() > 0:
            return True
    except Exception:
        pass
    try:
        row_html = row.get_attribute("outerHTML") or ""
        return any(field in row_html for field in ("ROBXMX_GXM2", "ROBXMX_ZS2", "ROBXMX_XXSM"))
    except Exception:
        return False


def _effective_detail_row_count(context: LocatorContext, selectors: dict[str, str]) -> int:
    try:
        rows = _detail_rows_locator(context, selectors)
        total = rows.count()
        effective = 0
        for idx in range(total):
            if _is_effective_detail_row(rows.nth(idx)):
                effective += 1
        return effective
    except Exception:
        return 0


def _ensure_detail_row_count(
    context: LocatorContext,
    page: Page,
    selectors: dict[str, str],
    expected_count: int,
    timeout: int,
    attempts: list[str],
) -> None:
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        current_count = _detail_row_count(context, selectors)
        effective_count = _effective_detail_row_count(context, selectors)
        attempts.append(f"detail_row_count={current_count}")
        attempts.append(f"detail_effective_row_count={effective_count}")
        if effective_count == expected_count:
            return
        page.wait_for_timeout(80)
    raise RuntimeError(f"报销明细有效行数未达到预期 expected={expected_count} attempts={attempts}")


def _rebuild_detail_rows(
    context: LocatorContext,
    page: Page,
    task: ReimbursementTaskRecord,
    selectors: dict[str, str],
    timeout: int,
) -> None:
    target_count = len(task.invoices)
    if target_count <= 0:
        raise RuntimeError("未找到可维护的发票明细数据")

    attempts: list[str] = [f"target_count={target_count}"]
    current_count = _detail_row_count(context, selectors)
    current_effective_count = _effective_detail_row_count(context, selectors)
    attempts.append(f"initial_count={current_count}")
    attempts.append(f"initial_effective_count={current_effective_count}")

    delete_selector = selectors.get("detail_delete_button", "")
    add_selector = selectors.get("detail_add_button", "")
    attempts.append(f"delete_selector={delete_selector}")
    attempts.append(f"add_selector={add_selector}")
    try:
        attempts.append(f"delete_button_count={context.locator(delete_selector).count() if delete_selector else 0}")
    except Exception as exc:
        attempts.append(f"delete_button_count_error={type(exc).__name__}")
    try:
        attempts.append(f"add_button_count={context.locator(add_selector).count() if add_selector else 0}")
    except Exception as exc:
        attempts.append(f"add_button_count_error={type(exc).__name__}")

    delete_attempted = False
    while current_count > 0:
        rows = _detail_rows_locator(context, selectors)
        row = rows.first
        try:
            if _wait_visible(row, 250):
                row.click(timeout=250)
                attempts.append("delete_select_row=ok")
        except Exception:
            try:
                row.click(timeout=250, force=True)
                attempts.append("delete_select_row=force_ok")
            except Exception as exc:
                attempts.append(f"delete_select_row=error:{type(exc).__name__}")
        try:
            attempts.append(f"delete_row_class_before={row.get_attribute('class') or ''}")
        except Exception:
            pass
        _click_locator_in_bill_contexts(page, selectors, delete_selector, min(timeout, 1800), "未找到可点击的‘删除’按钮")
        delete_attempted = True
        page.wait_for_timeout(150)
        next_count = _detail_row_count(context, selectors)
        next_effective_count = _effective_detail_row_count(context, selectors)
        attempts.append(f"after_delete_count={next_count}")
        attempts.append(f"after_delete_effective_count={next_effective_count}")
        try:
            next_rows = _detail_rows_locator(context, selectors)
            if next_count > 0:
                next_row = next_rows.first
                attempts.append(f"after_delete_row_class={next_row.get_attribute('class') or ''}")
        except Exception:
            pass
        if next_count >= current_count:
            if current_count == 1 and next_count == 1:
                attempts.append("delete_kept_single_placeholder")
                current_count = 0
                break
            break
        current_count = next_count

    if delete_attempted and current_count == 0:
        attempts.append("baseline_row=none")
    elif not delete_attempted and current_count == 0:
        attempts.append("baseline_row=already_empty")
    else:
        raise RuntimeError(f"未成功清空默认报销明细行 attempts={attempts}")

    add_needed = target_count
    attempts.append(f"add_needed={add_needed}")
    for index in range(max(add_needed, 0)):
        before_add_count = _detail_row_count(context, selectors)
        before_add_effective_count = _effective_detail_row_count(context, selectors)
        attempts.append(f"before_add_count[{index}]={before_add_count}")
        attempts.append(f"before_add_effective_count[{index}]={before_add_effective_count}")
        _click_locator_in_bill_contexts(page, selectors, add_selector, min(timeout, 1800), "未找到可点击的‘增加’按钮")
        page.wait_for_timeout(150)
        attempts.append(f"add_row_index={index}")
        after_add_count = _detail_row_count(context, selectors)
        after_add_effective_count = _effective_detail_row_count(context, selectors)
        attempts.append(f"after_add_count[{index}]={after_add_count}")
        attempts.append(f"after_add_effective_count[{index}]={after_add_effective_count}")

    _ensure_detail_row_count(context, page, selectors, target_count, min(timeout, 3000), attempts)


def _activate_detail_row_editing(
    row,
    page: Page,
    attempts: list[str],
    row_label: str,
) -> None:
    try:
        attempts.append(f"{row_label}:class_before={row.get_attribute('class') or ''}")
    except Exception:
        pass

    activate_selectors = [
        'td[field="ROBXMX_GXM2"] .datagrid-cell',
        'td[field="ROBXMX_GXM2"]',
        'td[field="ROBXMX_ZS2"] .datagrid-cell',
        'td[field="ROBXMX_ZS2"]',
        'td[field="ROBXMX_XXSM"] .datagrid-cell',
        'td[field="ROBXMX_XXSM"]',
    ]
    activated = False
    for selector in activate_selectors:
        try:
            cell = row.locator(selector).first
            if not _wait_visible(cell, 220):
                continue
            try:
                cell.click(timeout=250)
                attempts.append(f"{row_label}:activate_click={selector}")
            except Exception:
                cell.dblclick(timeout=250)
                attempts.append(f"{row_label}:activate_dblclick={selector}")
            page.wait_for_timeout(80)
            activated = True
            if "datagrid-row-editing" in (row.get_attribute("class") or ""):
                break
        except Exception as exc:
            attempts.append(f"{row_label}:activate_error={selector}:{type(exc).__name__}")

    if not activated:
        try:
            row.click(timeout=250, force=True)
            attempts.append(f"{row_label}:activate_row_click")
            page.wait_for_timeout(80)
        except Exception as exc:
            attempts.append(f"{row_label}:activate_row_error:{type(exc).__name__}")

    try:
        attempts.append(f"{row_label}:class_after={row.get_attribute('class') or ''}")
    except Exception:
        pass


def _select_detail_reception_type(
    context: LocatorContext,
    row,
    page: Page,
    selectors: dict[str, str],
    reception_type_value: str,
    attempts: list[str],
    row_label: str,
) -> bool:
    try:
        target_cell = row.locator('td[field="ROBXMX_GXM2"]').first
        if _wait_visible(target_cell, 300):
            try:
                target_cell.click(timeout=300)
                attempts.append(f"{row_label}:reception_cell_click=ok")
            except Exception:
                target_cell.click(timeout=300, force=True)
                attempts.append(f"{row_label}:reception_cell_click=force_ok")
            page.wait_for_timeout(100)
    except Exception as exc:
        attempts.append(f"{row_label}:reception_cell_error:{type(exc).__name__}")

    arrow_candidates = [
        row.locator('td[field="ROBXMX_GXM2"] a.textbox-icon.combo-arrow').first,
        row.locator('td[field="ROBXMX_GXM2"] .textbox-addon-right a.combo-arrow').first,
        context.locator('td[field="ROBXMX_GXM2"] a.textbox-icon.combo-arrow:visible').last,
        context.locator('td[field="ROBXMX_GXM2"] .textbox-addon-right a.combo-arrow:visible').last,
        context.locator('a.textbox-icon.combo-arrow:visible').last,
    ]
    selector_candidate = selectors.get("reception_type_select", "")
    if selector_candidate:
        arrow_candidates.insert(2, context.locator(f"{selector_candidate}:visible").last)

    arrow_clicked = False
    for idx, candidate in enumerate(arrow_candidates):
        try:
            if not _wait_visible(candidate, 220):
                attempts.append(f"{row_label}:reception_arrow[{idx}]=hidden")
                continue
            try:
                candidate.click(timeout=300)
                attempts.append(f"{row_label}:reception_arrow[{idx}]=click_ok")
            except Exception:
                candidate.click(timeout=300, force=True)
                attempts.append(f"{row_label}:reception_arrow[{idx}]=force_click_ok")
            arrow_clicked = True
            page.wait_for_timeout(120)
            break
        except Exception as exc:
            attempts.append(f"{row_label}:reception_arrow[{idx}]=error:{type(exc).__name__}")

    visible_panel = _first_visible_locator(context, 'div.panel.combo-p:visible, div.combo-panel:visible', 300)
    attempts.append(f"{row_label}:reception_panel={'visible' if visible_panel is not None else 'hidden'}")

    option = None
    option_candidates = context.locator('div.panel.combo-p:visible .combobox-item, div.combo-panel:visible .combobox-item')
    try:
        option_count = option_candidates.count()
        attempts.append(f"{row_label}:reception_option_count={option_count}")
        for idx in range(option_count):
            candidate = option_candidates.nth(idx)
            if not _wait_visible(candidate, 150):
                continue
            text = (candidate.inner_text(timeout=200) or "").strip()
            attempts.append(f"{row_label}:reception_option[{idx}]={text}")
            if text == reception_type_value:
                option = candidate
                break
    except Exception as exc:
        attempts.append(f"{row_label}:reception_option_scan_error:{type(exc).__name__}")

    if option is not None:
        option.click(timeout=300)
        page.wait_for_timeout(120)
        attempts.append(f"{row_label}:reception_option_click=ok")
    else:
        attempts.append(f"{row_label}:reception_option_missing")

    combo_text = row.locator(
        'td[field="ROBXMX_GXM2"] input.textbox-text, '
        'td[field="ROBXMX_GXM2"] .combo-text'
    ).first
    if _combo_value_selected(combo_text, reception_type_value):
        attempts.append(f"{row_label}:reception_selected={reception_type_value}")
        return True

    if visible_panel is not None:
        try:
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            page.wait_for_timeout(150)
            attempts.append(f"{row_label}:reception_keyboard=used")
        except Exception as exc:
            attempts.append(f"{row_label}:reception_keyboard_error:{type(exc).__name__}")
    else:
        attempts.append(f"{row_label}:reception_keyboard=skip_no_panel")

    if _combo_value_selected(combo_text, reception_type_value):
        attempts.append(f"{row_label}:reception_selected_by_keyboard={reception_type_value}")
        return True

    if not arrow_clicked:
        attempts.append(f"{row_label}:reception_arrow=hidden")
    else:
        attempts.append(f"{row_label}:reception_verify_failed={reception_type_value}")
    return False


def _fill_detail_rows(
    context: LocatorContext,
    page: Page,
    task: ReimbursementTaskRecord,
    selectors: dict[str, str],
    timeout: int,
) -> None:
    _rebuild_detail_rows(context, page, task, selectors, timeout)
    rows = _detail_rows_locator(context, selectors)
    row_count = _detail_row_count(context, selectors)
    if row_count == 0:
        raise RuntimeError("未检测到可填写的报销明细行")

    filled = 0
    reception_type_value = selectors.get("_detail_reception_type_value", "") or "内部接待"
    reception_selected_count = 0
    attempts: list[str] = [f"row_count={row_count}"]
    for index, invoice in enumerate(task.invoices):
        if index >= row_count:
            break
        row = rows.nth(index)
        attempts.append(f"row[{index}]:start")
        try:
            row_html = row.get_attribute("outerHTML") or ""
            attempts.append(f"row[{index}]:has_gxm2={'ROBXMX_GXM2' in row_html}")
            attempts.append(f"row[{index}]:has_zs2={'ROBXMX_ZS2' in row_html}")
            attempts.append(f"row[{index}]:has_xxsm={'ROBXMX_XXSM' in row_html}")
        except Exception:
            pass
        _activate_detail_row_editing(row, page, attempts, f"row[{index}]")
        try:
            if _select_detail_reception_type(
                context,
                row,
                page,
                selectors,
                reception_type_value,
                attempts,
                f"row[{index}]",
            ):
                filled += 1
                reception_selected_count += 1
        except Exception as exc:
            attempts.append(f"row[{index}]:reception_error:{type(exc).__name__}")
        if invoice.company_count:
            if _fill_detail_cell_value(
                row,
                page,
                f'{selectors["company_count_input"]}, '
                'td[field="ROBXMX_ZS2"] input.textbox-text, '
                'td[field="ROBXMX_ZS2"] .textbox.numberbox input.textbox-text',
                'td[field="ROBXMX_ZS2"]',
                invoice.company_count,
                timeout,
                attempts,
                f"row[{index}]",
                "company_count",
            ):
                filled += 1
        else:
            attempts.append(f"row[{index}]:company_count=skip_empty")
        if invoice.approved_amount:
            if _fill_detail_cell_value(
                row,
                page,
                f'{selectors.get("approved_amount_input", "")}, '
                'td[field="ROBXMX_BXJE"] input.textbox-text, '
                'td[field="ROBXMX_BXJE"] input[type="text"]',
                'td[field="ROBXMX_BXJE"]',
                invoice.approved_amount,
                timeout,
                attempts,
                f"row[{index}]",
                "approved_amount",
            ):
                filled += 1
        else:
            attempts.append(f"row[{index}]:approved_amount=skip_empty")
        if invoice.remark:
            if _fill_detail_cell_value(
                row,
                page,
                f'{selectors["remark_input"]}, '
                'td[field="ROBXMX_XXSM"] input.datagrid-editable-input, '
                'td[field="ROBXMX_XXSM"] input[type="text"]',
                'td[field="ROBXMX_XXSM"]',
                invoice.remark,
                timeout,
                attempts,
                f"row[{index}]",
                "remark",
            ):
                filled += 1
        else:
            attempts.append(f"row[{index}]:remark=skip_empty")
    expected_rows = min(len(task.invoices), row_count)
    if expected_rows > 0 and reception_selected_count == 0:
        raise RuntimeError(f"报销明细行已打开，但接待类型未成功选中 attempts={attempts}")
    if filled == 0:
        raise RuntimeError(f"报销明细行已打开，但未成功填写公司人数或备注 attempts={attempts}")


def _ensure_upload_files_selected(context: LocatorContext, file_paths: list[str], timeout: int) -> None:
    file_names = [Path(path).name for path in file_paths]
    success_selectors = [
        '.state-complete',
        '.upload-state-done',
        '.upload-success',
        '.uploadBtn.state-finish',
        '.uploadBtn.state-confirm',
        'text=上传成功',
        'text=成功',
    ]
    start_button_selector = '.uploadBtn'
    context.wait_for_timeout(80) if hasattr(context, "wait_for_timeout") else None
    end_at = perf_counter() + (min(timeout, 1800) / 1000)
    while perf_counter() < end_at:
        for selector in success_selectors:
            try:
                if _wait_visible(context.locator(selector).first, 180):
                    return
            except Exception:
                continue
        for file_name in file_names:
            try:
                if _wait_visible(context.get_by_text(file_name, exact=False).first, 180):
                    try:
                        if not _wait_visible(context.locator(start_button_selector).first, 120):
                            return
                    except Exception:
                        return
            except Exception:
                continue
        try:
            if _wait_visible(context.locator('.webuploader-queue, .filelist, .upload-list').first, 180):
                try:
                    if not _wait_visible(context.locator(start_button_selector).first, 120):
                        return
                except Exception:
                    return
        except Exception:
            pass
        context.wait_for_timeout(40) if hasattr(context, "wait_for_timeout") else None
    raise RuntimeError(f"上传动作后未检测到明确完成标志，file_names={file_names}")


def _ensure_upload_file_ready(context: LocatorContext, selectors: dict[str, str], timeout: int) -> None:
    marker_selectors = [
        selectors.get("file_input", ""),
        selectors.get("choose_file_button", ""),
        '#filePicker input[type="file"]',
        '#filePicker .webuploader-pick',
    ]
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        for selector in marker_selectors:
            if not selector:
                continue
            try:
                if _wait_visible(context.locator(selector).first, 100):
                    return
            except Exception:
                continue
        context.wait_for_timeout(30) if hasattr(context, "wait_for_timeout") else None
    raise RuntimeError("未检测到已就绪的‘选择文件’控件")


def _trigger_open_add_bill_page_direct(context: LocatorContext, timeout: int) -> None:
    end_at = perf_counter() + (timeout / 1000)
    last_error: Exception | None = None
    while perf_counter() < end_at:
        try:
            result = context.evaluate(
                """
                () => {
                  const jq = window.$ || window.jQuery;
                  const btn = document.querySelector('[data-action="openAddBillPage"]');
                  if (btn && jq) {
                    jq(btn).trigger('click');
                    return 'trigger-hidden-button';
                  }
                  if (btn) {
                    btn.click();
                    return 'click-hidden-button';
                  }
                  const direct = window.openAddBillPage
                    || window.rtf?.allFunc?.allFunc?.openAddBillPage
                    || window.rtf?.allFunc?.openAddBillPage;
                  if (typeof direct === 'function') {
                    direct();
                    return 'call-function';
                  }
                  return 'unavailable';
                }
                """
            )
            if result and result != 'unavailable':
                return
            last_error = RuntimeError(f'openAddBillPage unavailable result={result}')
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise RuntimeError(f'未成功直接触发 openAddBillPage：{last_error}')
    raise RuntimeError('未成功直接触发 openAddBillPage')


def _open_new_bill_dropdown(page: Page, context: LocatorContext, selectors: dict[str, str], timeout: int) -> None:
    if _is_new_bill_dropdown_open(page, selectors, 400):
        return

    arrow_selectors = [
        selectors.get("new_bill_dropdown_arrow", ""),
        '#XSelectorLX + span.combo .combo-arrow',
        'xpath=//select[@id="XSelectorLX"]/following-sibling::span[contains(@class,"combo")]//a[contains(@class,"combo-arrow")]',
    ]

    end_at = perf_counter() + (timeout / 1000)
    last_error: Exception | None = None
    while perf_counter() < end_at:
        try:
            shown = context.evaluate(
                """
                () => {
                  const el = document.querySelector('#XSelectorLX');
                  const jq = window.$ || window.jQuery;
                  if (!el || !jq || typeof jq(el).combobox !== 'function') {
                    return { shown: false, optionCount: 0, panelItemCount: 0 };
                  }
                  jq(el).combobox('showPanel');
                  const data = jq(el).combobox('getData') || [];
                  const panel = jq(el).combobox('panel');
                  const panelItemCount = panel ? panel.find('.combobox-item').length : 0;
                  return { shown: true, optionCount: data.length, panelItemCount };
                }
                """
            )
            if shown and (shown.get('panelItemCount', 0) > 0 or shown.get('optionCount', 0) > 0):
                page.wait_for_timeout(100)
                if _is_new_bill_dropdown_open(page, selectors, 300):
                    return
            if shown:
                last_error = RuntimeError(
                    f"已调用 showPanel，但尚未加载选项 option_count={shown.get('optionCount', 0)} panel_item_count={shown.get('panelItemCount', 0)}"
                )
        except Exception as exc:
            last_error = exc

        for selector in arrow_selectors:
            if not selector:
                continue
            locator = context.locator(selector).first
            try:
                if _wait_visible(locator, 200):
                    locator.click(timeout=250, force=True)
                    page.wait_for_timeout(80)
                    if _is_new_bill_dropdown_open(page, selectors, 250):
                        return
            except Exception as exc:
                last_error = exc

        page.wait_for_timeout(60)

    if last_error is not None:
        raise RuntimeError(f"未成功展开‘新建单据’下拉菜单：{last_error}")
    raise RuntimeError("未成功展开‘新建单据’下拉菜单")


def _ensure_bill_type_options_loaded(page: Page, context: LocatorContext, timeout: int) -> None:
    end_at = perf_counter() + (timeout / 1000)
    last_snapshot: str | None = None
    while perf_counter() < end_at:
        try:
            snapshot = context.evaluate(
                """
                () => {
                  const el = document.querySelector('#XSelectorLX');
                  const jq = window.$ || window.jQuery;
                  if (!el || !jq || typeof jq(el).combobox !== 'function') {
                    return 'combobox-unavailable';
                  }
                  const data = jq(el).combobox('getData') || [];
                  const panel = jq(el).combobox('panel');
                  const panelItemCount = panel ? panel.find('.combobox-item').length : 0;
                  const textbox = jq(el).combobox('textbox');
                  if (data.length === 0 && textbox && textbox.length) {
                    textbox.focus();
                    textbox.trigger(jq.Event('keydown', { keyCode: 40 }));
                  }
                  if (data.length === 0) {
                    try { jq(el).combobox('reload'); } catch (e) {}
                  }
                  return `data=${data.length};panel_items=${panelItemCount}`;
                }
                """
            )
            last_snapshot = str(snapshot)
            if _is_new_bill_dropdown_open(page, {"bill_type_expense": 'text=费用报销类'}, 250):
                return
            if 'data=' in last_snapshot:
                parts = dict(item.split('=') for item in last_snapshot.split(';') if '=' in item)
                if int(parts.get('data', '0')) > 0 or int(parts.get('panel_items', '0')) > 0:
                    return
        except Exception as exc:
            last_snapshot = str(exc)
        page.wait_for_timeout(100)

    raise RuntimeError(f"费用报销类选项未加载完成，diagnostic={last_snapshot}")


def _is_new_bill_dropdown_open(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    indicator_selectors = [
        'div.combo-panel:visible',
        'div.panel.combo-p:visible',
        'div.combo-panel:visible .combobox-item',
        'div.panel.combo-p:visible .combobox-item',
        selectors.get("bill_type_expense", ""),
        'text=费用报销类',
    ]
    return _wait_any_marker(page, indicator_selectors, timeout)


def _ensure_my_reimbursement_page(page: Page, selectors: dict[str, str], timeout: int) -> None:
    if not _is_my_reimbursement_page(page, selectors, timeout):
        raise RuntimeError("未成功进入‘我要报账’页面，未检测到页面到达标志")


def _ensure_business_entertainment_bill_page(page: Page, selectors: dict[str, str], timeout: int) -> None:
    if not _is_business_entertainment_bill_page(page, selectors, timeout):
        raise RuntimeError("未成功进入‘业务招待费报销’单据页，未检测到页面到达标志")


def _is_my_reimbursement_page(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    context = _resolve_reimbursement_context(page, selectors)
    marker_selectors = [
        selectors.get("new_bill_button", ""),
        'h2:has-text("新建单据")',
        'text=费用报销类',
        'text=业务招待费报销',
        'text=草稿箱',
    ]
    return _wait_markers_in_context(context, page, marker_selectors, timeout)


def _is_business_entertainment_bill_page(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    try:
        if "7453727a-449f-4b2d-8a26-b3d99ba359fc" in page.url:
            return True
    except Exception:
        pass
    for candidate in _page_candidates(page):
        try:
            if "7453727a-449f-4b2d-8a26-b3d99ba359fc" in getattr(candidate, "url", ""):
                return True
        except Exception:
            pass
    bill_context = _resolve_bill_form_context(page, selectors)
    reimbursement_context = _resolve_reimbursement_context(page, selectors)
    try:
        if bill_context is reimbursement_context:
            return False
    except Exception:
        pass
    marker_selectors = [
        selectors.get("electronic_image_tab_entry", ""),
        selectors.get("save_button", ""),
        'text=电子影像',
        'text=报销明细信息',
        'text=保存',
        'text=业务招待费报销',
    ]
    return _wait_markers_in_context(bill_context, page, marker_selectors, timeout)


def _is_business_entertainment_bill_page_precheck(page: Page, selectors: dict[str, str]) -> bool:
    try:
        if "7453727a-449f-4b2d-8a26-b3d99ba359fc" in page.url:
            return True
    except Exception:
        pass
    try:
        for candidate in _page_candidates(page):
            try:
                if "7453727a-449f-4b2d-8a26-b3d99ba359fc" in getattr(candidate, "url", ""):
                    return True
            except Exception:
                continue
    except Exception:
        pass
    bill_context = _get_cached_bill_form_context(page)
    if bill_context is None:
        return False
    marker_selectors = [
        selectors.get("electronic_image_tab_entry", ""),
        selectors.get("save_button", ""),
        'text=电子影像',
        'text=报销明细信息',
        'text=保存',
    ]
    return _wait_markers_in_context(bill_context, page, marker_selectors, 120)


def _ensure_electronic_image_page(page: Page, selectors: dict[str, str], timeout: int) -> None:
    if _is_electronic_image_page_precheck(page, selectors, timeout):
        return
    raise RuntimeError("未成功进入电子影像页面")


def _ensure_invoice_recognized(page: Page, selectors: dict[str, str], timeout: int) -> None:
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        if _is_invoice_recognized(page, selectors, 180):
            duplicate_end_at = perf_counter() + 1.5
            while perf_counter() < duplicate_end_at:
                duplicate_message = _detect_duplicate_invoice_message(page, selectors)
                if duplicate_message:
                    raise DuplicateInvoiceDetectedError(duplicate_message)
                page.wait_for_timeout(60)
            return
        page.wait_for_timeout(60)
    raise RuntimeError(_diagnose_invoice_recognition(page, selectors))


def _ensure_reimbursement_saved(page: Page, selectors: dict[str, str], timeout: int) -> None:
    if _is_reimbursement_saved(page, selectors, timeout):
        return
    raise RuntimeError("未检测到报销单保存完成标志")


def _ensure_electronic_image_tab_closed(page: Page, selectors: dict[str, str], timeout: int) -> None:
    end_at = perf_counter() + (timeout / 1000)
    selected_image_tab = page.locator('li.tabs-selected').filter(has_text="电子影像")
    while perf_counter() < end_at:
        try:
            if selected_image_tab.count() == 0:
                return
        except Exception:
            return
        if not _is_electronic_image_page(page, selectors, 120):
            return
        page.wait_for_timeout(50)
    raise RuntimeError("电子影像页签关闭后仍然处于激活状态")


def _is_electronic_image_page(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    if _resolve_image_system_context(page) is not None:
        return True
    markers = [
        selectors.get("local_upload_button", ""),
        selectors.get("recognize_button", ""),
        'text=本地上传',
        'text=识别',
        'text=电子影像',
    ]
    per_try_timeout = min(timeout, 120)
    rounds = max(1, int(max(timeout, 180) / per_try_timeout))
    contexts = _candidate_bill_contexts(page, selectors)
    for _ in range(rounds):
        for context in contexts:
            for selector in markers:
                if not selector:
                    continue
                try:
                    if _wait_visible(context.locator(selector).first, per_try_timeout):
                        return True
                except Exception:
                    continue
        page.wait_for_timeout(25)
    return False


def _is_electronic_image_page_precheck(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    marker_selectors = [
        selectors.get("local_upload_button", ""),
        selectors.get("recognize_button", ""),
        'text=本地上传',
        'text=识别',
        'text=电子影像',
    ]
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx: LocatorContext | None) -> None:
        if ctx is None:
            return
        marker = id(ctx)
        if marker in seen:
            return
        seen.add(marker)
        contexts.append(ctx)

    add(_get_cached_electronic_image_context(page))
    add(_get_cached_bill_form_context(page))
    add(_get_cached_reimbursement_context(page))
    add(page)

    per_try_timeout = min(timeout, 80)
    rounds = max(1, int(max(timeout, 80) / max(per_try_timeout, 1)))
    for _ in range(rounds):
        for context in contexts:
            for selector in marker_selectors:
                if not selector:
                    continue
                try:
                    if _wait_visible(context.locator(selector).first, per_try_timeout):
                        return True
                except Exception:
                    continue
        page.wait_for_timeout(20)
    return False


def _is_reimbursement_saved(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    marker_selectors = [
        selectors.get("save_success_toast", ""),
        selectors.get("saved_bill_marker", ""),
        'text=保存成功',
        'text=业务招待费报销',
    ]
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        for context in _candidate_bill_contexts(page, selectors):
            if _wait_markers_in_context(context, page, marker_selectors, 180):
                return True
        if _wait_any_marker(page, marker_selectors, 180):
            return True
        page.wait_for_timeout(50)
    return False


def _ensure_upload_dialog_open(page: Page, selectors: dict[str, str], timeout: int) -> None:
    if _is_upload_dialog_open(page, selectors, timeout):
        return
    raise RuntimeError(_diagnose_upload_dialog(page, selectors))


def _is_upload_dialog_open(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    dialog_host_context = _resolve_electronic_image_context(page, selectors)
    dialog_selector = selectors.get("upload_dialog", "")
    if dialog_selector:
        try:
            if _count_visible_elements(dialog_host_context, dialog_selector) > 0:
                return True
        except Exception:
            pass
    iframe_selector = selectors.get("upload_dialog_iframe", 'iframe[id^="layui-layer-iframe"]')
    try:
        if _count_visible_elements(dialog_host_context, iframe_selector) > 0:
            return True
    except Exception:
        pass
    return _resolve_upload_dialog_context(page, selectors) is not None


def _ensure_reimbursement_bill_tab_closed(page: Page, selectors: dict[str, str], timeout: int) -> None:
    end_at = perf_counter() + (timeout / 1000)
    selected_bill_tab = page.locator('li.tabs-selected').filter(has_text="业务招待费报销")
    while perf_counter() < end_at:
        try:
            if selected_bill_tab.count() == 0 and _is_my_reimbursement_page(page, selectors, 120):
                return
        except Exception:
            if _is_my_reimbursement_page(page, selectors, 120):
                return
        page.wait_for_timeout(40)
    raise RuntimeError("关闭报销单页签后未返回我要报账列表")


def _diagnose_upload_dialog(page: Page, selectors: dict[str, str]) -> str:
    attempts: list[str] = []
    dialog_host_context = _resolve_electronic_image_context(page, selectors)

    outer_checks = [
        ("dialog", selectors.get("upload_dialog", "")),
        ("dialog_iframe", selectors.get("upload_dialog_iframe", 'iframe[id^="layui-layer-iframe"]')),
        ("shade", '.layui-layer-shade'),
    ]
    for label, selector in outer_checks:
        if not selector:
            continue
        try:
            locator = dialog_host_context.locator(selector)
            count = locator.count()
            attempts.append(f"{label}:count={count}")
            if count > 0:
                try:
                    visible = _wait_visible(locator.first, 200)
                    attempts.append(f"{label}:visible={visible}")
                except Exception as exc:
                    attempts.append(f"{label}:visible=error:{type(exc).__name__}")
        except Exception as exc:
            attempts.append(f"{label}:count=error:{type(exc).__name__}")

    upload_context = _resolve_upload_dialog_context(page, selectors)
    if upload_context is None:
        attempts.append("upload_iframe_context:none")
    else:
        attempts.append("upload_iframe_context:resolved")
        inner_checks = [
            ("file_input", selectors.get("file_input", "")),
            ("start_upload_button", selectors.get("start_upload_button", "")),
            ("choose_file_button", selectors.get("choose_file_button", "")),
        ]
        for label, selector in inner_checks:
            if not selector:
                continue
            try:
                locator = upload_context.locator(selector)
                count = locator.count()
                attempts.append(f"{label}:count={count}")
                if count > 0:
                    try:
                        visible = _wait_visible(locator.first, 200)
                        attempts.append(f"{label}:visible={visible}")
                    except Exception as exc:
                        attempts.append(f"{label}:visible=error:{type(exc).__name__}")
            except Exception as exc:
                attempts.append(f"{label}:count=error:{type(exc).__name__}")

    return f"未成功打开上传弹窗 attempts={attempts}"


def _wait_markers_in_context(context: LocatorContext, page: Page, marker_selectors: list[str], timeout: int) -> bool:
    per_try_timeout = min(timeout, 400)
    rounds = max(1, int(timeout / per_try_timeout))
    for _ in range(rounds):
        for selector in marker_selectors:
            if not selector:
                continue
            try:
                if _wait_visible(context.locator(selector).first, per_try_timeout):
                    return True
            except Exception:
                continue
        page.wait_for_timeout(60)
    return False


def _wait_any_marker(page: Page, marker_selectors: list[str], timeout: int) -> bool:
    per_try_timeout = min(timeout, 400)
    rounds = max(1, int(timeout / per_try_timeout))
    for _ in range(rounds):
        for candidate in _page_candidates(page):
            for selector in marker_selectors:
                if not selector:
                    continue
                try:
                    if _wait_visible(candidate.locator(selector).first, per_try_timeout):
                        return True
                except Exception:
                    continue
        page.wait_for_timeout(60)
    return False


def _is_invoice_recognized(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    toast_markers = [
        selectors.get("recognize_success_toast", ""),
        '.layui-layer.layui-layer-msg .layui-layer-content:has-text("识别成功")',
        'text=识别成功！',
        'text=识别成功',
    ]
    value_markers = [
        '#InvoiceNUM input[data-bind="InvoiceNUM"]',
        selectors.get("recognize_success_marker", ""),
        'input[data-bind="InvoiceNUM"]',
    ]
    contexts = _candidate_recognition_contexts(page, selectors)
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        for context in contexts:
            for selector in toast_markers:
                if not selector:
                    continue
                try:
                    if _wait_visible(context.locator(selector).first, 150):
                        return True
                except Exception:
                    continue
            for selector in value_markers:
                if not selector:
                    continue
                try:
                    locator = context.locator(selector)
                    if locator.count() > 0 and _locator_has_non_empty_value(locator.first):
                        return True
                except Exception:
                    continue
        page.wait_for_timeout(80)
    return False


def _locator_has_non_empty_value(locator) -> bool:
    try:
        value = (locator.input_value(timeout=120) or "").strip()
        if value:
            return True
    except Exception:
        pass
    try:
        value = (locator.get_attribute("value", timeout=120) or "").strip()
        if value:
            return True
    except Exception:
        pass
    try:
        text = (locator.text_content(timeout=120) or "").strip()
        if text:
            return True
    except Exception:
        pass
    return False


def _detect_duplicate_invoice_message(page: Page, selectors: dict[str, str]) -> str | None:
    duplicate_selectors = [
        selectors.get("duplicate_invoice_marker", ""),
        '#txtDuplicate',
        '#txtDuplicate span',
        'text=发票重复',
    ]
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx: LocatorContext | None) -> None:
        if ctx is None:
            return
        marker = id(ctx)
        if marker in seen:
            return
        seen.add(marker)
        contexts.append(ctx)

    add(_get_cached_electronic_image_context(page))
    add(_resolve_image_system_context(page))
    for context in _candidate_recognition_contexts(page, selectors):
        add(context)

    for context in contexts:
        for selector in duplicate_selectors:
            if not selector:
                continue
            try:
                locator = context.locator(selector).first
                if _wait_visible(locator, 120):
                    text = ""
                    try:
                        text = (locator.inner_text(timeout=120) or "").strip()
                    except Exception:
                        text = ""
                    if not text:
                        try:
                            text = (locator.text_content(timeout=120) or "").strip()
                        except Exception:
                            text = ""
                    if "发票重复" in text:
                        return f"{text}，已中止当前报销单录入"
                    if selector in {"#txtDuplicate", "#txtDuplicate span", 'text=发票重复'}:
                        return "发票重复，已中止当前报销单录入"
            except Exception:
                continue
    return None


def _diagnose_invoice_recognition(page: Page, selectors: dict[str, str]) -> str:
    attempts: list[str] = []
    marker_checks = [
        ("recognize_success_toast", selectors.get("recognize_success_toast", "") or '.layui-layer.layui-layer-msg .layui-layer-content'),
        ("invoice_num_container", '#InvoiceNUM'),
        ("invoice_num_bound", '#InvoiceNUM input[data-bind="InvoiceNUM"]'),
        ("invoice_num_input", selectors.get("recognize_success_marker", "") or 'input[data-bind="InvoiceNUM"]'),
        ("recognize_button", selectors.get("recognize_button", "")),
        ("duplicate_invoice_marker", selectors.get("duplicate_invoice_marker", "") or '#txtDuplicate'),
    ]
    for idx, context in enumerate(_candidate_recognition_contexts(page, selectors)):
        context_name = _context_debug_name(context, idx)
        for label, selector in marker_checks:
            if not selector:
                continue
            try:
                locator = context.locator(selector)
                count = locator.count()
                attempts.append(f"{context_name}:{label}:count={count}")
                if count > 0:
                    try:
                        visible = _wait_visible(locator.first, 200)
                        attempts.append(f"{context_name}:{label}:visible={visible}")
                    except Exception as exc:
                        attempts.append(f"{context_name}:{label}:visible=error:{type(exc).__name__}")
            except Exception as exc:
                attempts.append(f"{context_name}:{label}:count=error:{type(exc).__name__}")
    return f"未检测到发票识别完成标志 attempts={attempts}"


def _page_candidates(page: Page):
    candidates: list[Any] = [page]
    try:
        candidates.extend(frame for frame in page.frames if frame != page.main_frame)
    except Exception:
        pass
    return candidates


def _context_debug_name(context: LocatorContext, index: int) -> str:
    try:
        if hasattr(context, "main_frame"):
            return "page"
        url = getattr(context, "url", "")
        if url:
            return f"frame[{index}]:{url}"
    except Exception:
        pass
    return f"context[{index}]"


def _attempt_finance_share_activation(page: Page, action, finance_ready_selectors: list[str], timeout: int) -> Page | None:
    before_pages = list(page.context.pages)
    action()

    for _ in range(4):
        page.wait_for_timeout(140)
        for candidate in reversed(page.context.pages):
            if candidate.is_closed():
                continue
            try:
                candidate.wait_for_load_state("domcontentloaded", timeout=300)
            except Exception:
                pass
            if _is_finance_share_page(candidate, finance_ready_selectors):
                return candidate

    if len(page.context.pages) > len(before_pages):
        for candidate in reversed(page.context.pages):
            if candidate not in before_pages and not candidate.is_closed():
                return candidate

    return None


def _safe_click_target(target, timeout: int, force: bool = False) -> None:
    target.click(timeout=timeout, force=force)


def _visible_tree_node(page: Page, text: str):
    return page.locator('div.tree-node:visible').filter(has=page.locator('span.tree-title', has_text=text)).first


def _ensure_tree_node_expanded(page: Page, text: str, timeout: int) -> None:
    node = _visible_tree_node(page, text)
    node.wait_for(state='visible', timeout=timeout)
    hit = node.locator('span.tree-hit').first
    if hit.count() == 0:
        return

    try:
        hit.click(timeout=timeout)
        page.wait_for_timeout(100)
    except Exception:
        pass

    try:
        clazz = hit.get_attribute('class') or ''
        if 'tree-collapsed' in clazz:
            hit.click(timeout=timeout)
            page.wait_for_timeout(100)
    except Exception:
        pass


def _click_tree_title_fast(page: Page, text: str, timeout: int) -> None:
    last_error: Exception | None = None
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        title_locator = _visible_tree_node(page, text).locator('span.tree-title').first
        try:
            if _wait_visible(title_locator, 300):
                title_locator.click(timeout=300)
                return
        except Exception as exc:
            last_error = exc
        page.wait_for_timeout(60)
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"未找到可点击的树菜单节点：{text}")


def _click_go_reimbursement_fast(page: Page, selector: str, timeout: int) -> None:
    _click_locator_fast(page, page, selector, timeout, "未找到可点击的‘我要报账’按钮")


def _click_locator_fast(context: LocatorContext, page: Page, selector: str, timeout: int, error_message: str) -> None:
    last_error: Exception | None = None
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        locator = context.locator(selector).first
        try:
            if _wait_visible(locator, 300):
                locator.click(timeout=300)
                return
        except Exception as exc:
            last_error = exc
        page.wait_for_timeout(60)
    if last_error is not None:
        raise last_error
    raise RuntimeError(error_message)


def _click_latest_visible_element(context: LocatorContext, selector: str) -> bool:
    try:
        return bool(
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
                  const nodes = Array.from(document.querySelectorAll(selector)).filter(isVisible);
                  const target = nodes[nodes.length - 1];
                  if (!target) return false;
                  target.click();
                  return true;
                }
                """,
                selector,
            )
        )
    except Exception:
        return False


def _count_visible_elements(context: LocatorContext, selector: str) -> int:
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


def _hover_locator_fast(context: LocatorContext, page: Page, selector: str, timeout: int, error_message: str) -> None:
    last_error: Exception | None = None
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        locator = context.locator(selector).first
        try:
            if _wait_visible(locator, 300):
                locator.hover(timeout=300)
                return
        except Exception as exc:
            last_error = exc
        page.wait_for_timeout(60)
    if last_error is not None:
        raise last_error
    raise RuntimeError(error_message)


def _wait_iam_login_state(username_locator, finance_locator, timeout_ms: int) -> str:
    interval_ms = 250
    elapsed_ms = 0
    while elapsed_ms <= timeout_ms:
        if _wait_visible(finance_locator, 250):
            return "finance"
        if _wait_visible(username_locator, 250):
            return "username"
        elapsed_ms += interval_ms
    return "timeout"


def _ensure_visible(locator, timeout_ms: int, error_message: str) -> None:
    if not _wait_visible(locator, timeout_ms):
        raise RuntimeError(error_message)


def _click_optional(locator) -> None:
    try:
        locator.click(force=True)
    except Exception:
        pass


def _activate_by_keyboard(page, locator) -> None:
    locator.focus()
    page.keyboard.press("Enter")


def _is_finance_share_page(page: Page, selectors: list[str]) -> bool:
    try:
        if "fssc.fsg.inner" in page.url.lower():
            return True
    except Exception:
        pass
    for selector in selectors:
        if not selector:
            continue
        try:
            if _wait_visible(page.locator(selector).first, 200):
                return True
        except Exception:
            continue
    return False


def _wait_visible(locator, timeout_ms: int) -> bool:
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
        return True
    except PlaywrightTimeoutError:
        return False


def _timed_batch_step(logger: logging.Logger, step_name: str, message: str, action) -> None:
    logger.info(f"[BATCH] [{step_name}] START {message}")
    started_at = perf_counter()
    action()
    logger.info(f"[BATCH] [{step_name}] SUCCESS {message} elapsed_ms={_elapsed_ms(started_at)}")


def _timed_substep(
    logger: logging.Logger,
    step_log: StepLogger,
    task_id: str,
    step_name: str,
    message: str,
    action,
) -> None:
    logger.info(f"[TASK {task_id}] [{step_name}] START {message}")
    step_log(task_id, step_name, f"START {message}")
    started_at = perf_counter()
    try:
        action()
    except Exception as first_error:
        retry_message = f"RETRY {message} delay_ms=500 first_error={type(first_error).__name__}"
        logger.info(f"[TASK {task_id}] [{step_name}] {retry_message}")
        step_log(task_id, step_name, retry_message)
        sleep(0.5)
        action()
    elapsed = _elapsed_ms(started_at)
    logger.info(f"[TASK {task_id}] [{step_name}] SUCCESS {message} elapsed_ms={elapsed}")
    step_log(task_id, step_name, f"SUCCESS {message} elapsed_ms={elapsed}")


def _elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


def _step(
    logger: logging.Logger,
    step_log: StepLogger,
    task: ReimbursementTaskRecord,
    step_name: str,
    status: str,
    message: str,
) -> None:
    logger.info(f"[TASK {task.task_id}] [{step_name}] {status} {message}")
    step_log(task.task_id, step_name, f"{status} {message}")


__all__ = [
    "ReimbursementFillFlow",
    "capture_screenshot",
    "initialize_batch_session",
    "reset_task_context",
    "run_task",
]
