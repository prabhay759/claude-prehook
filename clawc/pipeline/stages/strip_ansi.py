from __future__ import annotations

import re
from abc import ABC, abstractmethod

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHFJA-Za-z]|\x1b\][^\x07]*\x07|\x1b[()][AB012]")


class Stage(ABC):
    name: str = ""

    @abstractmethod
    def apply(self, text: str, *, tool_name: str = "") -> str | None: ...


class StripAnsi(Stage):
    name = "strip_ansi"

    def apply(self, text: str, *, tool_name: str = "") -> str | None:
        cleaned = _ANSI_RE.sub("", text)
        return cleaned if cleaned != text else None
