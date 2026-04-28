from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


TASK_SHEET_REQUIRED_FIELDS = (
    "task_id",
    "bill_type",
    "payment_purpose",
)

INVOICE_SHEET_REQUIRED_FIELDS = (
    "task_id",
    "file_path",
    "remark",
)


@dataclass(slots=True)
class ReimbursementInvoiceRecord:
    task_id: str
    company_count: str
    file_path: str
    remark: str
    source_row: int
    approved_amount: str = ""

    @property
    def file_name(self) -> str:
        return Path(self.file_path).name


@dataclass(slots=True)
class ReimbursementTaskRecord:
    task_id: str
    bill_type: str
    business_department: str
    payment_purpose: str
    source_row: int
    invoices: list[ReimbursementInvoiceRecord] = field(default_factory=list)

    @property
    def attachment_count(self) -> int:
        return len(self.invoices)

    @property
    def file_path(self) -> str:
        return ";".join(invoice.file_path for invoice in self.invoices)


@dataclass(slots=True)
class ReimbursementTaskResult:
    status: str
    message: str
    screenshot_path: str | None = None


__all__ = [
    "TASK_SHEET_REQUIRED_FIELDS",
    "INVOICE_SHEET_REQUIRED_FIELDS",
    "ReimbursementInvoiceRecord",
    "ReimbursementTaskRecord",
    "ReimbursementTaskResult",
]
