from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any

EXIT_CONTINUE = 0
EXIT_BLOCK = 2
EXIT_WARN = 1  # non-blocking: logged, shown to user not Claude


@dataclass
class HookInput:
    hook_event_name: str = ""
    session_id: str = ""
    transcript_path: str = ""
    cwd: str = ""
    permission_mode: str = "default"
    tool_name: str = ""
    tool_use_id: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)
    tool_result: str = ""
    source: str = ""
    model: str = ""

    @classmethod
    def from_stdin(cls) -> "HookInput":
        try:
            raw: dict[str, Any] = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError):
            raw = {}
        fields = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        init_kwargs = {k: raw[k] for k in fields if k in raw}
        return cls(**init_kwargs)


@dataclass
class HookOutput:
    continue_: bool = True
    stop_reason: str = ""
    suppress_output: bool = False
    hook_specific_output: dict[str, Any] = field(default_factory=dict)

    def emit(self, exit_code: int = EXIT_CONTINUE) -> None:
        payload: dict[str, Any] = {}
        if not self.continue_:
            payload["continue"] = False
            if self.stop_reason:
                payload["stopReason"] = self.stop_reason
        if self.suppress_output:
            payload["suppressOutput"] = True
        if self.hook_specific_output:
            payload["hookSpecificOutput"] = self.hook_specific_output
        if payload:
            print(json.dumps(payload))
        sys.exit(exit_code)
