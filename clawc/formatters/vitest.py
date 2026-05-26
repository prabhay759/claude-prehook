from __future__ import annotations

from ._base import Formatter


class VitestFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        return tool_name == "Bash" and "vitest" in tool_input.get("command", "") or (
            " passed" in content and " failed" in content and "Duration" in content
        )

    def format(self, content: str) -> str:
        lines = content.splitlines()
        out: list[str] = []
        for line in lines:
            if (
                line.strip().startswith("✓")
                or line.strip().startswith("\xd7")
                or line.strip().startswith("FAIL")
                or "passed" in line
                or "failed" in line
                or "Duration" in line
                or line.startswith("  AssertionError")
            ):
                out.append(line)
        return "\n".join(out) if out else content
