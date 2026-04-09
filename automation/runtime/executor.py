from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import sys
from typing import Protocol

from automation.browser.session import open_browser
from automation.storage.db import (
    connect,
    fetch_batch_summary,
    init_db,
    insert_operation_log,
    insert_task_run,
)
from automation.storage.task_writer import TaskResultWriteError, write_task_result


class Flow(Protocol):
    name: str

    def load_tasks(self, task_path: str) -> list[object]: ...

    def validate_tasks(self, tasks: list[object]) -> list[str]: ...

    def initialize_batch_session(self, page, config: dict, logger) -> None: ...

    def run_task(self, page, config: dict, task, logger, step_log): ...

    def capture_screenshot(self, page, screenshot_dir: str, task) -> str: ...

    def reset_task_context(self, page, config: dict, logger, task_id: str) -> None: ...


@dataclass(slots=True)
class BatchSummary:
    batch_id: str
    started_at: str
    task_count: int
    success: int
    failed: int
    report_path: str
    result_file_to_open: str


class BeforeHoldHook(Protocol):
    def __call__(self, result_file_to_open: str) -> None: ...


def execute_batch(
    flow: Flow,
    config: dict,
    tasks_path: str,
    headed: bool,
    logger,
    keep_browser_open: bool = False,
    before_hold: BeforeHoldHook | None = None,
) -> BatchSummary:
    tasks = flow.load_tasks(tasks_path)
    errors = flow.validate_tasks(tasks)
    if errors:
        raise RuntimeError("[RUN] task validation failed\n" + "\n".join(f"- {item}" for item in errors))

    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    started_at = datetime.now().isoformat(timespec="seconds")
    success = 0
    failed = 0
    result_file_to_open = str(Path(tasks_path).resolve())

    with connect(config["paths"]["sqlite_path"]) as conn:
        init_db(conn)

        def step_log(task_id: str, step_name: str, message: str) -> None:
            insert_operation_log(
                conn=conn,
                batch_id=batch_id,
                task_id=task_id,
                step_name=step_name,
                status="INFO",
                message=message,
                created_at=datetime.now().isoformat(timespec="seconds"),
            )

        with open_browser(
            headed=headed,
            browser_channel=config["system"].get("browser_channel") or None,
            executable_path=config["system"].get("browser_executable_path") or None,
        ) as (_, _, page):
            flow.initialize_batch_session(page, config, logger)
            for index, task in enumerate(tasks, start=1):
                start_time = datetime.now().isoformat(timespec="seconds")
                logger.info(f"[TASK {index}/{len(tasks)}] start {task.task_id}")
                screenshot_path = None
                result = flow.run_task(page, config, task, logger, step_log)
                if result.status != "success" and config["runtime"].get("screenshot_on_error", True):
                    try:
                        screenshot_path = flow.capture_screenshot(page, config["paths"]["screenshot_dir"], task)
                    except Exception:
                        screenshot_path = None
                end_time = datetime.now().isoformat(timespec="seconds")
                insert_task_run(
                    conn=conn,
                    batch_id=batch_id,
                    task=task,
                    status=result.status,
                    message=result.message,
                    screenshot_path=screenshot_path,
                    start_time=start_time,
                    end_time=end_time,
                )
                try:
                    writeback_path = write_task_result(tasks_path, task, _format_task_result_cell(result.status, result.message))
                    result_file_to_open = writeback_path
                    logger.info(f"[TASK {task.task_id}] result_written={writeback_path}")
                except TaskResultWriteError as exc:
                    fallback_hint = _extract_fallback_result_path(str(exc))
                    if fallback_hint:
                        result_file_to_open = fallback_hint
                    logger.warning(f"[TASK {task.task_id}] result_write_warning={exc}")

                if result.status == "success":
                    success += 1
                else:
                    failed += 1
                    logger.info(f"[TASK {task.task_id}] FAILED {result.message}")
                    if screenshot_path:
                        logger.info(f"[TASK {task.task_id}] screenshot={screenshot_path}")

                flow.reset_task_context(page, config, logger, task.task_id)

            report_path = _write_report(
                report_dir=config["paths"]["report_dir"],
                batch_id=batch_id,
                started_at=started_at,
                task_count=len(tasks),
                success=success,
                failed=failed,
            )
            if keep_browser_open:
                if before_hold is not None:
                    before_hold(result_file_to_open)
                _hold_browser_open(logger, headed)

    return BatchSummary(
        batch_id=batch_id,
        started_at=started_at,
        task_count=len(tasks),
        success=success,
        failed=failed,
        report_path=report_path,
        result_file_to_open=result_file_to_open,
    )


def report_batch(config: dict, batch_id: str | None):
    with connect(config["paths"]["sqlite_path"]) as conn:
        init_db(conn)
        return fetch_batch_summary(conn, batch_id)


def _write_report(
    report_dir: str,
    batch_id: str,
    started_at: str,
    task_count: int,
    success: int,
    failed: int,
) -> str:
    import json

    path = Path(report_dir) / f"{batch_id}.json"
    payload = {
        "batch_id": batch_id,
        "started_at": started_at,
        "task_count": task_count,
        "success": success,
        "failed": failed,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _format_task_result_cell(status: str, message: str) -> str:
    if status == "success":
        return "success"
    compact_message = " ".join((message or "").split())
    if len(compact_message) > 120:
        compact_message = compact_message[:117] + "..."
    return f"failed: {compact_message}" if compact_message else "failed"


def _extract_fallback_result_path(message: str) -> str | None:
    marker = "已写入备用文件:"
    if marker not in message:
        return None
    return message.split(marker, 1)[1].strip()


def _hold_browser_open(logger, headed: bool) -> None:
    if not headed:
        return
    if not sys.stdin or not sys.stdin.isatty():
        return
    logger.info("[SUMMARY] 浏览器保持打开。查看完成后按任意键关闭浏览器并结束程序。")
    if os.name == "nt":
        try:
            import msvcrt

            msvcrt.getwch()
            return
        except Exception:
            pass
    try:
        input()
    except EOFError:
        pass
