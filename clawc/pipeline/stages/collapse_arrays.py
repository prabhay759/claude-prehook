from __future__ import annotations

import json
from abc import ABC, abstractmethod

_MIN_ARRAY_LEN = 5


class Stage(ABC):
    name: str = ""

    @abstractmethod
    def apply(self, text: str, *, tool_name: str = "") -> str | None: ...


def _tabularize(rows: list[dict[str, object]], keys: list[str]) -> str:
    widths = {k: len(k) for k in keys}
    for row in rows:
        for k in keys:
            widths[k] = max(widths[k], len(str(row.get(k, ""))))

    sep = "+" + "+".join("-" * (widths[k] + 2) for k in keys) + "+"
    header = "|" + "|".join(f" {k:<{widths[k]}} " for k in keys) + "|"
    lines = [sep, header, sep]
    for row in rows:
        lines.append("|" + "|".join(f" {str(row.get(k, '')):<{widths[k]}} " for k in keys) + "|")
    lines.append(sep)
    return "\n".join(lines)


def _try_toon(data: list[object]) -> str | None:
    try:
        from toon import encode as toon_encode  # type: ignore[import]
        return str(toon_encode(data))
    except ImportError:
        return None


class CollapseArrays(Stage):
    name = "collapse_arrays"

    def apply(self, text: str, *, tool_name: str = "") -> str | None:
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(data, list) or len(data) < _MIN_ARRAY_LEN:
            return None

        if not all(isinstance(item, dict) for item in data):
            return None

        key_sets = [frozenset(d.keys()) for d in data]  # type: ignore[union-attr]
        if len(set(key_sets)) > 1:
            return None

        keys = sorted(key_sets[0])

        toon_result = _try_toon(data)
        if toon_result:
            return toon_result

        return _tabularize(data, keys)  # type: ignore[arg-type]
