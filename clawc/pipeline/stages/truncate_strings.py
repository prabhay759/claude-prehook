from __future__ import annotations

import json
from abc import ABC, abstractmethod

_DEFAULT_MAX_LEN = 500
_ELLIPSIS = "…[truncated]"


class Stage(ABC):
    name: str = ""

    @abstractmethod
    def apply(self, text: str, *, tool_name: str = "") -> str | None: ...


def _truncate(obj: object, max_len: int) -> tuple[object, bool]:
    changed = False
    if isinstance(obj, str):
        if len(obj) > max_len:
            return obj[:max_len] + _ELLIPSIS, True
        return obj, False
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            new_v, c = _truncate(v, max_len)
            result[k] = new_v
            changed = changed or c
        return result, changed
    if isinstance(obj, list):
        result_list = []
        for item in obj:
            new_item, c = _truncate(item, max_len)
            result_list.append(new_item)
            changed = changed or c
        return result_list, changed
    return obj, False


class TruncateStrings(Stage):
    name = "truncate_strings"

    def __init__(self, max_len: int = _DEFAULT_MAX_LEN) -> None:
        self.max_len = max_len

    def apply(self, text: str, *, tool_name: str = "") -> str | None:
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            lines = text.splitlines()
            result = []
            changed = False
            for line in lines:
                if len(line) > self.max_len * 2:
                    result.append(line[: self.max_len * 2] + _ELLIPSIS)
                    changed = True
                else:
                    result.append(line)
            return "\n".join(result) if changed else None

        cleaned, changed = _truncate(data, self.max_len)
        if not changed:
            return None
        return json.dumps(cleaned, separators=(",", ":"))
