"""
Deterministic, local embedding backend (no network).

This is intentionally simple and dependency-free: a feature-hashing style embedder
that produces a fixed-dimension float32 vector from text.
"""

from __future__ import annotations

import base64
import hashlib
import math
import re
from array import array

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def hash_embed_to_float32_bytes(
    text: str,
    *,
    dim: int,
    salt: str,
) -> bytes:
    """
    Embed `text` into a dense float32 vector and return its raw bytes.

    Algorithm:
    - tokenize to [a-z0-9]+ terms
    - for each token: hash(salt + token) -> (index, sign)
    - accumulate signed counts in that index
    - L2-normalize (unit length) if norm > 0
    """
    if dim <= 0:
        raise ValueError("dim must be positive")

    vec = array("f", [0.0]) * dim
    toks = _tokenize(text)
    if not toks:
        return vec.tobytes()

    salt_b = salt.encode("utf-8", errors="strict")
    for tok in toks:
        h = hashlib.blake2b(salt_b + tok.encode("utf-8", errors="ignore"), digest_size=16).digest()
        idx = int.from_bytes(h[:8], "big", signed=False) % dim
        sign = -1.0 if (h[8] & 1) else 1.0
        vec[idx] += sign

    # L2 normalize
    ss = 0.0
    for v in vec:
        ss += float(v) * float(v)
    if ss > 0.0:
        inv = 1.0 / math.sqrt(ss)
        for i in range(dim):
            vec[i] = float(vec[i]) * inv

    return vec.tobytes()


def hash_embed_to_base64(
    text: str,
    *,
    dim: int,
    salt: str,
) -> str:
    """Convenience: embed and base64-encode float32 bytes."""
    return base64.b64encode(hash_embed_to_float32_bytes(text, dim=dim, salt=salt)).decode("ascii")

