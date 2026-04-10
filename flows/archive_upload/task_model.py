from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


REQUIRED_TASK_FIELDS = (
    "task_id",
    "employee_id",
    "business_line",
    "business_type",
    "file_path",
)


@dataclass(slots=True)
class TaskRecord:
    task_id: str
    employee_id: str
    employee_name: str
    business_line: str
    business_type: str
    file_path: str
    source_row: int

    @property
    def file_name(self) -> str:
        return Path(self.file_path).name


@dataclass(slots=True)
class TaskResult:
    status: str
    message: str
    screenshot_path: str | None = None


__all__ = ["REQUIRED_TASK_FIELDS", "TaskRecord", "TaskResult"]
