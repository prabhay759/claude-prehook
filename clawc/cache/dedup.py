from __future__ import annotations

import hashlib

REF_PREFIX = "§ref:"
REF_SUFFIX = "§"
# §ref:abcd1234§  ≈ 13 Claude tokens


def sha256_hex(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


def make_ref_token(content_hash_full: str) -> str:
    return f"{REF_PREFIX}{content_hash_full[:8]}{REF_SUFFIX}"


def is_ref_token(text: str) -> bool:
    return text.startswith(REF_PREFIX) and text.endswith(REF_SUFFIX)


def extract_hash_prefix(ref: str) -> str:
    return ref[len(REF_PREFIX) : -len(REF_SUFFIX)]
