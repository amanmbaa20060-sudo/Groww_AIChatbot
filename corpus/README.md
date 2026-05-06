# Corpus (Phase 0)

This folder holds the **closed corpus** definition for the Mutual Fund FAQ assistant.

## Files

| File | Purpose |
|------|---------|
| `url_manifest.yaml` | Single source of truth: AMC, **exactly 17** Groww scheme URLs (`groww_scheme_url`), `scheme_id`, `slug`, `display_name`, `coarse_category`, `source_type`. |

## Schema (`schemes[]`)

Each entry includes:

- `scheme_id` — stable internal identifier (snake_case).
- `slug` — Groww path segment under `/mutual-funds/`.
- `display_name` — Human-readable scheme name.
- `coarse_category` — High-level bucket for filters and analytics (not a regulatory label).
- `groww_scheme_url` — Full HTTPS URL; **must** match the allowlist in `docs/phase-wise-architecture.md` §3.1 character-for-character.
- `source_type` — Always `groww_scheme_page` for this project.
- `isin` — Optional; `null` until filled from official data (non-PII).

## Validation

From the repository root:

```bash
pip install -r requirements.txt
python scripts/validate_manifest.py
```

Phase 1+ ingestion must read **only** URLs from this manifest.
