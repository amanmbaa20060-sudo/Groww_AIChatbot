# Edge Cases — Phase 2 (Retrieval and Grounded Generation)

Companion to [phase-wise-architecture.md](phase-wise-architecture.md) §5. Covers retrieval, LLM generation, citation enforcement, and the **≤3 sentences + exactly one §3.1 URL** contract.

---

## Retrieval

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Zero hits** | Query embedding far from all chunks. | Return “no grounded answer” + optional single §3.1 link for user-selected scheme; do not hallucinate. |
| **Wrong scheme top-1** | “HDFC liquid” retrieves chunks from another debt fund. | Metadata filter by resolved `scheme_id`; MMR to diversify if needed. |
| **Contradictory chunks** | Stale exit load vs current block both retrieved. | Prefer chunk with newer date on page if extractable; else lowest rank / human QA flag. |
| **Query rewrite over-expands** | Rule turns “TER” into noisy expansion hurting recall. | Disable or narrow rewrite for short queries; measure on golden set. |
| **Hybrid BM25 ties** | Many chunks score equally on keyword. | Tie-break by recency metadata or vector score. |
| **User asks multi-part** | “Expense ratio and exit load and benchmark?” | Still one answer: prioritize primary intent or split turns in UI policy; never exceed three sentences without product decision. |

---

## Generation (LLM)

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Fourth sentence sneaks in** | Model adds disclaimer sentence. | Post-process sentence count; strip or regenerate with stricter prompt. |
| **Markdown link + bare URL** | Two URLs pass naive regex (“[text](url)” and same url repeated). | Count unique §3.1 URLs; require exactly one. |
| **Paraphrase without numbers** | User asked for minimum SIP; model says “low minimum” without ₹ value. | Validator checks presence of key entities from retrieved span or re-prompt. |
| **Language mix** | Hinglish query → English answer OK, but model drifts to Hindi only. | Language policy in prompt; default English for this project unless scope changes. |

---

## Citations

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Citation URL not in context** | Model cites correct path but chunk context omitted that URL string. | Reject; regenerate with forced `[source_url]` in context. |
| **www vs non-www** | Model outputs `https://www.groww.in/...` while manifest is `https://groww.in/...`. | Normalize allowed URLs in validator to match §3.1 canonical form. |
| **Relative link** | `/mutual-funds/...` only. | Expand using known host **only** if path matches a §3.1 path; else reject. |

---

## Footer (“Last updated”)

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Footer missing** | Model omits required line. | Template append from batch metadata, not model free-text. |
| **Placeholder date** | Model prints “today” incorrectly. | Inject date from server or ingestion metadata in template. |

---

## Fallback path (validation failure)

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Which §3.1 URL to show** | Multiple schemes mentioned; validation failed. | Deterministic rule: first resolved scheme from session, or ELSS page for tax-ish failures—document choice. |
