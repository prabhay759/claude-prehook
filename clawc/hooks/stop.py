from __future__ import annotations

from ._protocol import EXIT_CONTINUE, HookInput, HookOutput


def handle(inp: HookInput) -> None:
    from clawc.cache.store import CacheStore
    from clawc.memory.auto_memory import write_session_summary

    store = CacheStore.open()
    stats = store.stats(inp.session_id or None)
    write_session_summary(stats, cwd=inp.cwd)
    HookOutput().emit(EXIT_CONTINUE)
