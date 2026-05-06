"""
Phase 3 guardrails (rule-based) for the closed-corpus MF assistant.

Key policy additions:
- If query contains personal information / asks for account-level help → refuse with NO URL.
- If we cannot answer from retrieved chunks (UNKNOWN) → respond with NO URL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.rag.answer import AnswerResult, answer_query
from app.llm.groq_chat import GroqError, groq_chat_completion


class QueryLabel(str, Enum):
    FACTUAL_MF = "FACTUAL_MF"
    ADVISORY = "ADVISORY"
    COMPARISON = "COMPARISON"
    PERFORMANCE_HISTORY = "PERFORMANCE_HISTORY"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    AMBIGUOUS = "AMBIGUOUS"
    PERSONAL_INFO = "PERSONAL_INFO"
    UNKNOWN = "UNKNOWN"


_RE_PAN = re.compile(r"\b[a-z]{5}\d{4}[a-z]\b", re.IGNORECASE)
_RE_AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_RE_OTP = re.compile(r"\botp\b", re.IGNORECASE)
_RE_BANK = re.compile(r"\b(account number|ifsc|upi|netbanking|debit card|credit card)\b", re.IGNORECASE)
_RE_PHONE = re.compile(r"\b\d{10}\b")
_RE_EMAIL = re.compile(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.IGNORECASE)

_RE_ADVICE = re.compile(r"\b(should i|recommend|suggest|good investment|buy|sell|best fund|where should i invest)\b", re.IGNORECASE)
_RE_COMPARE = re.compile(r"\b(vs\.?|versus|better than|compare|which is better)\b", re.IGNORECASE)
_RE_PERF = re.compile(r"\b(returns?|cagr|performance|rank|best performer|past performance)\b", re.IGNORECASE)


@dataclass(frozen=True)
class GuardrailResult:
    label: QueryLabel
    response: str


@dataclass(frozen=True)
class GuardrailStructured:
    label: QueryLabel
    answer_text: str
    citation_url: str | None
    last_updated_utc_date: str | None
    llm_used: bool = False
    llm_error: str | None = None


def _groq_generate_answer_text(*, query: str, grounded_snippet: str, model: str) -> str:
    """
    Generate a short, facts-only answer using Groq, grounded to provided snippet.

    Safety constraints:
    - Must not add extra URLs
    - Must keep ≤3 sentences
    """
    sys_msg = (
        "You are a facts-only mutual fund FAQ assistant. "
        "You must answer ONLY using the provided snippet. "
        "Max 3 sentences. Do NOT provide investment advice. "
        "Do NOT include any URLs in the answer text."
    )
    user_msg = (
        f"Question: {query}\n\n"
        f"Snippet (ground truth):\n{grounded_snippet}\n\n"
        "Return the direct factual answer."
    )
    r = groq_chat_completion(
        model=model,
        temperature=0.0,
        max_tokens=220,
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ],
    )
    return r.text


def classify_query(q: str) -> QueryLabel:
    q = (q or "").strip()
    if not q:
        return QueryLabel.AMBIGUOUS

    # Personal info / account-level support (NO URL)
    if (
        _RE_PAN.search(q)
        or _RE_AADHAAR.search(q)
        or _RE_OTP.search(q)
        or _RE_BANK.search(q)
        or _RE_EMAIL.search(q)
        or _RE_PHONE.search(q)
    ):
        return QueryLabel.PERSONAL_INFO

    if _RE_COMPARE.search(q):
        return QueryLabel.COMPARISON
    if _RE_ADVICE.search(q):
        return QueryLabel.ADVISORY
    if _RE_PERF.search(q):
        return QueryLabel.PERFORMANCE_HISTORY

    # Default: treat as factual; Phase 2 retrieval will decide if UNKNOWN
    return QueryLabel.FACTUAL_MF


def run_phase3(
    *,
    query: str,
    chunks_root: Path,
    registry_latest_path: Path,
    scheme_filter: set[str] | None = None,
    use_groq: bool = False,
    groq_model: str = "llama-3.1-8b-instant",
) -> GuardrailResult:
    r = run_phase3_structured(
        query=query,
        chunks_root=chunks_root,
        registry_latest_path=registry_latest_path,
        scheme_filter=scheme_filter,
        use_groq=use_groq,
        groq_model=groq_model,
    )
    # Keep legacy response formatting for CLI callers
    if r.citation_url and r.last_updated_utc_date:
        return GuardrailResult(
            label=r.label,
            response=f"{r.answer_text}\n\nSource: {r.citation_url}\nLast updated from sources: {r.last_updated_utc_date}",
        )
    return GuardrailResult(label=r.label, response=r.answer_text)


def run_phase3_structured(
    *,
    query: str,
    chunks_root: Path,
    registry_latest_path: Path,
    scheme_filter: set[str] | None = None,
    use_groq: bool = False,
    groq_model: str = "llama-3.1-8b-instant",
) -> GuardrailStructured:
    label = classify_query(query)

    if label == QueryLabel.PERSONAL_INFO:
        return GuardrailStructured(
            label=label,
            answer_text=(
                "I can’t help with requests that include or ask for personal/account details (PAN/Aadhaar/OTP/bank/contact info). "
                "Please remove any personal information and ask a general, factual question about the schemes."
            ),
            citation_url=None,
            last_updated_utc_date=None,
            llm_used=False,
            llm_error=None,
        )

    # Obvious out-of-scope entities (keep minimal; do not overreach)
    if re.search(r"\b(ceo|founder|headquarters|customer care number|helpline)\b", query, re.IGNORECASE):
        return GuardrailStructured(
            label=QueryLabel.OUT_OF_SCOPE,
            answer_text="I can only answer factual questions about the 17 allowlisted mutual fund scheme pages in this project.",
            citation_url=None,
            last_updated_utc_date=None,
            llm_used=False,
            llm_error=None,
        )

    if label in (QueryLabel.ADVISORY, QueryLabel.COMPARISON):
        # Phase 3 allows optional one URL, but user asked: for personal info/unknown we attach no URL.
        # For advisory/comparison, we still refuse; keep response URL-free by default.
        return GuardrailStructured(
            label=label,
            answer_text="I can’t provide investment advice or comparisons. If you ask for a specific factual field (expense ratio, exit load, benchmark, etc.), I can answer from the indexed corpus.",
            citation_url=None,
            last_updated_utc_date=None,
            llm_used=False,
            llm_error=None,
        )

    if label == QueryLabel.PERFORMANCE_HISTORY:
        return GuardrailStructured(
            label=label,
            answer_text="I can’t provide numeric performance/returns or rankings. If you ask about factual scheme details (expense ratio, exit load, benchmark, lock-in, etc.), I can answer from the indexed corpus.",
            citation_url=None,
            last_updated_utc_date=None,
            llm_used=False,
            llm_error=None,
        )

    # Factual path: call Phase 2; if no grounded hit → UNKNOWN (NO URL)
    res: AnswerResult = answer_query(
        query=query,
        chunks_root=chunks_root,
        registry_latest_path=registry_latest_path,
        top_k=5,
        scheme_filter=scheme_filter,
    )

    if not res.citation_url:
        return GuardrailStructured(
            label=QueryLabel.UNKNOWN,
            answer_text=res.answer_text,
            citation_url=None,
            last_updated_utc_date=res.last_updated_utc_date,
            llm_used=False,
            llm_error=None,
        )

    if use_groq:
        # For PERSONAL_INFO/UNKNOWN/OUT_OF_SCOPE we already returned above, so here we may safely generate.
        # Ground using the most relevant retrieved snippet(s) but keep it small.
        snippet = "\n".join([h.text[:800] for h in res.hits[:2]])
        try:
            ans_text = _groq_generate_answer_text(
                query=query,
                grounded_snippet=snippet,
                model=groq_model,
            )
            return GuardrailStructured(
                label=QueryLabel.FACTUAL_MF,
                answer_text=ans_text,
                citation_url=res.citation_url,
                last_updated_utc_date=res.last_updated_utc_date,
                llm_used=True,
                llm_error=None,
            )
        except GroqError as e:
            return GuardrailStructured(
                label=QueryLabel.FACTUAL_MF,
                answer_text=res.answer_text,
                citation_url=res.citation_url,
                last_updated_utc_date=res.last_updated_utc_date,
                llm_used=False,
                llm_error=str(e),
            )

    return GuardrailStructured(
        label=QueryLabel.FACTUAL_MF,
        answer_text=res.answer_text,
        citation_url=res.citation_url,
        last_updated_utc_date=res.last_updated_utc_date,
        llm_used=False,
        llm_error=None,
    )

