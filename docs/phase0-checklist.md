# Phase 0 checklist (closed corpus governance)

This repo implements **Phase 0** from `docs/phase-wise-architecture.md` as the “single source of truth” for what can be fetched, indexed, and cited.

## Artifacts

- **URL + scheme manifest**: `corpus/url_manifest.yaml`
  - Must contain **exactly 17** schemes.
  - Each scheme must have:
    - `scheme_id`, `slug`, `display_name`, `coarse_category`, `groww_scheme_url`, `source_type`
  - Every `groww_scheme_url` must match **exactly** one of the 17 URLs in `docs/phase-wise-architecture.md` §3.1.
  - `closed_corpus: true` must be set.

- **Manifest validator**: `scripts/validate_manifest.py`
  - Enforces the **exact** allowlist of 17 URLs.
  - Enforces `amc.id == hdfc_mutual_fund` and `source_type == groww_scheme_page`.

- **Runtime allowlist enforcement**:
  - `app/corpus/manifest.py` loads the allowlisted URL set from `corpus/url_manifest.yaml`.
  - `app/guardrails/phase3.py` refuses to emit a citation URL unless it is allowlisted.

## How to validate Phase 0

From repo root:

```bash
python scripts/validate_manifest.py
```

Expected: `OK: corpus/url_manifest.yaml (17 schemes, closed corpus).`

