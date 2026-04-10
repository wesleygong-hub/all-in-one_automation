from __future__ import annotations

import csv
from pathlib import Path

from flows.archive_upload.task_model import REQUIRED_TASK_FIELDS, TaskRecord


def load_tasks(task_path: str) -> list[TaskRecord]:
    path = Path(task_path).resolve()
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    tasks: list[TaskRecord] = []
    for idx, row in enumerate(rows, start=2):
        if _is_description_row(row):
            continue
        tasks.append(
            TaskRecord(
                task_id=(row.get("task_id") or "").strip(),
                employee_id=(row.get("employee_id") or "").strip(),
                employee_name=(row.get("employee_name") or "").strip(),
                business_line=(row.get("business_line") or "").strip(),
                business_type=(row.get("business_type") or "").strip(),
                file_path=(row.get("file_path") or "").strip(),
                source_row=idx,
            )
        )
    return tasks


def validate_tasks(tasks: list[TaskRecord]) -> list[str]:
    errors: list[str] = []
    for task in tasks:
        for field in REQUIRED_TASK_FIELDS:
            value = getattr(task, field)
            if not value:
                errors.append(f"row {task.source_row}: `{field}` is required")
    return errors


def _is_description_row(row: dict[str, str | None]) -> bool:
    task_id = (row.get("task_id") or "").strip()
    employee_id = (row.get("employee_id") or "").strip()
    return task_id == "任务唯一编号" and employee_id == "人员编号/工号"


__all__ = ["load_tasks", "validate_tasks"]
