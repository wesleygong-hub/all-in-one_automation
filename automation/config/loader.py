from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml


ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


def _expand_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, str):
        expanded = os.path.expandvars(value)
        return ENV_VAR_PATTERN.sub(_replace_env_var, expanded)
    return value


def _replace_env_var(match: re.Match[str]) -> str:
    var_name = match.group(1) or match.group(2) or ""
    return os.environ.get(var_name, match.group(0))


def _normalize_path(project_root: Path, value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = project_root / path
    return str(path.resolve())


def load_config(config_path: str, validate_auth: bool = True) -> dict[str, Any]:
    path = Path(config_path).resolve()
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    config = _expand_env(raw)
    project_root = _infer_project_root(path)

    paths = config.setdefault("paths", {})
    paths.setdefault("sqlite_path", "./data/runtime.db")
    paths.setdefault("screenshot_dir", "./output/screenshots")
    paths.setdefault("report_dir", "./output/reports")
    paths["sqlite_path"] = _normalize_path(project_root, paths["sqlite_path"])
    paths["screenshot_dir"] = _normalize_path(project_root, paths["screenshot_dir"])
    paths["report_dir"] = _normalize_path(project_root, paths["report_dir"])

    system = config.setdefault("system", {})
    system.setdefault("timeout_ms", 15000)
    system.setdefault("headed", True)
    system.setdefault("browser_channel", "msedge")
    system.setdefault("browser_executable_path", "")

    runtime = config.setdefault("runtime", {})
    runtime.setdefault("screenshot_on_error", True)
    runtime.setdefault("log_level", "INFO")

    auth = config.setdefault("auth", {})
    config.setdefault("selectors", {})
    config.setdefault("mapping", {})
    if validate_auth:
        _validate_auth_config(auth)
    return config


def ensure_runtime_dirs(config: dict[str, Any]) -> None:
    paths = config["paths"]
    Path(paths["sqlite_path"]).parent.mkdir(parents=True, exist_ok=True)
    Path(paths["screenshot_dir"]).mkdir(parents=True, exist_ok=True)
    Path(paths["report_dir"]).mkdir(parents=True, exist_ok=True)


def _infer_project_root(config_path: Path) -> Path:
    if config_path.parent.name.lower() == "config":
        return config_path.parent.parent
    return config_path.parent


def _validate_auth_config(auth: dict[str, Any]) -> None:
    for field in ("username", "password"):
        value = auth.get(field, "")
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"config auth.{field} is empty")
        if "${" in value or value.startswith("$") or value.startswith("%"):
            raise RuntimeError(
                f"config auth.{field} was not resolved from environment variables: {value}. "
                f"Please set the environment variable before running the command."
            )


__all__ = ["load_config", "ensure_runtime_dirs"]
