from __future__ import annotations

import json
from abc import ABC, abstractmethod


class Stage(ABC):
    name: str = ""

    @abstractmethod
    def apply(self, text: str, *, tool_name: str = "") -> str | None: ...


def _strip_nulls(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: _strip_nulls(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_nulls(item) for item in obj]
    return obj


class StripNulls(Stage):
    name = "strip_nulls"

    def apply(self, text: str, *, tool_name: str = "") -> str | None:
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None
        cleaned = _strip_nulls(data)
        if cleaned == data:
            return None
        return json.dumps(cleaned, separators=(",", ":"))
