from __future__ import annotations

from ._protocol import EXIT_CONTINUE, HookInput, HookOutput


def handle(inp: HookInput) -> None:
    from clawc.cache.store import CacheStore
    from clawc.memory.resume import build_resume_context

    store = CacheStore.open()
    session_id = inp.session_id or "default"
    store.ensure_session(session_id, cwd=inp.cwd)

    context = build_resume_context(store, session_id, inp.cwd)
    if context:
        HookOutput(
            hook_specific_output={
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        ).emit(EXIT_CONTINUE)
    else:
        HookOutput().emit(EXIT_CONTINUE)
