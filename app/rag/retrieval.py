"""
Phase 2 retrieval (lexical-first) over Phase 1 artifacts.

Current data reality:
- chunk text is key/value heavy and term-exact (exit_load, expense_ratio, benchmark, etc.)
- embeddings are hash-based (Phase 1.4) and not a strong semantic signal

So we use lexical scoring + section-aware boosting + optional scheme_id filtering.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_CANONICAL_KEY_LINE = re.compile(r"(?m)^(exit_load|expense_ratio|fund_manager|benchmark_name|benchmark|aum|nav|tax_impact):")


def _tokenize(q: str) -> list[str]:
    return _TOKEN_RE.findall(q.lower())


def normalize_query(q: str) -> str:
    ql = q.lower().strip()
    # small, explicit synonym map (rules only)
    ql = ql.replace("ter", "expense ratio")
    ql = ql.replace("exitload", "exit load")
    # prefer underscore form to match flattened mfServerSideData keys
    ql = ql.replace("exit load", "exit_load")
    ql = ql.replace("expense ratio", "expense_ratio")
    ql = ql.replace("fund manager", "fund_manager")
    ql = ql.replace("aum", "aum")
    return ql


def infer_intent_fields(q: str) -> set[str]:
    ql = q.lower()
    out: set[str] = set()
    if "exit_load" in ql or "exit load" in ql or "exitload" in ql:
        out.add("exit_load")
    if "expense_ratio" in ql or "expense" in ql or "ter" in ql:
        out.add("expense_ratio")
    if "benchmark" in ql:
        out.add("benchmark")
        out.add("benchmark_name")
    if "fund_manager" in ql or "fund manager" in ql or "manager" in ql:
        out.add("fund_manager")
        out.add("fund_manager_details")
    if "tax" in ql:
        out.add("tax_impact")
    if "aum" in ql:
        out.add("aum")
    if "nav" in ql:
        out.add("nav")
    return out


@dataclass(frozen=True)
class ChunkHit:
    chunk_id: str
    scheme_id: str
    source_url: str
    doc_type: str
    section_path: str
    score: float
    text: str


def iter_chunks(chunks_root: Path, *, scheme_ids: set[str] | None = None) -> Iterable[dict[str, Any]]:
    if scheme_ids is None:
        for p in chunks_root.rglob("chunks.jsonl"):
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    yield json.loads(line)
        return

    for sid in sorted(scheme_ids):
        p = chunks_root / sid / "chunks.jsonl"
        if not p.is_file():
            continue
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)


def lexical_score(text: str, query_tokens: list[str]) -> float:
    """
    Very small BM25-ish score:
    - count token occurrences
    - log dampening
    """
    tl = text.lower()
    s = 0.0
    for tok in query_tokens:
        if not tok:
            continue
        c = tl.count(tok)
        if c:
            s += 1.0 + math.log(1.0 + c)
    return s


def section_boost(section_path: str, intent_fields: set[str]) -> float:
    sp = (section_path or "").lower()
    if not sp:
        return 0.0
    b = 0.0
    for f in intent_fields:
        if sp == f:
            b += 6.0
        elif f in sp:
            # Prefer exact keys over related subsections like fund_manager_details
            if sp.endswith("_details") and f in sp:
                b += 1.5
            else:
                b += 3.0
    return b


def retrieve(
    *,
    chunks_root: Path,
    query: str,
    top_k: int = 5,
    scheme_filter: set[str] | None = None,
) -> list[ChunkHit]:
    nq = normalize_query(query)
    q_tokens = _tokenize(nq)
    intent = infer_intent_fields(nq)

    def row_matches_intent(row: dict[str, Any]) -> bool:
        if not intent:
            return True
        sp = str(row.get("section_path") or "").lower()
        if any(f in sp for f in intent):
            return True
        t = str(row.get("text") or "").lower()
        return any(f"{f}:" in t for f in intent)

    def score_row(row: dict[str, Any]) -> float:
        text = str(row.get("text") or "")
        base = lexical_score(text, q_tokens)
        sp = str(row.get("section_path") or "").lower()
        boost = section_boost(sp, intent)
        # extra boost if exact structured key appears (helps key/value queries)
        tl = text.lower()
        for f in intent:
            if f"{f}:" in tl:
                boost += 4.0
        # Strong preference for canonical single-value keys when present
        if "fund_manager" in intent and "fund_manager:" in tl:
            boost += 20.0
        if "expense_ratio" in intent and "expense_ratio:" in tl:
            boost += 20.0
            # Prefer the canonical current value over historic series when possible
            if "historic" in sp:
                boost -= 8.0
        if "exit_load" in intent and "exit_load:" in tl:
            boost += 20.0
        # Strong boost when the *requested* canonical key appears at start-of-line
        for k in intent:
            if re.search(rf"(?m)^{re.escape(k)}:", text):
                boost += 30.0
        return base + boost

    # If scheme-filtered and we have a clear intent (exit_load, expense_ratio, etc.),
    # prefer intent-matching chunks first; fallback to general lexical if no hit.
    candidates = list(iter_chunks(chunks_root, scheme_ids=scheme_filter))
    primary = [r for r in candidates if row_matches_intent(r)]
    if primary:
        candidates = primary

    hits: list[ChunkHit] = []
    for row in candidates:
        text = str(row.get("text") or "")
        if not text:
            continue
        score = score_row(row)
        if score <= 0.0:
            continue
        hits.append(
            ChunkHit(
                chunk_id=str(row["chunk_id"]),
                scheme_id=str(row["scheme_id"]),
                source_url=str(row["source_url"]),
                doc_type=str(row.get("doc_type") or ""),
                section_path=str(row.get("section_path") or ""),
                score=score,
                text=text,
            )
        )

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[: max(1, top_k)]

