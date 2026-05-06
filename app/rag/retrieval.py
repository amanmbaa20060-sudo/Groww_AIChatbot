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
from functools import lru_cache
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


def _load_chunk_text_by_id(chunks_root: Path, *, scheme_id: str, chunk_id: str) -> str | None:
    p = chunks_root / scheme_id / "chunks.jsonl"
    if not p.is_file():
        return None
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("chunk_id") == chunk_id:
                t = obj.get("text")
                return str(t) if isinstance(t, str) else None
    return None


@lru_cache(maxsize=4)
def _load_faiss_index(index_dir: str) -> tuple[object, list[dict[str, Any]], int]:
    """
    Load FAISS index + row metadata.
    Cached by index_dir string path.
    """
    try:
        import faiss  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"faiss import failed: {e}") from e

    idx_path = Path(index_dir) / "index.faiss"
    meta_path = Path(index_dir) / "meta.jsonl"
    index_meta_path = Path(index_dir) / "index_meta.json"
    if not idx_path.is_file():
        raise FileNotFoundError(f"Missing FAISS index: {idx_path}")
    if not meta_path.is_file():
        raise FileNotFoundError(f"Missing FAISS meta: {meta_path}")
    index = faiss.read_index(str(idx_path))
    meta: list[dict[str, Any]] = []
    with meta_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            meta.append(json.loads(line))

    dim = 768
    if index_meta_path.is_file():
        try:
            im = json.loads(index_meta_path.read_text(encoding="utf-8"))
            v = im.get("embedding_dim")
            if isinstance(v, int) and v > 0:
                dim = v
        except Exception:
            pass

    return index, meta, dim


def retrieve_faiss(
    *,
    chunks_root: Path,
    index_dir: Path,
    query: str,
    top_k: int = 5,
    scheme_filter: set[str] | None = None,
    search_k: int | None = None,
) -> list[ChunkHit]:
    """
    Vector retrieval via FAISS.
    Uses the same Phase 1.4 hash embedder (L2-normalized), and IndexFlatIP.
    """
    try:
        import numpy as np  # type: ignore
        from ingestion.phase1.subphase_1_4_embed.hash_embedder import hash_embed_to_float32_bytes
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"missing vector deps: {e}") from e

    index, meta_rows, dim = _load_faiss_index(str(index_dir))
    q_bytes = hash_embed_to_float32_bytes(query, dim=dim, salt=f"groww_rag_hash_v1_dim={dim}")
    q = np.frombuffer(q_bytes, dtype=np.float32).reshape(1, dim)

    # Search more than top_k if scheme_filter is applied, then filter down.
    if search_k is None:
        search_k = max(top_k * 8, top_k)
    scores, idxs = index.search(q, int(search_k))
    out: list[ChunkHit] = []

    for score, row_idx in zip(scores[0].tolist(), idxs[0].tolist()):
        if row_idx < 0 or row_idx >= len(meta_rows):
            continue
        m = meta_rows[row_idx]
        scheme_id = str(m.get("scheme_id") or "")
        if scheme_filter and scheme_id not in scheme_filter:
            continue
        chunk_id = str(m.get("chunk_id") or "")
        if not scheme_id or not chunk_id:
            continue
        text = _load_chunk_text_by_id(chunks_root, scheme_id=scheme_id, chunk_id=chunk_id)
        if not text:
            continue
        out.append(
            ChunkHit(
                chunk_id=chunk_id,
                scheme_id=scheme_id,
                source_url=str(m.get("source_url") or ""),
                doc_type=str(m.get("doc_type") or ""),
                section_path=str(m.get("section_path") or ""),
                score=float(score),
                text=text,
            )
        )
        if len(out) >= top_k:
            break

    return out


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
    faiss_index_dir: Path | None = None,
) -> list[ChunkHit]:
    nq = normalize_query(query)
    q_tokens = _tokenize(nq)
    intent = infer_intent_fields(nq)

    def score_hit_text(text: str, section_path: str) -> float:
        base = lexical_score(text, q_tokens)
        sp = (section_path or "").lower()
        boost = section_boost(sp, intent)
        tl = text.lower()
        for f in intent:
            if f"{f}:" in tl:
                boost += 4.0
        if "fund_manager" in intent and "fund_manager:" in tl:
            boost += 20.0
        if "expense_ratio" in intent and "expense_ratio:" in tl:
            boost += 20.0
            if "historic" in sp:
                boost -= 8.0
        if "exit_load" in intent and "exit_load:" in tl:
            boost += 20.0
        for k in intent:
            if re.search(rf"(?m)^{re.escape(k)}:", text):
                boost += 30.0
        return base + boost

    # If FAISS index exists, use it to shortlist candidates, then re-rank using lexical/intent scoring.
    if faiss_index_dir is not None:
        try:
            if (faiss_index_dir / "index.faiss").is_file():
                cand = retrieve_faiss(
                    chunks_root=chunks_root,
                    index_dir=faiss_index_dir,
                    query=query,
                    top_k=max(top_k * 10, top_k),
                    scheme_filter=scheme_filter,
                    search_k=max(top_k * 50, top_k),
                )
                if cand:
                    reranked: list[ChunkHit] = []
                    for h in cand:
                        s = score_hit_text(h.text, h.section_path) + (0.25 * float(h.score))
                        reranked.append(
                            ChunkHit(
                                chunk_id=h.chunk_id,
                                scheme_id=h.scheme_id,
                                source_url=h.source_url,
                                doc_type=h.doc_type,
                                section_path=h.section_path,
                                score=s,
                                text=h.text,
                            )
                        )
                    reranked.sort(key=lambda h: h.score, reverse=True)
                    return reranked[: max(1, top_k)]
        except Exception:
            pass

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
        sp = str(row.get("section_path") or "")
        return score_hit_text(text, sp)

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

