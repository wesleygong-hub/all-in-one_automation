from __future__ import annotations

import csv
from pathlib import Path

from flows.archive_upload.task_model import TaskRecord


class TaskResultWriteError(RuntimeError):
    pass


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


__all__ = ["TaskResultWriteError", "write_task_result"]
