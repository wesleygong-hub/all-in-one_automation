from __future__ import annotations

import argparse
import logging
import os

from automation.config.loader import ensure_runtime_dirs, load_config
from automation.runtime.executor import execute_batch, report_batch
from automation.runtime.logger import print_block, setup_logger
from flows.archive_upload import ArchiveUploadFlow


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
    config = load_config(args.config, validate_auth=False)
    ensure_runtime_dirs(config)
    flow = _resolve_flow(args.flow)
    tasks = flow.load_tasks(args.tasks)
    errors = flow.validate_tasks(tasks)

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
    config = load_config(args.config)
    ensure_runtime_dirs(config)
    flow = _resolve_flow(args.flow)

    print_block(
        logger,
        [
            f"[RUN] flow={flow.name}",
            f"[RUN] headed={args.headed or config['system'].get('headed', True)}",
        ],
    )
    try:
        summary = execute_batch(
            flow=flow,
            config=config,
            tasks_path=args.tasks,
            headed=args.headed or bool(config["system"].get("headed", True)),
            logger=logger,
            keep_browser_open=True,
            before_hold=lambda path: _open_result_file(logger, path),
        )
    except RuntimeError as exc:
        print_block(logger, [str(exc)])
        return 1

    logger.info(f"[SUMMARY] total={summary.task_count} success={summary.success} failed={summary.failed}")
    logger.info(f"[SUMMARY] report={summary.report_path}")
    return 0 if summary.failed == 0 else 1


def cmd_report(args: argparse.Namespace, logger: logging.Logger) -> int:
    config = load_config(args.config)
    ensure_runtime_dirs(config)
    rows = report_batch(config, args.batch_id)
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


def _open_result_file(logger: logging.Logger, file_path: str) -> None:
    try:
        os.startfile(file_path)
        logger.info(f"[SUMMARY] results_opened={file_path}")
    except Exception as exc:
        logger.warning(f"[SUMMARY] results_open_warning={exc}")


def _resolve_flow(flow_name: str | None):
    if not flow_name or flow_name == "archive-upload":
        return ArchiveUploadFlow()
    raise RuntimeError(f"Unsupported flow: {flow_name}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DSN archive upload CLI POC")
    subparsers = parser.add_subparsers(dest="command")

    validate = subparsers.add_parser("validate", help="Validate task file and config")
    validate.add_argument("flow", nargs="?", default="archive-upload")
    validate.add_argument("--config", required=True)
    validate.add_argument("--tasks", required=True)

    run = subparsers.add_parser("run", help="Run browser automation")
    run.add_argument("flow", nargs="?", default="archive-upload")
    run.add_argument("--config", required=True)
    run.add_argument("--tasks", required=True)
    run.add_argument("--headed", action="store_true")

    report = subparsers.add_parser("report", help="Show batch summary")
    report.add_argument("--config", required=True)
    report.add_argument("--batch-id")
    return parser


__all__ = [
    "cmd_report",
    "cmd_run",
    "cmd_validate",
    "main",
]
