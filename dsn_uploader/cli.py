from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dsn_uploader.config import ensure_runtime_dirs, load_config
from dsn_uploader.db import (
    connect,
    fetch_batch_summary,
    init_db,
    insert_operation_log,
    insert_task_run,
)
from dsn_uploader.logging_utils import print_block, setup_logger
from dsn_uploader.tasks import TaskResultWriteError, load_tasks, validate_tasks, write_task_result


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    logger = setup_logger()
    if args.command == "validate":
        return cmd_validate(args, logger)
    if args.command == "run":
        return cmd_run(args, logger)
    if args.command == "report":
        return cmd_report(args, logger)
    parser.print_help()
    return 1


def cmd_validate(args: argparse.Namespace, logger: logging.Logger) -> int:
    config = load_config(args.config)
    ensure_runtime_dirs(config)
    tasks = load_tasks(args.tasks)
    errors = validate_tasks(tasks)

    if errors:
        print_block(logger, ["[VALIDATE] failed"] + [f"- {item}" for item in errors])
        return 1

    print_block(
        logger,
        [
            "[VALIDATE] success",
            f"- task_count: {len(tasks)}",
            f"- sqlite_path: {config['paths']['sqlite_path']}",
            f"- screenshot_dir: {config['paths']['screenshot_dir']}",
            f"- report_dir: {config['paths']['report_dir']}",
        ],
    )
    return 0


def cmd_run(args: argparse.Namespace, logger: logging.Logger) -> int:
    from dsn_uploader.browser import open_browser
    from dsn_uploader.workflow import capture_screenshot, initialize_batch_session, reset_task_context, run_task

    config = load_config(args.config)
    ensure_runtime_dirs(config)
    tasks = load_tasks(args.tasks)
    errors = validate_tasks(tasks)
    if errors:
        print_block(logger, ["[RUN] task validation failed"] + [f"- {item}" for item in errors])
        return 1

    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    started_at = datetime.now().isoformat(timespec="seconds")
    print_block(
        logger,
        [
            f"[BATCH] start batch_id={batch_id}",
            f"[BATCH] tasks={len(tasks)} headed={args.headed or config['system'].get('headed', True)}",
        ],
    )

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

        success = 0
        failed = 0
        result_file_to_open = str(Path(args.tasks).resolve())
        headed = args.headed or bool(config["system"].get("headed", True))
        with open_browser(
            headed=headed,
            browser_channel=config["system"].get("browser_channel") or None,
            executable_path=config["system"].get("browser_executable_path") or None,
        ) as (_, _, page):
            initialize_batch_session(page, config, logger)
            for index, task in enumerate(tasks, start=1):
                start_time = datetime.now().isoformat(timespec="seconds")
                logger.info(f"[TASK {index}/{len(tasks)}] start {task.task_id}")
                screenshot_path = None
                result = run_task(page, config, task, logger, step_log)
                if result.status != "success" and config["runtime"].get("screenshot_on_error", True):
                    try:
                        screenshot_path = capture_screenshot(page, config["paths"]["screenshot_dir"], task)
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
                    writeback_path = write_task_result(
                        args.tasks,
                        task,
                        _format_task_result_cell(result.status, result.message),
                    )
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

                reset_task_context(page, config, logger, task.task_id)

            report_path = _write_report(
                report_dir=config["paths"]["report_dir"],
                batch_id=batch_id,
                started_at=started_at,
                task_count=len(tasks),
                success=success,
                failed=failed,
            )
            logger.info(f"[SUMMARY] total={len(tasks)} success={success} failed={failed}")
            logger.info(f"[SUMMARY] report={report_path}")
            _open_result_file(logger, result_file_to_open)
            _hold_browser_open(logger, headed)
    return 0 if failed == 0 else 1


def cmd_report(args: argparse.Namespace, logger: logging.Logger) -> int:
    config = load_config(args.config)
    ensure_runtime_dirs(config)
    with connect(config["paths"]["sqlite_path"]) as conn:
        init_db(conn)
        rows = fetch_batch_summary(conn, args.batch_id)
    if not rows:
        logger.info("[REPORT] no batch data found")
        return 0
    current_batch = None
    for row in rows:
        batch_id = row["batch_id"]
        if batch_id != current_batch:
            logger.info(f"[REPORT] batch_id={batch_id}")
            current_batch = batch_id
        logger.info(f"- {row['status']}: {row['count']}")
    return 0


def _write_report(
    report_dir: str,
    batch_id: str,
    started_at: str,
    task_count: int,
    success: int,
    failed: int,
) -> str:
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


def _open_result_file(logger: logging.Logger, file_path: str) -> None:
    try:
        os.startfile(file_path)
        logger.info(f"[SUMMARY] results_opened={file_path}")
    except Exception as exc:
        logger.warning(f"[SUMMARY] results_open_warning={exc}")


def _hold_browser_open(logger: logging.Logger, headed: bool) -> None:
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


def _extract_fallback_result_path(message: str) -> str | None:
    marker = "已写入备用文件:"
    if marker not in message:
        return None
    return message.split(marker, 1)[1].strip()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DSN archive upload CLI POC")
    subparsers = parser.add_subparsers(dest="command")

    validate = subparsers.add_parser("validate", help="Validate task file and config")
    validate.add_argument("--config", required=True)
    validate.add_argument("--tasks", required=True)

    run = subparsers.add_parser("run", help="Run browser automation")
    run.add_argument("--config", required=True)
    run.add_argument("--tasks", required=True)
    run.add_argument("--headed", action="store_true")

    report = subparsers.add_parser("report", help="Show batch summary")
    report.add_argument("--config", required=True)
    report.add_argument("--batch-id")
    return parser
