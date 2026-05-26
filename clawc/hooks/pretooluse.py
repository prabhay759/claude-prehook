from __future__ import annotations

from ._protocol import EXIT_CONTINUE, HookInput, HookOutput


def handle(inp: HookInput) -> None:
    # PreToolUse on Bash: currently a passthrough.
    # Future: intercept known expensive commands or inject additionalContext.
    HookOutput().emit(EXIT_CONTINUE)
