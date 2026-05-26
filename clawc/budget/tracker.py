from __future__ import annotations

from dataclasses import dataclass, field

_WARNING_THRESHOLD = 0.70
_ESCALATE_THRESHOLD = 0.80
_CRITICAL_THRESHOLD = 0.90
_DEFAULT_WINDOW = 200_000


@dataclass
class WindowUsage:
    used: int = 0
    window_size: int = _DEFAULT_WINDOW

    @property
    def ratio(self) -> float:
        return self.used / self.window_size if self.window_size else 0.0

    @property
    def is_warning(self) -> bool:
        return self.ratio >= _WARNING_THRESHOLD

    @property
    def is_escalated(self) -> bool:
        return self.ratio >= _ESCALATE_THRESHOLD

    @property
    def is_critical(self) -> bool:
        return self.ratio >= _CRITICAL_THRESHOLD


@dataclass
class BudgetTracker:
    session_id: str
    window_size: int = _DEFAULT_WINDOW
    _used: int = field(default=0, init=False)

    def add(self, tokens: int) -> None:
        self._used += tokens

    @property
    def usage(self) -> WindowUsage:
        return WindowUsage(self._used, self.window_size)

    def compression_pressure(self) -> float:
        ratio = self.usage.ratio
        if ratio < _WARNING_THRESHOLD:
            return 0.0
        elif ratio < _ESCALATE_THRESHOLD:
            return 0.5
        elif ratio < _CRITICAL_THRESHOLD:
            return 0.8
        return 1.0
