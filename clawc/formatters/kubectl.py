from __future__ import annotations

from ._base import Formatter


class KubectlFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        cmd = tool_input.get("command", "")
        return tool_name == "Bash" and cmd.startswith("kubectl ")

    def format(self, content: str) -> str:
        return content
