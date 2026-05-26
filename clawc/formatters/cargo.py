from __future__ import annotations

from ._base import Formatter


class CargoFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        cmd = tool_input.get("command", "")
        return tool_name == "Bash" and (
            cmd.startswith("cargo ") or "Compiling " in content or "error[E" in content
        )

    def format(self, content: str) -> str:
        lines = content.splitlines()
        out: list[str] = []
        for line in lines:
            if (
                line.startswith("error")
                or line.startswith("warning")
                or line.startswith("  -->")
                or line.startswith("   |")
                or line.startswith("test ")
                or "FAILED" in line
                or "test result:" in line
                or line.startswith("Finished")
                or line.startswith("error[")
            ):
                out.append(line)
        return "\n".join(out) if out else content
