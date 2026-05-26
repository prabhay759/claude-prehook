from __future__ import annotations

from abc import ABC, abstractmethod

from .strip_ansi import StripAnsi
from .strip_nulls import StripNulls
from .strip_fields import StripFields
from .condense_logs import CondenseLogs
from .truncate_strings import TruncateStrings
from .flatten_json import FlattenJson
from .collapse_arrays import CollapseArrays
from .prose_textrank import ProseTextrank


class Stage(ABC):
    name: str = ""

    @abstractmethod
    def apply(self, text: str, *, tool_name: str = "") -> str | None:
        ...


STAGE_REGISTRY: list[Stage] = [
    StripAnsi(),
    StripNulls(),
    StripFields(),
    CondenseLogs(),
    TruncateStrings(),
    FlattenJson(),
    CollapseArrays(),
    ProseTextrank(),
]
