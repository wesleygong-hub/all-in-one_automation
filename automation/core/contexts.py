from __future__ import annotations

from typing import Any, Callable


def selector_context_hint(selectors: dict[str, str], selector_name: str) -> str:
    try:
        hints = selectors.get("_context_hints", {}) or {}
        value = hints.get(selector_name, "")
        return str(value).strip()
    except Exception:
        return ""


def append_unique_context(contexts: list[Any], seen: set[int], context: Any | None) -> bool:
    if context is None:
        return False
    marker = id(context)
    if marker in seen:
        return False
    seen.add(marker)
    contexts.append(context)
    return True


def context_debug_name(context: Any, index: int) -> str:
    try:
        if hasattr(context, "main_frame"):
            return "page"
        url = getattr(context, "url", "")
        if url:
            return f"frame[{index}]:{url}"
    except Exception:
        pass
    return f"context[{index}]"


def cache_page_context(page: Any, cache_key: str, context: Any) -> None:
    try:
        setattr(page, cache_key, context)
    except Exception:
        pass


def get_cached_page_context(page: Any, cache_key: str) -> Any | None:
    try:
        return getattr(page, cache_key, None)
    except Exception:
        return None


def cache_browser_context_value(page: Any, cache_key: str, value: Any) -> None:
    try:
        setattr(page.context, cache_key, value)
    except Exception:
        pass


def get_cached_browser_context_value(page: Any, cache_key: str) -> Any | None:
    try:
        return getattr(page.context, cache_key, None)
    except Exception:
        return None


def cache_active_working_page(page: Any, working_page: Any, cache_key: str = "_active_working_page") -> None:
    if working_page is None:
        return
    cache_browser_context_value(page, cache_key, working_page)


def get_cached_active_working_page(page: Any, cache_key: str = "_active_working_page") -> Any | None:
    cached_page = get_cached_browser_context_value(page, cache_key)
    if cached_page is None:
        return None
    try:
        if cached_page.is_closed():
            return None
    except Exception:
        return None
    return cached_page


def resolve_selector_context(
    page: Any,
    selectors: dict[str, str],
    selector_name: str,
    context_resolvers: dict[str, Callable[[], Any]],
) -> Any | None:
    hint = selector_context_hint(selectors, selector_name)
    if not hint:
        return None
    if hint == "page":
        return page
    resolver = context_resolvers.get(hint)
    if resolver is None:
        return None
    try:
        return resolver()
    except Exception:
        return None


def candidate_contexts_for_selector(
    page: Any,
    selectors: dict[str, str],
    selector_name: str,
    context_resolvers: dict[str, Callable[[], Any]],
) -> list[Any]:
    contexts: list[Any] = []
    seen: set[int] = set()

    context = resolve_selector_context(page, selectors, selector_name, context_resolvers)
    if context is None:
        return contexts
    marker = id(context)
    if marker in seen:
        return contexts
    seen.add(marker)
    contexts.append(context)
    return contexts


def context_matches_markers(
    context: Any,
    marker_selectors: list[str],
    wait_visible: Callable[[Any, int], bool],
    timeout_ms: int,
) -> bool:
    for selector in marker_selectors:
        if not selector:
            continue
        try:
            if wait_visible(context.locator(selector).first, timeout_ms):
                return True
        except Exception:
            continue
    return False


def get_cached_page_context_matching(
    page: Any,
    cache_key: str,
    marker_selectors: list[str],
    wait_visible: Callable[[Any, int], bool],
    timeout_ms: int,
) -> Any | None:
    context = get_cached_page_context(page, cache_key)
    if context is None:
        return None
    if context_matches_markers(context, marker_selectors, wait_visible, timeout_ms):
        return context
    return None


def resolve_first_visible_frame_context(
    parent: Any,
    iframe_selectors: list[str],
    wait_visible: Callable[[Any, int], bool],
    timeout_ms: int,
) -> Any | None:
    for selector in iframe_selectors:
        if not selector:
            continue
        try:
            iframe_node = parent.locator(selector).first
            if wait_visible(iframe_node, timeout_ms):
                handle = iframe_node.element_handle()
                if handle is not None:
                    frame = handle.content_frame()
                    if frame is not None:
                        return frame
        except Exception:
            continue
    return None


def resolve_context_by_markers(
    candidates: list[Any],
    marker_selectors: list[str],
    wait_visible: Callable[[Any, int], bool],
    timeout_ms: int,
) -> Any | None:
    for candidate in candidates:
        if candidate is None:
            continue
        if context_matches_markers(candidate, marker_selectors, wait_visible, timeout_ms):
            return candidate
    return None


__all__ = [
    "append_unique_context",
    "cache_active_working_page",
    "cache_browser_context_value",
    "cache_page_context",
    "candidate_contexts_for_selector",
    "context_debug_name",
    "context_matches_markers",
    "get_cached_active_working_page",
    "get_cached_browser_context_value",
    "get_cached_page_context_matching",
    "get_cached_page_context",
    "resolve_context_by_markers",
    "resolve_first_visible_frame_context",
    "resolve_selector_context",
    "selector_context_hint",
]
