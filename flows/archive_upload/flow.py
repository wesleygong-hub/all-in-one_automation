from __future__ import annotations

from dataclasses import dataclass

from dsn_uploader.workflow import (
    capture_screenshot,
    initialize_batch_session,
    reset_task_context,
    run_task,
)
from flows.archive_upload.task_loader import load_tasks, validate_tasks


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
