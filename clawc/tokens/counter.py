from __future__ import annotations

_CHARS_PER_TOKEN = 3.5


class Counter:
    def __init__(self, fast: bool = True) -> None:
        self.fast = fast

    def count(self, text: str) -> int:
        if self.fast:
            return max(1, int(len(text) / _CHARS_PER_TOKEN))
        try:
            import anthropic

            client = anthropic.Anthropic()
            resp = client.messages.count_tokens(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": text}],
            )
            return resp.input_tokens
        except Exception:
            return max(1, int(len(text) / _CHARS_PER_TOKEN))
