from __future__ import annotations

from ._base import Formatter
from .cargo import CargoFormatter
from .docker import DockerFormatter
from .eslint import EslintFormatter
from .git import GitFormatter
from .go_test import GoTestFormatter
from .jest import JestFormatter
from .kubectl import KubectlFormatter
from .npm import NpmFormatter
from .pytest import PytestFormatter
from .ruff import RuffFormatter
from .unittest_ import UnittestFormatter
from .vitest import VitestFormatter

_REGISTRY: list[Formatter] = [
    PytestFormatter(),
    UnittestFormatter(),
    GoTestFormatter(),
    JestFormatter(),
    VitestFormatter(),
    RuffFormatter(),
    EslintFormatter(),
    GitFormatter(),
    CargoFormatter(),
    NpmFormatter(),
    DockerFormatter(),
    KubectlFormatter(),
]


class FormatterRegistry:
    @staticmethod
    def detect_and_apply(tool_name: str, tool_input: dict, content: str) -> str | None:
        for fmt in _REGISTRY:
            if fmt.can_handle(tool_name, tool_input, content):
                return fmt.format(content)
        return None
