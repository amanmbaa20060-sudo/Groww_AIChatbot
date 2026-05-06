# Edge Cases — Phase 0 (Scope, Corpus, and Governance)

Companion to [phase-wise-architecture.md](phase-wise-architecture.md) §3. Covers manifest, allowlist, policy, and “last updated” decisions before build.

---

## Corpus and URL manifest

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **URL drift** | Groww changes path slugs or adds redirects; bookmarks use old paths. | Treat manifest as source of truth; CI fails if fetch returns non-200 or final URL not in §3.1; version manifest on change. |
| **HTTP vs HTTPS** | User or script uses `http://groww.in/...`. | Normalize to `https://` in manifest and validators; reject non-HTTPS in allowlist. |
| **Trailing slash / query params** | `.../hdfc-liquid-fund-direct-growth/` or `?utm=...`. | Canonicalize to exact §3.1 strings for storage and citation checks. |
| **Duplicate scheme intent** | Two rows accidentally point at the same slug or one scheme listed twice. | Manifest lint: unique URLs; unique internal `scheme_id`. |
| **Scheme rename** | Display name on site changes; internal slug unchanged. | Metadata table tracks `display_name` separately from URL; do not fork URLs without architecture update. |
| **Missing scheme in metadata** | URL exists in manifest but no category / tags for filters in later phases. | Block Phase 1 until every row has `scheme_id`, display name, coarse category. |

---

## Allowlist and governance

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **“Just one more URL”** | Stakeholder asks to add HDFC FAQ or AMFI without doc change. | Per architecture: reject until §3.1 is formally revised and signed off. |
| **Subdomain** | Content on `www.groww.in` vs `groww.in`. | Allowlist only full URLs as in architecture; fetcher must match after redirect resolution. |
| **ISIN / code in manifest** | Optional ISIN added incorrectly (typo, wrong scheme). | Validate format offline; cross-check one fact per scheme against page. |

---

## Content policy and dates

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Ambiguous “last updated”** | Footer uses crawl time but page shows different NAV date. | Document single rule (e.g. ingestion batch UTC date); state limitation in user-facing copy if needed. |
| **Performance vs facts** | Policy says no return numbers but examples blur line (e.g. “historic returns” on page). | Policy doc: list allowed paraphrases vs forbidden numeric performance claims. |
| **Conflicting policies** | Problem statement asks for educational regulator links; project locks links to §3.1 only. | Phase 0 sign-off records precedence: **this repo** follows closed corpus; refusal link rules as in architecture §6. |

---

## Deliverables and exit

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Partial checklist** | Compliance checklist “mostly done”. | Exit criteria are binary: manifest exact, allowlist exact, no waiver without recorded exception. |
| **Manifest in code vs file** | URLs duplicated in Python and YAML and they diverge. | Single manifest file; code imports or validates against it at startup. |
