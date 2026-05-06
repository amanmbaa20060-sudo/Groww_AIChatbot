"""Character-window chunking with overlap; strip section sentinels from chunk text."""

from __future__ import annotations

import re
from typing import Any

_SECTION_SENTINEL = re.compile(r"<<<SECTION:([^>]+)>>>")

# ~450–500 tokens at ~4 chars/token ≈ architecture 400–800 token band (conservative)
DEFAULT_TARGET = 1800
DEFAULT_OVERLAP = 250


def _last_section_before(full_text: str, pos: int) -> str:
    head = full_text[:pos]
    found = list(_SECTION_SENTINEL.finditer(head))
    if not found:
        return "root"
    return found[-1].group(1).strip()


def _strip_sentinels(s: str) -> str:
    s = _SECTION_SENTINEL.sub("", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def chunk_normalized_text(
    full_text: str,
    scheme_id: str,
    source_url: str,
    doc_type: str,
    *,
    target_chars: int = DEFAULT_TARGET,
    overlap: int = DEFAULT_OVERLAP,
) -> list[dict[str, Any]]:
    if target_chars < 200:
        raise ValueError("target_chars too small")
    if overlap >= target_chars:
        raise ValueError("overlap must be < target_chars")

    chunks: list[dict[str, Any]] = []
    n = len(full_text)
    if n == 0:
        return []

    start = 0
    idx = 0
    while start < n:
        end = min(n, start + target_chars)
        # Prefer break at paragraph near end (last double newline before end in window)
        if end < n:
            window = full_text[start:end]
            para = window.rfind("\n\n")
            if para > target_chars // 3:
                end = start + para

        segment = full_text[start:end]
        section_path = _last_section_before(full_text, start)
        clean = _strip_sentinels(segment)
        if clean:
            cid = f"{scheme_id}_c{idx:04d}"
            chunks.append(
                {
                    "chunk_id": cid,
                    "chunk_index": idx,
                    "scheme_id": scheme_id,
                    "scheme_ids": [scheme_id],
                    "source_url": source_url,
                    "doc_type": doc_type,
                    "section_path": section_path,
                    "text": clean,
                    "char_count": len(clean),
                }
            )
            idx += 1

        if end >= n:
            break
        if not clean:
            start = max(start + 1, end)
            continue
        next_start = end - overlap
        if next_start <= start:
            next_start = start + max(1, target_chars // 2)
        start = next_start

    return chunks
