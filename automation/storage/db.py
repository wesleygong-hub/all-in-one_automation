from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from flows.archive_upload.task_model import TaskRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS task_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    employee_id TEXT,
    employee_name TEXT,
    business_line TEXT,
    business_type TEXT,
    file_path TEXT,
    status TEXT NOT NULL,
    message TEXT,
    screenshot_path TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    source_row INTEGER
);

CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    created_at TEXT NOT NULL
);
"""


@contextmanager
def connect(db_path: str) -> Iterator[sqlite3.Connection]:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    sqlite_path = _resolve_sqlite_path(db_path)
    conn = sqlite3.connect(sqlite_path)
    try:
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()


def _resolve_sqlite_path(db_path: str) -> str:
    primary = _sqlite_safe_path(db_path)
    if _can_use_sqlite_path(primary):
        return primary
    fallback = _fallback_sqlite_path(db_path)
    Path(fallback).parent.mkdir(parents=True, exist_ok=True)
    return fallback


def _can_use_sqlite_path(db_path: str) -> bool:
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS __dsn_healthcheck (x INTEGER)")
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def _sqlite_safe_path(db_path: str) -> str:
    if os.name != "nt":
        return db_path
    try:
        return _get_short_path(db_path)
    except Exception:
        return db_path


def _get_short_path(path: str) -> str:
    import ctypes

    resolved = Path(path).resolve()
    parent = resolved.parent
    name = resolved.name
    buffer_size = 260
    output = ctypes.create_unicode_buffer(buffer_size)
    result = ctypes.windll.kernel32.GetShortPathNameW(str(parent), output, buffer_size)
    if result == 0:
        raise OSError(f"failed to resolve short path: {parent}")
    return str(Path(output.value) / name)


def _fallback_sqlite_path(original_path: str) -> str:
    digest = hashlib.sha1(str(Path(original_path).resolve()).encode("utf-8")).hexdigest()[:8]
    base = Path(tempfile.gettempdir()) / "dsn_uploader_sqlite"
    return str((base / f"runtime_{digest}.db").resolve())


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def insert_task_run(
    conn: sqlite3.Connection,
    batch_id: str,
    task: TaskRecord,
    status: str,
    message: str,
    screenshot_path: str | None,
    start_time: str,
    end_time: str,
) -> None:
    conn.execute(
        """
        INSERT INTO task_runs (
            batch_id, task_id, employee_id, employee_name, business_line, business_type,
            file_path, status, message, screenshot_path, start_time, end_time, source_row
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            batch_id,
            task.task_id,
            task.employee_id,
            task.employee_name,
            task.business_line,
            task.business_type,
            task.file_path,
            status,
            message,
            screenshot_path,
            start_time,
            end_time,
            task.source_row,
        ),
    )
    conn.commit()


def insert_operation_log(
    conn: sqlite3.Connection,
    batch_id: str,
    task_id: str,
    step_name: str,
    status: str,
    message: str,
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO operation_logs (batch_id, task_id, step_name, status, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (batch_id, task_id, step_name, status, message, created_at),
    )
    conn.commit()


def fetch_batch_summary(conn: sqlite3.Connection, batch_id: str | None = None) -> list[sqlite3.Row]:
    if batch_id:
        return conn.execute(
            """
            SELECT batch_id, status, COUNT(*) AS count
            FROM task_runs
            WHERE batch_id = ?
            GROUP BY batch_id, status
            ORDER BY batch_id DESC, status
            """,
            (batch_id,),
        ).fetchall()
    return conn.execute(
        """
        SELECT batch_id, status, COUNT(*) AS count
        FROM task_runs
        GROUP BY batch_id, status
        ORDER BY batch_id DESC, status
        """
    ).fetchall()


__all__ = [
    "connect",
    "fetch_batch_summary",
    "init_db",
    "insert_operation_log",
    "insert_task_run",
]
