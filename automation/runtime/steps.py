from __future__ import annotations

import logging
from time import perf_counter, sleep
from typing import Callable


StepLogger = Callable[[str, str, str], None]
NonRetryableExceptions = tuple[type[Exception], ...]


def elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


def log_task_step(
    logger: logging.Logger,
    step_log: StepLogger,
    task_id: object,
    step_name: str,
    status: str,
    message: str,
) -> None:
    resolved_task_id = _resolve_task_id(task_id)
    logger.info(f"[TASK {resolved_task_id}] [{step_name}] {status} {message}")
    step_log(resolved_task_id, step_name, f"{status} {message}")


def _resolve_task_id(task_id: object) -> str:
    if isinstance(task_id, str):
        return task_id
    try:
        candidate = getattr(task_id, "task_id", None)
    except Exception:
        candidate = None
    if candidate is None:
        return str(task_id)
    return str(candidate)


def run_batch_step(logger: logging.Logger, step_name: str, message: str, action) -> None:
    logger.info(f"[BATCH] [{step_name}] START {message}")
    started_at = perf_counter()
    action()
    logger.info(f"[BATCH] [{step_name}] SUCCESS {message} elapsed_ms={elapsed_ms(started_at)}")


def run_task_substep(
    logger: logging.Logger,
    step_log: StepLogger,
    task_id: str,
    step_name: str,
    message: str,
    action,
    retry_delay_s: float = 0.5,
    retry_attempts: int = 1,
    non_retryable_exceptions: NonRetryableExceptions = (),
) -> None:
    log_task_step(logger, step_log, task_id, step_name, "START", message)
    started_at = perf_counter()
    completed_retries = 0
    while True:
        try:
            action()
            break
        except Exception as error:
            if non_retryable_exceptions and isinstance(error, non_retryable_exceptions):
                raise
            if completed_retries >= retry_attempts:
                log_task_step(
                    logger,
                    step_log,
                    task_id,
                    step_name,
                    "FAILED",
                    (
                        f"{message} retries_exhausted={completed_retries}/{retry_attempts} "
                        f"elapsed_ms={elapsed_ms(started_at)} error={type(error).__name__}: {error}"
                    ),
                )
                raise
            completed_retries += 1
            retry_message = (
                f"RETRY {message} attempt={completed_retries}/{retry_attempts} "
                f"delay_ms={int(retry_delay_s * 1000)} first_error={type(error).__name__}"
            )
            logger.info(f"[TASK {task_id}] [{step_name}] {retry_message}")
            step_log(task_id, step_name, retry_message)
            sleep(retry_delay_s)
    log_task_step(
        logger,
        step_log,
        task_id,
        step_name,
        "SUCCESS",
        f"{message} elapsed_ms={elapsed_ms(started_at)}",
    )


__all__ = [
    "NonRetryableExceptions",
    "StepLogger",
    "elapsed_ms",
    "log_task_step",
    "run_batch_step",
    "run_task_substep",
]
