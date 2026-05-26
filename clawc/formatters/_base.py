from __future__ import annotations

from abc import ABC, abstractmethod


class Formatter(ABC):
    @abstractmethod
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool: ...

    @abstractmethod
    def format(self, content: str) -> str: ...

    def _head(self, content: str, chars: int = 300) -> str:
        return content[:chars]
