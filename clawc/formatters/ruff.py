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
        out = [l for l in lines if not l.startswith("Checking ") and not l.startswith("Watching")]
        return "\n".join(out) if out else content
