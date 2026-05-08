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

from app.rag.retrieval import ChunkHit, infer_intent_fields, iter_chunks, normalize_query, retrieve
from app.corpus.manifest import allowlisted_schemes

_LINE_SPLIT = re.compile(r"\r?\n")
_NAV_KEY_LINE = re.compile(r"(?m)^nav:\s*\S")
_EXPENSE_RATIO_KEY_LINE = re.compile(r"(?m)^expense_ratio:\s*\S")
_EXIT_LOAD_KEY_LINE = re.compile(r"(?m)^exit_load:\s*\S")
_LOCK_IN_YEARS_KEY_LINE = re.compile(r"(?m)^(additional_details\.lock_in_yrs|lock_in\.years):\s*\S")
_GROWW_RATING_KEY_LINE = re.compile(r"(?m)^groww_rating:\s*\S")
_RISK_RATING_KEY_LINE = re.compile(r"(?m)^risk_rating:\s*\S")
_NFO_RISK_KEY_LINE = re.compile(r"(?m)^nfo_risk:\s*\S")

# Nested / noisy keys: use for retrieval boosts elsewhere, but not for verbatim answer lines
# (e.g. fund_manager_details lists many person_name rows; top-level fund_manager is authoritative).
_EXTRACTION_SKIP_KEYS = frozenset({"fund_manager_details"})

_RE_HTML_TAG = re.compile(r"<[^>]+>")


def _extraction_intent_keys(intent: set[str]) -> set[str]:
    return {k for k in intent if k not in _EXTRACTION_SKIP_KEYS}


def _primary_intent_keys(intent: set[str]) -> list[str]:
    """
    Phase 2: return only the single requested field when possible.
    Prefer canonical top-level keys over nested/auxiliary keys.
    """
    # Most specific / most commonly asked
    if "expense_ratio" in intent:
        return ["expense_ratio"]
    if "exit_load" in intent:
        return ["exit_load"]
    if "fund_manager" in intent:
        return ["fund_manager"]
    if "benchmark_name" in intent:
        return ["benchmark_name"]
    if "benchmark" in intent:
        return ["benchmark"]
    if "groww_rating" in intent:
        return ["groww_rating"]
    if "nfo_risk" in intent:
        return ["nfo_risk"]
    if "risk_rating" in intent:
        return ["risk_rating"]
    # NAV: keep nav_date inline as supporting context (still one line output).
    if "nav" in intent:
        return ["nav", "nav_date"] if "nav_date" in intent else ["nav"]
    # Lock-in: prefer lock_in.years (cleaner), otherwise additional_details.lock_in_yrs.
    if "lock_in.years" in intent:
        return ["lock_in.years"]
    if "additional_details.lock_in_yrs" in intent:
        return ["additional_details.lock_in_yrs"]
    # Tax: prefer category_info.tax_impact if present in intent
    if "category_info.tax_impact" in intent:
        return ["category_info.tax_impact"]
    if "tax_impact" in intent:
        return ["tax_impact"]
    # AUM
    if "aum" in intent:
        return ["aum"]
    if "description" in intent:
        return ["description"]
    return sorted(_extraction_intent_keys(intent), key=len, reverse=True)


def _hits_include_nav_line(hits: list[ChunkHit]) -> bool:
    return any(_NAV_KEY_LINE.search(h.text) for h in hits)


def _hits_include_expense_ratio_line(hits: list[ChunkHit]) -> bool:
    return any(_EXPENSE_RATIO_KEY_LINE.search(h.text) for h in hits)


def _hits_include_exit_load_line(hits: list[ChunkHit]) -> bool:
    return any(_EXIT_LOAD_KEY_LINE.search(h.text) for h in hits)


def _hits_include_lock_in_line(hits: list[ChunkHit]) -> bool:
    return any(_LOCK_IN_YEARS_KEY_LINE.search(h.text) for h in hits)


def _hits_include_groww_rating_line(hits: list[ChunkHit]) -> bool:
    return any(_GROWW_RATING_KEY_LINE.search(h.text) for h in hits)


def _hits_include_risk_rating_line(hits: list[ChunkHit]) -> bool:
    return any(_RISK_RATING_KEY_LINE.search(h.text) for h in hits)

def _hits_include_nfo_risk_line(hits: list[ChunkHit]) -> bool:
    return any(_NFO_RISK_KEY_LINE.search(h.text) for h in hits)


def _first_chunk_hit_with_nav(
    chunks_root: Path,
    scheme_filter: set[str] | None,
) -> ChunkHit | None:
    """
    NAV often lives only in a late `meta_desc` chunk; FAISS shortlists can miss it.
    Scan on-disk chunks when we need NAV but retrieval didn't surface a `nav:` line.
    """
    for row in iter_chunks(chunks_root, scheme_ids=scheme_filter):
        text = str(row.get("text") or "")
        if not _NAV_KEY_LINE.search(text):
            continue
        return ChunkHit(
            chunk_id=str(row["chunk_id"]),
            scheme_id=str(row["scheme_id"]),
            source_url=str(row["source_url"]),
            doc_type=str(row.get("doc_type") or ""),
            section_path=str(row.get("section_path") or ""),
            score=0.0,
            text=text,
        )
    return None


def _first_chunk_hit_with_expense_ratio(
    chunks_root: Path,
    scheme_filter: set[str] | None,
) -> ChunkHit | None:
    """
    `historic_fund_expense[...]` appears in many schemes and can dominate retrieval.
    When the user asks for expense ratio, prefer the canonical top-level `expense_ratio:` line.
    """
    for row in iter_chunks(chunks_root, scheme_ids=scheme_filter):
        text = str(row.get("text") or "")
        if not _EXPENSE_RATIO_KEY_LINE.search(text):
            continue
        return ChunkHit(
            chunk_id=str(row["chunk_id"]),
            scheme_id=str(row["scheme_id"]),
            source_url=str(row["source_url"]),
            doc_type=str(row.get("doc_type") or ""),
            section_path=str(row.get("section_path") or ""),
            score=0.0,
            text=text,
        )
    return None


def _first_chunk_hit_with_exit_load(
    chunks_root: Path,
    scheme_filter: set[str] | None,
) -> ChunkHit | None:
    for row in iter_chunks(chunks_root, scheme_ids=scheme_filter):
        text = str(row.get("text") or "")
        if not _EXIT_LOAD_KEY_LINE.search(text):
            continue
        return ChunkHit(
            chunk_id=str(row["chunk_id"]),
            scheme_id=str(row["scheme_id"]),
            source_url=str(row["source_url"]),
            doc_type=str(row.get("doc_type") or ""),
            section_path=str(row.get("section_path") or ""),
            score=0.0,
            text=text,
        )
    return None


def _first_chunk_hit_with_lock_in_years(
    chunks_root: Path,
    scheme_filter: set[str] | None,
) -> ChunkHit | None:
    for row in iter_chunks(chunks_root, scheme_ids=scheme_filter):
        text = str(row.get("text") or "")
        if not _LOCK_IN_YEARS_KEY_LINE.search(text):
            continue
        return ChunkHit(
            chunk_id=str(row["chunk_id"]),
            scheme_id=str(row["scheme_id"]),
            source_url=str(row["source_url"]),
            doc_type=str(row.get("doc_type") or ""),
            section_path=str(row.get("section_path") or ""),
            score=0.0,
            text=text,
        )
    return None


def _first_chunk_hit_with_groww_rating(
    chunks_root: Path,
    scheme_filter: set[str] | None,
) -> ChunkHit | None:
    for row in iter_chunks(chunks_root, scheme_ids=scheme_filter):
        text = str(row.get("text") or "")
        if not _GROWW_RATING_KEY_LINE.search(text):
            continue
        return ChunkHit(
            chunk_id=str(row["chunk_id"]),
            scheme_id=str(row["scheme_id"]),
            source_url=str(row["source_url"]),
            doc_type=str(row.get("doc_type") or ""),
            section_path=str(row.get("section_path") or ""),
            score=0.0,
            text=text,
        )
    return None


def _first_chunk_hit_with_risk_rating(
    chunks_root: Path,
    scheme_filter: set[str] | None,
) -> ChunkHit | None:
    for row in iter_chunks(chunks_root, scheme_ids=scheme_filter):
        text = str(row.get("text") or "")
        if not _RISK_RATING_KEY_LINE.search(text):
            continue
        return ChunkHit(
            chunk_id=str(row["chunk_id"]),
            scheme_id=str(row["scheme_id"]),
            source_url=str(row["source_url"]),
            doc_type=str(row.get("doc_type") or ""),
            section_path=str(row.get("section_path") or ""),
            score=0.0,
            text=text,
        )
    return None


def _first_chunk_hit_with_nfo_risk(
    chunks_root: Path,
    scheme_filter: set[str] | None,
) -> ChunkHit | None:
    for row in iter_chunks(chunks_root, scheme_ids=scheme_filter):
        text = str(row.get("text") or "")
        if not _NFO_RISK_KEY_LINE.search(text):
            continue
        return ChunkHit(
            chunk_id=str(row["chunk_id"]),
            scheme_id=str(row["scheme_id"]),
            source_url=str(row["source_url"]),
            doc_type=str(row.get("doc_type") or ""),
            section_path=str(row.get("section_path") or ""),
            score=0.0,
            text=text,
        )
    return None


def _canonical_value_lines(text: str, intent: set[str], *, max_lines: int = 6) -> list[str]:
    """
    Pull verbatim `key: value` lines from structured chunk text for keys we inferred from the query.
    Longer keys first so `benchmark_name` wins over `benchmark` when both appear on separate lines.
    """
    keys = _primary_intent_keys(intent)
    if not keys:
        return []
    lines = [ln.strip() for ln in _LINE_SPLIT.split(text) if ln.strip()]
    out: list[str] = []

    # Special-case: NAV returns a single line including nav_date if available.
    if keys and keys[0] == "nav":
        nav_ln: str | None = None
        nav_date_ln: str | None = None
        for ln in lines:
            ll = ln.lower()
            if ll.startswith("nav:"):
                nav_ln = ln
            elif ll.startswith("nav_date:"):
                nav_date_ln = ln
            if nav_ln and ("nav_date" not in intent or nav_date_ln):
                break
        if nav_ln and nav_date_ln:
            return [f"{nav_ln} ({nav_date_ln})"]
        if nav_ln:
            return [nav_ln]
        return []

    # Default: return the first exact `key:` line for the primary requested key.
    primary = keys[0]
    prefix = f"{primary.lower()}:"
    for ln in lines:
        if ln.lower().startswith(prefix):
            out.append(ln)
            break
    return out[:max_lines]


@dataclass(frozen=True)
class AnswerResult:
    answer_text: str
    citation_url: str  # empty when UNKNOWN
    last_updated_utc_date: str  # YYYY-MM-DD (UTC)
    hits: list[ChunkHit]
    used_canonical_extraction: bool = False
    grounded_lines: list[str] | None = None


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
    text = _RE_HTML_TAG.sub("", " ".join(lines)).strip()
    parts = re.split(r"(?<=[.?!])\s+", text)
    trimmed = " ".join(parts[:max_sentences]).strip()
    return trimmed if trimmed else text.strip()


def _scheme_display_name(scheme_id: str) -> str:
    for s in allowlisted_schemes():
        if s.get("scheme_id") == scheme_id and s.get("display_name"):
            return str(s["display_name"])
    # fallback: prettify scheme_id
    return scheme_id.replace("_", " ").strip()


def _friendly_one_liner(*, scheme_name: str, key: str, value: str, extra: str | None = None) -> str:
    k = key.lower().strip()
    v = value.strip()
    # Clean common punctuation/duplication from values (keeps facts unchanged).
    v = re.sub(r"\s+", " ", v).strip()
    v = re.sub(r"[.]+\s*$", "", v).strip()
    if extra:
        extra = extra.strip()
    if k == "nav":
        # include nav_date as "as of" when present
        if extra:
            return f'The NAV for {scheme_name} is {v} (as of {extra}).'
        return f"The NAV for {scheme_name} is {v}."
    if k == "expense_ratio":
        return f"The expense ratio for {scheme_name} is {v}."
    if k == "exit_load":
        # Values sometimes already start with "Exit load ..."; avoid "exit load ... is Exit load ...".
        v2 = re.sub(r"^\s*exit\s*load\s*(of|:)?\s*", "", v, flags=re.IGNORECASE).strip()
        v2 = v2 if v2 else v
        return f"The exit load for {scheme_name} is {v2}."
    if k in {"lock_in.years", "additional_details.lock_in_yrs"}:
        return f"The lock-in period for {scheme_name} is {v}."
    if k == "groww_rating":
        return f"The Groww rating for {scheme_name} is {v}."
    if k == "risk_rating":
        return f"The risk rating for {scheme_name} is {v}."
    if k == "nfo_risk":
        return f"The riskometer for {scheme_name} is {v}."
    if k == "fund_manager":
        return f"The fund manager for {scheme_name} is {v}."
    if k in {"benchmark", "benchmark_name"}:
        return f"The benchmark for {scheme_name} is {v}."
    if k in {"aum"}:
        return f"The AUM for {scheme_name} is {v}."
    if k in {"tax_impact", "category_info.tax_impact"}:
        return f"The tax impact for {scheme_name} is {v}."
    if k == "description":
        return f"About {scheme_name}: {v}."
    return f"The {k.replace('_', ' ')} for {scheme_name} is {v}."


def _parse_key_value(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    k, v = line.split(":", 1)
    k = k.strip()
    v = _RE_HTML_TAG.sub("", v).strip()
    if not k or not v:
        return None
    return k, v


def answer_query(
    *,
    query: str,
    chunks_root: Path,
    registry_latest_path: Path,
    top_k: int = 5,
    scheme_filter: set[str] | None = None,
) -> AnswerResult:
    faiss_dir: Path | None = None
    try:
        if registry_latest_path.is_file():
            latest = json.loads(registry_latest_path.read_text(encoding="utf-8"))
            index_name = latest.get("index_name")
            if isinstance(index_name, str) and index_name.strip():
                cand = Path("data/index") / index_name
                if (cand / "index.faiss").is_file():
                    faiss_dir = cand
    except Exception:
        faiss_dir = None

    nq = normalize_query(query)
    intent_nav = infer_intent_fields(nq)

    hits = retrieve(
        chunks_root=chunks_root,
        query=query,
        top_k=top_k,
        scheme_filter=scheme_filter,
        faiss_index_dir=faiss_dir,
    )
    if "nav" in intent_nav and not _hits_include_nav_line(hits):
        scan_schemes = scheme_filter if scheme_filter else ({hits[0].scheme_id} if hits else None)
        if scan_schemes:
            fill = _first_chunk_hit_with_nav(chunks_root, scan_schemes)
            if fill:
                rest = [h for h in hits if h.chunk_id != fill.chunk_id]
                hits = [fill] + rest

    if "expense_ratio" in intent_nav and not _hits_include_expense_ratio_line(hits):
        scan_schemes = scheme_filter if scheme_filter else ({hits[0].scheme_id} if hits else None)
        if scan_schemes:
            fill = _first_chunk_hit_with_expense_ratio(chunks_root, scan_schemes)
            if fill:
                rest = [h for h in hits if h.chunk_id != fill.chunk_id]
                hits = [fill] + rest

    if "exit_load" in intent_nav and not _hits_include_exit_load_line(hits):
        scan_schemes = scheme_filter if scheme_filter else ({hits[0].scheme_id} if hits else None)
        if scan_schemes:
            fill = _first_chunk_hit_with_exit_load(chunks_root, scan_schemes)
            if fill:
                rest = [h for h in hits if h.chunk_id != fill.chunk_id]
                hits = [fill] + rest

    if ("additional_details.lock_in_yrs" in intent_nav or "lock_in.years" in intent_nav) and not _hits_include_lock_in_line(hits):
        scan_schemes = scheme_filter if scheme_filter else ({hits[0].scheme_id} if hits else None)
        if scan_schemes:
            fill = _first_chunk_hit_with_lock_in_years(chunks_root, scan_schemes)
            if fill:
                rest = [h for h in hits if h.chunk_id != fill.chunk_id]
                hits = [fill] + rest

    if "groww_rating" in intent_nav and not _hits_include_groww_rating_line(hits):
        scan_schemes = scheme_filter if scheme_filter else ({hits[0].scheme_id} if hits else None)
        if scan_schemes:
            fill = _first_chunk_hit_with_groww_rating(chunks_root, scan_schemes)
            if fill:
                rest = [h for h in hits if h.chunk_id != fill.chunk_id]
                hits = [fill] + rest

    if "risk_rating" in intent_nav and not _hits_include_risk_rating_line(hits):
        scan_schemes = scheme_filter if scheme_filter else ({hits[0].scheme_id} if hits else None)
        if scan_schemes:
            fill = _first_chunk_hit_with_risk_rating(chunks_root, scan_schemes)
            if fill:
                rest = [h for h in hits if h.chunk_id != fill.chunk_id]
                hits = [fill] + rest

    if "nfo_risk" in intent_nav and not _hits_include_nfo_risk_line(hits):
        scan_schemes = scheme_filter if scheme_filter else ({hits[0].scheme_id} if hits else None)
        if scan_schemes:
            fill = _first_chunk_hit_with_nfo_risk(chunks_root, scan_schemes)
            if fill:
                rest = [h for h in hits if h.chunk_id != fill.chunk_id]
                hits = [fill] + rest

    if not hits:
        # No hit → still return a safe response without fabricating facts.
        last = _load_last_updated(registry_latest_path)
        return AnswerResult(
            answer_text="I couldn’t find that information in the indexed corpus.",
            citation_url="",
            last_updated_utc_date=last,
            hits=[],
            used_canonical_extraction=False,
            grounded_lines=None,
        )

    intent = intent_nav
    extract_keys = _extraction_intent_keys(intent)

    top = hits[0]
    canonical: list[str] = []
    if extract_keys:
        for h in hits:
            canonical = _canonical_value_lines(h.text, intent)
            if canonical:
                top = h
                break

        # If the user asked for a specific factual key and we couldn't find the exact `key: value`
        # line anywhere in the retrieved hits, treat as UNKNOWN (avoid answering with an unrelated fact).
        if not canonical:
            last = _load_last_updated(registry_latest_path)
            return AnswerResult(
                answer_text="I couldn’t find that information in the indexed corpus.",
                citation_url="",
                last_updated_utc_date=last,
                hits=hits,
                used_canonical_extraction=False,
                grounded_lines=None,
            )

    if canonical:
        lines = canonical
        used_canonical = True
    else:
        lines = _extract_relevant_lines(top.text, query=query)
        used_canonical = False

    # If we can't extract anything meaningful, treat it as UNKNOWN.
    if not lines:
        last = _load_last_updated(registry_latest_path)
        return AnswerResult(
            answer_text="I couldn’t find that information in the indexed corpus.",
            citation_url="",
            last_updated_utc_date=last,
            hits=hits,
            used_canonical_extraction=False,
            grounded_lines=None,
        )
    # Factual output should be one friendly line when we have a canonical key/value.
    if used_canonical and lines:
        scheme_name = _scheme_display_name(top.scheme_id)
        # special case: "nav: ... (nav_date: ...)" from canonical extraction
        ln = lines[0]
        m = re.match(r"^\s*nav:\s*(.+?)\s*\(\s*nav_date:\s*(.+?)\s*\)\s*$", ln, flags=re.IGNORECASE)
        if m:
            a = _friendly_one_liner(scheme_name=scheme_name, key="nav", value=m.group(1), extra=m.group(2))
        else:
            kv = _parse_key_value(ln)
            if kv:
                a = _friendly_one_liner(scheme_name=scheme_name, key=kv[0], value=kv[1])
            else:
                a = _compose_answer(lines, max_sentences=1)
    else:
        a = _compose_answer(lines, max_sentences=1)

    last = _load_last_updated(registry_latest_path)
    # enforce exactly one citation URL (top hit source_url)
    citation = top.source_url
    return AnswerResult(
        answer_text=a,
        citation_url=citation,
        last_updated_utc_date=last,
        hits=hits,
        used_canonical_extraction=used_canonical,
        grounded_lines=lines,
    )

