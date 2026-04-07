from __future__ import annotations

import csv
from pathlib import Path

from dsn_uploader.models import REQUIRED_TASK_FIELDS, TaskRecord


class TaskResultWriteError(RuntimeError):
    pass


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


def write_task_result(task_path: str, task: TaskRecord, result_text: str) -> str:
    path = Path(task_path).resolve()
    rows = _load_task_rows(path)
    _apply_result_to_rows(rows, task, result_text)

    try:
        _write_task_rows(path, rows)
        return str(path)
    except PermissionError as exc:
        fallback_path = path.with_name(f"{path.stem}.result{path.suffix}")
        try:
            _write_task_rows(fallback_path, rows)
            raise TaskResultWriteError(
                f"任务结果无法写回原文件，可能正被占用；已写入备用文件: {fallback_path}"
            ) from exc
        except Exception as fallback_exc:
            raise TaskResultWriteError(
                f"任务结果无法写回原文件，且备用文件写入失败: {fallback_path}"
            ) from fallback_exc


def _load_task_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    return rows


def _apply_result_to_rows(rows: list[list[str]], task: TaskRecord, result_text: str) -> None:
    target_index = task.source_row - 1
    if target_index < 0 or target_index >= len(rows):
        raise RuntimeError(f"task row out of range: {task.source_row}")

    row = rows[target_index]
    while len(row) < 7:
        row.append("")
    row[6] = result_text

    if rows:
        while len(rows[0]) < 7:
            rows[0].append("")
        rows[0][6] = "upload_result"
    if len(rows) > 1:
        while len(rows[1]) < 7:
            rows[1].append("")
        if not rows[1][6]:
            rows[1][6] = "上传结果"


def _write_task_rows(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)


def _is_description_row(row: dict[str, str | None]) -> bool:
    task_id = (row.get("task_id") or "").strip()
    employee_id = (row.get("employee_id") or "").strip()
    return task_id == "任务唯一编号" and employee_id == "人员编号/工号"
