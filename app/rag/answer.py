"""
Phase 2 grounded answering (no external LLM required for now).

This module is intentionally conservative:
- selects top retrieved chunk(s)
- extracts a few relevant lines
- returns a single allowlisted citation URL (or empty when UNKNOWN)
- returns last-updated UTC date (from registry metadata)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.rag.retrieval import ChunkHit, infer_intent_fields, normalize_query, retrieve

_LINE_SPLIT = re.compile(r"\r?\n")


@dataclass(frozen=True)
class AnswerResult:
    answer_text: str
    citation_url: str  # empty when UNKNOWN
    last_updated_utc_date: str  # YYYY-MM-DD (UTC)
    hits: list[ChunkHit]


def _load_last_updated(registry_latest_path: Path, *, fallback: str = "1970-01-01") -> str:
    if not registry_latest_path.is_file():
        return fallback
    try:
        obj = json.loads(registry_latest_path.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    v = obj.get("ingestion_batch_date_utc")
    if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return v
    return fallback


def _extract_relevant_lines(text: str, *, query: str, max_lines: int = 4) -> list[str]:
    nq = normalize_query(query)
    intent = infer_intent_fields(nq)
    q = nq.lower()
    toks = [t for t in re.findall(r"[a-z0-9_]+", q) if len(t) >= 3]
    lines = [ln.strip() for ln in _LINE_SPLIT.split(text) if ln.strip()]
    if not lines:
        return []

    # If we know the user likely wants a specific structured key, prioritize exact key lines.
    key_prefixes = tuple(f"{k}:" for k in sorted(intent))
    if key_prefixes:
        exact = [ln for ln in lines if ln.lower().startswith(key_prefixes)]
        if exact:
            return exact[:max_lines]

    scored: list[tuple[int, str]] = []
    for ln in lines:
        ll = ln.lower()
        s = 0
        for t in toks:
            if t in ll:
                s += 1
        scored.append((s, ln))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = [ln for s, ln in scored if s > 0][:max_lines]
    if out:
        return out
    # fallback: first few lines
    return lines[:max_lines]


def _compose_answer(lines: list[str], *, max_sentences: int = 3) -> str:
    if not lines:
        return "I couldn’t find a matching factual snippet in the indexed corpus."
    # simple sentence cap: join lines and then split on period-like punctuation
    text = " ".join(lines)
    parts = re.split(r"(?<=[.?!])\s+", text)
    trimmed = " ".join(parts[:max_sentences]).strip()
    return trimmed if trimmed else text.strip()


def answer_query(
    *,
    query: str,
    chunks_root: Path,
    registry_latest_path: Path,
    top_k: int = 5,
    scheme_filter: set[str] | None = None,
) -> AnswerResult:
    hits = retrieve(chunks_root=chunks_root, query=query, top_k=top_k, scheme_filter=scheme_filter)
    if not hits:
        # No hit → still return a safe response without fabricating facts.
        last = _load_last_updated(registry_latest_path)
        return AnswerResult(
            answer_text="I couldn’t find that information in the indexed corpus.",
            citation_url="",
            last_updated_utc_date=last,
            hits=[],
        )

    top = hits[0]
    lines = _extract_relevant_lines(top.text, query=query)
    # If we can't extract anything meaningful, treat it as UNKNOWN.
    if not lines:
        last = _load_last_updated(registry_latest_path)
        return AnswerResult(
            answer_text="I couldn’t find that information in the indexed corpus.",
            citation_url="",
            last_updated_utc_date=last,
            hits=hits,
        )
    a = _compose_answer(lines)

    last = _load_last_updated(registry_latest_path)
    # enforce exactly one citation URL (top hit source_url)
    citation = top.source_url
    return AnswerResult(answer_text=a, citation_url=citation, last_updated_utc_date=last, hits=hits)

