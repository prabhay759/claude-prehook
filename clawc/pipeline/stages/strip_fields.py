from __future__ import annotations

import json
from abc import ABC, abstractmethod

_DEFAULT_DENY = frozenset(
    {
        "debug", "trace", "verbose", "stackTrace", "stack_trace",
        "requestId", "request_id", "traceId", "trace_id", "spanId", "span_id",
        "duration_ms", "elapsed", "timestamp", "createdAt", "created_at",
        "updatedAt", "updated_at", "_links", "_embedded", "__typename",
    }
)


class Stage(ABC):
    name: str = ""

    @abstractmethod
    def apply(self, text: str, *, tool_name: str = "") -> str | None: ...


def _strip_fields(obj: object, deny: frozenset[str]) -> object:
    if isinstance(obj, dict):
        return {k: _strip_fields(v, deny) for k, v in obj.items() if k not in deny}
    if isinstance(obj, list):
        return [_strip_fields(item, deny) for item in obj]
    return obj


class StripFields(Stage):
    name = "strip_fields"

    def __init__(self, deny: frozenset[str] | None = None) -> None:
        self.deny = deny if deny is not None else _DEFAULT_DENY

    def apply(self, text: str, *, tool_name: str = "") -> str | None:
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None
        cleaned = _strip_fields(data, self.deny)
        if cleaned == data:
            return None
        return json.dumps(cleaned, separators=(",", ":"))
