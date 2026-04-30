from __future__ import annotations

import logging
from typing import Callable

from automation.core.contexts import cache_browser_context_value
from automation.runtime.steps import StepLogger, log_task_step


FailureAction = Callable[[], str | list[str] | None]


def handle_task_failure(
    page,
    task,
    logger: logging.Logger,
    step_log: StepLogger,
    exc: Exception,
    capture_screenshot: FailureAction,
    cleanup: FailureAction,
    screenshot_cache_key: str = "_last_failure_screenshot_path",
) -> None:
    log_task_step(logger, step_log, task, "task_failure_guard", "START", f"处理未预期失败 {type(exc).__name__}: {exc}")
    try:
        failure_screenshot_path = capture_screenshot()
        cache_browser_context_value(page, screenshot_cache_key, failure_screenshot_path)
        log_task_step(logger, step_log, task, "capture_failure_screenshot", "SUCCESS", str(failure_screenshot_path))
    except Exception as screenshot_exc:
        cache_browser_context_value(page, screenshot_cache_key, None)
        log_task_step(logger, step_log, task, "capture_failure_screenshot", "FAILED", str(screenshot_exc))

    try:
        actions = cleanup()
        cleanup_message = _format_cleanup_result(actions)
        log_task_step(logger, step_log, task, "cleanup_failed_task", "SUCCESS", cleanup_message)
    except Exception as cleanup_exc:
        task_id = getattr(task, "task_id", task)
        logger.exception(f"[TASK {task_id}] [cleanup_failed_task] FAILED {cleanup_exc}")
        log_task_step(logger, step_log, task, "cleanup_failed_task", "FAILED", str(cleanup_exc))

    log_task_step(logger, step_log, task, "task_failure_guard", "FAILED", f"{type(exc).__name__}: {exc}")


def _format_cleanup_result(actions: str | list[str] | None) -> str:
    if actions is None:
        return "no_action"
    if isinstance(actions, str):
        return actions or "no_action"
    return "|".join(str(action) for action in actions) if actions else "no_action"


__all__ = ["handle_task_failure"]
