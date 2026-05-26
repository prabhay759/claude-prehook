from __future__ import annotations

import math
import re
from collections import Counter

_ENTROPY_THRESHOLD = 5.2

_UNSAFE_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]+-----"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ"),  # JWT header.payload
    re.compile(r"(?:CREATE|ALTER|DROP)\s+TABLE", re.IGNORECASE),
    re.compile(r'  File "[^"]+", line \d+, in '),  # Python traceback frame
    re.compile(r"^\s+at .+\(.+:\d+:\d+\)$", re.MULTILINE),  # JS/Node stack frame
    re.compile(r"^[A-Z_][A-Z0-9_]*=.{20,}$", re.MULTILINE),  # env var blocks
]


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    encoded = text.encode("utf-8", errors="replace")
    counts = Counter(encoded)
    total = len(encoded)
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)


def is_unsafe(content: str) -> bool:
    if _shannon_entropy(content) > _ENTROPY_THRESHOLD:
        return True
    return any(p.search(content) for p in _UNSAFE_PATTERNS)
