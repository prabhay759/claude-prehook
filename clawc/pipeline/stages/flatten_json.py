from __future__ import annotations

import json
from abc import ABC, abstractmethod

_MAX_DEPTH = 2


class Stage(ABC):
    name: str = ""

    @abstractmethod
    def apply(self, text: str, *, tool_name: str = "") -> str | None: ...


def _depth(obj: object) -> int:
    if isinstance(obj, dict):
        if not obj:
            return 1
        return 1 + max(_depth(v) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return 1
        return 1 + max(_depth(v) for v in obj)
    return 0


def _flatten(obj: object, prefix: str = "") -> dict[str, object]:
    result: dict[str, object] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict) and _depth(v) == 1:
                for ik, iv in v.items():
                    result[f"{full_key}.{ik}"] = iv
            else:
                result[full_key] = v
    else:
        result[prefix] = obj
    return result


class FlattenJson(Stage):
    name = "flatten_json"

    def apply(self, text: str, *, tool_name: str = "") -> str | None:
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        if _depth(data) <= _MAX_DEPTH:
            return None
        flattened = _flatten(data)
        if flattened == data:
            return None
        return json.dumps(flattened, separators=(",", ":"))
