from __future__ import annotations

from abc import ABC, abstractmethod


class Stage(ABC):
    name: str = ""

    @abstractmethod
    def apply(self, text: str, *, tool_name: str = "") -> str | None: ...


class CondenseLogs(Stage):
    name = "condense_logs"
    MAX_REPEATS = 3

    def apply(self, text: str, *, tool_name: str = "") -> str | None:
        lines = text.splitlines()
        if len(lines) < 2:
            return None

        out: list[str] = []
        prev: str | None = None
        count = 0
        changed = False

        for line in lines:
            if line == prev:
                count += 1
                if count <= self.MAX_REPEATS:
                    out.append(line)
                elif count == self.MAX_REPEATS + 1:
                    out.append(f"[…{count - self.MAX_REPEATS} more identical lines suppressed]")
                    changed = True
            else:
                prev = line
                count = 1
                out.append(line)

        return "\n".join(out) if changed else None
