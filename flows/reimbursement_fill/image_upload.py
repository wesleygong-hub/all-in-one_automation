from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import Page


LocatorContext = Any


def set_upload_files(context: LocatorContext, selector: str, file_paths: list[str], timeout: int, wait_visible: Callable[[Any, int], bool]) -> None:
    locator = context.locator(selector).first
    if not wait_visible(locator, min(timeout, 800)):
        raise RuntimeError("上传弹窗中未检测到文件选择控件")
    locator.set_input_files(file_paths, timeout=timeout)


def ensure_upload_files_selected(context: LocatorContext, file_paths: list[str], timeout: int) -> None:
    file_names = [Path(path).name for path in file_paths]
    success_selectors = [
        ".state-complete",
        ".upload-state-done",
        ".upload-success",
        ".uploadBtn.state-finish",
        ".uploadBtn.state-confirm",
        "text=上传成功",
        "text=成功",
    ]
    start_button_selector = ".uploadBtn"
    context.wait_for_timeout(80) if hasattr(context, "wait_for_timeout") else None
    end_at = __import__("time").perf_counter() + (min(timeout, 1800) / 1000)
    while __import__("time").perf_counter() < end_at:
        for selector in success_selectors:
            try:
                if context.locator(selector).first.wait_for(state="visible", timeout=180) is None:
                    return
            except Exception:
                continue
        for file_name in file_names:
            try:
                if context.get_by_text(file_name, exact=False).first.wait_for(state="visible", timeout=180) is None:
                    try:
                        context.locator(start_button_selector).first.wait_for(state="visible", timeout=120)
                    except Exception:
                        return
            except Exception:
                continue
        try:
            if context.locator(".webuploader-queue, .filelist, .upload-list").first.wait_for(state="visible", timeout=180) is None:
                try:
                    context.locator(start_button_selector).first.wait_for(state="visible", timeout=120)
                except Exception:
                    return
        except Exception:
            pass
        context.wait_for_timeout(40) if hasattr(context, "wait_for_timeout") else None
    raise RuntimeError(f"上传动作后未检测到明确完成标志，file_names={file_names}")


def ensure_upload_file_ready(
    context: LocatorContext,
    selectors: dict[str, str],
    timeout: int,
    wait_visible: Callable[[Any, int], bool],
) -> None:
    candidates = [
        selectors.get("file_input", ""),
        selectors.get("choose_file_button", ""),
        '#filePicker input[type="file"]',
        "#filePicker .webuploader-pick",
    ]
    end_at = __import__("time").perf_counter() + (timeout / 1000)
    while __import__("time").perf_counter() < end_at:
        for selector in candidates:
            if not selector:
                continue
            try:
                locator = context.locator(selector).first
                if wait_visible(locator, 120):
                    return
            except Exception:
                continue
        context.wait_for_timeout(30) if hasattr(context, "wait_for_timeout") else None
    raise RuntimeError("未检测到已就绪的‘选择文件’控件")


def diagnose_upload_dialog(
    page: Page,
    selectors: dict[str, str],
    resolve_electronic_image_context: Callable[[Page, dict[str, str]], LocatorContext],
    resolve_upload_dialog_context: Callable[[Page, dict[str, str]], LocatorContext | None],
    count_visible_elements: Callable[[LocatorContext, str], int],
    wait_visible: Callable[[Any, int], bool],
) -> str:
    attempts: list[str] = []
    dialog_host_context = resolve_electronic_image_context(page, selectors)

    outer_checks = [
        ("dialog", selectors.get("upload_dialog", "")),
        ("dialog_iframe", selectors.get("upload_dialog_iframe", 'iframe[id^="layui-layer-iframe"]')),
        ("shade", ".layui-layer-shade"),
    ]
    for label, selector in outer_checks:
        if not selector:
            continue
        try:
            locator = dialog_host_context.locator(selector)
            count = locator.count()
            attempts.append(f"{label}:count={count}")
            if count > 0:
                try:
                    visible = wait_visible(locator.first, 200)
                    attempts.append(f"{label}:visible={visible}")
                except Exception as exc:
                    attempts.append(f"{label}:visible=error:{type(exc).__name__}")
        except Exception as exc:
            attempts.append(f"{label}:count=error:{type(exc).__name__}")

    upload_context = resolve_upload_dialog_context(page, selectors)
    if upload_context is None:
        attempts.append("upload_iframe_context:none")
    else:
        attempts.append("upload_iframe_context:resolved")
        inner_checks = [
            ("file_input", selectors.get("file_input", "")),
            ("start_upload_button", selectors.get("start_upload_button", "")),
            ("choose_file_button", selectors.get("choose_file_button", "")),
        ]
        for label, selector in inner_checks:
            if not selector:
                continue
            try:
                locator = upload_context.locator(selector)
                count = locator.count()
                attempts.append(f"{label}:count={count}")
                if count > 0:
                    try:
                        visible = wait_visible(locator.first, 200)
                        attempts.append(f"{label}:visible={visible}")
                    except Exception as exc:
                        attempts.append(f"{label}:visible=error:{type(exc).__name__}")
            except Exception as exc:
                attempts.append(f"{label}:count=error:{type(exc).__name__}")

    return f"未成功打开上传弹窗 attempts={attempts}"
__all__ = [
    "diagnose_upload_dialog",
    "ensure_upload_file_ready",
    "ensure_upload_files_selected",
    "set_upload_files",
]
