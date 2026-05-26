from __future__ import annotations

from ._base import Formatter


class RuffFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        return tool_name == "Bash" and (
            "ruff" in tool_input.get("command", "")
            or ("Found " in content and "fixable" in content)
        )

    def format(self, content: str) -> str:
        lines = content.splitlines()
        out = [
            ln for ln in lines
            if not ln.startswith("Checking ") and not ln.startswith("Watching")
        ]
        return "\n".join(out) if out else content
