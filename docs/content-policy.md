# Content policy (Phase 0)

Aligned with `docs/problemstatement.md` and `docs/phase-wise-architecture.md`. **This repository** restricts corpus and user-visible links to `corpus/url_manifest.yaml` (§3.1 equivalent).

## Allowed assistant behaviour

- Answer **factual**, verifiable questions about the seventeen HDFC schemes (e.g. expense ratio, exit load, minimum SIP, benchmark name, risk label as shown on source pages, ELSS lock-in description, how to interpret fields that appear on the scheme page).
- Responses: **maximum 3 sentences** for factual answers (per problem statement).
- **Exactly one** citation URL per factual answer, and that URL **must** be one of the `groww_scheme_url` values in `corpus/url_manifest.yaml`.
- Footer line (per problem statement): `Last updated from sources: <date>` — date semantics in `docs/last-updated-policy.md`.
- LLM calls (Phase 2+): Use **Groq** (credentials via env var such as `GROQ_API_KEY`; never committed).

## Forbidden outputs

- Investment advice, opinions, or recommendations (“should I buy”, “is it good”, “where should I put ₹X”).
- Comparisons that rank or prefer one fund over another (“which is better”).
- **Numeric performance storytelling** (returns, CAGR, “would have become”, rankings). For performance-related user queries, do not state numbers; at most a short pointer plus **one** allowed scheme URL (see architecture Phase 3).
- Third-party blogs, aggregators, or any URL **not** in the manifest.
- Invented or unverifiable numbers not supported by retrieved chunks.

## Refusal and edge routing

- Advisory / comparative / out-of-domain queries → polite refusal; any optional link **must** still be a manifest URL (see `docs/edge-cases-phase-3.md`).

## Change control

Updates to allowed topics or sentence rules require a doc revision and version note in `corpus/url_manifest.yaml` or this file’s git history.
