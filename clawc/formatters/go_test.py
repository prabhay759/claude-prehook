from __future__ import annotations

from ._base import Formatter


class GoTestFormatter(Formatter):
    def can_handle(self, tool_name: str, tool_input: dict, content: str) -> bool:
        return tool_name == "Bash" and (
            "go test" in tool_input.get("command", "")
            or ("--- FAIL:" in content or "--- PASS:" in content or "ok  \t" in content)
        )

    def format(self, content: str) -> str:
        lines = content.splitlines()
        out: list[str] = []
        for line in lines:
            if (
                line.startswith("--- FAIL:")
                or line.startswith("--- PASS:")
                or line.startswith("FAIL\t")
                or line.startswith("ok  \t")
                or line.startswith("FAIL")
                or "panic:" in line
            ):
                out.append(line)
        return "\n".join(out) if out else content
