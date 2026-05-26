from __future__ import annotations

from dataclasses import dataclass, field

from .safemode import is_unsafe
from .stages import STAGE_REGISTRY, Stage


@dataclass
class StageResult:
    text: str
    original_tokens: int
    compressed_tokens: int
    stages_applied: list[str] = field(default_factory=list)
    safe_mode: bool = False

    @property
    def tokens_saved(self) -> int:
        return max(0, self.original_tokens - self.compressed_tokens)

    @property
    def reduction_pct(self) -> float:
        if self.original_tokens == 0:
            return 0.0
        return self.tokens_saved / self.original_tokens * 100


class CompressionPipeline:
    MIN_BYTES = 100

    def __init__(self, stages: list[Stage] | None = None) -> None:
        self.stages = stages if stages is not None else STAGE_REGISTRY

    def run(self, content: str, *, tool_name: str = "") -> StageResult:
        from clawc.tokens.counter import Counter

        counter = Counter(fast=True)
        orig_tokens = counter.count(content)

        if len(content) < self.MIN_BYTES:
            return StageResult(content, orig_tokens, orig_tokens)

        if is_unsafe(content):
            return StageResult(content, orig_tokens, orig_tokens, safe_mode=True)

        text = content
        applied: list[str] = []
        for stage in self.stages:
            result = stage.apply(text, tool_name=tool_name)
            if result is not None and result != text:
                applied.append(stage.name)
                text = result

        compressed_tokens = counter.count(text)
        return StageResult(text, orig_tokens, compressed_tokens, applied)


_default_pipeline = CompressionPipeline()


def run(content: str, *, tool_name: str = "") -> StageResult:
    return _default_pipeline.run(content, tool_name=tool_name)
