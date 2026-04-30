from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AttemptLog:
    entries: list[str] = field(default_factory=list)

    def add(self, *parts: Any) -> None:
        self.entries.append(":".join(str(part) for part in parts))

    def add_value(self, scope: str, name: str, value: Any) -> None:
        self.entries.append(f"{scope}:{name}={value}")

    def add_error(self, scope: str, name: str, exc: Exception) -> None:
        self.entries.append(f"{scope}:{name}=error:{type(exc).__name__}")

    def extend(self, entries: list[str]) -> None:
        self.entries.extend(entries)

    def as_list(self) -> list[str]:
        return list(self.entries)

    def __bool__(self) -> bool:
        return bool(self.entries)


__all__ = ["AttemptLog"]
