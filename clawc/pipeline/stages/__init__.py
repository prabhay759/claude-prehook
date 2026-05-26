from __future__ import annotations

from abc import ABC, abstractmethod

from .collapse_arrays import CollapseArrays
from .condense_logs import CondenseLogs
from .flatten_json import FlattenJson
from .prose_textrank import ProseTextrank
from .strip_ansi import StripAnsi
from .strip_fields import StripFields
from .strip_nulls import StripNulls
from .truncate_strings import TruncateStrings


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
