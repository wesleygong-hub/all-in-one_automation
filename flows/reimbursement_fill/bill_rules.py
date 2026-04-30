from __future__ import annotations

from typing import Any


def resolve_task_bill_subtype(task: Any, mapping: dict[str, Any]) -> str:
    raw_value = str(getattr(task, "bill_type", "") or "").strip()
    subtype_mapping = mapping.get("bill_subtype", {}) or {}
    if raw_value in subtype_mapping:
        return str(subtype_mapping.get(raw_value, raw_value)).strip()
    if raw_value:
        for mapped_value in subtype_mapping.values():
            mapped_text = str(mapped_value).strip()
            if mapped_text == raw_value:
                return mapped_text
    if "市内交通" in raw_value or "车费" in raw_value:
        return str(subtype_mapping.get("city_transport", "市内交通费报销")).strip()
    if "业务招待" in raw_value:
        return str(subtype_mapping.get("business_entertainment", "业务招待费报销")).strip()
    return raw_value or str(subtype_mapping.get("business_entertainment", "业务招待费报销")).strip()


def is_city_transport_bill(task: Any, mapping: dict[str, Any]) -> bool:
    return "市内交通费报销" in resolve_task_bill_subtype(task, mapping)


def bill_page_markers(selectors: dict[str, str], bill_subtype: str) -> list[str]:
    markers = [
        selectors.get("electronic_image_tab_entry", ""),
        selectors.get("save_button", ""),
        "text=电子影像",
        "text=保存",
    ]
    if "市内交通费报销" in bill_subtype:
        markers.extend(
            [
                selectors.get("city_transport_detail_tab_select", ""),
                selectors.get("attachment_count_input", ""),
                selectors.get("payment_purpose_input", ""),
                selectors.get("payment_purpose_input_fallback", ""),
                "text=费用分摊",
                "text=付款用途",
                "text=报账金额",
                'xpath=//label[contains(normalize-space(.),"附件个数")]',
                'xpath=//label[contains(normalize-space(.),"付款用途")]',
                'xpath=//label[contains(normalize-space(.),"报账金额")]',
            ]
        )
    else:
        markers.extend(
            [
                selectors.get("detail_tab_select", ""),
                selectors.get("business_unit_input", ""),
                selectors.get("payment_purpose_input", ""),
                selectors.get("payment_purpose_input_fallback", ""),
                "text=报销明细信息",
                "text=业务单位",
                "text=付款用途",
                'xpath=//label[contains(normalize-space(.),"业务单位")]',
                'xpath=//label[contains(normalize-space(.),"付款用途")]',
            ]
        )
    return markers


def dedupe_selectors(candidates: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        result.append(candidate)
    return result


def detail_button_selector_candidates(configured_selector: str, action: str) -> list[str]:
    candidates: list[str] = []
    if configured_selector:
        candidates.append(configured_selector)
    if action == "add":
        candidates.extend(
            [
                'a[data-action="AddItemCommonBXFY"][data-tabpanel="XtraTabPage3"]',
                'a[data-action="AddItemCommonFP"][data-tabpanel="XtraTabPageFP"]',
                'xpath=//a[@data-tabpanel="XtraTabPage3"][.//span[normalize-space(.)="增加"]]',
                'xpath=//a[@data-tabpanel="XtraTabPageFP"][.//span[normalize-space(.)="增加"]]',
                'xpath=//a[contains(@data-action,"AddItemCommon")][.//span[normalize-space(.)="增加"]]',
            ]
        )
    else:
        candidates.extend(
            [
                'a[data-action="RemoveSelectCommonBXFY"][data-tabpanel="XtraTabPage3"]',
                'a[data-action="RemoveSelectCommonFP"][data-tabpanel="XtraTabPageFP"]',
                'xpath=//a[@data-tabpanel="XtraTabPage3"][.//span[normalize-space(.)="删除"]]',
                'xpath=//a[@data-tabpanel="XtraTabPageFP"][.//span[normalize-space(.)="删除"]]',
                'xpath=//a[contains(@data-action,"RemoveSelectCommon")][.//span[normalize-space(.)="删除"]]',
            ]
        )
    return dedupe_selectors(candidates)


def bill_subtype_candidates(selectors: dict[str, str], bill_subtype: str) -> list[str]:
    candidates: list[str] = []
    if "市内交通费报销" in bill_subtype:
        candidates.append(selectors.get("bill_subtype_city_transport", ""))
    if "业务招待费报销" in bill_subtype:
        candidates.extend(
            [
                selectors.get("bill_subtype_business_entertainment", ""),
                '[id="7453727a-449f-4b2d-8a26-b3d99ba359fc"]',
            ]
        )
    candidates.extend(
        [
            f'a.td:has-text("{bill_subtype}")',
            f'xpath=//a[contains(@class,"td") and normalize-space(.)="{bill_subtype}"]',
        ]
    )
    return dedupe_selectors(candidates)


def bill_tab_selector_candidates(configured_selector: str, tab_text: str) -> list[str]:
    candidates: list[str] = []
    if configured_selector:
        candidates.append(configured_selector)
    candidates.extend(
        [
            f"text={tab_text}",
            f'xpath=//li[contains(@class,"tabs-selected")]//span[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]',
            f'xpath=//li//a[contains(@class,"tabs-inner")]//span[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]',
            f'xpath=//li//a[contains(@class,"tabs-inner")][.//span[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]]',
            f'xpath=//*[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]',
            f'xpath=//a[contains(@class,"tabs-inner")]//*[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]',
            f'xpath=//span[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]',
        ]
    )
    return dedupe_selectors(candidates)


def bill_tab_click_selector_candidates(configured_selector: str, tab_text: str) -> list[str]:
    candidates: list[str] = []
    if configured_selector:
        candidates.append(configured_selector)
    candidates.extend(
        [
            f'xpath=//li//a[contains(@class,"tabs-inner")][.//span[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]]',
            f'xpath=//a[contains(@class,"tabs-inner")][.//span[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]]',
            f'xpath=//span[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]/ancestor::a[contains(@class,"tabs-inner")][1]',
            f'xpath=//li//span[contains(@class,"tabs-title") and normalize-space(.)="{tab_text}"]',
            f"text={tab_text}",
        ]
    )
    return dedupe_selectors(candidates)


__all__ = [
    "bill_page_markers",
    "bill_subtype_candidates",
    "bill_tab_click_selector_candidates",
    "bill_tab_selector_candidates",
    "dedupe_selectors",
    "detail_button_selector_candidates",
    "is_city_transport_bill",
    "resolve_task_bill_subtype",
]
