from __future__ import annotations

from ._base import Formatter


class DockerFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        cmd = tool_input.get("command", "")
        return tool_name == "Bash" and (
            cmd.startswith("docker ") or "Step " in content and "--->" in content
        )

    def format(self, content: str) -> str:
        lines = content.splitlines()
        out: list[str] = []
        for line in lines:
            if (
                line.startswith("Step ")
                or line.startswith("Successfully")
                or line.startswith("ERROR")
                or line.startswith("error")
                or "sha256:" in line
            ):
                out.append(line)
        return "\n".join(out) if out else content
