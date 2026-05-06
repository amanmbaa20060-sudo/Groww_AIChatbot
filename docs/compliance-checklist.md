# Phase 0 compliance checklist

Use this as a sign-off gate before starting Phase 1 ingestion. Check each item when true.

## Corpus and allowlist

- [ ] `corpus/url_manifest.yaml` exists and `python scripts/validate_manifest.py` exits with code 0.
- [ ] Exactly **17** schemes; each `groww_scheme_url` is **HTTPS** and host is `groww.in` (no `www.`, no query string).
- [ ] Every URL matches `docs/phase-wise-architecture.md` §3.1 **character-for-character**.
- [ ] Each row has `scheme_id`, `slug`, `display_name`, `coarse_category`, `source_type: groww_scheme_page`.
- [ ] `closed_corpus: true` is present and understood: **no** extra URLs in fetchers, index, or citations without manifest version bump and architecture update.

## Governance documents

- [ ] `docs/content-policy.md` reviewed for alignment with facts-only and manifest-only links.
- [ ] `docs/last-updated-policy.md` reviewed; footer semantics agreed for Phase 2 implementation.
- [ ] `docs/edge-cases-phase-0.md` skimmed; known manifest URL edge cases acknowledged.

## Privacy (design-level for later phases)

- [ ] No requirement to collect PAN, Aadhaar, account numbers, OTPs, email, or phone for the FAQ flow (per problem statement).

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Owner | | | |
| Reviewer | | | |
