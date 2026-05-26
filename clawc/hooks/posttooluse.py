from __future__ import annotations

from ._protocol import EXIT_CONTINUE, HookInput, HookOutput


def handle(inp: HookInput) -> None:
    content = inp.tool_result
    if not content or len(content.strip()) == 0:
        HookOutput().emit(EXIT_CONTINUE)

    from clawc.cache.dedup import sha256_hex
    from clawc.cache.delta import compute_simhash, find_near_dup, make_patch
    from clawc.cache.store import CacheStore
    from clawc.formatters import FormatterRegistry
    from clawc.pipeline import run as pipeline_run
    from clawc.pipeline.safemode import is_unsafe

    store = CacheStore.open()
    session_id = inp.session_id or "default"
    store.ensure_session(session_id, cwd=inp.cwd)

    content_hash = sha256_hex(content)

    # 1. Cache hit → return §ref§ immediately
    entry = store.lookup(content_hash)
    if entry:
        store.record_hit(content_hash)
        store.record_compression(
            session_id=session_id,
            tool_name=inp.tool_name,
            content_hash=content_hash,
            original_tokens=max(1, int(len(content) / 3.5)),
            compressed_tokens=13,  # §ref:HASH§ is ~13 tokens
            stages_applied=[],
            was_cache_hit=True,
            tool_use_id=inp.tool_use_id,
        )
        HookOutput(
            hook_specific_output={
                "hookEventName": "PostToolUse",
                "updatedToolOutput": entry["ref_token"],
            }
        ).emit(EXIT_CONTINUE)

    # 2. Near-dup check (simhash delta)
    recent = store.recent_entries(limit=200)
    delta_result = find_near_dup(recent, content, content_hash)
    if delta_result:
        base_hash, dist, new_sh = delta_result
        base_entry = store.lookup(base_hash)
        if base_entry:
            patch = make_patch(base_entry["compressed"], content)
            if len(patch) < len(content) * 0.6:
                output = f"{base_entry['ref_token']}\n[delta from cached]\n{patch}"
                store.store_delta(base_hash, content_hash, dist, patch)
                store.store(content_hash, content, output, inp.tool_name, new_sh)
                store.record_compression(
                    session_id=session_id,
                    tool_name=inp.tool_name,
                    content_hash=content_hash,
                    original_tokens=max(1, int(len(content) / 3.5)),
                    compressed_tokens=max(1, int(len(output) / 3.5)),
                    stages_applied=["delta"],
                    tool_use_id=inp.tool_use_id,
                )
                HookOutput(
                    hook_specific_output={
                        "hookEventName": "PostToolUse",
                        "updatedToolOutput": output,
                    }
                ).emit(EXIT_CONTINUE)

    # 3. Safe-mode routing → passthrough, no rewrite
    if is_unsafe(content):
        store.store(content_hash, content, content, inp.tool_name, compute_simhash(content))
        store.record_compression(
            session_id=session_id,
            tool_name=inp.tool_name,
            content_hash=content_hash,
            original_tokens=max(1, int(len(content) / 3.5)),
            compressed_tokens=max(1, int(len(content) / 3.5)),
            stages_applied=[],
            was_safe_mode=True,
            tool_use_id=inp.tool_use_id,
        )
        HookOutput().emit(EXIT_CONTINUE)

    # 4. Formatter detection
    formatted = FormatterRegistry.detect_and_apply(inp.tool_name, inp.tool_input, content)
    work_content = formatted if formatted is not None else content

    # 5. Compression pipeline
    result = pipeline_run(work_content, tool_name=inp.tool_name)

    # 6. Persist and return
    sh = compute_simhash(result.text)
    store.store(content_hash, content, result.text, inp.tool_name, sh)
    store.record_compression(
        session_id=session_id,
        tool_name=inp.tool_name,
        content_hash=content_hash,
        original_tokens=result.original_tokens,
        compressed_tokens=result.compressed_tokens,
        stages_applied=result.stages_applied,
        was_safe_mode=result.safe_mode,
        tool_use_id=inp.tool_use_id,
    )

    # Only rewrite if we actually compressed something
    if result.text != content:
        HookOutput(
            hook_specific_output={
                "hookEventName": "PostToolUse",
                "updatedToolOutput": result.text,
            }
        ).emit(EXIT_CONTINUE)
    else:
        HookOutput().emit(EXIT_CONTINUE)
