from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter, sleep
from typing import Any

from playwright.sync_api import Page

from automation.core.actions import (
    click_latest_visible_element as _click_latest_visible_element_base,
    click_locator_fast as _click_locator_fast_base,
    fill_first_matching_locator as _fill_first_matching_locator_base,
    fill_locator_value as _fill_locator_value_base,
)
from automation.core.contexts import (
    append_unique_context as _append_unique_context,
    cache_browser_context_value,
    candidate_contexts_for_selector as _candidate_contexts_for_selector_base,
    get_cached_page_context,
    resolve_context_by_markers as _resolve_context_by_markers_base,
    resolve_first_visible_frame_context,
    resolve_selector_context as _resolve_selector_context_base,
)
from automation.core.waits import (
    count_visible_elements as _count_visible_elements_base,
    ensure_visible as _ensure_visible_base,
    locator_has_non_empty_value as _locator_has_non_empty_value_base,
    wait_visible_bool as _wait_visible_base,
)
from automation.core.ui_patterns import (
    click_dialog_button_if_needed,
    has_visible_dialog,
    wait_for_selected_tab_closed as _wait_for_selected_tab_closed_base,
    wait_for_tab_closed_and_state as _wait_for_tab_closed_and_state_base,
)
from automation.runtime.steps import (
    StepLogger,
    elapsed_ms as _elapsed_ms,
    log_task_step as _step,
    run_batch_step as _timed_batch_step,
    run_task_substep as _timed_substep,
)
from flows.reimbursement_fill.cleanup import (
    diagnose_cleanup_state as _diagnose_cleanup_state_base,
    select_cleanup_working_page as _select_cleanup_working_page_base,
)
from flows.reimbursement_fill.bill_rules import (
    bill_page_markers as _bill_page_markers_base,
    bill_subtype_candidates as _bill_subtype_candidates_base,
    bill_tab_click_selector_candidates as _bill_tab_click_selector_candidates_base,
    bill_tab_selector_candidates as _bill_tab_selector_candidates_base,
    dedupe_selectors as _dedupe_selectors_base,
    detail_button_selector_candidates as _detail_button_selector_candidates_base,
    is_city_transport_bill as _is_city_transport_bill_base,
    resolve_task_bill_subtype as _resolve_task_bill_subtype_base,
)
from flows.reimbursement_fill.bill_creation import (
    click_bill_subtype_link as _click_bill_subtype_link_base,
    diagnose_new_bill_menu as _diagnose_new_bill_menu_base,
    first_visible_locator as _first_visible_locator_base,
    follow_new_page_after_bill_click as _follow_new_page_after_bill_click_base,
    is_new_bill_menu_open as _is_new_bill_menu_open_base,
    open_new_bill_menu as _open_new_bill_menu_base,
)
from flows.reimbursement_fill.contexts import (
    cache_active_working_page as _cache_active_working_page_base,
    cache_bill_form_context as _cache_bill_form_context_base,
    cache_bill_outer_context as _cache_bill_outer_context_base,
    cache_electronic_image_context as _cache_electronic_image_context_base,
    cache_reimbursement_context as _cache_reimbursement_context_base,
    context_debug_name as _context_debug_name_base,
    get_cached_active_working_page as _get_cached_active_working_page_base,
    get_cached_bill_form_context as _get_cached_bill_form_context_base,
    get_cached_bill_outer_context as _get_cached_bill_outer_context_base,
    get_cached_electronic_image_context as _get_cached_electronic_image_context_base,
    get_cached_reimbursement_context as _get_cached_reimbursement_context_base,
    page_candidates as _page_candidates_base,
)
from flows.reimbursement_fill.image_upload import (
    diagnose_upload_dialog as _diagnose_upload_dialog_base,
    ensure_upload_file_ready as _ensure_upload_file_ready_base,
    ensure_upload_files_selected as _ensure_upload_files_selected_base,
    set_upload_files as _set_upload_files_base,
)
from flows.reimbursement_fill.invoice_recognition import (
    observe_recognition_outcome as _observe_recognition_outcome_base,
)
from flows.reimbursement_fill.navigation import (
    activate_by_keyboard as _activate_by_keyboard_base,
    attempt_finance_share_activation as _attempt_finance_share_activation_base,
    click_go_reimbursement_fast as _click_go_reimbursement_fast_base,
    click_optional as _click_optional_base,
    click_tree_title_fast as _click_tree_title_fast_base,
    ensure_tree_node_expanded as _ensure_tree_node_expanded_base,
    is_finance_share_page as _is_finance_share_page_base,
    safe_click_target as _safe_click_target_base,
    visible_tree_node as _visible_tree_node_base,
    wait_iam_login_state as _wait_iam_login_state_base,
)
from flows.reimbursement_fill.page_state import (
    ensure_electronic_image_page as _ensure_electronic_image_page_base,
    ensure_my_reimbursement_page as _ensure_my_reimbursement_page_base,
    ensure_reimbursement_bill_tab_closed as _ensure_reimbursement_bill_tab_closed_base,
    ensure_reimbursement_saved as _ensure_reimbursement_saved_base,
    ensure_target_reimbursement_bill_page as _ensure_target_reimbursement_bill_page_base,
    ensure_upload_dialog_open as _ensure_upload_dialog_open_base,
    has_selected_bill_tab_title as _has_selected_bill_tab_title_base,
    has_selected_bill_tab_title_fast as _has_selected_bill_tab_title_fast_base,
    is_electronic_image_page as _is_electronic_image_page_base,
    is_electronic_image_page_precheck as _is_electronic_image_page_precheck_base,
    is_fast_clean_reimbursement_state as _is_fast_clean_reimbursement_state_base,
    is_my_reimbursement_page as _is_my_reimbursement_page_base,
    is_reimbursement_saved as _is_reimbursement_saved_base,
    is_target_reimbursement_bill_page as _is_target_reimbursement_bill_page_base,
    is_target_reimbursement_bill_page_precheck as _is_target_reimbursement_bill_page_precheck_base,
    is_upload_dialog_open as _is_upload_dialog_open_base,
    wait_for_selected_bill_tab_title as _wait_for_selected_bill_tab_title_base,
)
from flows.reimbursement_fill.task_loader import load_tasks, validate_tasks
from flows.reimbursement_fill.task_model import ReimbursementTaskRecord, ReimbursementTaskResult


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

    def build_failed_result(self, message: str):
        return ReimbursementTaskResult(status="failed", message=message)


def initialize_batch_session(page, config: dict[str, Any], logger: logging.Logger) -> None:
    timeout = int(config["system"].get("timeout_ms", 15000))
    selectors = config.get("selectors", {})
    selectors["_context_hints"] = config.get("selector_contexts", {})
    logger.info("[BATCH] [open_iam_panel] START 打开 IAM 面板")
    started_at = perf_counter()
    page.goto(config["system"]["base_url"], wait_until="domcontentloaded")
    logger.info(f"[BATCH] [open_iam_panel] SUCCESS IAM 面板已打开 elapsed_ms={_elapsed_ms(started_at)}")
    _login_iam(page, config, logger)
    _cache_active_working_page(page, page)

    logger.info("[BATCH] [open_finance_share] START 进入财务共享")
    started_at = perf_counter()
    working_page = _open_finance_share(page, config, selectors, timeout)
    _cache_active_working_page(page, working_page)
    logger.info(f"[BATCH] [open_finance_share] SUCCESS 已进入财务共享 elapsed_ms={_elapsed_ms(started_at)}")

    logger.info("[BATCH] [open_my_reimbursement] START 进入我要报账")
    started_at = perf_counter()
    _open_my_reimbursement(working_page, selectors, timeout, logger, "BATCH", lambda *_args: None)
    _cache_active_working_page(page, working_page)
    try:
        _cache_reimbursement_context(working_page, _resolve_reimbursement_context(working_page, selectors))
    except Exception:
        pass
    logger.info(f"[BATCH] [open_my_reimbursement] SUCCESS 已进入我要报账 elapsed_ms={_elapsed_ms(started_at)}")


def run_task(page, config: dict[str, Any], task: ReimbursementTaskRecord, logger: logging.Logger, step_log: StepLogger) -> ReimbursementTaskResult:
    timeout = int(config["system"].get("timeout_ms", 15000))
    selectors = config.get("selectors", {})
    selectors["_context_hints"] = config.get("selector_contexts", {})
    working_page = page
    try:
        _step(logger, step_log, task, "resolve_task_entry_page", "START", "定位当前任务入口页面")
        started_at = perf_counter()
        working_page, entry_state, entry_message = _resolve_task_entry_page(page, selectors)
        _step(
            logger,
            step_log,
            task,
            "resolve_task_entry_page",
            "SUCCESS",
            f"{entry_message} state={entry_state} elapsed_ms={_elapsed_ms(started_at)}",
        )
        _step(logger, step_log, task, "ensure_my_reimbursement_entry", "START", "确认当前位于我要报账页面")
        started_at = perf_counter()
        _ensure_my_reimbursement_page(working_page, selectors, min(timeout, 300))
        try:
            _cache_reimbursement_context(working_page, _resolve_reimbursement_context(working_page, selectors))
        except Exception:
            pass
        _cache_active_working_page(page, working_page)
        _step(
            logger,
            step_log,
            task,
            "ensure_my_reimbursement_entry",
            "SUCCESS",
            f"当前位于我要报账页面 elapsed_ms={_elapsed_ms(started_at)}",
        )

        bill_subtype = _resolve_task_bill_subtype(task, config.get("mapping", {}))
        _step(logger, step_log, task, "create_reimbursement_bill", "START", f"创建{bill_subtype}单据")
        started_at = perf_counter()
        working_page = _create_reimbursement_bill(
            working_page,
            config,
            selectors,
            config.get("mapping", {}),
            task,
            timeout,
            logger,
            task.task_id,
            step_log,
        )
        _cache_active_working_page(page, working_page)
        _step(
            logger,
            step_log,
            task,
            "create_reimbursement_bill",
            "SUCCESS",
            f"已进入{bill_subtype}单据页 elapsed_ms={_elapsed_ms(started_at)}",
        )

        _step(logger, step_log, task, "open_electronic_image_tab", "START", "打开电子影像")
        started_at = perf_counter()
        _open_electronic_image_tab(
            working_page,
            selectors,
            timeout,
            logger,
            task.task_id,
            step_log,
            bill_subtype=bill_subtype,
        )
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
            return _abort_duplicate_invoice_task(
                working_page,
                selectors,
                timeout,
                logger,
                task,
                step_log,
                exc,
                config["paths"]["screenshot_dir"],
            )
        _step(logger, step_log, task, "detect_uploaded_invoice", "SUCCESS", f"已检测到上传发票 elapsed_ms={_elapsed_ms(started_at)}")

        _step(logger, step_log, task, "recognize_uploaded_invoice", "START", "识别已上传发票")
        started_at = perf_counter()
        try:
            _recognize_uploaded_invoice(working_page, selectors, timeout, logger, task.task_id, step_log)
        except DuplicateInvoiceDetectedError as exc:
            _step(logger, step_log, task, "recognize_uploaded_invoice", "FAILED", str(exc))
            return _abort_duplicate_invoice_task(
                working_page,
                selectors,
                timeout,
                logger,
                task,
                step_log,
                exc,
                config["paths"]["screenshot_dir"],
            )
        _step(logger, step_log, task, "recognize_uploaded_invoice", "SUCCESS", f"已完成发票识别 elapsed_ms={_elapsed_ms(started_at)}")

        if _is_city_transport_bill(task, config.get("mapping", {})):
            _timed_substep(
                logger,
                step_log,
                task.task_id,
                "wait_after_recognize_success",
                "等待识别成功结果稳定",
                lambda: working_page.wait_for_timeout(1000),
            )

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
        _cache_active_working_page(page, working_page)
        _step(logger, step_log, task, "close_reimbursement_bill_tab", "SUCCESS", f"已关闭当前报销单页签并返回我要报账 elapsed_ms={_elapsed_ms(started_at)}")

        return ReimbursementTaskResult(status="success", message="reimbursement form saved")
    except Exception:
        try:
            failure_screenshot_path = capture_screenshot(working_page, config["paths"]["screenshot_dir"], task)
            cache_browser_context_value(page, "_last_failure_screenshot_path", failure_screenshot_path)
        except Exception:
            cache_browser_context_value(page, "_last_failure_screenshot_path", None)
        _cleanup_failed_reimbursement_task(page, working_page, selectors, timeout, logger, task.task_id)
        raise


def reset_task_context(page, config: dict[str, Any], logger: logging.Logger, task_id: str) -> None:
    timeout = int(config.get("system", {}).get("timeout_ms", 15000))
    selectors = config.get("selectors", {})
    selectors["_context_hints"] = config.get("selector_contexts", {})
    working_page = _get_cached_active_working_page(page) or page
    if _is_fast_clean_reimbursement_state(working_page, selectors):
        logger.info(f"[TASK {task_id}] context_reset=no_action")
        return
    actions = _cleanup_failed_reimbursement_task(page, working_page, selectors, timeout, logger, task_id)
    logger.info(f"[TASK {task_id}] context_reset={'|'.join(actions) if actions else 'no_action'}")


def _cleanup_failed_reimbursement_task(
    page: Page,
    working_page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
) -> list[str]:
    actions: list[str] = []
    working_page = _select_cleanup_working_page_base(page, working_page, actions)
    logger.info(
        f"[TASK {task_id}] [context_reset_diag] INFO "
        f"{_diagnose_cleanup_state_base(page, working_page, selectors, _is_electronic_image_page, _has_selected_bill_tab_title, _is_my_reimbursement_page)}"
    )
    _clear_reimbursement_runtime_caches(working_page, keep_active_page=True)

    try:
        if _is_electronic_image_page(working_page, selectors, 120):
            _close_electronic_image_tab(
                working_page,
                selectors,
                min(timeout, 1800),
                logger,
                task_id,
                lambda *_args: None,
            )
            actions.append("electronic_image_closed")
    except Exception as exc:
        actions.append(f"electronic_image_close_error={type(exc).__name__}")

    try:
        if _has_selected_bill_tab_title(working_page, "业务招待费报销", 80) or _has_selected_bill_tab_title(working_page, "市内交通费报销", 80):
            _close_reimbursement_bill_tab(
                working_page,
                selectors,
                min(timeout, 2500),
                logger,
                task_id,
                lambda *_args: None,
            )
            actions.append("bill_tab_closed")
    except Exception as exc:
        actions.append(f"bill_tab_close_error={type(exc).__name__}")

    try:
        if not _is_my_reimbursement_page(working_page, selectors, 220):
            _open_my_reimbursement(working_page, selectors, min(timeout, 3000), logger, task_id, lambda *_args: None)
            actions.append("my_reimbursement_restored")
    except Exception as exc:
        actions.append(f"my_reimbursement_restore_error={type(exc).__name__}")

    _cache_active_working_page(page, working_page)
    _clear_reimbursement_runtime_caches(page, keep_active_page=True)
    return actions


def capture_screenshot(page, screenshot_dir: str, task: ReimbursementTaskRecord) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_id = str(getattr(task, "task_id", "") or "unknown_task")
    safe_task_id = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in task_id)
    path = Path(screenshot_dir) / f"{timestamp}_{safe_task_id}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_page = _get_cached_active_working_page(page) or page
    screenshot_page.screenshot(path=str(path), full_page=True)
    return str(path)


def _resolve_task_bill_subtype(task: ReimbursementTaskRecord, mapping: dict[str, Any]) -> str:
    return _resolve_task_bill_subtype_base(task, mapping)


def _is_city_transport_bill(task: ReimbursementTaskRecord, mapping: dict[str, Any]) -> bool:
    return _is_city_transport_bill_base(task, mapping)


def _bill_page_markers(selectors: dict[str, str], bill_subtype: str) -> list[str]:
    return _bill_page_markers_base(selectors, bill_subtype)


def _dedupe_selectors(candidates: list[str]) -> list[str]:
    return _dedupe_selectors_base(candidates)


def _detail_button_selector_candidates(configured_selector: str, action: str) -> list[str]:
    return _detail_button_selector_candidates_base(configured_selector, action)


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


def _create_reimbursement_bill(
    page: Page,
    config: dict[str, Any],
    selectors: dict[str, str],
    mapping: dict[str, Any],
    task: ReimbursementTaskRecord,
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> Page:
    bill_subtype = _resolve_task_bill_subtype(task, mapping)
    detect_timeout = min(timeout, 520)
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
    if _has_selected_bill_tab_title(page, bill_subtype, 120):
        _timed_substep(
            logger,
            step_log,
            task_id,
            "precheck_reimbursement_bill_page",
            f"预检{bill_subtype}单据页状态",
            lambda: bill_page_state.__setitem__("matched", _is_target_reimbursement_bill_page_precheck(page, selectors, bill_subtype)),
        )
    else:
        bill_page_state["matched"] = False
        _step(
            logger,
            step_log,
            task_id,
            "precheck_reimbursement_bill_page",
            "SKIP",
            f"当前未选中{bill_subtype}页签 elapsed_ms=0",
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
        "click_bill_subtype",
        f"点击{bill_subtype}",
        lambda: _click_bill_subtype_link(page, context, selectors, bill_subtype, click_timeout),
    )
    bill_tab_state: dict[str, bool] = {}
    _step(logger, step_log, task_id, "wait_selected_bill_tab_title", "START", f"快速检测{bill_subtype}页签激活")
    title_started_at = perf_counter()
    bill_tab_state["matched"] = _wait_for_selected_bill_tab_title(page, bill_subtype, 380)
    _step(
        logger,
        step_log,
        task_id,
        "wait_selected_bill_tab_title",
        "SUCCESS",
        f"matched={bill_tab_state.get('matched', False)} elapsed_ms={_elapsed_ms(title_started_at)}",
    )
    if bill_tab_state.get("matched", False):
        _clear_reimbursement_runtime_caches(page, keep_active_page=True)
        _timed_substep(
            logger,
            step_log,
            task_id,
            "cache_target_bill_context",
            "缓存目标单据上下文",
            lambda: _cache_target_bill_context_fast(page, selectors, bill_subtype, min(timeout, 360)),
        )
        return page
    next_page_holder: dict[str, Page] = {"page": page}
    _timed_substep(
        logger,
        step_log,
        task_id,
        "follow_new_bill_page",
        "等待新单据页面切换",
        lambda: next_page_holder.__setitem__("page", _follow_new_page_after_bill_click(page, 600)),
    )
    page = next_page_holder["page"]
    if _wait_for_selected_bill_tab_title(page, bill_subtype, 380):
        _clear_reimbursement_runtime_caches(page, keep_active_page=True)
        _timed_substep(
            logger,
            step_log,
            task_id,
            "cache_target_bill_context",
            "缓存目标单据上下文",
            lambda: _cache_target_bill_context_fast(page, selectors, bill_subtype, min(timeout, 360)),
        )
        return page
    _timed_substep(
        logger,
        step_log,
        task_id,
        "detect_reimbursement_bill_page",
        f"检测{bill_subtype}单据页到达",
        lambda: _ensure_target_reimbursement_bill_page(page, selectors, bill_subtype, detect_timeout),
    )
    _clear_reimbursement_runtime_caches(page, keep_active_page=True)
    _timed_substep(
        logger,
        step_log,
        task_id,
        "cache_target_bill_context",
        "缓存目标单据上下文",
        lambda: _cache_target_bill_context_fast(page, selectors, bill_subtype, min(timeout, 520)),
    )
    return page


def _open_electronic_image_tab(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
    bill_subtype: str | None = None,
) -> None:
    click_timeout = min(timeout, 1200)
    detect_timeout = min(timeout, 800)
    click_diag: dict[str, str] = {}
    if bill_subtype:
        _timed_substep(
            logger,
            step_log,
            task_id,
            "prepare_electronic_image_context",
            "准备电子影像入口上下文",
            lambda: _cache_target_bill_context_fast(page, selectors, bill_subtype, min(timeout, 360)),
        )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "click_electronic_image_tab",
        "点击电子影像入口",
        lambda: _click_electronic_image_tab(
            page,
            selectors,
            click_timeout,
            bill_subtype=bill_subtype,
            diag_holder=click_diag,
        ),
        retry_delay_s=0.12,
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
    screenshot_dir: str,
) -> ReimbursementTaskResult:
    try:
        failure_screenshot_path = capture_screenshot(page, screenshot_dir, task)
        cache_browser_context_value(page, "_last_failure_screenshot_path", failure_screenshot_path)
    except Exception:
        cache_browser_context_value(page, "_last_failure_screenshot_path", None)
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
    _clear_reimbursement_runtime_caches(page)
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
    detect_timeout = min(timeout, 10000)
    image_context = _resolve_electronic_image_context(page, selectors)
    _timed_substep(
        logger,
        step_log,
        task_id,
        "click_recognize_button",
        "点击识别",
        lambda: _click_locator_fast(image_context, page, selectors["recognize_button"], click_timeout, "未找到可点击的‘识别’按钮"),
    )
    _detect_invoice_recognition_with_diagnostics(page, selectors, detect_timeout, logger, task_id, step_log)


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
    bill_subtype = _resolve_task_bill_subtype(task, mapping)
    is_city_transport = _is_city_transport_bill(task, mapping)
    try:
        bill_context = _resolve_target_bill_form_context(page, selectors, bill_subtype, min(field_timeout, 1200))
        _cache_bill_form_context(page, bill_context)
    except Exception:
        bill_context = _resolve_bill_form_context(page, selectors)
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
    if not is_city_transport:
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
    if is_city_transport:
        _timed_substep(
            logger,
            step_log,
            task_id,
            "open_cost_share_tab",
            "打开费用分摊",
            lambda: _ensure_city_transport_cost_share_open(
                page,
                selectors,
                bill_subtype,
                bill_context,
                field_timeout,
            ),
        )
        _timed_substep(
            logger,
            step_log,
            task_id,
            "fill_cost_share_rows",
            "填写费用分摊",
            lambda: _fill_city_transport_detail_row(
                _resolve_city_transport_cost_share_context(page, selectors, bill_subtype, bill_context),
                page,
                task,
                selectors,
                field_timeout,
            ),
        )
    else:
        _timed_substep(
            logger,
            step_log,
            task_id,
            "open_detail_tab",
            "打开报销明细信息",
            lambda: _ensure_business_detail_grid_open(page, selectors, bill_subtype, bill_context, field_timeout),
        )
        _timed_substep(
            logger,
            step_log,
            task_id,
            "fill_detail_rows",
            "填写报销明细",
            lambda: _fill_detail_rows(
                _resolve_business_detail_context(page, selectors, bill_subtype, bill_context),
                page,
                task,
                selectors,
                field_timeout,
            ),
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
    confirm_timeout = min(timeout, 700)
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
        lambda: _confirm_reimbursement_bill_tab_close_if_needed(page, selectors, confirm_timeout, logger, task_id, step_log),
        retry_delay_s=0.12,
    )
    _timed_substep(
        logger,
        step_log,
        task_id,
        "detect_reimbursement_bill_tab_closed",
        "检测已返回我要报账列表",
        lambda: _ensure_reimbursement_bill_tab_closed(page, selectors, detect_timeout),
    )
    _clear_reimbursement_runtime_caches(page, keep_active_page=True)


def _confirm_reimbursement_bill_tab_close_if_needed(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> None:
    confirm_selectors = [
        selectors.get("reimbursement_bill_close_confirm_button", ""),
        'xpath=//div[contains(@class,"messager-button")]//a[contains(@class,"l-btn")][.//span[contains(@class,"l-btn-text") and normalize-space(.)="确定"]]',
        'xpath=//div[contains(@class,"messager-button")]//a[.//span[normalize-space(.)="确定"]]',
        'xpath=//div[contains(@class,"messager-button")]//span[contains(@class,"l-btn-text") and normalize-space(.)="确定"]/ancestor::a[1]',
        'xpath=//div[contains(@class,"messager-button")]//span[normalize-space(.)="确定"]/ancestor::a[1]',
    ]
    diag_parts: list[str] = []
    page.wait_for_timeout(30)
    primary_build_started_at = perf_counter()
    primary_contexts = _candidate_close_confirm_contexts(page, selectors, include_resolved=False)
    primary_build_elapsed_ms = _elapsed_ms(primary_build_started_at)
    primary_started_at = perf_counter()
    clicked, dialog_seen, attempts = click_dialog_button_if_needed(
        page,
        primary_contexts,
        _wait_visible,
        button_text="确定",
        confirm_selectors=confirm_selectors,
        timeout_ms=min(timeout, 260),
        post_click_wait_ms=20,
    )
    primary_elapsed_ms = _elapsed_ms(primary_started_at)
    diag_parts.append(
        f"build_primary_contexts elapsed_ms={primary_build_elapsed_ms} contexts={len(primary_contexts)} "
        f"phase=primary elapsed_ms={primary_elapsed_ms} contexts={len(primary_contexts)} "
        f"clicked={clicked} dialog_seen={dialog_seen}"
    )
    if clicked:
        return
    if not dialog_seen:
        return

    fallback_build_started_at = perf_counter()
    fallback_contexts = _candidate_close_confirm_contexts(page, selectors, include_resolved=True)
    fallback_build_elapsed_ms = _elapsed_ms(fallback_build_started_at)
    fallback_started_at = perf_counter()
    clicked, dialog_seen, fallback_attempts = click_dialog_button_if_needed(
        page,
        fallback_contexts,
        _wait_visible,
        button_text="确定",
        confirm_selectors=confirm_selectors,
        timeout_ms=min(timeout, 700),
        post_click_wait_ms=20,
    )
    fallback_elapsed_ms = _elapsed_ms(fallback_started_at)
    diag_parts.append(
        f"build_fallback_contexts elapsed_ms={fallback_build_elapsed_ms} contexts={len(fallback_contexts)} "
        f"phase=fallback elapsed_ms={fallback_elapsed_ms} contexts={len(fallback_contexts)} "
        f"clicked={clicked} dialog_seen={dialog_seen}"
    )
    if clicked:
        return
    combined_attempts = attempts + fallback_attempts
    if dialog_seen:
        raise RuntimeError(f"未成功点击关闭报销单确认框的‘确定’按钮 attempts={combined_attempts}")
    return

def _candidate_close_confirm_contexts(
    page: Page,
    selectors: dict[str, str],
    include_resolved: bool,
) -> list[LocatorContext]:
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx: LocatorContext | None) -> None:
        _append_unique_context(contexts, seen, ctx)

    add(get_cached_page_context(page, "_bill_outer_context"))
    add(get_cached_page_context(page, "_bill_form_context"))
    add(get_cached_page_context(page, "_reimbursement_context"))
    cached_working_page = _get_cached_active_working_page(page)
    if cached_working_page is not None:
        add(cached_working_page)
    if include_resolved:
        add(_resolve_selector_context(page, selectors, "reimbursement_bill_close_confirm_button"))
        add(_resolve_bill_outer_context(page, selectors))
        add(_resolve_bill_form_context(page, selectors))
        add(_resolve_reimbursement_context(page, selectors))
    try:
        for frame in reversed(page.frames):
            try:
                if frame == page.main_frame:
                    continue
                url = getattr(frame, "url", "") or ""
                if (
                    "Index.html" in url
                    or "/session/fssc/mybill/" in url
                    or "/ro/ywcl/" in url
                    or "funcid=" in url
                ):
                    add(frame)
            except Exception:
                continue
    except Exception:
        pass
    add(page)
    return contexts


def _has_visible_close_confirm_dialog(context: LocatorContext) -> bool:
    return has_visible_dialog(context, _wait_visible, ".messager-button", 80)


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
    frame = resolve_first_visible_frame_context(page, [iframe_selector], _wait_visible, 220)
    if frame is not None:
        return frame

    return page


def _resolve_bill_outer_context(page: Page, selectors: dict[str, str]) -> LocatorContext | None:
    cached_context = _get_cached_bill_outer_context(page)
    if cached_context is not None:
        return cached_context
    try:
        for frame in reversed(list(page.frames)):
            try:
                if frame == page.main_frame:
                    continue
                url = getattr(frame, "url", "") or ""
                if "Index.html" not in url:
                    continue
                if "/session/fssc/mybill/" in url or "/ro/ywcl/" in url:
                    _cache_bill_outer_context(page, frame)
                    return frame
            except Exception:
                continue
    except Exception:
        pass
    outer_iframe_selectors = [
        selectors.get("bill_page_iframe", ""),
        'iframe[id^="rtf_frm_"][src*="firstlatitude="]',
        'iframe[id^="rtf_frm_"][src*="/mybill/"]',
        'iframe[src*="funcid="]',
    ]
    context = resolve_first_visible_frame_context(page, outer_iframe_selectors, _wait_visible, 220)
    _cache_bill_outer_context(page, context)
    return context


def _cache_bill_outer_context(page: Page, context: LocatorContext | None) -> None:
    _cache_bill_outer_context_base(page, context)


def _clear_reimbursement_runtime_caches(page: Page, keep_active_page: bool = False) -> None:
    _cache_bill_outer_context(page, None)
    _cache_bill_form_context(page, None)
    _cache_reimbursement_context(page, None)
    _cache_electronic_image_context(page, None)
    if not keep_active_page:
        _cache_active_working_page(page, None)


def _get_cached_bill_outer_context(page: Page) -> LocatorContext | None:
    return _get_cached_bill_outer_context_base(page, _wait_visible)


def _cache_reimbursement_context(page: Page, context: LocatorContext | None) -> None:
    _cache_reimbursement_context_base(page, context)


def _get_cached_reimbursement_context(page: Page) -> LocatorContext | None:
    return _get_cached_reimbursement_context_base(page, _wait_visible)


def _resolve_bill_form_context(page: Page, selectors: dict[str, str]) -> LocatorContext:
    cached_context = _get_cached_bill_form_context(page)
    if cached_context is not None:
        return cached_context
    outer_context = _resolve_bill_outer_context(page, selectors)
    if outer_context is not None:
        nested = _resolve_inner_bill_iframe(outer_context, selectors)
        if nested is not None:
            _cache_bill_form_context(page, nested)
            return nested
        _cache_bill_form_context(page, outer_context)
        return outer_context

    parent = _resolve_reimbursement_context(page, selectors)
    nested = _resolve_inner_bill_iframe(parent, selectors)
    if nested is not None:
        _cache_bill_form_context(page, nested)
        return nested

    marker_context = _resolve_context_by_markers(
        page,
        [
            selectors.get("electronic_image_tab_entry", ""),
            selectors.get("save_button", ""),
            selectors.get("detail_tab_select", ""),
            selectors.get("city_transport_detail_tab_select", ""),
            "text=电子影像",
            "text=保存",
            "text=报销明细信息",
            "text=费用分摊",
        ],
        selectors,
    )
    if marker_context is not None and not hasattr(marker_context, "main_frame"):
        _cache_bill_form_context(page, marker_context)
        return marker_context
    return parent


def _resolve_target_bill_form_context(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    timeout: int,
) -> LocatorContext:
    marker_selectors = _bill_page_markers(selectors, bill_subtype)
    preferred_frame_markers: list[str] = []
    if "市内交通费报销" in bill_subtype:
        preferred_frame_markers = [
            'iframe#billIframe',
            'iframe[id="billIframe"]',
            'iframe.approvalIframe',
            'iframe[src*="/ro/ywcl/"]',
            'iframe[src*="secondlatitude=SQ"]',
        ]
    else:
        preferred_frame_markers = [
            'iframe#billIframe',
            'iframe[id="billIframe"]',
            'iframe.approvalIframe',
            'iframe[src*="/ro/ywcl/"]',
            selectors.get("bill_page_iframe", ""),
            'iframe[id^="rtf_frm_"][src*="/mybill/"]',
            'iframe[id^="rtf_frm_"][src*="ywlx=WEBROBX"]',
            'iframe[src*="funcid="][src*="/mybill/"]',
        ]

    context = resolve_first_visible_frame_context(page, preferred_frame_markers, _wait_visible, min(timeout, 500))
    if context is not None and _wait_markers_in_context(context, page, marker_selectors, min(timeout, 600)):
        return context

    candidates = _candidate_bill_contexts(page, selectors)
    resolved = _resolve_context_by_markers_base(candidates, marker_selectors, _wait_visible, min(timeout, 120))
    if resolved is not None and not hasattr(resolved, "main_frame"):
        return resolved

    fallback = _resolve_bill_form_context(page, selectors)
    if fallback is not None and not hasattr(fallback, "main_frame"):
        return fallback
    raise RuntimeError(f"未定位到匹配‘{bill_subtype}’的单据上下文")


def _resolve_target_bill_form_context_quick(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
) -> LocatorContext | None:
    try:
        cached = _get_cached_bill_form_context(page)
        if cached is not None:
            return cached
    except Exception:
        pass

    preferred_urls: tuple[str, ...]
    if "市内交通费报销" in bill_subtype:
        preferred_urls = ("/ro/ywcl/", "secondlatitude=SQ", "Index.html")
    else:
        preferred_urls = ("/session/fssc/mybill/", "/mybill/", "ywlx=WEBROBX", "Index.html")

    try:
        for frame in reversed(page.frames):
            try:
                if frame == page.main_frame:
                    continue
                url = getattr(frame, "url", "") or ""
                if not url:
                    continue
                if any(marker in url for marker in preferred_urls):
                    return frame
            except Exception:
                continue
    except Exception:
        pass

    try:
        outer = _resolve_bill_outer_context(page, selectors)
        if outer is not None:
            nested = _resolve_inner_bill_iframe(outer, selectors)
            if nested is not None:
                return nested
            return outer
    except Exception:
        pass
    return None


def _cache_target_bill_context_fast(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    timeout: int,
) -> None:
    try:
        quick = _resolve_target_bill_form_context_quick(page, selectors, bill_subtype)
        if quick is not None:
            _cache_bill_form_context(page, quick)
            return
    except Exception:
        pass
    try:
        _cache_bill_form_context(page, _resolve_target_bill_form_context(page, selectors, bill_subtype, timeout))
    except Exception:
        pass


def _cache_bill_form_context(page: Page, context: LocatorContext | None) -> None:
    _cache_bill_form_context_base(page, context)


def _get_cached_bill_form_context(page: Page) -> LocatorContext | None:
    return _get_cached_bill_form_context_base(page, _wait_visible)


def _resolve_inner_bill_iframe(parent: LocatorContext, selectors: dict[str, str]) -> LocatorContext | None:
    iframe_selectors = [
        selectors.get("bill_form_iframe", ""),
        'iframe#billIframe',
        'iframe[id="billIframe"]',
        'iframe[id^="bill"]',
        'iframe.approvalIframe',
        'iframe[src*="/session/fssc/mybill/"][src*="Index.html"]',
        'iframe[src*="/mybill/"][src*="Index.html"]',
        'iframe[src*="/session/fssc/mybill/"][src*="formID="]',
        'iframe[src*="/ro/ywcl/"][src*="firstlatitude="]',
    ]
    return resolve_first_visible_frame_context(parent, iframe_selectors, _wait_visible, 500)


def _candidate_bill_contexts(page: Page, selectors: dict[str, str]) -> list[LocatorContext]:
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx):
        _append_unique_context(contexts, seen, ctx)

    add(_resolve_bill_form_context(page, selectors))
    add(_resolve_bill_outer_context(page, selectors))
    add(_resolve_reimbursement_context(page, selectors))
    try:
        for frame in page.frames:
            try:
                url = getattr(frame, "url", "") or ""
                if (
                    "/mybill/" in url
                    or "/ro/ywcl/" in url
                    or "firstlatitude=" in url
                    or "funcid=" in url
                ):
                    add(frame)
            except Exception:
                continue
    except Exception:
        pass
    add(page)
    return contexts


def _resolve_selector_context(page: Page, selectors: dict[str, str], selector_name: str) -> LocatorContext | None:
    return _resolve_selector_context_base(
        page,
        selectors,
        selector_name,
        {
            "reimbursement_iframe": lambda: _resolve_reimbursement_context(page, selectors),
            "bill_iframe": lambda: _resolve_bill_form_context(page, selectors),
            "bill_form_iframe": lambda: _resolve_bill_form_context(page, selectors),
            "bill_outer_iframe": lambda: _resolve_bill_outer_context(page, selectors) or _resolve_bill_form_context(page, selectors),
            "image_system_iframe": lambda: _resolve_image_system_context(page) or _get_cached_electronic_image_context(page),
            "upload_dialog_iframe": lambda: _resolve_upload_dialog_context(page, selectors),
        },
    )


def _candidate_contexts_for_selector(page: Page, selectors: dict[str, str], selector_name: str) -> list[LocatorContext]:
    return _candidate_contexts_for_selector_base(
        page,
        selectors,
        selector_name,
        {
            "reimbursement_iframe": lambda: _resolve_reimbursement_context(page, selectors),
            "bill_iframe": lambda: _resolve_bill_form_context(page, selectors),
            "bill_form_iframe": lambda: _resolve_bill_form_context(page, selectors),
            "bill_outer_iframe": lambda: _resolve_bill_outer_context(page, selectors) or _resolve_bill_form_context(page, selectors),
            "image_system_iframe": lambda: _resolve_image_system_context(page) or _get_cached_electronic_image_context(page),
            "upload_dialog_iframe": lambda: _resolve_upload_dialog_context(page, selectors),
        },
    )


def _candidate_recognition_contexts(page: Page, selectors: dict[str, str]) -> list[LocatorContext]:
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx):
        _append_unique_context(contexts, seen, ctx)

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


def _click_electronic_image_tab(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    bill_subtype: str | None = None,
    diag_holder: dict[str, str] | None = None,
) -> None:
    overall_started = perf_counter()
    selector_candidates = [
        ("config.electronic_image_tab_entry", selectors.get("electronic_image_tab_entry", "")),
        ("name.btnViewImage", 'a[name="btnViewImage"]'),
        ("action.ViewImage", 'a[data-action="ViewImage"]'),
        ("text.button_electronic_image", 'xpath=//a[.//span[contains(@class,"l-btn-text") and normalize-space(.)="电子影像"]]'),
    ]
    contexts: list[tuple[str, LocatorContext]] = []
    seen: set[int] = set()

    def add_context(label: str, ctx: LocatorContext):
        if ctx is None:
            return
        marker = id(ctx)
        if marker in seen:
            return
        seen.add(marker)
        contexts.append((label, ctx))

    build_started = perf_counter()
    attempts: list[str] = []
    end_at = perf_counter() + (timeout / 1000)
    diag_parts: list[str] = []

    def click_result_verified() -> bool:
        verify_timeout = min(max(timeout, 400), 1200)
        return _has_selected_bill_tab_title(page, "电子影像", verify_timeout)

    def try_fast_dom_click(context_group: list[tuple[str, LocatorContext]]) -> tuple[bool, str | None]:
        for context_label, context in context_group:
            for selector_label, selector in selector_candidates:
                if not selector:
                    continue
                try:
                    locator = context.locator(selector).first
                    if locator.count() == 0:
                        attempts.append(f"{context_label}:{selector_label}:fast_dom=false")
                        continue
                    visible = _wait_visible(locator, 30)
                    attempts.append(f"{context_label}:{selector_label}:fast_dom_visible={visible}")
                    if not visible:
                        continue
                    try:
                        locator.evaluate(
                            """(el) => {
                              el.scrollIntoView({ block: 'center', inline: 'center' });
                              ['mouseover', 'mouseenter', 'mousedown', 'mouseup', 'click'].forEach((type) => {
                                el.dispatchEvent(new MouseEvent(type, { bubbles: true }));
                              });
                            }"""
                        )
                        attempts.append(f"{context_label}:{selector_label}:fast_dom_click=ok")
                        return True, f"phase=fast_dom context={context_label} selector={selector_label}"
                    except Exception as exc:
                        attempts.append(f"{context_label}:{selector_label}:fast_dom_click=fail:{type(exc).__name__}")
                except Exception as exc:
                    attempts.append(f"{context_label}:{selector_label}:fast_dom_error:{type(exc).__name__}")
        return False, None

    def try_context_group(
        context_group: list[tuple[str, LocatorContext]],
        visible_timeout: int,
        click_timeout_ms: int,
        phase_name: str,
    ) -> tuple[bool, str | None]:
        for context_label, context in context_group:
            for selector_label, selector in selector_candidates:
                if not selector:
                    continue
                locator = _first_visible_locator(context, selector, visible_timeout)
                if locator is None:
                    attempts.append(f"{context_label}:{selector_label}:visible=false")
                    continue
                attempts.append(f"{context_label}:{selector_label}:visible=true")
                try:
                    locator.scroll_into_view_if_needed(timeout=max(80, visible_timeout))
                    attempts.append(f"{context_label}:{selector_label}:scroll=ok")
                except Exception:
                    attempts.append(f"{context_label}:{selector_label}:scroll=fail")
                try:
                    locator.click(timeout=click_timeout_ms)
                    return True, f"phase={phase_name} context={context_label} selector={selector_label} mode=click"
                except Exception as exc:
                    attempts.append(f"{context_label}:{selector_label}:click=fail:{type(exc).__name__}")
                try:
                    locator.click(timeout=click_timeout_ms, force=True)
                    return True, f"phase={phase_name} context={context_label} selector={selector_label} mode=force_click"
                except Exception as exc:
                    attempts.append(f"{context_label}:{selector_label}:force_click=fail:{type(exc).__name__}")
                try:
                    locator.evaluate("(el) => el.click()")
                    attempts.append(f"{context_label}:{selector_label}:js_click=ok")
                    return True, f"phase={phase_name} context={context_label} selector={selector_label} mode=js_click"
                except Exception as exc:
                    attempts.append(f"{context_label}:{selector_label}:js_click=fail:{type(exc).__name__}")
        return False, None

    def build_context_groups() -> tuple[list[tuple[str, LocatorContext]], list[tuple[str, LocatorContext]], int]:
        build_started_local = perf_counter()
        contexts.clear()
        seen.clear()
        if bill_subtype:
            try:
                add_context("target_bill_context", _resolve_target_bill_form_context_quick(page, selectors, bill_subtype))
            except Exception:
                pass
        for idx, hinted in enumerate(_candidate_contexts_for_selector(page, selectors, "electronic_image_tab_entry")):
            add_context(f"selector_hint[{idx}]", hinted)
        try:
            add_context("bill_outer_context", _resolve_bill_outer_context(page, selectors))
        except Exception:
            pass
        try:
            add_context("bill_form_context", _resolve_bill_form_context(page, selectors))
        except Exception:
            pass
        try:
            add_context("reimbursement_context", _resolve_reimbursement_context(page, selectors))
        except Exception:
            pass
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

        fast_contexts_local: list[tuple[str, LocatorContext]] = []
        fallback_contexts_local: list[tuple[str, LocatorContext]] = []
        for label, context in contexts:
            if label.startswith(("target_bill_context", "selector_hint", "bill_outer_context", "bill_form_context", "reimbursement_context")):
                fast_contexts_local.append((label, context))
            else:
                fallback_contexts_local.append((label, context))
        return fast_contexts_local, fallback_contexts_local, int((perf_counter() - build_started_local) * 1000)

    initial_fast_contexts: list[tuple[str, LocatorContext]] = []
    if bill_subtype:
        try:
            quick_target = _resolve_target_bill_form_context_quick(page, selectors, bill_subtype)
            if quick_target is not None:
                initial_fast_contexts.append(("target_bill_context", quick_target))
        except Exception:
            pass
    if not initial_fast_contexts:
        for idx, hinted in enumerate(_candidate_contexts_for_selector(page, selectors, "electronic_image_tab_entry")):
            initial_fast_contexts.append((f"selector_hint[{idx}]", hinted))

    rounds = 0
    fast_contexts = initial_fast_contexts
    fallback_contexts: list[tuple[str, LocatorContext]] = []
    expanded_contexts = False
    while perf_counter() < end_at:
        rounds += 1
        round_started = perf_counter()
        clicked, detail = try_fast_dom_click(fast_contexts)
        if clicked:
            verified = click_result_verified()
            build_ms = int((perf_counter() - build_started) * 1000) if not expanded_contexts else None
            diag_parts.append(f"context_build_ms={build_ms if build_ms is not None else 0}")
            diag_parts.append(f"contexts={len(fast_contexts) + len(fallback_contexts)}")
            diag_parts.append(f"fast_contexts={len(fast_contexts)}")
            diag_parts.append(f"fallback_contexts={len(fallback_contexts)}")
            diag_parts.append(f"context_expanded={expanded_contexts}")
            diag_parts.append(f"rounds={rounds}")
            diag_parts.append(f"round_ms={int((perf_counter() - round_started) * 1000)}")
            if detail:
                diag_parts.append(detail)
            diag_parts.append(f"post_verify={verified}")
            if not verified:
                page.wait_for_timeout(40)
                continue
            diag_parts.append(f"total_ms={int((perf_counter() - overall_started) * 1000)}")
            if diag_holder is not None:
                diag_holder["info"] = " ".join(diag_parts)
            return
        clicked, detail = try_context_group(fast_contexts, 40, 100, "fast_click")
        if clicked:
            verified = click_result_verified()
            build_ms = int((perf_counter() - build_started) * 1000) if not expanded_contexts else None
            diag_parts.append(f"context_build_ms={build_ms if build_ms is not None else 0}")
            diag_parts.append(f"contexts={len(fast_contexts) + len(fallback_contexts)}")
            diag_parts.append(f"fast_contexts={len(fast_contexts)}")
            diag_parts.append(f"fallback_contexts={len(fallback_contexts)}")
            diag_parts.append(f"context_expanded={expanded_contexts}")
            diag_parts.append(f"rounds={rounds}")
            diag_parts.append(f"round_ms={int((perf_counter() - round_started) * 1000)}")
            if detail:
                diag_parts.append(detail)
            diag_parts.append(f"post_verify={verified}")
            if not verified:
                page.wait_for_timeout(40)
                continue
            diag_parts.append(f"total_ms={int((perf_counter() - overall_started) * 1000)}")
            if diag_holder is not None:
                diag_holder["info"] = " ".join(diag_parts)
            return
        if not expanded_contexts:
            fast_contexts, fallback_contexts, expanded_build_ms = build_context_groups()
            expanded_contexts = True
            diag_parts.append(f"context_build_ms={expanded_build_ms}")
            diag_parts.append(f"contexts={len(fast_contexts) + len(fallback_contexts)}")
            diag_parts.append(f"fast_contexts={len(fast_contexts)}")
            diag_parts.append(f"fallback_contexts={len(fallback_contexts)}")
            clicked, detail = try_context_group(fast_contexts, 40, 100, "expanded_fast_click")
            if clicked:
                verified = click_result_verified()
                diag_parts.append(f"context_expanded={expanded_contexts}")
                diag_parts.append(f"rounds={rounds}")
                diag_parts.append(f"round_ms={int((perf_counter() - round_started) * 1000)}")
                if detail:
                    diag_parts.append(detail)
                diag_parts.append(f"post_verify={verified}")
                if not verified:
                    page.wait_for_timeout(40)
                    continue
                diag_parts.append(f"total_ms={int((perf_counter() - overall_started) * 1000)}")
                if diag_holder is not None:
                    diag_holder["info"] = " ".join(diag_parts)
                return
        clicked, detail = try_context_group(fallback_contexts, 80, 140, "fallback_click")
        if clicked:
            verified = click_result_verified()
            diag_parts.append(f"context_expanded={expanded_contexts}")
            diag_parts.append(f"rounds={rounds}")
            diag_parts.append(f"round_ms={int((perf_counter() - round_started) * 1000)}")
            if detail:
                diag_parts.append(detail)
            diag_parts.append(f"post_verify={verified}")
            if not verified:
                page.wait_for_timeout(40)
                continue
            diag_parts.append(f"total_ms={int((perf_counter() - overall_started) * 1000)}")
            if diag_holder is not None:
                diag_holder["info"] = " ".join(diag_parts)
            return
        page.wait_for_timeout(20)
    if not diag_parts:
        build_ms = int((perf_counter() - build_started) * 1000) if not expanded_contexts else 0
        diag_parts.append(f"context_build_ms={build_ms}")
        diag_parts.append(f"contexts={len(fast_contexts) + len(fallback_contexts)}")
        diag_parts.append(f"fast_contexts={len(fast_contexts)}")
        diag_parts.append(f"fallback_contexts={len(fallback_contexts)}")
        diag_parts.append(f"context_expanded={expanded_contexts}")
    diag_parts.append(f"rounds={rounds}")
    diag_parts.append(f"total_ms={int((perf_counter() - overall_started) * 1000)}")
    if diag_holder is not None:
        diag_holder["info"] = " ".join(diag_parts)
    raise RuntimeError(f"未找到可点击的‘电子影像’入口 attempts={attempts}")


def _open_new_bill_menu(page: Page, context: LocatorContext, selectors: dict[str, str], timeout: int) -> None:
    _open_new_bill_menu_base(
        page,
        context,
        selectors,
        timeout,
        _is_new_bill_menu_open,
        _click_latest_visible_element,
        _first_visible_locator,
    )


def _is_new_bill_menu_open(context: LocatorContext, page: Page, selectors: dict[str, str], timeout: int) -> bool:
    return _is_new_bill_menu_open_base(context, page, selectors, timeout, _wait_markers_in_context)


def _first_visible_locator(context: LocatorContext, selector: str, timeout_ms: int):
    return _first_visible_locator_base(context, selector, timeout_ms, _wait_visible)


def _diagnose_new_bill_menu(page: Page, context: LocatorContext, selectors: dict[str, str]) -> None:
    _diagnose_new_bill_menu_base(page, context, selectors)


def _bill_subtype_candidates(selectors: dict[str, str], bill_subtype: str) -> list[str]:
    return _bill_subtype_candidates_base(selectors, bill_subtype)


def _click_bill_subtype_link(page: Page, context: LocatorContext, selectors: dict[str, str], bill_subtype: str, timeout: int) -> None:
    _click_bill_subtype_link_base(
        page,
        context,
        selectors,
        bill_subtype,
        timeout,
        _bill_subtype_candidates,
        _first_visible_locator,
    )


def _follow_new_page_after_bill_click(page: Page, timeout: int) -> Page:
    return _follow_new_page_after_bill_click_base(page, timeout)


def _resolve_electronic_image_context(page: Page, selectors: dict[str, str]) -> LocatorContext:
    cached_context = _get_cached_electronic_image_context(page)
    if cached_context is not None:
        return cached_context
    for selector_name in ("local_upload_button", "invoice_list_item", "recognize_button"):
        hinted_context = _resolve_selector_context(page, selectors, selector_name)
        if hinted_context is not None:
            return hinted_context
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
    _cache_electronic_image_context_base(page, context)


def _get_cached_electronic_image_context(page: Page) -> LocatorContext | None:
    return _get_cached_electronic_image_context_base(page, _wait_visible)


def _resolve_context_by_markers(page: Page, marker_selectors: list[str], selectors: dict[str, str]) -> LocatorContext | None:
    return _resolve_context_by_markers_base(_page_candidates(page), marker_selectors, _wait_visible, 80)


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
                markers = [
                    'text=本地上传',
                    'text=识别',
                    '#btnInOCR',
                    '.sortwrap .thumb',
                ]
                for selector in markers:
                    try:
                        if _wait_visible(frame.locator(selector).first, 60):
                            return frame
                    except Exception:
                        continue
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
    _set_upload_files_base(context, selector, file_paths, timeout, _wait_visible)


def _fill_locator_value(context: LocatorContext, selector: str, value: str, timeout: int, error_message: str) -> None:
    _fill_locator_value_base(context, selector, value, timeout, error_message, _wait_visible)


def _fill_locator_value_in_bill_contexts(
    page: Page,
    selectors: dict[str, str],
    selector: str,
    value: str,
    timeout: int,
    error_message: str,
) -> None:
    _fill_first_matching_locator_base(
        _candidate_bill_contexts(page, selectors),
        [selector],
        value,
        timeout,
        error_message,
        _wait_visible,
        _context_debug_name,
    )


def _fill_any_locator_value_in_bill_contexts(
    page: Page,
    selectors: dict[str, str],
    selector_candidates: list[str],
    value: str,
    timeout: int,
    error_message: str,
) -> None:
    _fill_first_matching_locator_base(
        _candidate_bill_contexts(page, selectors),
        selector_candidates,
        value,
        timeout,
        error_message,
        _wait_visible,
        _context_debug_name,
    )


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


def _click_locator_in_context(
    context: LocatorContext,
    page: Page,
    selector: str,
    timeout: int,
    error_message: str,
) -> None:
    attempts: list[str] = []
    context_name = _context_debug_name(context, 0)
    try:
        locator = context.locator(selector)
        count = locator.count()
        attempts.append(f"{context_name}:count={count}")
        if count == 0:
            raise RuntimeError(f"{error_message} attempts={attempts}")
        _click_locator_fast(context, page, selector, min(timeout, 1200), error_message)
        return
    except Exception as exc:
        if isinstance(exc, RuntimeError) and str(exc).startswith(error_message):
            raise
        attempts.append(f"{context_name}:error={type(exc).__name__}")
    raise RuntimeError(f"{error_message} attempts={attempts}")


def _click_any_locator_in_contexts(
    contexts: list[LocatorContext],
    page: Page,
    selector_candidates: list[str],
    timeout: int,
    error_message: str,
) -> None:
    attempts: list[str] = []
    for idx, context in enumerate(contexts):
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
                _click_locator_fast(context, page, selector, min(timeout, 1200), error_message)
                return
            except Exception as exc:
                attempts.append(f"{context_name}:{selector}:error={type(exc).__name__}")
    raise RuntimeError(f"{error_message} attempts={attempts}")


def _bill_tab_selector_candidates(configured_selector: str, tab_text: str) -> list[str]:
    return _bill_tab_selector_candidates_base(configured_selector, tab_text)


def _bill_tab_click_selector_candidates(configured_selector: str, tab_text: str) -> list[str]:
    return _bill_tab_click_selector_candidates_base(configured_selector, tab_text)


def _candidate_business_detail_contexts(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    primary_context: LocatorContext | None = None,
) -> list[LocatorContext]:
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx: LocatorContext | None) -> None:
        _append_unique_context(contexts, seen, ctx)

    add(primary_context)
    add(_get_cached_bill_form_context(page))
    try:
        add(_resolve_target_bill_form_context_quick(page, selectors, bill_subtype))
    except Exception:
        pass
    add(_resolve_bill_form_context(page, selectors))
    add(_resolve_bill_outer_context(page, selectors))
    return contexts


def _candidate_cost_share_contexts(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    primary_context: LocatorContext | None = None,
) -> list[LocatorContext]:
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx: LocatorContext | None) -> None:
        _append_unique_context(contexts, seen, ctx)

    add(primary_context)
    add(_resolve_bill_outer_context(page, selectors))
    add(_get_cached_bill_form_context(page))
    try:
        add(_resolve_target_bill_form_context_quick(page, selectors, bill_subtype))
    except Exception:
        pass
    add(_resolve_bill_form_context(page, selectors))
    return contexts


def _has_any_selector_in_context(context: LocatorContext, selector_candidates: list[str]) -> bool:
    for selector in selector_candidates:
        if not selector:
            continue
        try:
            if context.locator(selector).count() > 0:
                return True
        except Exception:
            continue
    return False


def _is_tab_selected_in_context(context: LocatorContext, tab_text: str) -> bool:
    selected_candidates = [
        f'xpath=//li[contains(@class,"tabs-selected")]//span[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]',
        f'xpath=//li[contains(@class,"tabs-selected")]//a[contains(@class,"tabs-inner")][.//span[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]]',
    ]
    return _has_any_selector_in_context(context, selected_candidates)


def _is_inner_bill_tab_selected(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    tab_text: str,
    contexts: list[LocatorContext] | None = None,
) -> bool:
    candidates = contexts or _candidate_target_bill_contexts(page, selectors, bill_subtype)
    for context in candidates:
        if _is_tab_selected_in_context(context, tab_text):
            return True
    return False


def _ensure_inner_bill_tab_selected(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    tab_text: str,
    configured_selector: str,
    timeout: int,
    error_message: str,
    contexts: list[LocatorContext] | None = None,
) -> None:
    candidate_contexts = contexts or _candidate_target_bill_contexts(page, selectors, bill_subtype)
    if _is_inner_bill_tab_selected(page, selectors, bill_subtype, tab_text, candidate_contexts):
        return
    click_candidates = _bill_tab_click_selector_candidates(configured_selector, tab_text)
    fast_contexts = candidate_contexts[:2]
    if fast_contexts:
        for context in fast_contexts:
            for selector in click_candidates:
                if not selector:
                    continue
                try:
                    if _click_latest_visible_element(context, selector):
                        page.wait_for_timeout(50)
                        if _is_inner_bill_tab_selected(page, selectors, bill_subtype, tab_text, candidate_contexts):
                            return
                except Exception:
                    continue
        try:
            _click_any_locator_in_contexts(
                fast_contexts,
                page,
                click_candidates,
                min(timeout, 700),
                error_message,
            )
            page.wait_for_timeout(60)
            if _is_inner_bill_tab_selected(page, selectors, bill_subtype, tab_text, candidate_contexts):
                return
        except Exception:
            pass
    _click_any_locator_in_contexts(
        candidate_contexts,
        page,
        click_candidates,
        min(timeout, 900),
        error_message,
    )
    page.wait_for_timeout(60)
    if _is_inner_bill_tab_selected(page, selectors, bill_subtype, tab_text, candidate_contexts):
        return
    raise RuntimeError(f"未成功切换到‘{tab_text}’页签")


def _ensure_city_transport_cost_share_open(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    bill_context: LocatorContext | None,
    timeout: int,
) -> None:
    _ensure_inner_bill_tab_selected(
        page,
        selectors,
        bill_subtype,
        "费用分摊",
        selectors.get("city_transport_detail_tab_select", "text=费用分摊"),
        timeout,
        "未找到可点击的‘费用分摊’页签",
        _candidate_cost_share_contexts(page, selectors, bill_subtype, bill_context),
    )


def _resolve_city_transport_cost_share_context(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    bill_context: LocatorContext | None = None,
) -> LocatorContext:
    fallback = bill_context
    for context in _candidate_cost_share_contexts(page, selectors, bill_subtype, bill_context):
        if fallback is None and not hasattr(context, "main_frame"):
            fallback = context
        if not _is_tab_selected_in_context(context, "费用分摊"):
            continue
        try:
            rows = _detail_rows_locator(context, selectors)
            if (
                _detail_row_count(context, selectors) > 0
                or context.locator('div.datagrid-view2 div.datagrid-body').count() > 0
                or rows.nth(0).locator('td[field="ROFYFT_FTSM"]').count() > 0
            ):
                return context
        except Exception:
            continue
    if fallback is not None:
        return fallback
    return _resolve_bill_form_context(page, selectors)


def _is_business_detail_grid_ready(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    bill_context: LocatorContext | None = None,
) -> bool:
    for context in _candidate_business_detail_contexts(page, selectors, bill_subtype, bill_context):
        if _is_tab_selected_in_context(context, "报销明细信息"):
            return True
    return False


def _resolve_business_detail_context(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    bill_context: LocatorContext | None = None,
) -> LocatorContext:
    add_candidates = _detail_button_selector_candidates(selectors.get("detail_add_button", ""), "add")
    delete_candidates = _detail_button_selector_candidates(selectors.get("detail_delete_button", ""), "delete")
    fallback = bill_context
    for context in _candidate_business_detail_contexts(page, selectors, bill_subtype, bill_context):
        if fallback is None and not hasattr(context, "main_frame"):
            fallback = context
        if _is_tab_selected_in_context(context, "报销明细信息") and (
            _has_any_selector_in_context(context, add_candidates)
            or _has_any_selector_in_context(context, delete_candidates)
            or _detail_row_count(context, selectors) >= 0
        ):
            return context
    if fallback is not None:
        return fallback
    return _resolve_bill_form_context(page, selectors)


def _ensure_business_detail_grid_open(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    bill_context: LocatorContext | None,
    timeout: int,
) -> None:
    _ensure_inner_bill_tab_selected(
        page,
        selectors,
        bill_subtype,
        "报销明细信息",
        selectors["detail_tab_select"],
        timeout,
        "未找到可点击的‘报销明细信息’页签",
        _candidate_business_detail_contexts(page, selectors, bill_subtype, bill_context),
    )


def _candidate_target_bill_contexts(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    primary_context: LocatorContext | None = None,
) -> list[LocatorContext]:
    contexts: list[LocatorContext] = []
    seen: set[int] = set()

    def add(ctx: LocatorContext | None) -> None:
        _append_unique_context(contexts, seen, ctx)

    add(primary_context)
    try:
        add(_resolve_target_bill_form_context(page, selectors, bill_subtype, 800))
    except Exception:
        pass
    add(_resolve_bill_outer_context(page, selectors))
    add(_resolve_bill_form_context(page, selectors))
    add(_resolve_reimbursement_context(page, selectors))
    add(page)
    return contexts


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
    if _wait_visible(input_locator, 180):
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
        if _wait_visible(cell, 180):
            try:
                cell.click(timeout=220)
            except Exception:
                cell.click(timeout=220, force=True)
            page.wait_for_timeout(40)
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
                if _wait_visible(locator, 160):
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
        page.wait_for_timeout(40)
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
    delete_selector_candidates = _detail_button_selector_candidates(delete_selector, "delete")
    add_selector_candidates = _detail_button_selector_candidates(add_selector, "add")
    attempts.append(f"delete_selector={delete_selector}")
    attempts.append(f"add_selector={add_selector}")
    attempts.append(f"delete_selector_candidates={delete_selector_candidates}")
    attempts.append(f"add_selector_candidates={add_selector_candidates}")
    try:
        attempts.append(
            "delete_button_count="
            + str(max((context.locator(selector).count() for selector in delete_selector_candidates if selector), default=0))
        )
    except Exception as exc:
        attempts.append(f"delete_button_count_error={type(exc).__name__}")
    try:
        attempts.append(
            "add_button_count="
            + str(max((context.locator(selector).count() for selector in add_selector_candidates if selector), default=0))
        )
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
        _click_any_locator_in_contexts(
            _candidate_business_detail_contexts(page, selectors, "业务招待费报销", context),
            page,
            delete_selector_candidates,
            min(timeout, 1000),
            "未找到可点击的‘删除’按钮",
        )
        delete_attempted = True
        page.wait_for_timeout(60)
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
        _click_any_locator_in_contexts(
            _candidate_business_detail_contexts(page, selectors, "业务招待费报销", context),
            page,
            add_selector_candidates,
            min(timeout, 1000),
            "未找到可点击的‘增加’按钮",
        )
        page.wait_for_timeout(60)
        attempts.append(f"add_row_index={index}")
        after_add_count = _detail_row_count(context, selectors)
        after_add_effective_count = _effective_detail_row_count(context, selectors)
        attempts.append(f"after_add_count[{index}]={after_add_count}")
        attempts.append(f"after_add_effective_count[{index}]={after_add_effective_count}")

    _ensure_detail_row_count(context, page, selectors, target_count, min(timeout, 1800), attempts)


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
            if not _wait_visible(cell, 140):
                continue
            try:
                cell.click(timeout=250)
                attempts.append(f"{row_label}:activate_click={selector}")
            except Exception:
                cell.dblclick(timeout=250)
                attempts.append(f"{row_label}:activate_dblclick={selector}")
            page.wait_for_timeout(40)
            activated = True
            if "datagrid-row-editing" in (row.get_attribute("class") or ""):
                break
        except Exception as exc:
            attempts.append(f"{row_label}:activate_error={selector}:{type(exc).__name__}")

    if not activated:
        try:
            row.click(timeout=250, force=True)
            attempts.append(f"{row_label}:activate_row_click")
            page.wait_for_timeout(40)
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
        if _wait_visible(target_cell, 180):
            try:
                target_cell.click(timeout=220)
                attempts.append(f"{row_label}:reception_cell_click=ok")
            except Exception:
                target_cell.click(timeout=220, force=True)
                attempts.append(f"{row_label}:reception_cell_click=force_ok")
            page.wait_for_timeout(50)
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
            if not _wait_visible(candidate, 140):
                attempts.append(f"{row_label}:reception_arrow[{idx}]=hidden")
                continue
            try:
                candidate.click(timeout=220)
                attempts.append(f"{row_label}:reception_arrow[{idx}]=click_ok")
            except Exception:
                candidate.click(timeout=220, force=True)
                attempts.append(f"{row_label}:reception_arrow[{idx}]=force_click_ok")
            arrow_clicked = True
            page.wait_for_timeout(60)
            break
        except Exception as exc:
            attempts.append(f"{row_label}:reception_arrow[{idx}]=error:{type(exc).__name__}")

    visible_panel = _first_visible_locator(context, 'div.panel.combo-p:visible, div.combo-panel:visible', 180)
    attempts.append(f"{row_label}:reception_panel={'visible' if visible_panel is not None else 'hidden'}")

    option = None
    option_candidates = context.locator('div.panel.combo-p:visible .combobox-item, div.combo-panel:visible .combobox-item')
    try:
        option_count = option_candidates.count()
        attempts.append(f"{row_label}:reception_option_count={option_count}")
        for idx in range(option_count):
            candidate = option_candidates.nth(idx)
            if not _wait_visible(candidate, 100):
                continue
            text = (candidate.inner_text(timeout=200) or "").strip()
            attempts.append(f"{row_label}:reception_option[{idx}]={text}")
            if text == reception_type_value:
                option = candidate
                break
    except Exception as exc:
        attempts.append(f"{row_label}:reception_option_scan_error:{type(exc).__name__}")

    if option is not None:
        option.click(timeout=220)
        page.wait_for_timeout(60)
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
            page.wait_for_timeout(80)
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


def _fill_city_transport_detail_row(
    context: LocatorContext,
    page: Page,
    task: ReimbursementTaskRecord,
    selectors: dict[str, str],
    timeout: int,
) -> None:
    row_count = _wait_city_transport_detail_row_count(context, selectors, min(timeout, 2600))
    rows = _detail_rows_locator(context, selectors)
    if row_count == 0:
        raise RuntimeError(
            "未检测到可填写的费用分摊行，可能当前发票已被报销使用或费用分摊信息尚未同步 "
            f"attempts={_diagnose_city_transport_cost_share(page, selectors)}"
        )

    remarks = [str(invoice.remark).strip() for invoice in task.invoices if str(invoice.remark).strip()]
    if not remarks:
        raise RuntimeError("费用分摊缺少可填写的‘分摊说明’")
    remark_value = "；".join(dict.fromkeys(remarks))

    attempts: list[str] = [f"row_count={row_count}"]
    row = rows.nth(0)
    if _fill_city_transport_remark_cell(row, page, selectors, remark_value, timeout, attempts, "row[0]"):
        return
    raise RuntimeError(f"费用分摊行已打开，但未成功填写‘分摊说明’ attempts={attempts}")


def _wait_city_transport_detail_row_count(
    context: LocatorContext,
    selectors: dict[str, str],
    timeout_ms: int,
) -> int:
    last_count = 0
    end_at = perf_counter() + (max(timeout_ms, 200) / 1000)
    while perf_counter() < end_at:
        last_count = _detail_row_count(context, selectors)
        if last_count > 0:
            return last_count
        try:
            context.wait_for_timeout(80)
        except Exception:
            pass
    return last_count


def _diagnose_city_transport_cost_share(page: Page, selectors: dict[str, str]) -> str:
    attempts: list[str] = []
    try:
        attempts.append(f"selected_transport_tab={_has_selected_bill_tab_title(page, '市内交通费报销', 80)}")
    except Exception as exc:
        attempts.append(f"selected_transport_tab=error:{type(exc).__name__}")
    try:
        attempts.append(f"selected_cost_share_tab={_is_inner_bill_tab_selected(page, selectors, '市内交通费报销', '费用分摊')}")
    except Exception as exc:
        attempts.append(f"selected_cost_share_tab=error:{type(exc).__name__}")
    try:
        attempts.append(f"selected_my_reimbursement={_is_my_reimbursement_page(page, selectors, 120)}")
    except Exception as exc:
        attempts.append(f"selected_my_reimbursement=error:{type(exc).__name__}")
    try:
        context = _resolve_bill_form_context(page, selectors)
        attempts.append(f"context={_context_debug_name(context, 0)}")
        rows = _detail_rows_locator(context, selectors)
        attempts.append(f"row_count={_detail_row_count(context, selectors)}")
        attempts.append(f"effective_row_count={_effective_detail_row_count(context, selectors)}")
        try:
            attempts.append(f"grid_body_count={context.locator('div.datagrid-view2 div.datagrid-body').count()}")
        except Exception as exc:
            attempts.append(f"grid_body_count=error:{type(exc).__name__}")
        try:
            attempts.append(f"cost_share_tab_count={context.locator(selectors.get('city_transport_detail_tab_select', 'text=费用分摊')).count()}")
        except Exception as exc:
            attempts.append(f"cost_share_tab_count=error:{type(exc).__name__}")
        try:
            attempts.append(f"remark_cell_count={rows.nth(0).locator('td[field=\"ROFYFT_FTSM\"]').count()}")
        except Exception as exc:
            attempts.append(f"remark_cell_count=error:{type(exc).__name__}")
    except Exception as exc:
        attempts.append(f"context_error={type(exc).__name__}")
    return " ".join(attempts)


def _diagnose_business_detail_grid(
    page: Page,
    selectors: dict[str, str],
    bill_subtype: str,
    bill_context: LocatorContext | None = None,
) -> str:
    attempts: list[str] = []
    try:
        attempts.append(f"selected_business_tab={_has_selected_bill_tab_title(page, '业务招待费报销', 80)}")
    except Exception as exc:
        attempts.append(f"selected_business_tab=error:{type(exc).__name__}")
    try:
        attempts.append(f"selected_detail_tab={_is_inner_bill_tab_selected(page, selectors, bill_subtype, '报销明细信息')}")
    except Exception as exc:
        attempts.append(f"selected_detail_tab=error:{type(exc).__name__}")
    try:
        attempts.append(f"selected_transport_tab={_has_selected_bill_tab_title(page, '市内交通费报销', 80)}")
    except Exception as exc:
        attempts.append(f"selected_transport_tab=error:{type(exc).__name__}")
    try:
        attempts.append(f"is_electronic_image={_is_electronic_image_page(page, selectors, 120)}")
    except Exception as exc:
        attempts.append(f"is_electronic_image=error:{type(exc).__name__}")
    try:
        attempts.append(f"is_my_reimbursement={_is_my_reimbursement_page(page, selectors, 120)}")
    except Exception as exc:
        attempts.append(f"is_my_reimbursement=error:{type(exc).__name__}")

    contexts = _candidate_business_detail_contexts(page, selectors, bill_subtype, bill_context)
    selector_candidates = _bill_tab_selector_candidates(selectors.get("detail_tab_select", "text=报销明细信息"), "报销明细信息")
    add_selector_candidates = _detail_button_selector_candidates(selectors.get("detail_add_button", ""), "add")
    delete_selector_candidates = _detail_button_selector_candidates(selectors.get("detail_delete_button", ""), "delete")
    for idx, context in enumerate(contexts):
        context_name = _context_debug_name(context, idx)
        attempts.append(f"context[{idx}]={context_name}")
        for selector in selector_candidates:
            if not selector:
                continue
            try:
                attempts.append(f"{context_name}:{selector}:count={context.locator(selector).count()}")
            except Exception as exc:
                attempts.append(f"{context_name}:{selector}:error={type(exc).__name__}")
        try:
            attempts.append(
                f"{context_name}:detail_delete_count="
                + str(max((context.locator(selector).count() for selector in delete_selector_candidates if selector), default=0))
            )
        except Exception as exc:
            attempts.append(f"{context_name}:detail_delete_count=error:{type(exc).__name__}")
        try:
            attempts.append(
                f"{context_name}:detail_add_count="
                + str(max((context.locator(selector).count() for selector in add_selector_candidates if selector), default=0))
            )
        except Exception as exc:
            attempts.append(f"{context_name}:detail_add_count=error:{type(exc).__name__}")
        try:
            attempts.append(f"{context_name}:detail_row_count={_detail_row_count(context, selectors)}")
        except Exception as exc:
            attempts.append(f"{context_name}:detail_row_count=error:{type(exc).__name__}")
    return " ".join(attempts)


def _fill_city_transport_remark_cell(
    row,
    page: Page,
    selectors: dict[str, str],
    value: str,
    timeout: int,
    attempts: list[str],
    row_label: str,
) -> bool:
    try:
        cell = row.locator('td[field="ROFYFT_FTSM"]').first
        if not _wait_visible(cell, 300):
            attempts.append(f"{row_label}:remark_cell_hidden")
            return False
        try:
            cell.click(timeout=300)
        except Exception:
            cell.click(timeout=300, force=True)
        page.wait_for_timeout(80)

        input_candidates = [
            cell.locator(selectors.get("city_transport_remark_input", 'td[field="ROFYFT_FTSM"] input.datagrid-editable-input.validatebox-text')).first,
            cell.locator("input.datagrid-editable-input.validatebox-text").first,
            cell.locator("input.datagrid-editable-input").first,
            cell.locator("input[type='text']").first,
            cell.locator("textarea").first,
            page.locator("input.datagrid-editable-input.validatebox-text:visible").last,
            page.locator("input.datagrid-editable-input:visible").last,
            page.locator("textarea:visible").last,
        ]
        for locator in input_candidates:
            if _wait_visible(locator, 250):
                locator.fill(value, timeout=timeout)
                attempts.append(f"{row_label}:cost_share_remark=filled")
                return True
        attempts.append(f"{row_label}:cost_share_remark=input_missing")
    except Exception as exc:
        attempts.append(f"{row_label}:cost_share_remark=error:{type(exc).__name__}")
    return _fill_detail_cell_value(
        row,
        page,
        selectors.get("city_transport_remark_input", 'td[field="ROFYFT_FTSM"] input.datagrid-editable-input.validatebox-text'),
        'td[field="ROFYFT_FTSM"]',
        value,
        timeout,
        attempts,
        row_label,
        "cost_share_remark_fallback",
    )


def _ensure_upload_files_selected(context: LocatorContext, file_paths: list[str], timeout: int) -> None:
    _ensure_upload_files_selected_base(context, file_paths, timeout)


def _ensure_upload_file_ready(context: LocatorContext, selectors: dict[str, str], timeout: int) -> None:
    _ensure_upload_file_ready_base(context, selectors, timeout, _wait_visible)


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
    _ensure_my_reimbursement_page_base(page, selectors, timeout, _is_my_reimbursement_page)


def _ensure_target_reimbursement_bill_page(page: Page, selectors: dict[str, str], bill_subtype: str, timeout: int) -> None:
    _ensure_target_reimbursement_bill_page_base(page, selectors, bill_subtype, timeout, _is_target_reimbursement_bill_page)


def _is_my_reimbursement_page(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    return _is_my_reimbursement_page_base(page, selectors, timeout, _resolve_reimbursement_context, _wait_markers_in_context)


def _is_target_reimbursement_bill_page(page: Page, selectors: dict[str, str], bill_subtype: str, timeout: int) -> bool:
    return _is_target_reimbursement_bill_page_base(
        page,
        selectors,
        bill_subtype,
        timeout,
        _has_selected_bill_tab_title,
        _resolve_bill_form_context,
        _resolve_reimbursement_context,
        _bill_page_markers,
        _wait_markers_in_context,
    )


def _is_target_reimbursement_bill_page_precheck(page: Page, selectors: dict[str, str], bill_subtype: str) -> bool:
    return _is_target_reimbursement_bill_page_precheck_base(
        page,
        selectors,
        bill_subtype,
        _has_selected_bill_tab_title,
        _get_cached_bill_form_context,
        _bill_page_markers,
        _wait_markers_in_context,
    )


def _has_selected_bill_tab_title(page: Page, bill_subtype: str, timeout: int) -> bool:
    return _has_selected_bill_tab_title_base(page, bill_subtype, timeout, _wait_visible)


def _has_selected_bill_tab_title_fast(page: Page, bill_subtype: str) -> bool:
    return _has_selected_bill_tab_title_fast_base(page, bill_subtype)


def _is_fast_clean_reimbursement_state(page: Page, selectors: dict[str, str]) -> bool:
    return _is_fast_clean_reimbursement_state_base(
        page,
        selectors,
        _resolve_image_system_context,
        _has_selected_bill_tab_title_fast,
        _get_cached_reimbursement_context,
        _resolve_reimbursement_context,
    )


def _wait_for_selected_bill_tab_title(page: Page, bill_subtype: str, timeout: int) -> bool:
    return _wait_for_selected_bill_tab_title_base(page, bill_subtype, timeout, _has_selected_bill_tab_title)


def _ensure_electronic_image_page(page: Page, selectors: dict[str, str], timeout: int) -> None:
    _ensure_electronic_image_page_base(page, selectors, timeout, _is_electronic_image_page_precheck)


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
        duplicate_message = _detect_duplicate_invoice_message(page, selectors)
        if duplicate_message:
            raise DuplicateInvoiceDetectedError(duplicate_message)
        page.wait_for_timeout(60)
    duplicate_message = _detect_duplicate_invoice_message(page, selectors)
    if duplicate_message:
        raise DuplicateInvoiceDetectedError(duplicate_message)
    raise RuntimeError(_diagnose_invoice_recognition(page, selectors))


def _detect_invoice_recognition_with_diagnostics(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
) -> None:
    logger.info(f"[TASK {task_id}] [detect_recognize_finished] START 检测识别完成")
    step_log(task_id, "detect_recognize_finished", "START 检测识别完成")
    started_at = perf_counter()
    try:
        _ensure_invoice_recognized_diagnostic(page, selectors, timeout, logger, task_id, step_log, attempt_index=1, final_attempt=False)
    except DuplicateInvoiceDetectedError:
        raise
    except Exception as first_error:
        retry_message = f"RETRY 检测识别完成 delay_ms=500 first_error={type(first_error).__name__}"
        logger.info(f"[TASK {task_id}] [detect_recognize_finished] {retry_message}")
        step_log(task_id, "detect_recognize_finished", retry_message)
        sleep(0.5)
        _ensure_invoice_recognized_diagnostic(page, selectors, timeout, logger, task_id, step_log, attempt_index=2, final_attempt=True)
    elapsed = _elapsed_ms(started_at)
    logger.info(f"[TASK {task_id}] [detect_recognize_finished] SUCCESS 检测识别完成 elapsed_ms={elapsed}")
    step_log(task_id, "detect_recognize_finished", f"SUCCESS 检测识别完成 elapsed_ms={elapsed}")


def _ensure_invoice_recognized_diagnostic(
    page: Page,
    selectors: dict[str, str],
    timeout: int,
    logger: logging.Logger,
    task_id: str,
    step_log: StepLogger,
    attempt_index: int,
    final_attempt: bool,
) -> None:
    recognize_started_at = perf_counter()
    recognize_timeout = min(timeout, 900 if attempt_index == 1 else 2600)
    recognized = _is_invoice_recognized(page, selectors, recognize_timeout)
    recognize_elapsed = _elapsed_ms(recognize_started_at)
    recognize_message = f"attempt={attempt_index} recognized={recognized} elapsed_ms={recognize_elapsed}"
    logger.info(f"[TASK {task_id}] [recognize_fast_check] INFO {recognize_message}")
    step_log(task_id, "recognize_fast_check", f"INFO {recognize_message}")

    duplicate_started_at = perf_counter()
    duplicate_observe_timeout = 900 if recognized else (1200 if attempt_index == 1 else 2600)
    duplicate_message: str | None = None
    if recognized:
        duplicate_message = _observe_duplicate_invoice_message(page, selectors, duplicate_observe_timeout)
    else:
        recognized, duplicate_message = _observe_recognition_outcome(page, selectors, duplicate_observe_timeout)
    duplicate_elapsed = _elapsed_ms(duplicate_started_at)
    duplicate_log_message = (
        f"attempt={attempt_index} duplicate_detected={bool(duplicate_message)} "
        f"recognized={recognized} elapsed_ms={duplicate_elapsed}"
    )
    logger.info(f"[TASK {task_id}] [recognize_duplicate_check] INFO {duplicate_log_message}")
    step_log(task_id, "recognize_duplicate_check", f"INFO {duplicate_log_message}")
    if duplicate_message:
        raise DuplicateInvoiceDetectedError(duplicate_message)
    if recognized:
        return
    if not final_attempt:
        raise RuntimeError("未检测到发票识别完成标志")

    diagnose_started_at = perf_counter()
    diagnosis = _diagnose_invoice_recognition(page, selectors)
    diagnose_elapsed = _elapsed_ms(diagnose_started_at)
    diagnose_message = f"attempt={attempt_index} elapsed_ms={diagnose_elapsed}"
    logger.info(f"[TASK {task_id}] [recognize_failure_diagnosis] INFO {diagnose_message}")
    step_log(task_id, "recognize_failure_diagnosis", f"INFO {diagnose_message}")
    raise RuntimeError(diagnosis)


def _observe_recognition_outcome(
    page: Page,
    selectors: dict[str, str],
    timeout_ms: int,
) -> tuple[bool, str | None]:
    return _observe_recognition_outcome_base(
        page,
        selectors,
        timeout_ms,
        _detect_duplicate_invoice_message_fast,
        _is_invoice_recognized,
    )


def _ensure_reimbursement_saved(page: Page, selectors: dict[str, str], timeout: int) -> None:
    _ensure_reimbursement_saved_base(page, selectors, timeout, _is_reimbursement_saved)


def _ensure_electronic_image_tab_closed(page: Page, selectors: dict[str, str], timeout: int) -> None:
    closed = _wait_for_selected_tab_closed_base(page, "电子影像", timeout, 50) or (
        not _is_electronic_image_page(page, selectors, 120)
    )
    if not closed:
        raise RuntimeError("电子影像页签关闭后仍然处于激活状态")


def _is_electronic_image_page(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    return _is_electronic_image_page_base(
        page,
        selectors,
        timeout,
        _resolve_image_system_context,
        _candidate_bill_contexts,
        _wait_visible,
    )


def _is_electronic_image_page_precheck(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    return _is_electronic_image_page_precheck_base(
        page,
        selectors,
        timeout,
        _get_cached_electronic_image_context,
        _get_cached_bill_form_context,
        _get_cached_reimbursement_context,
        _wait_visible,
    )


def _is_reimbursement_saved(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    return _is_reimbursement_saved_base(
        page,
        selectors,
        timeout,
        _candidate_bill_contexts,
        _wait_markers_in_context,
        _wait_any_marker,
    )


def _ensure_upload_dialog_open(page: Page, selectors: dict[str, str], timeout: int) -> None:
    _ensure_upload_dialog_open_base(page, selectors, timeout, _is_upload_dialog_open, _diagnose_upload_dialog)


def _is_upload_dialog_open(page: Page, selectors: dict[str, str], timeout: int) -> bool:
    return _is_upload_dialog_open_base(
        page,
        selectors,
        timeout,
        _resolve_electronic_image_context,
        _resolve_upload_dialog_context,
        _count_visible_elements,
    )


def _ensure_reimbursement_bill_tab_closed(page: Page, selectors: dict[str, str], timeout: int) -> None:
    _ensure_reimbursement_bill_tab_closed_base(page, selectors, timeout, _is_my_reimbursement_page)


def _diagnose_upload_dialog(page: Page, selectors: dict[str, str]) -> str:
    return _diagnose_upload_dialog_base(
        page,
        selectors,
        _resolve_electronic_image_context,
        _resolve_upload_dialog_context,
        _count_visible_elements,
        _wait_visible,
    )


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
        '.layui-layer-content:has-text("识别成功")',
        'div.layui-layer-content:has-text("识别成功")',
        'text=识别成功！',
        'text=识别成功',
    ]
    contexts = _primary_recognition_contexts(page, selectors)
    end_at = perf_counter() + (timeout / 1000)
    while perf_counter() < end_at:
        for context in contexts:
            for selector in toast_markers:
                if not selector:
                    continue
                try:
                    if _wait_visible(context.locator(selector).first, 30):
                        return True
                except Exception:
                    continue
        page.wait_for_timeout(40)
    return False


def _primary_recognition_contexts(page: Page, selectors: dict[str, str]) -> list[LocatorContext]:
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

    add(_resolve_selector_context(page, selectors, "recognize_success_toast"))
    add(_resolve_selector_context(page, selectors, "recognize_success_marker"))
    add(_resolve_selector_context(page, selectors, "recognize_button"))
    add(_get_cached_electronic_image_context(page))
    add(_resolve_image_system_context(page))
    add(_resolve_electronic_image_context(page, selectors))
    return contexts


def _locator_has_non_empty_value(locator) -> bool:
    return _locator_has_non_empty_value_base(locator)


def _detect_duplicate_invoice_message(page: Page, selectors: dict[str, str]) -> str | None:
    return _detect_duplicate_invoice_message_in_contexts(
        page,
        selectors,
        timeout_ms=180,
        include_all_candidates=True,
        broad_selectors=True,
    )


def _detect_duplicate_invoice_message_fast(page: Page, selectors: dict[str, str], timeout_ms: int) -> str | None:
    return _detect_duplicate_invoice_message_in_contexts(
        page,
        selectors,
        timeout_ms=timeout_ms,
        include_all_candidates=False,
        broad_selectors=False,
    )


def _detect_duplicate_invoice_message_in_contexts(
    page: Page,
    selectors: dict[str, str],
    timeout_ms: int,
    include_all_candidates: bool,
    broad_selectors: bool,
) -> str | None:
    duplicate_selectors = [
        selectors.get("duplicate_invoice_marker", ""),
        "#txtDuplicate",
        "#txtDuplicate span",
        "#txtDuplicate *",
        "text=发票重复",
    ]
    if broad_selectors:
        duplicate_selectors.extend(
            [
                'xpath=//*[contains(normalize-space(.),"发票重复")]',
                'xpath=//*[contains(normalize-space(.),"重复报销")]',
                'xpath=//*[contains(normalize-space(.),"已报销")]',
                'xpath=//*[contains(normalize-space(.),"已经报销")]',
                'xpath=//*[contains(normalize-space(.),"已使用")]',
            ]
        )
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

    add(_resolve_selector_context(page, selectors, "duplicate_invoice_marker"))
    add(_get_cached_electronic_image_context(page))
    add(_resolve_image_system_context(page))
    add(_resolve_electronic_image_context(page, selectors))
    if include_all_candidates:
        for context in _candidate_recognition_contexts(page, selectors):
            add(context)
        add(page)

    per_locator_timeout = max(20, min(timeout_ms, 40))
    for context in contexts:
        for selector in duplicate_selectors:
            if not selector:
                continue
            try:
                locator = context.locator(selector)
                if locator.count() <= 0:
                    continue
                for index in range(min(locator.count(), 8)):
                    candidate = locator.nth(index)
                    text = _duplicate_invoice_locator_text(candidate, per_locator_timeout)
                    if _looks_like_duplicate_invoice_message(text):
                        return _format_duplicate_invoice_message(text)
                    try:
                        visible = _wait_visible(candidate, per_locator_timeout)
                    except Exception:
                        visible = False
                    if visible and selector in {"#txtDuplicate", "#txtDuplicate span", "#txtDuplicate *", "text=发票重复"}:
                        return "发票重复，已中止当前报销单录入"
            except Exception:
                continue
    return None


def _duplicate_invoice_locator_text(locator, timeout_ms: int) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for getter in (
        lambda: locator.inner_text(timeout=timeout_ms),
        lambda: locator.text_content(timeout=timeout_ms),
        lambda: locator.input_value(timeout=timeout_ms),
        lambda: locator.get_attribute("value", timeout=timeout_ms),
        lambda: locator.get_attribute("title", timeout=timeout_ms),
        lambda: locator.get_attribute("data-original-title", timeout=timeout_ms),
    ):
        try:
            value = getter()
        except Exception:
            continue
        if value:
            normalized = " ".join(str(value).split())
            if normalized and normalized not in seen:
                seen.add(normalized)
                values.append(normalized)
    return " ".join(value for value in values if value)


def _looks_like_duplicate_invoice_message(text: str) -> bool:
    normalized = " ".join((text or "").split())
    if not normalized:
        return False
    duplicate_keywords = ("发票重复", "重复报销", "重复提交", "已报销", "已经报销", "已使用")
    return any(keyword in normalized for keyword in duplicate_keywords)


def _format_duplicate_invoice_message(text: str) -> str:
    normalized = " ".join((text or "").split())
    return f"{normalized or '发票重复'}，已中止当前报销单录入"


def _observe_duplicate_invoice_message(page: Page, selectors: dict[str, str], timeout_ms: int) -> str | None:
    end_at = perf_counter() + (timeout_ms / 1000)
    while perf_counter() < end_at:
        duplicate_message = _detect_duplicate_invoice_message_fast(page, selectors, 40)
        if duplicate_message:
            return duplicate_message
        page.wait_for_timeout(40)
    return None


def _diagnose_invoice_recognition(page: Page, selectors: dict[str, str]) -> str:
    attempts: list[str] = []
    marker_checks = [
        ("recognize_success_toast", selectors.get("recognize_success_toast", "") or '.layui-layer.layui-layer-msg .layui-layer-content'),
        ("recognize_success_toast_fallback", '.layui-layer-content:has-text("识别成功")'),
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
                        visible = _wait_visible(locator.first, 60)
                        attempts.append(f"{context_name}:{label}:visible={visible}")
                    except Exception as exc:
                        attempts.append(f"{context_name}:{label}:visible=error:{type(exc).__name__}")
            except Exception as exc:
                attempts.append(f"{context_name}:{label}:count=error:{type(exc).__name__}")
    return f"未检测到发票识别完成标志 attempts={attempts}"




def _page_candidates(page: Page):
    return _page_candidates_base(page)


def _cache_active_working_page(page: Page, working_page: Page | None) -> None:
    _cache_active_working_page_base(page, working_page)


def _get_cached_active_working_page(page: Page) -> Page | None:
    return _get_cached_active_working_page_base(page)


def _resolve_task_entry_page(page: Page, selectors: dict[str, str]) -> tuple[Page, str, str]:
    attempts: list[str] = []
    cached_page = _get_cached_active_working_page(page)
    if cached_page is not None:
        try:
            cached_url = getattr(cached_page, "url", "")
        except Exception:
            cached_url = ""
        try:
            if _is_my_reimbursement_page(cached_page, selectors, 300):
                attempts.append(f"cached:my_reimbursement:url={cached_url}")
                return cached_page, "my_reimbursement", f"复用缓存工作页 attempts={attempts}"
        except Exception as exc:
            attempts.append(f"cached:my_reimbursement:error={type(exc).__name__}:url={cached_url}")
        finance_ready_selectors = [
            selectors.get("menu_finance_share", ""),
            selectors.get("go_reimbursement_button", ""),
        ]
        try:
            if _is_finance_share_page(cached_page, finance_ready_selectors):
                attempts.append(f"cached:finance_share:url={cached_url}")
                return cached_page, "finance_share", f"复用缓存工作页 attempts={attempts}"
        except Exception as exc:
            attempts.append(f"cached:finance_share:error={type(exc).__name__}:url={cached_url}")

    try:
        browser_pages = [candidate for candidate in page.context.pages if not candidate.is_closed()]
    except Exception:
        browser_pages = [page]
    if page not in browser_pages:
        browser_pages.insert(0, page)

    finance_ready_selectors = [
        selectors.get("menu_finance_share", ""),
        selectors.get("go_reimbursement_button", ""),
    ]

    for index, candidate in enumerate(reversed(browser_pages)):
        try:
            candidate.wait_for_load_state("domcontentloaded", timeout=150)
        except Exception:
            pass
        label = f"tab[{len(browser_pages) - 1 - index}]"
        try:
            url = getattr(candidate, "url", "")
        except Exception:
            url = ""
        try:
            if _is_my_reimbursement_page(candidate, selectors, 300):
                attempts.append(f"{label}:my_reimbursement:url={url}")
                return candidate, "my_reimbursement", f"复用已有页面 attempts={attempts}"
        except Exception as exc:
            attempts.append(f"{label}:my_reimbursement:error={type(exc).__name__}:url={url}")
            continue
        try:
            if _is_finance_share_page(candidate, finance_ready_selectors):
                attempts.append(f"{label}:finance_share:url={url}")
                return candidate, "finance_share", f"复用已有页面 attempts={attempts}"
        except Exception as exc:
            attempts.append(f"{label}:finance_share:error={type(exc).__name__}:url={url}")
            continue
        attempts.append(f"{label}:other:url={url}")

    return page, "unknown", f"未命中可复用页面，沿用当前页 attempts={attempts}"


def _context_debug_name(context: LocatorContext, index: int) -> str:
    return _context_debug_name_base(context, index)


def _attempt_finance_share_activation(page: Page, action, finance_ready_selectors: list[str], timeout: int) -> Page | None:
    return _attempt_finance_share_activation_base(page, action, finance_ready_selectors, timeout, _is_finance_share_page)


def _safe_click_target(target, timeout: int, force: bool = False) -> None:
    _safe_click_target_base(target, timeout, force=force)


def _visible_tree_node(page: Page, text: str):
    return _visible_tree_node_base(page, text)


def _ensure_tree_node_expanded(page: Page, text: str, timeout: int) -> None:
    _ensure_tree_node_expanded_base(page, text, timeout)


def _click_tree_title_fast(page: Page, text: str, timeout: int) -> None:
    _click_tree_title_fast_base(page, text, timeout, _wait_visible)


def _click_go_reimbursement_fast(page: Page, selector: str, timeout: int) -> None:
    _click_go_reimbursement_fast_base(page, selector, timeout, _click_locator_fast)


def _click_locator_fast(context: LocatorContext, page: Page, selector: str, timeout: int, error_message: str) -> None:
    _click_locator_fast_base(context, page, selector, timeout, error_message)


def _click_latest_visible_element(context: LocatorContext, selector: str) -> bool:
    return _click_latest_visible_element_base(context, selector)


def _count_visible_elements(context: LocatorContext, selector: str) -> int:
    return _count_visible_elements_base(context, selector)


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
    return _wait_iam_login_state_base(username_locator, finance_locator, timeout_ms, _wait_visible)


def _ensure_visible(locator, timeout_ms: int, error_message: str) -> None:
    _ensure_visible_base(locator, timeout_ms, error_message)


def _click_optional(locator) -> None:
    _click_optional_base(locator)


def _activate_by_keyboard(page, locator) -> None:
    _activate_by_keyboard_base(page, locator)


def _is_finance_share_page(page: Page, selectors: list[str]) -> bool:
    return _is_finance_share_page_base(page, selectors, _wait_visible)


def _wait_visible(locator, timeout_ms: int) -> bool:
    return _wait_visible_base(locator, timeout_ms)


__all__ = [
    "ReimbursementFillFlow",
    "capture_screenshot",
    "initialize_batch_session",
    "reset_task_context",
    "run_task",
]
